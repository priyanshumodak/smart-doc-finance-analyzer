FROM python:3.11-slim
ENV OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PUBLIC_DEMO_MODE=1 EXTRACTION_MODE=ocr OCR_LANGUAGES=eng+hin MAX_UPLOAD_MB=10 MAX_PAGES=5 DATABASE_PATH=/tmp/finance-demo/documents.sqlite3 BACKEND_URL=http://127.0.0.1:8000
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin poppler-utils libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements-ocr.txt frontend/requirements.txt /tmp/requirements/
RUN pip install --no-cache-dir -r /tmp/requirements/requirements-ocr.txt -r /tmp/requirements/requirements.txt
COPY backend /app/backend
COPY frontend /app/frontend
COPY sample_docs/demo_digital_invoice.pdf sample_docs/demo_continued_invoice.pdf sample_docs/demo_invoice.png sample_docs/demo_bank_statement.png sample_docs/demo_financial_report.pdf /app/sample_docs/
COPY sample_docs/real_receipts /app/sample_docs/real_receipts
COPY scripts/serve_public.py /app/scripts/serve_public.py
RUN useradd --create-home appuser
USER appuser
EXPOSE 8501
CMD ["python", "scripts/serve_public.py"]
