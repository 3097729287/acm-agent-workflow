"""Three hidden native launches prove normal bounds and maximized restoration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'backend')]


def phase(directory,number):
    import webview
    from window_memory import bind,remembered
    from persistence import load_document
    path=directory/'desktop-window.json'
    bounds=remembered(path)
    window=webview.create_window('TB hidden window memory proof',html='<html><body>Fixture</body></html>',
                                **bounds,hidden=True)
    bind(window,path)
    result={}
    def verify():
        from System import Action
        from System.Drawing import Point,Size
        from System.Windows.Forms import FormWindowState
        try:
            window.events.loaded.wait(20)
            assert window.native is not None, 'Native window did not initialize'
            values=[]
            def inspect():
                form=window.native
                if number==1:form.Location=Point(40,50);form.Size=Size(1200,760)
                rectangle=form.Bounds if form.WindowState==FormWindowState.Normal else form.RestoreBounds
                values.append({'x':rectangle.X,'y':rectangle.Y,'width':rectangle.Width,'height':rectangle.Height,
                               'maximized':form.WindowState==FormWindowState.Maximized})
                if number==2:form.WindowState=FormWindowState.Maximized
            window.native.Invoke(Action(inspect))
            actual=values[0]
            if number>1:
                expected=remembered(path)
                assert actual==expected,(number,actual,expected)
            result.update(ok=True,phase=number,observed=actual)
        except Exception as error:result.update(ok=False,error=repr(error))
        finally:window.destroy()
    webview.start(verify,gui='edgechromium',private_mode=True,storage_path=str(directory/('profile-'+str(number))))
    saved=load_document(path,{})
    assert saved and (number!=2 or saved['maximized']),saved
    print(json.dumps(result),flush=True)
    assert result.get('ok'),result


def run():
    with tempfile.TemporaryDirectory(prefix='tb-window-proof-',ignore_cleanup_errors=True) as temporary:
        directory=Path(temporary)
        for number in (1,2,3):
            value=subprocess.run([sys.executable,str(Path(__file__).resolve()),str(directory),str(number)],
                                 env=dict(os.environ,TB_STATE_DIR=str(directory),TB_OFFLINE='1'),
                                 capture_output=True,text=True,encoding='utf-8',timeout=45,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if value.returncode:raise AssertionError(value.stdout+'\n'+value.stderr)
            print(value.stdout.strip(),flush=True)


if __name__=='__main__':
    if len(sys.argv)==3:phase(Path(sys.argv[1]),int(sys.argv[2]))
    else:run()
