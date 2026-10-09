"""Release checks require an explicitly isolated state directory."""
import json
import os
from pathlib import Path
import threading
import time


def run(action, output):
    from paths import ROOT, STATE, FRONTEND
    from version import VERSION
    server = None
    report = {'ok': False, 'version': VERSION}
    try:
        if not os.environ.get('TB_STATE_DIR'):
            raise RuntimeError('Set TB_STATE_DIR to a disposable directory before running a release probe')
        from backend import create_server
        server = create_server(port=int(os.environ.get('TB_PACKAGE_PORT', '0')), dist_dir=FRONTEND,
                               training_file=STATE / 'tb-personal.sqlite3', integration_auto_start=False)
        data = server.store.data()
        workspace = server.training.workspace()
        rows = [row for row in data['rows'] if row.get('solutionAvailable')]
        xterfusion = next(row for row in rows if row['title'] == 'Xterfusion')
        text = server.store.solution(xterfusion['id'])['markdown']
        assert len(rows) >= 607 and len(text) > 4000
        assert len(server.lectures.for_problem(xterfusion['id'])) == 1
        report.update(ok=True, root=str(ROOT), state=str(STATE), frozen=bool(getattr(__import__('sys'), 'frozen', False)),
                      initialTrainingEmpty=workspace['summary']['total']==0, problems=len(data['rows']), solutions=len(rows),
                      lectures=len(server.lectures.snapshot()['lectures']), xterfusionCharacters=len(text),
                      library=server.store.library.check(), profile=server.training.profile()['profile'],
                      baseUrl='http://127.0.0.1:'+str(server.server_port))
        if action == '--package-check':
            from judge import Judge
            class Fixture:
                def bundle(self, identity):
                    return {'scope':'local','cases':[{'input':'','output':'42\n'}],
                            'limits':{'timeMs':1000,'memoryMb':64},'checker':None,
                            'caseInsensitive':False,'nonunique':False,'coverage':'Release compiler fixture'}
            runner = Judge(Fixture(), STATE / 'release-compiler-check')
            result = runner.execute('release-check','#include <iostream>\nint main(){std::cout<<42<<"\\n";}')
            report.update(compiler=str(runner.compiler), compilerVerdict=result['verdict'])
            assert result['verdict']=='AC', result
        else:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            if action == '--serve-check':
                Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                while not Path(output).with_suffix('.stop').exists():
                    time.sleep(.2)
            elif action == '--native-check':
                import webview
                window = webview.create_window('TB release validation',report['baseUrl'],hidden=True,width=1480,height=920)
                def check():
                    try:
                        deadline=time.monotonic()+30
                        while time.monotonic()<deadline:
                            if window.evaluate_js("!!document.querySelector('.nav-item')"):
                                report['nativeLoaded']=True
                                return
                            time.sleep(.1)
                        raise RuntimeError('Desktop interface did not load')
                    except Exception as error:
                        report.update(ok=False,error=str(error))
                    finally:
                        window.destroy()
                webview.start(check,gui='edgechromium',private_mode=True,storage_path=str(STATE/'release-profile'))
            server.shutdown()
            worker.join(3)
    except Exception as error:
        import traceback
        report.update(ok=False,error=str(error),traceback=traceback.format_exc())
    finally:
        if server:
            server.server_close()
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report.get('ok') else 1
