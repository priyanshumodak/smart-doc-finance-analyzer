"""SQLite history with atomic writes and parameterised filtering."""
import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def connect():
    path = Path(os.getenv('DATABASE_PATH', 'storage/documents.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT, created_at TEXT, status TEXT, result TEXT)')
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def save(result):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?)',
                   (result['id'],result['filename'],result['created_at'],result['status'],json.dumps(result,ensure_ascii=False)))

def get(document_id):
    with connect() as db:
        row = db.execute('SELECT result FROM documents WHERE id=?', (document_id,)).fetchone()
    return json.loads(row['result']) if row else None

def listing(query='', limit=50, offset=0):
    with connect() as db:
        rows = db.execute('SELECT id,filename,created_at,status FROM documents WHERE filename LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                          ('%'+query+'%',limit,offset)).fetchall()
    return [dict(row) for row in rows]



def preview_path(document_id,page):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}',document_id) or int(page)<1:
        raise ValueError('Invalid preview identity')
    root=Path(os.getenv('DATABASE_PATH','storage/documents.sqlite3')).parent/'previews'/document_id
    return root/f'{int(page)}.png'


def save_preview(document_id,page,image):
    path=preview_path(document_id,page)
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path,format='PNG')


def save_training_review(record):
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS training_reviews (document_id TEXT, page INTEGER, record TEXT, PRIMARY KEY(document_id,page))')
        db.execute('INSERT OR REPLACE INTO training_reviews VALUES (?,?,?)',
                   (record['document_id'],record['page'],json.dumps(record,ensure_ascii=False)))


def training_reviews():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS training_reviews (document_id TEXT, page INTEGER, record TEXT, PRIMARY KEY(document_id,page))')
        rows=db.execute('SELECT record FROM training_reviews').fetchall()
    return [json.loads(row['record']) for row in rows]


def invalidate_training_review(document_id,page):
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS training_reviews (document_id TEXT, page INTEGER, record TEXT, PRIMARY KEY(document_id,page))')
        db.execute('DELETE FROM training_reviews WHERE document_id=? AND page=?',(document_id,page))
