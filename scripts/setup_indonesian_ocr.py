"""Install optional OCR languages in the ignored workspace cache on Windows."""
import hashlib
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]

def main():
    root=ROOT/'models'/'tessdata';root.mkdir(parents=True,exist_ok=True)
    for language in ('eng','ind','hin'):
        target=root/(language+'.traineddata')
        if not target.exists():
            response=requests.get(f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{language}.traineddata',timeout=90)
            response.raise_for_status(); temporary=target.with_suffix('.tmp'); temporary.write_bytes(response.content);temporary.replace(target)
        print(language,hashlib.sha256(target.read_bytes()).hexdigest())
    print('Restart the app. OCR auto-detects this workspace language cache. Tesseract itself must already be installed.')

if __name__=='__main__': main()
