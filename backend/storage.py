"""SQLite history with atomic writes and parameterised filtering."""
from threading import Lock

_schema_lock = Lock()

from contextvars import ContextVar

visitor = ContextVar("visitor", default="local")

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
    with _schema_lock:
        connection.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT, created_at TEXT, status TEXT, result TEXT)')
        columns = {row[1] for row in connection.execute('PRAGMA table_info(documents)')}
        if 'owner' not in columns:
            connection.execute("ALTER TABLE documents ADD COLUMN owner TEXT NOT NULL DEFAULT 'local'")
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def save(result):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO documents (id,filename,created_at,status,result,owner) VALUES (?,?,?,?,?,?)',
                   (result['id'],result['filename'],result['created_at'],result['status'],json.dumps(result,ensure_ascii=False),visitor.get()))

def get(document_id):
    with connect() as db:
        row = db.execute('SELECT result FROM documents WHERE id=? AND owner=?', (document_id,visitor.get())).fetchone()
    return json.loads(row['result']) if row else None

def listing(query='', limit=50, offset=0):
    with connect() as db:
        rows = db.execute('SELECT id,filename,created_at,status FROM documents WHERE filename LIKE ? AND owner=? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                          ('%'+query+'%',visitor.get(),limit,offset)).fetchall()
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


def clear_visitor():
    import shutil
    with connect() as db:
        ids = [row['id'] for row in db.execute('SELECT id FROM documents WHERE owner=?', (visitor.get(),))]
        for identity in ids:
            shutil.rmtree(preview_path(identity,1).parent, ignore_errors=True)
            db.execute('CREATE TABLE IF NOT EXISTS training_reviews (document_id TEXT, page INTEGER, record TEXT, PRIMARY KEY(document_id,page))')
            db.execute('DELETE FROM training_reviews WHERE document_id=?', (identity,))
        db.execute('DELETE FROM documents WHERE owner=?', (visitor.get(),))
    return len(ids)
