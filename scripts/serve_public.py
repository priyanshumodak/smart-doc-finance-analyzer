"""Supervise the internal API and public Streamlit server in one container."""
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.setdefault('PUBLIC_DEMO_MODE','1')
    os.environ.setdefault('EXTRACTION_MODE','ocr')
    os.environ['BACKEND_URL'] = 'http://127.0.0.1:8000'
    processes = []

    def stop(*args):
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *args: sys.exit(0))
    try:
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000']))
        for attempt in range(120):
            if processes[0].poll() is not None:
                raise RuntimeError('Extraction API exited during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2) as response:
                    import json
                    if not json.load(response)['ocr_available']:
                        raise RuntimeError('Tesseract is unavailable; check the server installation')
                break
            except OSError:
                time.sleep(.5)
        else:
            raise RuntimeError('Extraction API did not become ready')
        processes.append(subprocess.Popen([sys.executable,'-m','streamlit','run','frontend/streamlit_app.py',
            '--server.address=0.0.0.0','--server.port='+os.getenv('PORT','8501'),
            '--server.maxUploadSize='+os.getenv('MAX_UPLOAD_MB','10'),
            '--browser.gatherUsageStats=false','--server.headless=true']))
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        raise RuntimeError('A web application process exited; stopping both services')
    finally:
        stop()


if __name__ == '__main__':
    main()
