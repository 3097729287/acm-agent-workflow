"""Disposable loopback fixture for real browser extension tests. No account access."""
import json
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
for directory in ('desktop', 'backend', 'backend/common'):
    sys.path.insert(0, str(ROOT / directory))
from backend import Handler
from browser_bridge import BrowserBridge

opened, saved, sessions = [], [], {}


class Fixture(Handler):
    def do_GET(self):
        target = urlsplit(self.path)
        query = parse_qs(target.query)
        if target.path == '/fixture/create':
            key = query['key'][0]
            url = query['url'][0]
            value = self.server.browser_bridge.submit(url, 'int main(){}', key)
            sessions[key] = value['sessionId']
            self.send_json(200, value)
        elif target.path == '/fixture/status':
            self.send_json(200, {key: self.server.browser_bridge.status(sid) for key, sid in sessions.items()})
        elif target.path == '/fixture/saved':
            self.send_json(200, [{'status': s['status'], 'platform': s['platform'], 'verdict': s['verdict']} for s in saved])
        elif target.path == '/fixture/opened':
            self.send_json(200, opened)
        else:
            super().do_GET()


server = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
server.frontend_origins = set()
server.dist_dir = ROOT / 'frontend' / 'public'
server.browser_extension_path = ROOT / 'build' / 'browser-extension'
server.browser_bridge = BrowserBridge('http://127.0.0.1:' + str(server.server_port), opener=opened.append,
                                       on_receipt=lambda sid, s: saved.append(s) or True)
print(json.dumps({'port': server.server_port}), flush=True)
server.serve_forever()
