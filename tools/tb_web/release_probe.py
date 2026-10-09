"""Release checks run only on an explicitly supplied, isolated installation."""
import json
import os
from pathlib import Path
import sys
import threading
import time


def run(action, output):
    from backend import create_server
    import toolutil
    root = Path(sys.executable).resolve().parent
    server = None
    try:
        server = create_server(port=int(os.environ.get('TB_PACKAGE_PORT', '0')), integration_auto_start=False)
        workspace = server.training.workspace()
        lectures = server.lectures.snapshot()
        profile = server.training.profile()
        report = {'ok': True, 'frozen': bool(getattr(sys, 'frozen', False)),
                  'version': '0.5.0', 'initialTrainingEmpty': workspace['summary']['total'] == 0,
                  'root': str(root), 'dataRoot': str(toolutil.DATA_ROOT),
                  'database': str(server.training.db_path), 'lectures': len(lectures.get('lectures', [])),
                  'profile': profile, 'hub': server.store.extensions.snapshot(),
                  'baseUrl': 'http://127.0.0.1:' + str(server.server_port)}
        if action == '--package-check':
            from judge import Judge
            class Fixture:
                def bundle(self, identity):
                    return {'scope': 'local', 'cases': [{'input': '', 'output': '42\n'}],
                            'limits': {'timeMs': 1000, 'memoryMb': 64}, 'checker': None,
                            'caseInsensitive': False, 'nonunique': False, 'coverage': 'Release compiler fixture'}
            runner = Judge(Fixture(), root / 'state' / 'release-compiler-check')
            report['compiler'] = str(runner.compiler)
            report['compilerResult'] = runner.execute('release-check', '#include <iostream>\nint main(){std::cout << 42 << "\\n";}', mode='submit')
            assert report['compilerResult']['verdict'] == 'AC', report['compilerResult']
            assert report['lectures'] >= 373, report['lectures']
        else:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            if action == '--serve-check':
                Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                while not (Path(output).with_suffix('.stop')).exists():
                    time.sleep(.2)
                server.shutdown()
                worker.join(3)
            elif action == '--native-check':
                import webview
                window = webview.create_window('TB release validation', report['baseUrl'], hidden=True, width=1480, height=920)
                def check():
                    try:
                        deadline = time.monotonic() + 25
                        while time.monotonic() < deadline:
                            if window.evaluate_js("!!document.querySelector('.nav-item')"):
                                report['nativeLoaded'] = True
                                report['nativeText'] = window.evaluate_js('document.body.innerText.slice(0,500)')
                                return
                            time.sleep(.1)
                        raise RuntimeError('Desktop interface did not load')
                    except Exception as error:
                        report.update(ok=False, error=str(error))
                    finally:
                        window.destroy()
                webview.start(check, gui='edgechromium', private_mode=True, storage_path=str(root / 'cache' / 'release-profile'))
                server.shutdown()
                worker.join(3)
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as error:
        import traceback
        report = {'ok': False, 'error': str(error), 'traceback': traceback.format_exc()}
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        if server:
            server.server_close()
    return 0 if report.get('ok') else 1
