"""Transactional SQLite documents; imports v0.5 JSON once without deleting it."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sqlite3

@contextmanager
def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    try:
        db.execute('PRAGMA busy_timeout=15000')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS documents (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        with db:
            yield db
    finally:
        db.close()

def location(path):
    path = Path(path).resolve()
    return path.parent / 'tb-documents.sqlite3', path.name

def save_document(path, value):
    database, key = location(path)
    with connect(database) as db:
        db.execute('INSERT INTO documents VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   (key, json.dumps(value, ensure_ascii=False)))

def load_document(path, default):
    database, key = location(path)
    if database.is_file():
        with connect(database) as db:
            row = db.execute('SELECT value FROM documents WHERE key=?', (key,)).fetchone()
        if row:
            return json.loads(row[0])
    path = Path(path)
    try:
        if path.stat().st_size > 40 * 1024 * 1024:
            return copy.deepcopy(default)
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return copy.deepcopy(default)
    save_document(path, value)
    return value
