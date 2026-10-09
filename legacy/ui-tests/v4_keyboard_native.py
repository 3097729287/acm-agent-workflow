"""Real native keys on a disposable, intercepted official-origin pane.

The temporary window is briefly shown to give SendKeys a real foreground target.
Every official-origin request, including the fixture POST, is intercepted before
network. No account, archive, personal database or live OJ is used.
"""
import ctypes
import json
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import webview
from official_bridge import OfficialBridge

URL='https://atcoder.jp/contests/abc478/tasks/abc478_d'
FORM='''<html><title>TB keyboard fixture</title><body><form method="post" action="/contests/abc478/submit">
<select name="taskScreenName"><option value="abc478_d">D</option></select>
<select name="languageId"><option value="1">C++17</option></select>
<textarea name="sourceCode" id="sourceCode"></textarea><button type="submit">Submit fixture</button>
</form></body></html>'''
def receipt(identity):return f'<html><table><thead><tr><th>Submission</th><th>Status</th></tr></thead><tr><td><a href="/contests/abc478/submissions/{identity}">{identity}</a><a href="/contests/abc478/tasks/abc478_d">D</a></td><td><span class="label">AC</span></td></tr></table></html>'

def run():
    result={};requests=[];key_events=[]
    with tempfile.TemporaryDirectory(prefix='tb-v4-keyboard-',ignore_cleanup_errors=True) as directory:
        main=webview.create_window('TB temporary native keyboard fixture',html='<html><body><input id="mainInput"><script>window.preserved=7</script></body></html>',hidden=True,width=1050,height=700)
        def fixture(view):
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            from System.IO import MemoryStream
            from System.Text import Encoding
            core=view.CoreWebView2;core.AddWebResourceRequestedFilter('*',CoreWebView2WebResourceContext.All)
            from System.Reflection import BindingFlags
            from System.Windows.Forms import Control
            controller=view.GetType().GetField('_coreWebView2Controller',BindingFlags.Instance|BindingFlags.NonPublic).GetValue(view)
            def key(_,event):key_events.append({'kind':str(event.KeyEventKind),'key':int(event.VirtualKey),'modifiers':str(Control.ModifierKeys),'alt':bool(event.PhysicalKeyStatus.IsMenuKeyDown),'repeat':bool(event.PhysicalKeyStatus.WasKeyDown),'handled':bool(event.Handled)})
            controller.AcceleratorKeyPressed+=key
            def serve(_,event):
                method=str(event.Request.Method);url=str(event.Request.Uri);requests.append((method,url))
                content=receipt('101') if method=='POST' else receipt('100') if '/submissions/me' in url else FORM
                event.Response=core.Environment.CreateWebResourceResponse(MemoryStream(Encoding.UTF8.GetBytes(content)),200,'OK','Content-Type: text/html; charset=utf-8')
            core.WebResourceRequested+=serve
        bridge=OfficialBridge(main,native_setup=fixture)
        main.events.closing+=bridge.on_closing
        def wait(check,timeout=8):
            until=time.monotonic()+timeout
            while time.monotonic()<until:
                value=check()
                if value:return value
                time.sleep(.05)
            return False
        def foreground():
            ctypes.windll.user32.GetForegroundWindow.restype=ctypes.c_void_p
            return ctypes.windll.user32.GetForegroundWindow()==int(main.native.Handle.ToInt64())
        def send(keys):
            assert foreground(),'No keys sent because fixture is not foreground'
            from System.Windows.Forms import SendKeys
            bridge._ui(lambda:SendKeys.SendWait(keys))
            time.sleep(.1)
        def focus_editor():
            def activate():
                main.native.Show();main.native.Activate();bridge.view.Focus()
            bridge._ui(activate)
            assert wait(foreground),'Fixture could not acquire foreground'
            time.sleep(.25)
            bridge._ui(lambda:bridge.view.Focus())
            assert bridge._eval("document.querySelector('textarea').focus();document.activeElement.id")=='sourceCode'
            time.sleep(.15)
        def verify():
            try:
                assert wait(lambda:main.evaluate_js('window.preserved')==7)
                opened=bridge.open(URL,'int main(){}','fixture');identity=opened['sessionId']
                assert wait(lambda:bridge.status(identity).get('status')=='ready')
                focus_editor();send('abs')
                result['ordinaryActual']=bridge._eval("document.querySelector('textarea').value")
                result['nativeFocus']=bridge._ui(lambda:str(main.native.ActiveControl))
                from System.Reflection import BindingFlags
                flags=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic
                result['controllerProperties']=bridge._ui(lambda:[str(p.Name) for p in bridge.view.GetType().GetProperties(flags) if 'controller' in str(p.Name).lower()])
                result['controllerFields']=bridge._ui(lambda:[str(p.Name)+':'+str(p.FieldType) for p in bridge.view.GetType().GetFields(flags) if 'controller' in str(p.Name).lower()])
                result['ordinaryInput']=all(letter in result['ordinaryActual'] for letter in 'abs')
                result['ordinaryInputNeverSubmitted']=not any(method=='POST' for method,_ in requests)
                # Complete any system IME composition before testing an Alt
                # accelerator; keep focus inside the original textarea.
                send('{ESC}')
                assert bridge._eval('document.activeElement.id')=='sourceCode'
                send('%b');result['altBFromEditor']=bool(wait(lambda:bridge.panel is None,timeout=2));result['keyEvents']=key_events
                if bridge.panel is not None:bridge.close(identity)
                result['mainPreserved']=main.evaluate_js('window.preserved')==7
                opened=bridge.open(URL,'int main(){}','fixture');identity=opened['sessionId']
                assert wait(lambda:bridge.status(identity).get('status')=='ready')
                focus_editor()
                for _ in range(10):
                    send('{TAB}')
                    toolbar=bridge._ui(lambda:any(control.Focused for control in bridge.status_label.Parent.Controls))
                    if toolbar:break
                result['tabReachesToolbar']=bool(toolbar)
                focus_editor();send('%s')
                result['altSFixtureSubmit']=bool(wait(lambda:any(method=='POST' for method,_ in requests),timeout=3))
                result['fixturePosts']=sum(method=='POST' for method,_ in requests)
                result['singleForm']=bridge._ui(lambda:__import__('System.Windows.Forms',fromlist=['Application']).Application.OpenForms.Count)==1
                result['ok']=all(result.get(key) for key in ('ordinaryInput','ordinaryInputNeverSubmitted','altBFromEditor','mainPreserved','tabReachesToolbar','altSFixtureSubmit','singleForm'))
            except Exception as error:result['error']=repr(error)
            finally:main.destroy()
        webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(Path(directory)/'profile'),debug=False)
        time.sleep(1)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert result.get('ok'),result
if __name__=='__main__':run()
