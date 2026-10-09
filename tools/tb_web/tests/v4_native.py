"""Single-Form native proof with intercepted official-origin fixtures.

All fixture requests (including its normal form POST) are intercepted before
network. The final real AtCoder login navigation is GET-only: no fill or submit.
Every database/profile is disposable; the archive remains read-only.
"""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import webview
from backend import create_server
from official_bridge import OfficialBridge

URL='https://atcoder.jp/contests/abc478/tasks/abc478_d'
FORM='''<!doctype html><html><title>Official-origin native fixture</title><body>
<form method="post" action="/contests/abc478/submit"><input type="hidden" name="csrf_token" value="fixture-csrf-only">
<select name="taskScreenName"><option value="abc478_d">D</option></select>
<select name="languageId"><option value="5031">C++ 17 (gcc)</option></select>
<textarea name="sourceCode"></textarea><button type="submit">Submit</button></form></body></html>'''
LOGIN='<html><title>Login fixture</title><form><input name="username"><input type="password"><button type="submit">Login</button></form></html>'
def history(identity,verdict):
    return f'<html><title>My Submissions fixture</title><table><thead><tr><th>Submission</th><th>Task</th><th>Status</th></tr></thead><tbody><tr><td><a href="/contests/abc478/submissions/{identity}">{identity}</a></td><td><a href="/contests/abc478/tasks/abc478_d">D</a></td><td><span class="label">{verdict}</span></td></tr></tbody></table></html>'

def run():
    result={};requests=[];mode={'login':False,'challenge':False,'wrongLanguage':False};main=None;bridge=None
    with tempfile.TemporaryDirectory(prefix='tb-v4-native-') as directory:
        temp=Path(directory).resolve()
        server=create_server(port=0,training_file=temp/'personal.sqlite',history_file=temp/'history.jsonl',backup_dir=temp/'backups',integration_auto_start=False,integration_state_dir=temp/'integrations')
        archive=server.store.data_file.read_bytes();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        main=webview.create_window('TB v4 hidden single-Form proof',base,width=1480,height=920,hidden=True)
        def fixture(view):
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            from System.IO import MemoryStream,StreamReader
            from System.Text import Encoding
            core=view.CoreWebView2;core.AddWebResourceRequestedFilter('*',CoreWebView2WebResourceContext.All)
            def serve(_,event):
                request=event.Request;url=str(request.Uri);method=str(request.Method);body=''
                if request.Content is not None:
                    body=str(StreamReader(request.Content,Encoding.UTF8).ReadToEnd())
                requests.append({'method':method,'url':url,'body':body})
                if mode['login']:content=LOGIN
                elif mode['wrongLanguage']:content='<html><body><p>Available languages: C++17</p><span class="ivu-select-selected-value">Python 3</span><textarea name="sourceCode"></textarea><button type="submit">提交代码</button></body></html>'
                elif mode['challenge'] and '/submissions/me' in url:content='<html><title>Just a moment</title><p>Checking your browser</p></html>'
                elif method=='POST':content=history('101','AC')
                elif '/submissions/me' in url:content=history('100','WA')
                else:content=FORM
                event.Response=core.Environment.CreateWebResourceResponse(MemoryStream(Encoding.UTF8.GetBytes(content)),200,'OK','Content-Type: text/html; charset=utf-8')
            core.WebResourceRequested+=serve
        bridge=OfficialBridge(main,guard=server.validate_official_url,native_setup=fixture)
        server.official_opener=bridge.open;server.official_submitter=bridge.submit;server.official_status=bridge.status;server.official_closer=bridge.close
        def api(path,body=None):
            request=Request(base+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-TB-Token':server.store.token},method='POST' if body is not None else 'GET')
            with urlopen(request,timeout=30) as response:return json.loads(response.read())
        def wait(check,timeout=25):
            until=time.monotonic()+timeout;last=None
            while time.monotonic()<until:
                last=check()
                if last:return last
                time.sleep(.1)
            raise AssertionError('Native condition did not complete: '+repr(last))
        def verify():
            try:
                wait(lambda:main.evaluate_js("!!document.querySelector('.nav-item')"))
                main.evaluate_js('window.tbNativePreserved={counter:7};true')
                code='// Native fixture only - never sent to real OJ\nint main(){return 0;}\n'
                opened=api('official/submit',{'id':'ABC 478::D','code':code});identity=opened['sessionId']
                wait(lambda:bridge.status(identity).get('status')=='finished')
                status=api('official/status?sessionId='+identity)
                assert status['verdict']=='AC' and status['submissionId']=='101',status
                from System.Windows.Forms import Application
                count=bridge._ui(lambda:Application.OpenForms.Count)
                assert count==1 and len(webview.windows)==1,(count,len(webview.windows))
                assert bridge._ui(lambda:bridge.view.FindForm()==main.native)
                posts=[request for request in requests if request['method']=='POST']
                assert len(posts)==1 and 'fixture-csrf-only' in posts[0]['body'] and 'sourceCode=' in posts[0]['body'],posts
                assert not server.training.submissions()['submissions']
                result.update(singleForm=count,singlePywebviewWindow=len(webview.windows),sameParent=True,fixtureNativePost=True,fixtureReceipt=status)
                api('official/close',{'sessionId':identity})
                assert bridge.panel is None
                assert main.evaluate_js('window.tbNativePreserved.counter')==7
                result['mainPreserved']=True
                # A successful challenge response is not a trustworthy baseline.
                mode['challenge']=True
                opened=api('official/submit',{'id':'ABC 478::D','code':code});identity=opened['sessionId']
                wait(lambda:len([request for request in requests if request['method']=='POST'])==2)
                time.sleep(.2)
                assert bridge.status(identity)['status']!='finished'
                assert not bridge.sessions[identity]['baselineKnown']
                result['challengeNeverCountsOldReceipt']=True
                api('official/close',{'sessionId':identity});mode['challenge']=False
                # Page text listing C++17 cannot masquerade as selected language.
                mode['wrongLanguage']=True
                nowcoder=next(row for row in server.store.data()['rows'] if row.get('url','').startswith('https://ac.nowcoder.com/acm/contest/'))
                opened=api('official/submit',{'id':nowcoder['id'],'code':code});identity=opened['sessionId']
                wait(lambda:bridge.status(identity).get('status')=='error')
                assert len([request for request in requests if request['method']=='POST'])==2
                assert 'C++17' in bridge._ui(lambda:bridge.status_label.Text)
                result['unselectedLanguageNeverSubmitted']=True
                api('official/close',{'sessionId':identity});mode['wrongLanguage']=False
                mode['login']=True
                opened=api('official/submit',{'id':'ABC 478::D','code':code});identity=opened['sessionId']
                wait(lambda:bridge.status(identity).get('status')=='needs_login')
                assert len([request for request in requests if request['method']=='POST'])==2
                bridge._try_submit(identity)
                assert bridge.status(identity)['status']=='needs_login'
                result['loginNeverSubmitted']=True
                api('official/close',{'sessionId':identity})
                # Real first-party login GET, without the fixture interceptor or intent.
                bridge.native_setup=None
                opened=api('official/open',{'id':'ABC 478::D','code':code});identity=opened['sessionId']
                wait(lambda:bridge.status(identity).get('status') in ('needs_login','needs_verification','error'),timeout=30)
                live=bridge.status(identity)
                assert live['status'] in ('needs_login','needs_verification'),live
                result['realLoginGetOnly']=live
                assert bridge._ui(lambda:Application.OpenForms.Count)==1
                api('official/close',{'sessionId':identity})
                assert main.evaluate_js('window.tbNativePreserved.counter')==7
                assert server.store.data_file.read_bytes()==archive
                assert server.training.workspace()['summary']['total']==0
                result['ok']=True
            except Exception as error:result['error']=repr(error)
            finally:
                bridge.close();main.destroy()
        try:webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(temp/'profile'),debug=False)
        finally:server.shutdown();server.server_close();thread.join(2)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert result.get('ok'),result
if __name__=='__main__':run()
