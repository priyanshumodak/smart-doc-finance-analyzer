import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from notebooks.finetune_layoutlmv3 import load_annotations

class TrainingAnnotationTests(unittest.TestCase):
    def test_unannotated_dataset_requires_explicit_weak_label_opt_in(self):
        with tempfile.TemporaryDirectory() as folder, patch('notebooks.finetune_layoutlmv3.run_ocr') as ocr:
            with self.assertRaisesRegex(ValueError,'allow_weak_labels'):
                load_annotations(Path(folder))
            ocr.assert_not_called()

    def test_supplied_annotation_splits_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            records=[{'id':str(i),'split':split} for i,split in enumerate(['train','train','validation','test'])]
            (root/'annotations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            result=load_annotations(root)
            self.assertEqual([r['id'] for r in result['test']],['3'])
            self.assertEqual([r['id'] for r in result['validation']],['2'])

if __name__=='__main__': unittest.main()
