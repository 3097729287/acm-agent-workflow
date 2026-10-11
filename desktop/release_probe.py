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
            assert result['verdict']=='SAMPLE_PASS', result
        else:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            if action == '--serve-check':
                Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                while not Path(output).with_suffix('.stop').exists():
                    time.sleep(.2)
            elif action == '--native-check':
                import webview
                from launch import bind_desktop_fullscreen
                from window_memory import is_fullscreen
                assert workspace['summary']['total'] == 0, 'Native UI probe requires fresh disposable state'
                assert server.training.submissions()['total'] == 0, 'Native UI probe refuses existing history'
                tested = next(row for row in rows if row['contest'] == '入门赛 49' and row['problem'] == 'D')
                code = '#include <bits/stdc++.h>\nusing namespace std; int main(){int n;cin>>n;long long one[61]={1},two[61]={0};for(int i=1;i<=n;++i){one[i]=one[i-1]+two[i-1];if(i>=2)two[i]=one[i-2];}cout<<one[n]+two[n]<<"\\n";}\n'
                server.training.save_draft(tested['id'], code)
                window = webview.create_window('TB release validation',report['baseUrl'],hidden=True,width=1480,height=920)
                bind_desktop_fullscreen(server, window)
                def check():
                    def wait_js(script, timeout=30):
                        deadline = time.monotonic() + timeout
                        while time.monotonic() < deadline:
                            if window.evaluate_js(script):
                                return
                            time.sleep(.1)
                        raise RuntimeError('Native UI condition timed out: ' + script)

                    def key(value, ctrl=False):
                        window.evaluate_js('window.dispatchEvent(new KeyboardEvent("keydown",' +
                                           json.dumps({'key': value, 'ctrlKey': ctrl, 'bubbles': True}) + '))')

                    try:
                        wait_js("!!document.querySelector('.nav-item')")
                        report['nativeLoaded'] = True
                        window.evaluate_js("document.querySelector('[aria-label=\"偏好设置\"]').click()")
                        wait_js("!!document.querySelector('input[aria-label=\"全屏\"]') && !document.querySelector('input[aria-label=\"全屏\"]').disabled")
                        assert not is_fullscreen(window)
                        window.evaluate_js("document.querySelector('input[aria-label=\"全屏\"]').click()")
                        wait_js("document.querySelector('input[aria-label=\"全屏\"]').checked")
                        assert is_fullscreen(window)
                        from System.Windows.Forms import Screen
                        assert window.native.Bounds == Screen.FromControl(window.native).Bounds
                        window.evaluate_js("document.querySelector('input[aria-label=\"全屏\"]').click()")
                        wait_js("!document.querySelector('input[aria-label=\"全屏\"]').checked")
                        assert not is_fullscreen(window)
                        report['fullscreenToggle'] = True
                        key('F11')
                        wait_js("document.querySelector('input[aria-label=\"全屏\"]').checked")
                        assert is_fullscreen(window)
                        key('F11')
                        wait_js("!document.querySelector('input[aria-label=\"全屏\"]').checked")
                        assert not is_fullscreen(window)
                        report['f11FrontendEvent'] = True
                        key('2', ctrl=True)
                        wait_js("!!document.querySelector('input[aria-label=\"搜索题目\"]')")
                        window.evaluate_js("(() => {const field=document.querySelector('input[aria-label=\"搜索题目\"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(field,'入门赛 49 D');field.dispatchEvent(new Event('input',{bubbles:true}));})()")
                        title = json.dumps(tested['title'], ensure_ascii=False)
                        wait_js("Array.from(document.querySelectorAll('.problem-table tbody tr')).some(row=>row.textContent.includes(" + title + "))")
                        window.evaluate_js("Array.from(document.querySelectorAll('.problem-table tbody tr')).find(row=>row.textContent.includes(" + title + ")).querySelector('.problem-title').click()")
                        wait_js("!!document.querySelector('.wb-run-actions') && document.querySelector('.cm-content')?.textContent.includes('long long one')")
                        labels = window.evaluate_js("Array.from(document.querySelectorAll('.wb-run-actions button')).map(node=>node.textContent.trim())")
                        assert labels == ['运行样例', '提交'], labels
                        report['buttonOrder'] = labels
                        window.evaluate_js("document.querySelectorAll('.wb-run-actions button')[0].click()")
                        wait_js("document.querySelector('.wb-result-summary')?.textContent.includes('样例通过')", timeout=90)
                        submission = next(row for row in server.training.submissions()['submissions'] if row['problemId'] == tested['id'] and row['mode'] == 'run')
                        assert submission['verdict'] == 'SAMPLE_PASS', submission['verdict']
                        assert submission['total'] > 0 and submission['passed'] == submission['total']
                        assert server.training.workspace()['summary']['accepted'] == 0
                        assert server.training.insights(server.store.extensions.snapshot())['growth']['totalXp'] == 0
                        assert all(not task['completed'] and task['scope'] == 'official' and task['version'] == 2 for task in server.training.daily_tasks()['tasks'])
                        report['localSubmission'] = {name: submission[name] for name in ('verdict', 'scope', 'passed', 'total')}
                        report['localAwardsNothing'] = True
                        report['officialSubmissionSent'] = False
                    except Exception as error:
                        import traceback
                        report.update(ok=False,error=str(error),traceback=traceback.format_exc())
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
