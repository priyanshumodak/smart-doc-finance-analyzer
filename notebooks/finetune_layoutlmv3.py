"""Train/evaluate LayoutLMv3 using exact synthetic labels or OCR-aligned weak labels."""
import argparse
import json
import os
import random
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from transformers import AutoProcessor, AutoModelForTokenClassification, Trainer, TrainingArguments, TrainerCallback, set_seed
from seqeval.metrics import precision_score, recall_score, f1_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.ocr_engine import run_ocr, tokens_to_dicts
from backend.validation import money
from backend.token_windows import word_windows

FIELDS=['vendor_name','bill_to','invoice_number','invoice_date','due_date','gstin','pan','place_of_supply',
        'subtotal','tax_amount','total_amount','cgst','sgst','igst']
LABEL_LIST=['O']+[f'{prefix}-{field.upper()}' for field in FIELDS for prefix in ('B','I')]
LABEL2ID={label:index for index,label in enumerate(LABEL_LIST)}
ID2LABEL={index:label for label,index in LABEL2ID.items()}

def auto_label(words,record):
    import re
    def norm(value):
        parsed=money(value)
        return str(parsed.normalize()) if parsed is not None else re.sub(r'\s+',' ',str(value)).casefold().strip(': ')
    labels=['O']*len(words)
    for field in FIELDS:
        value=record.get(field)
        if value is None:
            continue
        parts=str(value).split()
        for start in range(len(words)-len(parts)+1):
            if all(norm(a)==norm(b) for a,b in zip(words[start:start+len(parts)],parts)) and all(label=='O' for label in labels[start:start+len(parts)]):
                labels[start]='B-'+field.upper()
                for index in range(1,len(parts)):
                    labels[start+index]='I-'+field.upper()
                break
    return labels

def load_annotations(root,allow_weak_labels=False):
    source=root/'annotations.jsonl'
    if source.exists():
        rows=[json.loads(line) for line in source.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    else:
        if not allow_weak_labels:
            raise ValueError('Missing annotations.jsonl. Supply verified word boxes/BIO labels or explicitly opt into --allow_weak_labels for a weak-label experiment.')
        rows=[]
        records=json.loads((root/'ground_truth.json').read_text(encoding='utf-8-sig'))
        for index,record in enumerate(records):
            path=root/record['image_path']
            with Image.open(path) as image:
                tokens=tokens_to_dicts(run_ocr(image.convert('RGB')))
            words=[token['text'] for token in tokens]
            if words:
                rows.append({'id':record.get('id',path.stem),'image_path':record['image_path'],
                             'words':words,'boxes':[token['norm_box'] for token in tokens],
                             'labels':auto_label(words,record),'split':record.get('split'),
                             'annotation_source':'ocr_weak_labels'})
    if not rows or len(rows)<4:
        raise ValueError('At least four annotated examples are required')
    if not all(row.get('split') in ('train','validation','test') for row in rows):
        random.Random(42).shuffle(rows)
        first,second=int(.7*len(rows)),int(.85*len(rows))
        for index,row in enumerate(rows):
            row['split']='train' if index<first else ('validation' if index<second else 'test')
    return {split:[row for row in rows if row['split']==split] for split in ('train','validation','test')}

class InvoiceDataset(Dataset):
    def __init__(self,root,rows,processor,max_length):
        self.root,self.processor,self.max_length=root,processor,max_length
        self.rows=[]
        for row in rows:
            for start,end in word_windows(row['words'],row['boxes'],processor.tokenizer,max_length,row['labels']):
                self.rows.append({**row,'words':row['words'][start:end],'boxes':row['boxes'][start:end],
                                  'labels':row['labels'][start:end],'word_window':[start,end]})
    def __len__(self):
        return len(self.rows)
    def __getitem__(self,index):
        row=self.rows[index]
        with Image.open(self.root/row['image_path']) as source:
            image=source.convert('RGB')
        encoding=self.processor(image,row['words'],boxes=row['boxes'],
                                word_labels=[LABEL2ID[label] for label in row['labels']],
                                truncation=True,padding='max_length',max_length=self.max_length,return_tensors='pt')
        represented={word for word in encoding.word_ids(batch_index=0) if word is not None}
        if len(represented)!=len(row['words']):
            raise ValueError(f"{row['id']} exceeds token context. Increase --max_length up to 512 or chunk the input.")
        return {key:value.squeeze(0) for key,value in encoding.items()}

def compute_metrics(prediction):
    logits,labels=prediction
    predicted=np.argmax(logits,axis=-1)
    gold=[[ID2LABEL[int(label)] for label in row if label!=-100] for row in labels]
    guesses=[[ID2LABEL[int(guess)] for guess,label in zip(p_row,l_row) if label!=-100] for p_row,l_row in zip(predicted,labels)]
    return {'precision':precision_score(gold,guesses,zero_division=0),'recall':recall_score(gold,guesses,zero_division=0),
            'f1':f1_score(gold,guesses,zero_division=0)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data_dir',required=True)
    parser.add_argument('--allow_weak_labels',action='store_true',help='Explicitly allow experimental OCR-matched weak labels when annotations are absent')
    parser.add_argument('--reviewed_data',help='Train-only supplement from export_reviewed_dataset.py')
    parser.add_argument('--output_dir',default='models/layoutlmv3-indian-invoices')
    parser.add_argument('--model_name',default='microsoft/layoutlmv3-base')
    parser.add_argument('--epochs',type=int,default=3)
    parser.add_argument('--target_validation_f1',type=float,help='Optional predeclared validation target for early stopping')
    parser.add_argument('--batch_size',type=int,default=1)
    parser.add_argument('--max_steps',type=int,default=-1)
    parser.add_argument('--train_limit',type=int)
    parser.add_argument('--eval_limit',type=int)
    parser.add_argument('--max_length',type=int,default=512,choices=[256,512])
    parser.add_argument('--cpu_threads',type=int,default=4)
    parser.add_argument('--freeze_backbone',action='store_true',help='Train classifier head only; efficient baseline, not full fine-tuning')
    parser.add_argument('--evaluate_only',action='store_true')
    parser.add_argument('--gradient_checkpointing',action='store_true')
    parser.add_argument('--resume_from_checkpoint')
    args=parser.parse_args()
    torch.set_num_threads(args.cpu_threads)
    set_seed(42)
    root=Path(args.data_dir).resolve()
    output=Path(args.output_dir)
    output.mkdir(parents=True,exist_ok=True)
    split=load_annotations(root,args.allow_weak_labels)
    reviewed_count=0
    if args.reviewed_data:
        review_root=Path(args.reviewed_data).resolve()
        rows=[json.loads(line) for line in (review_root/'annotations.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        reserved=set()
        for name in ('validation','test'):
            source=root/f'{name}.json'
            if source.exists():
                reserved.update(str(row.get('invoice_number')) for row in json.loads(source.read_text(encoding='utf-8-sig')) if row.get('invoice_number'))
        for row in rows:
            if row.get('split')!='train' or not row.get('ready_for_training') or row.get('reserved_evaluation_document'):
                raise ValueError('Reviewed supplement contains unapproved, unaligned or reserved examples')
            if str(row.get('fields',{}).get('invoice_number')) in reserved:
                raise ValueError('Reviewed supplement overlaps reserved invoice numbers')
            split['train'].append({**row,'image_path':str((review_root/row['image_path']).resolve())})
            reviewed_count+=1
    if args.train_limit:
        split['train']=split['train'][:args.train_limit]
    if args.eval_limit:
        split['validation']=split['validation'][:args.eval_limit]
        split['test']=split['test'][:args.eval_limit]
    if any(not split[name] for name in split):
        raise ValueError('Train, validation and test must all be nonempty')
    processor=AutoProcessor.from_pretrained(args.model_name,apply_ocr=False)
    model=AutoModelForTokenClassification.from_pretrained(args.model_name,num_labels=len(LABEL_LIST),
                                                          id2label=ID2LABEL,label2id=LABEL2ID)
    if args.freeze_backbone:
        for parameter in model.base_model.parameters():
            parameter.requires_grad=False
    checkpointing_mode='off'
    trainer_checkpointing=args.gradient_checkpointing
    if args.gradient_checkpointing and not model.supports_gradient_checkpointing:
        # Transformers 4.42 LayoutLMv3 exposes encoder checkpointing but its
        # top-level model does not advertise the capability. Use that verified
        # encoder path without changing the installed library or model weights.
        from functools import partial
        from torch.utils.checkpoint import checkpoint
        encoder=getattr(model.base_model,'encoder',None)
        if encoder is None or not hasattr(encoder,'gradient_checkpointing'):
            raise ValueError('This model has no compatible checkpointing encoder')
        encoder.gradient_checkpointing=True
        encoder._gradient_checkpointing_func=partial(checkpoint,use_reentrant=False)
        trainer_checkpointing=False
        checkpointing_mode='layoutlmv3_encoder_compat'
    elif args.gradient_checkpointing:
        checkpointing_mode='native'
    datasets={name:InvoiceDataset(root,rows,processor,args.max_length) for name,rows in split.items()}
    training=TrainingArguments(output_dir=str(output),num_train_epochs=args.epochs,max_steps=args.max_steps,
                               per_device_train_batch_size=args.batch_size,per_device_eval_batch_size=args.batch_size,
                               eval_strategy='epoch',save_strategy='epoch',logging_steps=10,save_total_limit=1,
                               learning_rate=1e-3 if args.freeze_backbone else 3e-5,load_best_model_at_end=True,
                               metric_for_best_model='f1',greater_is_better=True,report_to=[],seed=42,disable_tqdm=True,
                               dataloader_num_workers=0,fp16=torch.cuda.is_available(),remove_unused_columns=False,
                               gradient_checkpointing=trainer_checkpointing)
    class ValidationTarget(TrainerCallback):
        def on_evaluate(self,arguments,state,control,metrics=None,**kwargs):
            if args.target_validation_f1 is not None and (metrics or {}).get('eval_f1',-1)>=args.target_validation_f1:
                control.should_training_stop=True
                control.should_save=True
            return control
    trainer=Trainer(model=model,args=training,train_dataset=datasets['train'],eval_dataset=datasets['validation'],
                    compute_metrics=compute_metrics,callbacks=[ValidationTarget()])
    manifest_path=root/'manifest.json'
    provenance=json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.exists() else {}
    metadata={'dataset_provenance':{key:provenance.get(key) for key in ('name','source','license','source_revision','real_documents')},'base_model':args.model_name,'train_mode':'classifier_head_only' if args.freeze_backbone else 'full_finetune',
              'cuda':torch.cuda.is_available(),'gradient_checkpointing':checkpointing_mode,'reviewed_training_examples':reviewed_count,'split_counts':{name:len(rows) for name,rows in split.items()},
              'model_windows':{name:len(dataset) for name,dataset in datasets.items()},'max_length':args.max_length,'dataset_path':str(root),'max_steps':args.max_steps,'epochs':args.epochs,'target_validation_f1':args.target_validation_f1,'seed':42,
              'annotation_sources':sorted({row.get('annotation_source','unknown') for rows in split.values() for row in rows}),
              'limitations':'Token/entity metrics use supplied words and labels, not OCR outputs. Dataset provenance and mapped label coverage determine the supported claims.'}
    (output/'training_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata,indent=2),flush=True)
    if not args.evaluate_only:
        trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
        metadata.update({'completed_optimizer_steps':trainer.state.global_step,'completed_epochs':trainer.state.epoch,
                         'selected_checkpoint':trainer.state.best_model_checkpoint,'best_validation_f1':trainer.state.best_metric,
                         'stop_reason':'Predeclared validation target reached' if args.target_validation_f1 is not None and trainer.state.best_metric is not None and trainer.state.best_metric>=args.target_validation_f1 else 'Configured training budget completed'})
        (output/'training_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        trainer.save_model(str(output))
        processor.save_pretrained(str(output))
    for name in ('validation','test'):
        metrics=trainer.evaluate(datasets[name],metric_key_prefix=name)
        trainer.save_metrics(name,metrics)
        print(name,json.dumps(metrics,indent=2),flush=True)
    print(f'Completed. Set TOKEN_MODEL_PATH={output.resolve()} to use this checkpoint.',flush=True)

if __name__=='__main__':
    main()
