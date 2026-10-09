"""Read-only native WebView2 integration check; the test window stays hidden."""
import json
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import webview
from backend import start_server

server = start_server(port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
result = {}
window = webview.create_window('TB Native Probe', f'http://127.0.0.1:{server.server_port}', width=1480, height=920, min_size=(1050,700), hidden=True, background_color='#101116')
def check():
    try:
        for _ in range(100):
            state = window.evaluate_js("({count:document.querySelectorAll('.problem-table tbody tr').length,ready:!!document.querySelector('.problem-title')})")
            if state and state.get('ready'): break
            time.sleep(.1)
        else: raise AssertionError('Native workbench did not load')
        result.update(state)
        window.evaluate_js("document.querySelector('.heading-actions .button:not(.primary)').click()")
        for _ in range(100):
            content = window.evaluate_js("({markdown:!!document.querySelector('.markdown'),mathErrors:document.querySelectorAll('.katex-error').length,reader:!!document.querySelector('.reader-panel')})")
            if content and content.get('markdown'):break
            time.sleep(.1)
        else:raise AssertionError('Native solution reader did not load')
        assert content['mathErrors']==0
        result.update(content)
        result['ok']=True
    except Exception as error:
        result['error']=repr(error)
    finally:
        window.destroy()
try:
    webview.start(check, gui='edgechromium', private_mode=True, debug=False)
finally:
    server.shutdown();server.server_close()
print(json.dumps(result,ensure_ascii=False))
assert result.get('ok'), result
