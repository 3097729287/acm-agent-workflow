"""Current HTTP boundaries and explicit SQL imports; no personal/live state touched."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import quote

import backend
from library import LibraryDatabase
from test_library import record


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tb-api-sql-')
        self.root = Path(self.temp.name)
        database = LibraryDatabase(self.root / 'library.sqlite3')
        database.import_records([record()], {}, {})
        self.server = backend.create_server(training_file=self.root / 'personal.sqlite3',
                                            library_file=database.path, data_root=self.root,
                                            data_file=self.root / 'absent.md', integration_auto_start=False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, path='/api/data', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        values = {'Content-Type': 'application/json', 'X-TB-Token': self.server.store.token}
        values.update(headers or {})
        connection.request('GET' if body is None else 'POST', path,
                           None if body is None else json.dumps(body).encode(), values)
        response = connection.getresponse()
        value = json.loads(response.read())
        status = response.status
        connection.close()
        return status, value

    def test_api_catalog_and_solution_work_without_frontend_or_markdown(self):
        status, data = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(data['rows'][0]['id'], 'fixture::A')
        self.assertEqual(self.request('/api/solution?id=' + quote('fixture::A'))[1]['markdown'], record()[2]['markdown'])
        self.assertEqual(self.request('/')[0], 404)

    def test_token_origin_host_and_traversal_guards_survive_architecture_split(self):
        body = {'id': 'fixture::A'}
        self.assertEqual(self.request('/api/training/start', body, {'X-TB-Token': 'invalid'})[0], 403)
        self.assertEqual(self.request('/api/training/start', body, {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request(headers={'Host': 'evil.example'})[0], 403)
        for path in ('/api/unknown', '/../backend.py', '/%2e%2e/backend.py', '/%5c..%5cbackend.py', '/api/data%00'):
            self.assertEqual(self.request(path)[0], 404, path)
        self.assertEqual(self.server.training.workspace()['summary']['total'], 0)

    def test_explicit_frontend_origin_allows_preflight_and_still_requires_token(self):
        origin = 'http://127.0.0.1:5173'
        def preflight(value):
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
            connection.request('OPTIONS', '/api/training/start', headers={'Origin': value})
            response = connection.getresponse()
            result = response.status, dict(response.getheaders())
            response.read()
            connection.close()
            return result
        self.assertEqual(preflight(origin)[0], 403)
        self.server.frontend_origins = frozenset({origin})
        status, headers = preflight(origin)
        self.assertEqual(status, 204)
        self.assertEqual(headers['Access-Control-Allow-Origin'], origin)
        self.assertIn('X-TB-Token', headers['Access-Control-Allow-Headers'])
        self.assertEqual(preflight('https://evil.example')[0], 403)
        headers = {'Origin': origin, 'Sec-Fetch-Site': 'cross-site'}
        self.assertEqual(self.request('/api/training/start', {'id': 'fixture::A'}, {**headers, 'X-TB-Token': 'bad'})[0], 403)
        self.assertEqual(self.request('/api/training/start', {'id': 'fixture::A'}, headers)[0], 200)

    def test_progress_is_derived_from_submissions_and_not_catalog_edits(self):
        self.assertEqual(self.request('/api/status', {'id': 'fixture::A', 'status': '独立AC'})[0], 410)
        self.assertEqual(self.request('/api/training/start', {'id': 'fixture::A'})[0], 200)
        self.assertFalse(self.server.training.workspace()['training'][0]['accepted'])

    def test_inbox_reports_missing_sections_and_does_not_partially_import(self):
        inbox = self.root / '题解' / '_收件箱'
        inbox.mkdir(parents=True)
        file = inbox / 'ABC1题解.md'
        file.write_text('# ABC 1 题解\n\n## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n| A | A | 枚举 | 1000 |\n| B | B | 枚举 | 1000 |\n\n## A. A\nOnly one section.\n', encoding='utf-8')
        original = file.read_bytes()
        preview = self.request('/api/inbox')[1]
        self.assertEqual(preview['pending'], 2)
        self.assertTrue(preview['errors'])
        self.assertTrue(self.request('/api/inbox', {'action': 'import'})[1]['errors'])
        self.assertEqual(len(self.server.store.raw_rows()), 1)
        self.assertEqual(file.read_bytes(), original)

    def test_inbox_commits_fenced_headings_and_lessons_then_preserves_source(self):
        inbox = self.root / '题解' / '_收件箱'
        inbox.mkdir(parents=True)
        file = inbox / 'ABC1题解.md'
        body = ('### 从零讲：枚举\n\n' + '枚举是逐一检查有限候选，再根据条件选择可行答案。' * 12)
        source = '# ABC 1 题解\n\n## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n| A | A | 枚举 | 1000 |\n\n## A. A\n```text\n## B. Fenced heading\n```\n' + body + '\n'
        file.write_text(source, encoding='utf-8')
        imported = self.request('/api/inbox', {'action': 'import'})[1]
        self.assertEqual(imported['result']['added'], 1)
        self.assertIn('## B. Fenced heading', self.server.store.solution('ABC 1::A')['markdown'])
        self.assertEqual(len(self.server.lectures.for_problem('ABC 1::A')), 1)
        self.assertEqual(next((inbox / '_已导入').glob('*.md')).read_text(encoding='utf-8'), source)


if __name__ == '__main__':
    unittest.main()
