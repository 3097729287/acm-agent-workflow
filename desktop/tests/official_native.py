"""Hidden native WebView proof: toolbar geometry and real DOM compiler choices.

All official-origin requests are intercepted, including form POSTs. No live OJ
account, personal database, keyboard input, or real official submission is used.
"""
import json
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"backend"))
import webview
from official_bridge import OfficialBridge


def run():
    result={};phase={'value':'main'};requests=[];mode={'language':'C++(g++ 13)','authorized':False,'hold':False}
    with tempfile.TemporaryDirectory(prefix='tb-v5-native-',ignore_cleanup_errors=True) as directory:
        main=webview.create_window('TB hidden official layout proof',html='<html><body><script>window.preserved=7</script></body></html>',width=1480,height=920,hidden=True)
        def fixture(view):
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            from System.IO import MemoryStream,StreamReader
            from System.Text import Encoding
            core=view.CoreWebView2;core.AddWebResourceRequestedFilter('*',CoreWebView2WebResourceContext.All)
            def serve(_,event):
                request=event.Request;body=''
                event.Response=core.Environment.CreateWebResourceResponse(MemoryStream(Encoding.UTF8.GetBytes('<html>Fixture only</html>')),200,'OK','Content-Type: text/html; charset=utf-8')
                if request.Content is not None:body=str(StreamReader(request.Content,Encoding.UTF8).ReadToEnd())
                requests.append((str(request.Method),str(request.Uri),body))
                headers='Content-Type: text/html; charset=utf-8'
                if not mode['authorized']:
                    content='<html><title>Login</title><body><input type="password"><button>Login</button></body></html>'
                elif str(request.Uri).split('?')[0].endswith('/submit_cd'):
                    content=json.dumps({'code':0,'data':{'submissionId':2001}});headers='Content-Type: application/json'
                elif str(request.Uri).split('?')[0].endswith('/status'):
                    content=json.dumps({'code':0,'data':{'status':5,'desc':'答案正确','memo':'通过全部用例'}});headers='Content-Type: application/json'
                elif str(request.Method)=='POST':
                    content='<html><title>submitted fixture</title><body><table><tr><td><a href="/contests/abc478/submissions/1001">1001</a><a href="/contests/abc478/tasks/abc478_d">D</a><span class="label">Running</span></td></tr></table></body></html>'
                    if 'codeforces.com' in str(request.Uri):
                        content='<html><title>My submissions</title><body><table><tr><td><a href="/contest/123/submission/1001">1001</a><a href="/contest/123/problem/A">A</a><a href="/profile/fixture">fixture</a><span class="label">Running</span></td></tr></table></body></html>'
                elif '/submissions/me' in str(request.Uri):
                    content='<html><table><tr><th>Submission</th><th>Status</th></tr></table></html>'
                elif str(request.Uri).endswith('/my'):
                    content='<html><table class="status-frame-datatable"><tr><th>Submission</th><th>Status</th></tr></table></html>'
                else:
                    content=f'<html><title>compiler fixture</title><body><header id="account">fixture-user · Login</header><form method="post" action="/contests/abc478/submit"><select name="taskScreenName"><option value="abc478_d">D</option></select><select name="languageId"><option value="native-compiler">{mode["language"]}</option></select><textarea name="sourceCode"></textarea><button type="submit">Submit</button></form></body></html>'
                    if 'codeforces.com' in str(request.Uri):
                        content=f'<html><title>Submit</title><body><header id="header"><a href="/profile/fixture">fixture</a></header><form method="post" action="/contest/123/submit"><select name="submittedProblemIndex"><option value="A">A</option></select><select name="programTypeId"><option value="native-compiler">{mode["language"]}</option></select><textarea name="source"></textarea><button type="submit">Submit</button></form></body></html>'
                    if '/acm/contest/' in str(request.Uri):
                        content=f'''<html><title>Nowcoder compiler fixture</title><body><form><div class="el-select el-select--small btn-language"><div class="el-input"><input class="el-input__inner" readonly value="{mode["language"]}"></div></div><textarea name="sourceCode"></textarea><button type="submit">保存并提交</button></form><script>
window.pageInfo={{contestId:'127263',questionId:'11604979'}};window.globalInfo={{ownerId:12345}};
document.querySelector('form').onsubmit=async event=>{{event.preventDefault();const data=await fetch('/submit_cd',{{method:'POST',body:new URLSearchParams({{questionId:'11604979',content:document.querySelector('textarea').value}})}}).then(r=>r.json());await fetch('/status?submissionId='+data.data.submissionId).then(r=>r.json());}};
</script></body></html>'''
                event.Response=core.Environment.CreateWebResourceResponse(MemoryStream(Encoding.UTF8.GetBytes(content)),200,'OK',headers)
            core.WebResourceRequested+=serve
        bridge=OfficialBridge(main,native_setup=fixture);main.events.closing+=bridge.on_closing
        def wait(check,timeout=10):
            until=time.monotonic()+timeout
            while time.monotonic()<until:
                value=check()
                if value:return value
                time.sleep(.05)
            raise AssertionError('Native fixture did not finish')
        def verify():
            try:
                wait(lambda:main.evaluate_js('window.preserved')==7)
                # Show an entirely transparent test form so child Visible values
                # are meaningful, without opening a visible window for the user.
                def show_hidden():
                    main.native.Opacity=0
                    main.native.Show()
                bridge._ui(show_hidden)
                target='https://atcoder.jp/contests/abc478/tasks/abc478_d'
                auth=bridge.submit(target,'int main(){}','login fixture')
                wait(lambda:bridge.status(auth['sessionId'])['status']=='needs_login')
                assert bridge.current is None
                assert not any(method=='POST' for method,_,_ in requests)
                assert bridge._ui(lambda:main.native.browser.webview.Visible)
                bridge.open(target,'int main(){}','authorize')
                assert bridge.current==auth['sessionId']
                geometry=bridge._ui(lambda:{'browserTop':bridge.view.Top,'toolbarBottom':bridge.status_label.Parent.Bottom})
                assert geometry['browserTop']>=geometry['toolbarBottom'],geometry
                mode['authorized']=True
                bridge._ui(lambda:bridge.view.CoreWebView2.Reload())
                wait(lambda:bridge.status(auth['sessionId'])['status']=='ready')
                assert not any(method=='POST' for method,_,_ in requests),'login never submits code'
                bridge.close(auth['sessionId'])
                assert bridge.current is None
                result['authorizationRequiredBeforeSubmit']=True
                result['authorizationDoesNotSubmit']=True
                values=[]
                for label in ['C++(g++ 13)','GNU G++17 7.3.0','GNU G++23 14.2 (64 bit)','C++（clang++18）','GNU G++20 13.2 (64 bit)']:
                    phase['value']=label;mode['language']=label;before=sum(method=='POST' for method,_,_ in requests)
                    target='https://ac.nowcoder.com/acm/contest/127263/B' if 'clang' in label else 'https://atcoder.jp/contests/abc478/tasks/abc478_d'
                    if 'G++20' in label:target='https://codeforces.com/contest/123/problem/A'
                    session=bridge.submit(target,'int main(){}',label)
                    wait(lambda:sum(method=='POST' for method,_,_ in requests)>before)
                    assert bridge.current is None,'submit must remain in TB'
                    assert bridge._ui(lambda:main.native.browser.webview.Visible),'main editor must stay visible'
                    if 'clang' not in label:
                        from training import ServiceError
                        try:bridge.submit(target,'int main(){return 1;}',label)
                        except ServiceError as error:assert error.status==409
                        else:raise AssertionError('Duplicate submit must be rejected')
                        # Simulate the site's dynamic verdict arriving later;
                        # only the host watcher reads it, with no UI polling.
                        bridge._eval("document.querySelector('.label').textContent='AC'",identity=session['sessionId'])
                    # No frontend status request: the hidden main view has no
                    # polling JS, yet the native host must collect this AC.
                    wait(lambda:bridge.status(session['sessionId'],inspect=False)['status']=='finished')
                    status=bridge.status(session['sessionId'],inspect=False);assert status.get('compiler')==label.replace('（','(').replace('）',')'),status
                    assert status.get('verdict')=='AC',status
                    values.append({'language':label,'backgroundSubmit':True,'formPosted':True,'receiptConfirmed':status.get('verdict')=='AC'})
                    bridge.close(session['sessionId']);assert main.evaluate_js('window.preserved')==7
                assert all('sourceCode=' in body or 'content=' in body or 'source=' in body for method,_,body in requests if method=='POST')
                result.update(ok=True,compilerCases=values,fixturePosts=sum(method=='POST' for method,_,_ in requests),mainPreserved=True)
            except Exception as error:result.update(error=repr(error),phase=phase['value'],requests=requests,sessions=bridge.sessions,observer=bridge._eval('({state:window.__tbNowcoder,page:window.pageInfo,owner:window.globalInfo,fetch:String(window.fetch)})'))
            finally:main.destroy()
        webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(Path(directory)/'profile'),debug=False)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert result.get('ok'),result


if __name__=='__main__':run()
