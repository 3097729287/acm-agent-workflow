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
    result={};phase={'value':'main'};requests=[];mode={'language':'C++(g++ 13)'}
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
                if str(request.Method)=='POST':
                    content='<html><title>submitted fixture</title><body>Submitted</body></html>'
                elif '/submissions/me' in str(request.Uri):
                    content='<html><table><tr><th>Submission</th><th>Status</th></tr></table></html>'
                else:
                    content=f'<html><title>compiler fixture</title><body><header id="account">fixture-user · Login</header><form method="post" action="/contests/abc478/submit"><select name="taskScreenName"><option value="abc478_d">D</option></select><select name="languageId"><option value="native-compiler">{mode["language"]}</option></select><textarea name="sourceCode"></textarea><button type="submit">Submit</button></form></body></html>'
                event.Response=core.Environment.CreateWebResourceResponse(MemoryStream(Encoding.UTF8.GetBytes(content)),200,'OK','Content-Type: text/html; charset=utf-8')
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
                values=[]
                for label in ['C++(g++ 13)','GNU G++17 7.3.0','GNU G++23 14.2 (64 bit)']:
                    phase['value']=label;mode['language']=label;before=sum(method=='POST' for method,_,_ in requests)
                    session=bridge.submit('https://atcoder.jp/contests/abc478/tasks/abc478_d','int main(){}',label)
                    wait(lambda:sum(method=='POST' for method,_,_ in requests)>before)
                    geometry=bridge._ui(lambda:{'browserTop':bridge.view.Top,'browserHeight':bridge.view.Height,'toolbarBottom':bridge.status_label.Parent.Bottom,'parentHeight':bridge.panel.Height,'toolbarBackground':str(bridge.status_label.Parent.BackColor),'buttonTextColor':str(bridge.status_label.Parent.Controls[0].ForeColor)})
                    assert geometry['browserTop']>=geometry['toolbarBottom'],geometry
                    assert geometry['browserHeight']>0 and geometry['parentHeight']>=geometry['browserTop']+geometry['browserHeight'],geometry
                    status=bridge.status(session['sessionId']);assert status.get('compiler')==label,status
                    values.append({'language':label,'geometry':geometry,'accepted':True})
                    bridge.close(session['sessionId']);assert main.evaluate_js('window.preserved')==7
                assert all('sourceCode=' in body for method,_,body in requests if method=='POST')
                result.update(ok=True,compilerCases=values,fixturePosts=sum(method=='POST' for method,_,_ in requests),mainPreserved=True)
            except Exception as error:result.update(error=repr(error),phase=phase['value'],requests=requests,sessions=bridge.sessions)
            finally:main.destroy()
        webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(Path(directory)/'profile'),debug=False)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert result.get('ok'),result


if __name__=='__main__':run()
