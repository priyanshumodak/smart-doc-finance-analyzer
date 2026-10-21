"""Streamlit Community Cloud entrypoint: no external backend service needed."""
import os
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
# This entrypoint is always a public, OCR-only demonstration.
os.environ['APP_RUNTIME'] = 'standalone'
os.environ['PUBLIC_DEMO_MODE'] = '1'
os.environ['EXTRACTION_MODE'] = 'ocr'
os.environ['TOKEN_MODEL_PATH'] = ''
os.environ.setdefault('MAX_UPLOAD_MB','5')
os.environ.setdefault('MAX_PAGES','3')
os.environ.setdefault('MAX_IMAGE_PIXELS','10000000')
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
os.environ.setdefault('DATABASE_PATH',str(Path(tempfile.gettempdir())/'finance-streamlit-demo'/'documents.sqlite3'))
runpy.run_path(str(ROOT/'frontend'/'streamlit_app.py'),run_name='__main__')
