import json
from pathlib import Path
cells=[]
def md(text):
    cells.append({'cell_type':'markdown','metadata':{},'source':text.splitlines(True)})
def code(text):
    cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':text.splitlines(True)})
md('# Train the Finance Analyzer on Google Colab\n\nSelect **Runtime → Change runtime type → GPU**. Upload the source/data ZIP produced with `python scripts/package_project.py --dataset`. LayoutLMv3 is CC-BY-NC-SA-4.0; this notebook is for academic/noncommercial project use. Training on synthetic data does not establish real-world accuracy.')
code('from google.colab import files\nuploaded = files.upload()\narchive = next(name for name in uploaded if name.endswith(".zip"))\nimport zipfile, pathlib, os\nproject = pathlib.Path("/content/finance-analyzer")\nproject.mkdir(exist_ok=True)\nwith zipfile.ZipFile(archive) as bundle:\n    root = project.resolve()\n    for name in bundle.namelist():\n        if not (root / name).resolve().is_relative_to(root):\n            raise ValueError("Unsafe archive path")\n    bundle.extractall(project)\nos.chdir(project)')
code('!apt-get -qq update && apt-get -qq install -y tesseract-ocr tesseract-ocr-hin poppler-utils fonts-dejavu-core\n!pip -q install transformers==4.42.4 accelerate==0.32.1 seqeval==1.2.2 Pillow==10.4.0 pytesseract==0.3.10 numpy==1.26.4\nimport torch\nprint("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU; select a GPU runtime")\nassert torch.cuda.is_available(), "Enable a GPU runtime before full training"')
code('from pathlib import Path\nif not Path("data/training_indian_invoices/manifest.json").exists():\n    !python data/build_training_dataset.py --n 1000 --out data/training_indian_invoices')
md('## Full training\n\nThis uses all 700 training images, 150 validation images, and 150 held-out test images. Validation selects the checkpoint; test metrics are reported after training. If a modern Colab image has incompatible preinstalled libraries, use a fresh runtime and rerun setup.')
code('!python notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --output_dir models/layoutlmv3-indian-invoices --epochs 3 --batch_size 1 --gradient_checkpointing')
code('import json\nfor split in ["validation", "test"]:\n    print(split, json.loads(Path(f"models/layoutlmv3-indian-invoices/{split}_results.json").read_text()))')
code('import shutil\nshutil.make_archive("trained-layoutlmv3", "zip", "models/layoutlmv3-indian-invoices")\nfiles.download("trained-layoutlmv3.zip")')
md('Extract the downloaded checkpoint into `models/layoutlmv3-indian-invoices` on your laptop. Restart with `scripts/start.ps1 -Mode token`. Keep the model files and the JSON metrics together for your report.')
# Convert intentional literal newlines in sources into actual notebook line breaks.
for cell in cells:
    text=''.join(cell['source']).replace('\\n','\n')
    cell['source']=text.splitlines(True)
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}
Path('notebooks/train_on_colab.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
