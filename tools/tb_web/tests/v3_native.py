"""Hidden native v3 probe. No real personal state, login, filling, or official submit.

Uses the current built dist, a private disposable WebView profile, an isolated
SQLite store, and a real second WebView loading AtCoder's public login/submit page.
"""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import webview
from backend import create_server
from official_bridge import OfficialBridge


def run():
    result = {}
    with tempfile.TemporaryDirectory(prefix="tb-v3-native-") as directory:
        temporary = Path(directory).resolve()
        server = create_server(port=0, training_file=temporary / "personal.sqlite3",
                               history_file=temporary / "history.jsonl",
                               backup_dir=temporary / "backups",
                               integration_state_dir=temporary / "integrations",
                               integration_auto_start=False)
        archive_before = server.store.data_file.read_bytes()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        original_create = webview.create_window
        window = original_create("TB v3 Hidden Native Probe", url, width=1480, height=920,
                                 hidden=True, background_color="#101116")
        bridge = OfficialBridge(window)
        server.official_opener = bridge.open
        returned = threading.Event()
        return_calls = []
        # Keep the main probe hidden while testing the real JS→Python return API.
        # Native main remains alive; the requested show/restore actions are recorded.
        original_show, original_restore = window.show, window.restore
        window.show = lambda: (return_calls.append("show"), returned.set())
        window.restore = lambda: return_calls.append("restore")

        def hidden_create(*args, **kwargs):
            kwargs["hidden"] = True
            return original_create(*args, **kwargs)

        webview.create_window = hidden_create

        def wait(view, expression, condition, timeout=20):
            deadline = time.monotonic() + timeout
            last = None
            while time.monotonic() < deadline:
                try:
                    last = view.evaluate_js(expression)
                except Exception:
                    time.sleep(.1)
                    continue
                if condition(last):
                    return last
                time.sleep(.1)
            raise AssertionError("Native page did not reach expected state: " + repr(last))

        def check():
            try:
                wait(window, "({nav:document.querySelectorAll('.nav-item').length,title:document.title})",
                     lambda state: state and state.get("nav", 0) >= 9)
                assert server.training.workspace()["summary"]["total"] == 0
                result["initialEmpty"] = True
                window.evaluate_js("document.querySelector('.nav-item[aria-label=\"题库\"]').click()")
                wait(window, "document.querySelectorAll('.problem-table tbody tr').length", lambda count: count and count > 0)
                window.evaluate_js("document.querySelector('.problem-table tbody tr .row-icon.start').click()")
                result["editor"] = wait(window, """(()=>{
                    const content=document.querySelector('.cm-content');
                    return {present:!!content,editable:content?.getAttribute('contenteditable'),
                      role:content?.getAttribute('role'),label:content?.getAttribute('aria-label'),
                      tokens:content?.querySelectorAll('span').length||0,
                      colors:content?[...new Set([...content.querySelectorAll('span')].map(e=>getComputedStyle(e).color))]:[]};
                })()""", lambda state: state and state.get("editable") == "true" and state.get("tokens", 0) > 3)
                assert result["editor"]["label"] == "C++ 代码"
                assert len(result["editor"]["colors"]) >= 3, result["editor"]
                regions = []
                for _ in range(7):
                    regions.append(window.evaluate_js("""(()=>{
                        document.dispatchEvent(new KeyboardEvent('keydown',{key:'F6',bubbles:true}));
                        const e=document.activeElement;
                        return {nav:!!e?.closest('.sidebar nav'),tree:!!e?.closest('.sidebar-tree-scroll'),
                          editor:!!e?.closest('.cm-editor'),console:!!e?.closest('.wb-console'),
                          tag:e?.tagName,label:e?.getAttribute('aria-label')};
                    })()"""))
                assert any(region.get("nav") for region in regions), regions
                assert any(region.get("tree") for region in regions), regions
                assert any(region.get("editor") for region in regions), regions
                result["focusRegions"] = regions
                assert not server.store.extensions.snapshot()["sync"]["busy"]
                assert server.training.workspace()["summary"]["pending"] == 0
                # Only our isolated local API receives this POST. Official navigation is GET.
                code = "// TB_NATIVE_PROBE_DO_NOT_SUBMIT\nint main(){return 0;}\n"
                request = Request(url + "/api/official/open",
                                  data=json.dumps({"id": "ABC 478::D", "code": code}).encode(),
                                  headers={"Content-Type": "application/json", "X-TB-Token": server.store.token},
                                  method="POST")
                with urlopen(request, timeout=10) as response:
                    opened = json.loads(response.read())
                result["officialOpened"] = opened
                assert opened["platform"] == "AtCoder" and opened["status"] == "opened"
                with bridge.lock:
                    official = bridge.windows[opened["sessionId"]]
                assert official is not window
                result["secondNativeWindow"] = len(webview.windows) >= 2
                assert result["secondNativeWindow"]
                page = wait(official, """(()=>({url:location.href,title:document.title,
                  toolbar:!!document.getElementById('tb-official-toolbar'),
                  actions:document.querySelectorAll('#tb-official-toolbar button').length,
                  codeFilled:[...document.querySelectorAll('input,textarea')].some(e=>(e.value||'').includes('TB_NATIVE_PROBE_DO_NOT_SUBMIT')),
                  body:(document.body?.innerText||'').slice(0,800)}))()""",
                            lambda state: state and state.get("toolbar") and state.get("actions") == 4,
                            timeout=35)
                assert urlsplit(page["url"]).hostname == "atcoder.jp", page
                assert not page["codeFilled"], "Code was filled without explicit action"
                assert "chrome-error" not in page["url"]
                result["officialPage"] = {key: page[key] for key in ("url", "title", "toolbar", "actions", "codeFilled")}
                # Invoke only the Return control. Never invoke Fill, Copy, login or submit.
                try:
                    official.evaluate_js("document.querySelectorAll('#tb-official-toolbar button')[3].click(); true")
                except Exception:
                    if not returned.is_set():
                        raise
                assert returned.wait(5), "Return-to-TB JS API did not reach Python"
                deadline = time.monotonic() + 5
                while bridge.windows and time.monotonic() < deadline:
                    time.sleep(.05)
                assert not bridge.windows
                result["returnCalls"] = return_calls
                assert return_calls == ["show", "restore"], return_calls
                assert window.evaluate_js("!!document.querySelector('.cm-content')")
                result["mainStillResponsive"] = True
                assert server.training.workspace()["summary"]["pending"] == 0
                assert server.training.submissions()["submissions"] == []
                assert server.store.data_file.read_bytes() == archive_before
                result["ok"] = True
            except Exception as error:
                result["error"] = repr(error)
            finally:
                bridge.close()
                window.destroy()

        try:
            webview.start(check, gui="edgechromium", private_mode=True,
                          storage_path=str(temporary / "webview-profile"), debug=False)
        finally:
            webview.create_window = original_create
            window.show, window.restore = original_show, original_restore
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    assert result.get("ok"), result


if __name__ == "__main__":
    run()
