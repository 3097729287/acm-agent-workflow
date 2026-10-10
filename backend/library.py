"""Portable educational library. Markdown is content, SQLite is its storage."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import datetime as dt

SCHEMA = '''
CREATE TABLE IF NOT EXISTS library_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bundled_items(
 table_name TEXT NOT NULL, item_id TEXT NOT NULL, digest TEXT NOT NULL,
 PRIMARY KEY(table_name, item_id));
CREATE TABLE IF NOT EXISTS problems(
 id TEXT PRIMARY KEY, url TEXT, raw TEXT NOT NULL, encoded TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS problems_url ON problems(url);
CREATE TABLE IF NOT EXISTS problem_urls(
 url_key TEXT PRIMARY KEY, problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS solutions(
 problem_id TEXT PRIMARY KEY REFERENCES problems(id) ON DELETE CASCADE,
 markdown TEXT NOT NULL, source_path TEXT NOT NULL, images TEXT NOT NULL, digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS statements(problem_id TEXT PRIMARY KEY, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lectures(id TEXT PRIMARY KEY, content TEXT NOT NULL, digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS problem_lectures(
 problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
 lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, position INTEGER NOT NULL,
 PRIMARY KEY(problem_id, lecture_id));
'''

def source_fingerprint(directory):
    """Stable fingerprint of the text seed; merge_seed uses it instead of file bytes."""
    directory = Path(directory)
    digest = hashlib.sha256()
    for name in sorted(path.name for path in directory.glob('*.json')):
        digest.update(name.encode('utf-8'))
        digest.update(b'\x00')
        digest.update((directory / name).read_bytes())
    return digest.hexdigest()


class LibraryDatabase:
    def __init__(self, path, readonly=False):
        self.path = Path(path).resolve()
        self.readonly = readonly
        if readonly:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            with self.connection() as db:
                exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='library_meta'").fetchone()
                version = db.execute("SELECT value FROM library_meta WHERE key='schema'").fetchone() if exists else None
            if version and int(version[0]) < 3:
                self.backup('schema-migration')
        with self.connection() as db:
            db.executescript(SCHEMA)
            db.execute("INSERT INTO library_meta VALUES ('schema', '3') ON CONFLICT(key) DO UPDATE SET value='3'")
            db.execute("INSERT OR IGNORE INTO library_meta VALUES ('revision', '0')")
            self._rebuild_urls(db)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=15) if self.readonly else sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA busy_timeout=15000')
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def backup(self, label='before-upgrade'):
        directory = self.path.parent / 'backups'
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (self.path.stem + '-' + label + '-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
        with self.connection() as source:
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
                if destination.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('Library backup failed integrity check')
            finally:
                destination.close()
        return target

    def merge_seed(self, path, fingerprint=None):
        """Upgrade bundled content, preserving locally imported/edited rows and fetched statements."""
        path = Path(path).resolve()
        if fingerprint is None:
            fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
        if self.metadata().get('bundled_sha256') == fingerprint:
            return False
        seed = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        seed.row_factory = sqlite3.Row
        try:
            if seed.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Bundled library is corrupt')
            tables = {
                'problems': ('id', ['id', 'url', 'raw', 'encoded']),
                'lectures': ('id', ['id', 'content', 'digest']),
                'solutions': ('problem_id', ['problem_id', 'markdown', 'source_path', 'images', 'digest']),
                'statements': ('problem_id', ['problem_id', 'content']),
            }
            rows = {name: list(seed.execute('SELECT * FROM ' + name)) for name in tables}
            links = {}
            for row in seed.execute('SELECT * FROM problem_lectures ORDER BY problem_id,position'):
                links.setdefault(row['problem_id'], []).append(tuple(row))
            for row in rows['problems']:
                links.setdefault(row['id'], [])
        finally:
            seed.close()
        if self.rows():
            self.backup()
        digest = lambda value: hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            def previous(table, identity):
                row = db.execute('SELECT digest FROM bundled_items WHERE table_name=? AND item_id=?', (table, identity)).fetchone()
                return row[0] if row else None
            def remember(table, identity, checksum):
                db.execute('INSERT INTO bundled_items VALUES (?,?,?) ON CONFLICT(table_name,item_id) DO UPDATE SET digest=excluded.digest', (table, identity, checksum))
            for table, (key, columns) in tables.items():
                for row in rows[table]:
                    identity = row[key]
                    content = {column: row[column] for column in columns}
                    checksum = digest(content)
                    current = db.execute('SELECT * FROM ' + table + ' WHERE ' + key + '=?', (identity,)).fetchone()
                    existing = digest({column: current[column] for column in columns}) if current else None
                    if current is None or existing == previous(table, identity):
                        placeholders = ','.join('?' for _ in columns)
                        changes = ','.join(column + '=excluded.' + column for column in columns if column != key)
                        db.execute('INSERT INTO ' + table + ' (' + ','.join(columns) + ') VALUES (' + placeholders + ') ON CONFLICT(' + key + ') DO UPDATE SET ' + changes, tuple(content.values()))
                        remember(table, identity, checksum)
                    elif existing == checksum:
                        remember(table, identity, checksum)
            for identity, content in links.items():
                checksum = digest(content)
                current = [tuple(row) for row in db.execute('SELECT * FROM problem_lectures WHERE problem_id=? ORDER BY position', (identity,))]
                existing = digest(current)
                if existing == previous('problem_lectures', identity) or not current and previous('problem_lectures', identity) is None:
                    db.execute('DELETE FROM problem_lectures WHERE problem_id=?', (identity,))
                    db.executemany('INSERT INTO problem_lectures VALUES (?,?,?,?)', content)
                    remember('problem_lectures', identity, checksum)
                elif existing == checksum:
                    remember('problem_lectures', identity, checksum)
            for key, value in {'bundled_sha256': fingerprint, 'content_version': '0.6.0'}.items():
                db.execute('INSERT INTO library_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            db.execute("UPDATE library_meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            self._rebuild_urls(db)
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Library upgrade has broken references')
        return True

    @staticmethod
    def _rebuild_urls(db):
        from insights import canonical_url
        db.execute('DELETE FROM problem_urls')
        for row in db.execute('SELECT id,url FROM problems ORDER BY rowid').fetchall():
            key = canonical_url(row['url'])
            if key:
                db.execute('INSERT OR IGNORE INTO problem_urls VALUES (?,?)', (key, row['id']))

    def rows(self, raw=False):
        column = 'raw' if raw else 'encoded'
        with self.connection() as db:
            return [json.loads(row[0]) for row in db.execute(f'SELECT {column} FROM problems ORDER BY rowid')]

    def catalog(self):
        """Read list metadata and solution presence in one database snapshot.

        Catalog requests never need to load every solution body or open a
        connection for each problem. Content readers use solution() separately.
        """
        with self.connection() as db:
            rows = db.execute('SELECT p.*, EXISTS(SELECT 1 FROM solutions s WHERE s.problem_id=p.id) AS available '
                              'FROM problems p ORDER BY p.rowid')
            return [{**dict(row), 'raw': json.loads(row['raw']), 'encoded': json.loads(row['encoded'])}
                    for row in rows]

    def find(self, identity=None, url=None):
        with self.connection() as db:
            row = db.execute('SELECT * FROM problems WHERE id=?', (identity,)).fetchone()
            if row is None and url:
                from insights import canonical_url
                key = canonical_url(url) if '://' in url else url
                row = db.execute('SELECT p.* FROM problems p JOIN problem_urls u ON u.problem_id=p.id WHERE u.url_key=?', (key,)).fetchone()
            return {**dict(row), 'raw': json.loads(row['raw']), 'encoded': json.loads(row['encoded'])} if row else None

    def solution(self, identity):
        with self.connection() as db:
            row = db.execute('SELECT * FROM solutions WHERE problem_id=?', (identity,)).fetchone()
            if not row:
                return None
            return {'markdown': row['markdown'], 'path': row['source_path'], 'images': json.loads(row['images']), 'digest': row['digest']}

    def statement(self, identity):
        with self.connection() as db:
            row = db.execute('SELECT content FROM statements WHERE problem_id=?', (identity,)).fetchone()
            return json.loads(row[0]) if row else None

    def save_statement(self, identity, value):
        value=dict(value,statementAvailable=bool(value.get('markdown')))
        value.setdefault('limits',{'timeMs':2000,'memoryMb':256})
        with self.connection() as db:
            db.execute('INSERT INTO statements VALUES (?,?) ON CONFLICT(problem_id) DO UPDATE SET content=excluded.content',
                       (identity, json.dumps(value, ensure_ascii=False)))

    def lecture_entries(self):
        with self.connection() as db:
            return {row[0]: json.loads(row[1]) for row in db.execute('SELECT id,content FROM lectures ORDER BY rowid')}

    def references(self, identity):
        with self.connection() as db:
            return [(row[0], row[1]) for row in db.execute('SELECT lecture_id,kind FROM problem_lectures WHERE problem_id=? ORDER BY position', (identity,))]

    def metadata(self):
        with self.connection() as db:
            return dict(db.execute('SELECT key,value FROM library_meta'))

    def import_records(self, records, lectures, references, metadata=None):
        # All content and relations commit together. A failed import leaves the old library readable.
        dumps = lambda value: json.dumps(value, ensure_ascii=False)
        with self.connection() as db:
            for raw, encoded, solution, statement in records:
                identity = encoded['id']
                db.execute('INSERT INTO problems VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET url=excluded.url,raw=excluded.raw,encoded=excluded.encoded',
                           (identity, encoded.get('url'), dumps(raw), dumps(encoded)))
                if solution:
                    markdown = solution['markdown']
                    db.execute('INSERT INTO solutions VALUES (?,?,?,?,?) ON CONFLICT(problem_id) DO UPDATE SET markdown=excluded.markdown,source_path=excluded.source_path,images=excluded.images,digest=excluded.digest',
                               (identity, markdown, solution.get('path', ''), dumps(solution.get('images', {})), hashlib.sha256(markdown.encode()).hexdigest()))
                if statement:
                    db.execute('INSERT INTO statements VALUES (?,?) ON CONFLICT(problem_id) DO UPDATE SET content=excluded.content', (identity, dumps(statement)))
                db.execute('DELETE FROM problem_lectures WHERE problem_id=?', (identity,))
            for identity, entry in lectures.items():
                digest = hashlib.sha256(entry['markdown'].encode()).hexdigest()
                db.execute('INSERT INTO lectures VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET content=excluded.content,digest=excluded.digest', (identity, dumps(entry), digest))
            for problem, links in references.items():
                for position, (lecture, kind) in enumerate(links):
                    db.execute('INSERT OR IGNORE INTO problem_lectures VALUES (?,?,?,?)', (problem, lecture, kind, position))
            for key, value in (metadata or {}).items():
                db.execute('INSERT INTO library_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))
            db.execute("UPDATE library_meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            self._rebuild_urls(db)
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Library references are inconsistent')

    def check(self):
        with self.connection() as db:
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            broken = db.execute('PRAGMA foreign_key_check').fetchall()
            counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('problems', 'solutions', 'statements', 'lectures', 'problem_lectures')}
        if integrity != 'ok' or broken:
            raise ValueError('Invalid library database')
        return counts

    def export_source(self, directory):
        """Write the public library as deterministic text JSON for version control.

        The SQLite file remains a build artifact; the returned directory is the
        git-tracked source that first start or packaging rebuilds from.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            meta = dict(db.execute('SELECT key,value FROM library_meta'))
            problems = [{'id': row['id'], 'url': row['url'], 'raw': json.loads(row['raw']),
                         'encoded': json.loads(row['encoded'])}
                        for row in db.execute('SELECT id,url,raw,encoded FROM problems ORDER BY id')]
            solutions = [{'problem_id': row['problem_id'], 'markdown': row['markdown'],
                          'source_path': row['source_path'], 'images': json.loads(row['images'])}
                         for row in db.execute('SELECT problem_id,markdown,source_path,images FROM solutions ORDER BY problem_id')]
            statements = [{'problem_id': row['problem_id'], 'content': json.loads(row['content'])}
                          for row in db.execute('SELECT problem_id,content FROM statements ORDER BY problem_id')]
            lectures = [{'id': row['id'], 'content': json.loads(row['content'])}
                        for row in db.execute('SELECT id,content FROM lectures ORDER BY id')]
            links = [{'problem_id': row['problem_id'], 'lecture_id': row['lecture_id'],
                      'kind': row['kind'], 'position': row['position']}
                     for row in db.execute('SELECT problem_id,lecture_id,kind,position FROM problem_lectures ORDER BY problem_id,position')]
        def dump(name, value):
            # LF-only: .gitattributes forces eol=lf, keeping the fingerprint stable across checkouts.
            (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8', newline='\n')
        dump('meta.json', meta)
        dump('problems.json', problems)
        dump('solutions.json', solutions)
        dump('statements.json', statements)
        dump('lectures.json', lectures)
        dump('links.json', links)
        return directory

    @classmethod
    def from_source(cls, directory, path):
        """Rebuild a SQLite seed from the text source checked into git."""
        directory = Path(directory)
        def load(name):
            with (directory / name).open(encoding='utf-8') as handle:
                return json.load(handle)
        problems = load('problems.json')
        solutions = load('solutions.json')
        statements = load('statements.json')
        lectures = load('lectures.json')
        links = load('links.json')
        meta = load('meta.json')
        database = cls(path)
        with database.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.executemany('INSERT OR REPLACE INTO problems (id,url,raw,encoded) VALUES (?,?,?,?)',
                           [(p['id'], p['url'], json.dumps(p['raw'], ensure_ascii=False), json.dumps(p['encoded'], ensure_ascii=False))
                            for p in problems])
            db.executemany('INSERT OR REPLACE INTO solutions (problem_id,markdown,source_path,images,digest) VALUES (?,?,?,?,?)',
                           [(s['problem_id'], s['markdown'], s['source_path'], json.dumps(s['images'], ensure_ascii=False),
                             hashlib.sha256(s['markdown'].encode()).hexdigest()) for s in solutions])
            db.executemany('INSERT OR REPLACE INTO statements (problem_id,content) VALUES (?,?)',
                           [(st['problem_id'], json.dumps(st['content'], ensure_ascii=False)) for st in statements])
            db.executemany('INSERT OR REPLACE INTO lectures (id,content,digest) VALUES (?,?,?)',
                           [(lecture['id'], json.dumps(lecture['content'], ensure_ascii=False),
                             hashlib.sha256(lecture['content']['markdown'].encode()).hexdigest()) for lecture in lectures])
            db.executemany('INSERT OR REPLACE INTO problem_lectures (problem_id,lecture_id,kind,position) VALUES (?,?,?,?)',
                           [(link['problem_id'], link['lecture_id'], link['kind'], link['position']) for link in links])
            for key, value in meta.items():
                db.execute('INSERT INTO library_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
            cls._rebuild_urls(db)
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Library source has broken references')
        with database.connection() as db:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Rebuilt library failed integrity check')
        return database
