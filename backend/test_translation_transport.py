"""Real local HTTP fixture exercises provider parsing, chunking and credential defaults."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from training import ServiceError
from translation import DeepSeekProvider, TranslationService, translation_chunks, protect
from translation_config import ProviderSettings


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tb-translation-transport-')
        self.root = Path(self.temp.name)
        self.requests = []
        self.reply = None
        self.code = 200
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append((self.path, payload, self.headers.get('Authorization')))
                content = payload['messages'][1]['content'].replace('Given a positive integer', '给定一个正整数')
                content = content.replace('find the answer and print its value.', '计算答案并输出其值。')
                result = owner.reply if owner.reply is not None else {'choices': [{'message': {'content': [{'type':'text','text':content}]}}]}
                raw = json.dumps(result).encode()
                self.send_response(owner.code)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict('os.environ', {'DSH_HOME': str(self.root / 'absent'), 'TB_TRANSLATION_API_KEY':'', 'DEEPSEEK_API_KEY':''})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def service(self, markdown):
        class Assets:
            lock = threading.RLock()
            def _cached(self, identity):
                return {'id':identity, 'markdown':markdown, 'url':'https://atcoder.jp/contests/abc1/tasks/abc1_a', 'statementAvailable':True}
        service = TranslationService(Assets(), self.root)
        service.configure({'provider':'custom', 'baseUrl':f'http://127.0.0.1:{self.server.server_port}/v1/chat/completions/', 'model':'fixture-model'})
        return service

    def test_anonymous_gateway_optional_finish_reason_and_text_array(self):
        service = self.service('Given a positive integer $n$, find the answer and print its value.\n\n```text\n1 2 3\n```')
        result = service.translate('p')
        self.assertIn('给定一个正整数 $n$', result['markdown'])
        self.assertIn('```text\n1 2 3\n```', result['markdown'])
        self.assertEqual(self.requests[0][0], '/v1/chat/completions')
        self.assertIsNone(self.requests[0][2])
        self.assertEqual(self.requests[0][1]['model'], 'fixture-model')
        self.assertFalse((self.root / 'translation-settings.json').exists())
        self.assertTrue(service.status()['verified'])
        self.assertTrue(service.translate('p')['cached'])

    def test_truncation_and_http_errors_never_cache_a_partial_result(self):
        service = self.service('Given a positive integer $n$, find the answer and print its value.')
        self.reply = {'choices':[{'finish_reason':'length','message':{'content':'截断正文'}}]}
        with self.assertRaisesRegex(ServiceError, '长度上限'):
            service.translate('p')
        self.assertFalse((self.root / 'translations' / 'tb-documents.sqlite3').exists())
        self.code = 401
        with self.assertRaisesRegex(ServiceError, '密钥'):
            service.test_connection()
        self.assertFalse(service.status()['verified'])

    def test_long_single_paragraph_requests_are_bounded_and_keep_all_spans(self):
        original = ('Given a positive integer $n$, find the answer and print its value. ' * 170
                    + '\n\n$$a_i \\le 10^{18}$$\n\n```cpp\nint main(){}\n```\n')
        chunks = translation_chunks(original)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(''.join(chunks), original)
        self.assertTrue(all(len(protect(part)[0]) < 4096 for part in chunks))
        service = self.service(original)
        translated = service.translate('p')['markdown']
        self.assertEqual(translated.count('$n$'), original.count('$n$'))
        self.assertIn('$$a_i \\le 10^{18}$$', translated)
        self.assertIn('```cpp\nint main(){}\n```', translated)
        self.assertEqual(len(self.requests), len(chunks))

    def test_deepseek_environment_key_works_without_a_saved_settings_file(self):
        key = 'sk-fixture123456789012345678901234'
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY':key}):
            settings = ProviderSettings(self.root)
            self.assertTrue(settings.status()['configured'])
            self.assertEqual(settings.credentials()[1:3], ('https://api.deepseek.com/chat/completions', 'deepseek-chat'))
            self.assertEqual(settings.credentials()[3], key)


if __name__ == '__main__':
    unittest.main()
