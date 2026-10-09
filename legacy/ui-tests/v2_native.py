"""Native WebView2 check with a temporary personal store and read-only archive."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import webview
from backend import create_server

result={}
with tempfile.TemporaryDirectory(prefix='tb-v2-native-') as directory:
    temporary=Path(directory)
    server=create_server(port=0,training_file=temporary/'personal.sqlite3',history_file=temporary/'history.jsonl',backup_dir=temporary/'backups')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    window=webview.create_window('TB v2 Native Check',f'http://127.0.0.1:{server.server_port}',width=1480,height=920,hidden=True,background_color='#101217')
    def wait(expression,condition):
        for _ in range(100):
            state=window.evaluate_js(expression)
            if condition(state):return state
            time.sleep(.1)
        raise AssertionError('WebView did not reach expected state')
    def check():
        try:
            wait("({ready:document.querySelector('.empty h2')?.textContent,progress:document.querySelector('.progress-chip')?.textContent})",lambda state:state and state.get('ready')=='从第一道题开始')
            window.evaluate_js("document.querySelector('.nav-item[aria-label=\"题库\"]').click()")
            result.update(wait("({count:document.querySelectorAll('.problem-table tbody tr').length,tableHeight:document.querySelector('.table-scroll')?.clientHeight})",lambda state:state and state.get('count',0)>0))
            window.evaluate_js("document.querySelector('.row-icon[aria-label^=\"题解 \"]').click()")
            result.update(wait("({reader:!!document.querySelector('.reader-panel .markdown'),mathErrors:document.querySelectorAll('.katex-error').length})",lambda state:state and state.get('reader')))
            assert result['mathErrors']==0
            assert server.training.workspace()['summary']['total']==0
            result['ok']=True
        except Exception as error:result['error']=repr(error)
        finally:window.destroy()
    try:webview.start(check,gui='edgechromium',private_mode=True,debug=False)
    finally:server.shutdown();server.server_close()
print(json.dumps(result,ensure_ascii=False))
assert result.get('ok'),result
