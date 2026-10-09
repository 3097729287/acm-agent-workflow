"""SQL storage, portable content, upgrades and v0.5 compatibility in disposable state."""
import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import backend
from library import LibraryDatabase
from paths import LIBRARY_SEED
from persistence import load_document, save_document


def record(identity='fixture::A', title='Fixture', markdown='## A. Fixture\n\nA solution.'):
    raw = {'场次': identity.split('::')[0], '题号': 'A', '题名': title,
           '知识点': '枚举', '难度': '1000', '状态': '未做', '日期': ''}
    encoded = {'id': identity, 'contest': raw['场次'], 'problem': 'A', 'title': title,
               'url': 'https://codeforces.com/contest/1/problem/A', 'status': '未做', 'date': ''}
    return raw, encoded, {'markdown': markdown, 'path': 'fixture.md'}, {'markdown': 'Public English statement.', 'samples': [], 'statementAvailable': True}


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tb-sql-tests-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_install_without_archive_reads_all_bundled_solutions(self):
        with patch.dict('os.environ', {'TB_OFFLINE': '1'}):
            server = backend.create_server(training_file=self.root / 'tb-personal.sqlite3',
                                           integration_auto_start=False)
        try:
            data = server.store.data()
            self.assertEqual(len(data['rows']), 607)
            self.assertTrue(all(row['solutionAvailable'] for row in data['rows']))
            row = next(row for row in data['rows'] if row['title'] == 'Xterfusion')
            self.assertIn('e2', server.store.solution(row['id'])['markdown'])
            self.assertEqual(len(server.lectures.for_problem(row['id'])), 1)
            self.assertEqual(server.training.workspace()['summary']['total'], 0)
            self.assertTrue(server.store.library.path.parent.samefile(self.root))
            self.assertEqual(server.store.library.check()['solutions'], 607)
            self.assertIsNone(server.dist_dir, 'API starts independently of frontend assets')
        finally:
            server.server_close()

    def test_catalog_queries_stay_bounded_and_an_import_is_immediately_visible(self):
        with patch.dict('os.environ', {'TB_OFFLINE': '1'}):
            server = backend.create_server(training_file=self.root / 'tb-personal.sqlite3', integration_auto_start=False)
        try:
            database = server.store.library
            with patch.object(database, 'connection', wraps=database.connection) as connections:
                catalog = server.store.data()
            self.assertEqual(len(catalog['rows']), 607)
            self.assertLessEqual(connections.call_count, 4, 'A list refresh must not open connections per problem')
            database.import_records([record('custom::A')], {}, {})
            self.assertIn('custom::A', {row['id'] for row in server.store.data()['rows']})
            self.assertTrue(all(row['solutionAvailable'] for row in server.store.data()['rows']))
        finally:
            server.server_close()

    def test_failed_import_is_atomic_and_foreign_keys_are_enforced(self):
        database = LibraryDatabase(self.root / 'library.sqlite3')
        database.import_records([record()], {}, {})
        before = database.metadata()['revision']
        with self.assertRaises(sqlite3.IntegrityError):
            database.import_records([record(title='Changed')], {}, {'fixture::A': [('missing', 'explicit')]})
        self.assertEqual(database.find('fixture::A')['encoded']['title'], 'Fixture')
        self.assertEqual(database.metadata()['revision'], before)
        database.check()

    def test_seed_upgrades_keep_custom_edits_extra_problems_and_personal_data(self):
        seed = LibraryDatabase(self.root / 'seed.sqlite3')
        seed.import_records([record(), record('fixture::B', 'Original B')], {}, {})
        live = LibraryDatabase(self.root / 'live.sqlite3')
        self.assertTrue(live.merge_seed(seed.path))
        self.assertFalse(live.merge_seed(seed.path))
        # A user import replaces A and creates C; fetched A statement is also personal cache.
        live.import_records([record(title='User A', markdown='My imported solution.'), record('custom::C', 'Extra')], {}, {})
        live.save_statement('fixture::A', {'markdown': 'Fetched statement', 'samples': []})
        personal = self.root / 'tb-personal.sqlite3'
        with contextlib.closing(sqlite3.connect(personal)) as db:
            db.execute('CREATE TABLE drafts(code TEXT)')
            db.execute("INSERT INTO drafts VALUES ('user draft')")
            db.commit()
        before = hashlib.sha256(personal.read_bytes()).hexdigest()
        seed.import_records([record(title='New A'), record('fixture::B', 'New B', 'New B solution.')], {}, {})
        self.assertTrue(live.merge_seed(seed.path))
        self.assertEqual(live.find('fixture::A')['encoded']['title'], 'User A')
        self.assertEqual(live.solution('fixture::A')['markdown'], 'My imported solution.')
        self.assertEqual(live.statement('fixture::A')['markdown'], 'Fetched statement')
        self.assertEqual(live.find('fixture::B')['encoded']['title'], 'New B')
        self.assertIsNotNone(live.find('custom::C'))
        self.assertEqual(hashlib.sha256(personal.read_bytes()).hexdigest(), before)
        self.assertEqual(len(list((self.root / 'backups').glob('*.sqlite3'))), 1)
        live.check()

    def test_json_migrates_once_and_source_bytes_never_change(self):
        legacy = self.root / 'integrations.json'
        original = '{"nickname":"旧用户","protectedKey":"encrypted fixture"}'.encode('utf-8')
        legacy.write_bytes(original)
        self.assertEqual(load_document(legacy, {})['nickname'], '旧用户')
        save_document(legacy, {'nickname': 'New user'})
        self.assertEqual(load_document(legacy, {})['nickname'], 'New user')
        self.assertEqual(legacy.read_bytes(), original)
        self.assertTrue((self.root / 'tb-documents.sqlite3').is_file())

    def test_local_markdown_links_become_portable_citations_without_changing_code(self):
        from lecture_library import portable_markdown
        original = ('参见[逆元](D:/Data/Code/题解/牛客/128/128题解.md)。\n'
                    r'参见[说明](<C:\archive\算法\inverse notes.md>)。' + '\n'
                    '文件 `D:/Data/Code/题解/128题解.md`。\n'
                    '网页[文档](https://example.com/doc)，公式 $a^2$。\n'
                    '示例 `[标题](D:/keep/example.md)`。\n'
                    '```cpp\nconst char* p="D:/keep/source.cpp";\n```\n')
        result, count = portable_markdown(original)
        self.assertEqual(count, 3)
        self.assertIn('逆元（`题解/牛客/128/128题解.md`）', result)
        self.assertIn('说明（`知识库/inverse notes.md`）', result)
        self.assertIn('文件 `题解/128题解.md`', result)
        self.assertIn('网页[文档](https://example.com/doc)，公式 $a^2$', result)
        self.assertIn('`[标题](D:/keep/example.md)`', result)
        self.assertIn('const char* p="D:/keep/source.cpp";', result)

    def test_bundled_library_has_no_personal_progress_or_absolute_source_paths(self):
        database = LibraryDatabase(LIBRARY_SEED,readonly=True)
        for row in database.rows(raw=True):
            self.assertEqual((row['状态'], row['日期']), ('未做', ''))
        with database.connection() as db:
            for row in db.execute('SELECT source_path FROM solutions'):
                self.assertFalse(Path(row[0]).is_absolute(), row[0])
            from lecture_curation import fenced_mask
            texts = [row[0] for row in db.execute('SELECT markdown FROM solutions')]
            for content, in db.execute('SELECT content FROM lectures'):
                entry = json.loads(content)
                texts.extend(entry.get(field, '') for field in ('markdown', 'sourceMarkdown'))
            for text in texts:
                lines = text.splitlines(keepends=True)
                prose = ''.join(line for line, fenced in zip(lines, fenced_mask(lines)) if not fenced)
                self.assertNotRegex(prose, r'(?:`|\]\(\s*<?)[A-Za-z]:[\\/]')
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
