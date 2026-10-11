"""Authenticated original-site submission in background WebView2 sessions."""
from __future__ import annotations
import datetime as dt
import json
import logging
import threading
import uuid
import sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,urlencode

HOSTS={'codeforces.com':'Codeforces','www.codeforces.com':'Codeforces','atcoder.jp':'AtCoder','ac.nowcoder.com':'牛客','www.luogu.com.cn':'洛谷','luogu.com.cn':'洛谷'}
LOGIN_HOSTS={'Codeforces':{'codeforces.com','www.codeforces.com'},'AtCoder':{'atcoder.jp'},'牛客':{'ac.nowcoder.com','nowcoder.com','www.nowcoder.com'},'洛谷':{'www.luogu.com.cn','luogu.com.cn','login.luogu.com.cn'}}
STATUSES={'loading','needs_login','needs_verification','ready','submitted','judging','finished','error','closed','hidden'}

def submission_target(url):
    import re
    p=urlsplit(url or '');platform=HOSTS.get((p.hostname or '').lower());problem='';path=p.path
    if not platform or p.scheme not in ('https','http') or p.username or p.password or p.port not in (None,80,443):raise ValueError('只能打开题库中四个竞赛平台的官方题目地址')
    if platform=='Codeforces':
        m=re.fullmatch(r'/(contest|gym)/(\d+)/problem/([A-Za-z]\d?)',path)
        if m:kind,contest,problem=m.groups();path=f'/{kind}/{contest}/submit'
        else:
            m=re.fullmatch(r'/problemset/problem/(\d+)/([A-Za-z]\d?)',path)
            if not m:raise ValueError('Codeforces 题目地址无效')
            contest,problem=m.groups();path=f'/contest/{contest}/submit'
    elif platform=='AtCoder':
        m=re.fullmatch(r'/contests/([\w-]+)/tasks/([\w-]+)',path)
        if not m:raise ValueError('AtCoder 题目地址无效')
        contest,problem=m.groups();path=f'/contests/{contest}/submit'
    elif platform=='牛客':
        if not re.fullmatch(r'/acm/contest/\d+/[A-Za-z]\d?',path):raise ValueError('牛客题目地址无效')
        problem=path.rsplit('/',1)[-1]
    elif not re.fullmatch(r'/problem/[A-Za-z0-9_]+',path):raise ValueError('洛谷题目地址无效')
    query=urlencode({'taskScreenName':problem}) if platform=='AtCoder' else ''
    return {'platform':platform,'url':urlunsplit(('https',p.netloc,path,query,'submit' if platform=='洛谷' else '')),'problem':problem,'originalUrl':url}

def page_script(session,action='inspect'):
    context=json.dumps({k:session.get(k) for k in ('sessionId','platform','problem','code','originalUrl','attempted','baseline','baselineKnown','baselineOwner')},ensure_ascii=True)
    asset_root=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    languages=(asset_root/'official_languages.js').read_text(encoding='utf-8')
    nowcoder=(asset_root/'official_nowcoder.js').read_text(encoding='utf-8')
    return r'''(()=>{
const ctx=CONTEXT,action=ACTION;
COMPILER_SELECTION
NOWCODER_RECEIPTS
const ncReceipt=installNowcoderReceipts(ctx);

const send=value=>{chrome.webview.postMessage(JSON.stringify({tbOfficial:true,sessionId:ctx.sessionId,...value}));return value;};
const visible=e=>e&&e.getClientRects().length>0;
const editors=()=>[...document.querySelectorAll('textarea')].filter(e=>/source|code|editor/i.test((e.name||'')+' '+(e.id||'')));
const hasEditor=()=>editors().length||document.querySelector('.CodeMirror,.ace_editor,.monaco-editor');
const login=()=>[...document.querySelectorAll('input[type=password]')].some(visible)||/\/login|\/enter(?:\/|$)|\/auth\/login/i.test(location.pathname);
const verification=()=>!hasEditor()&&(/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(document.title+' '+(document.body?.innerText||'').slice(0,1200))||[...document.querySelectorAll('iframe')].some(e=>visible(e)&&/captcha|challenge/i.test(e.src)));
function normal(text){
text=(text||'').trim().replace(/_/g,' ').replace(/\s+/g,' ');
const map={'AC':'AC','OK':'AC','ACCEPTED':'AC','通过':'AC','WA':'WA','WRONG ANSWER':'WA','答案错误':'WA','TLE':'TLE','TIME LIMIT EXCEEDED':'TLE','超时':'TLE','MLE':'MLE','MEMORY LIMIT EXCEEDED':'MLE','内存超限':'MLE','RE':'RE','RUNTIME ERROR':'RE','运行错误':'RE','CE':'CE','COMPILATION ERROR':'CE','COMPILE ERROR':'CE','编译错误':'CE','OLE':'OLE','OUTPUT LIMIT EXCEEDED':'OLE'};
const exact=map[text.toUpperCase()];if(exact)return exact;
for(const [label,value] of Object.entries(map))if(label.length>3&&new RegExp('^'+label+'(?:\\s+(?:on|in|at)\\b|$)','i').test(text))return value;
return /^(WJ|WR|TESTING|Judging|Running|Waiting|Pending|Queuing|评测中|等待评测)(\b|$)/i.test(text)?'JUDGING':null;
}
function taskPath(path){return path.replace(/^\/problemset\/problem\/(\d+)\/([A-Za-z]\d?)$/,'/contest/$1/problem/$2');}
function receipts(doc=document){const rows=[];doc.querySelectorAll('tr').forEach(row=>{const links=[...row.querySelectorAll('a[href]')];const a=links.find(a=>/\/submission(?:s)?\/\d+/.test(a.getAttribute('href')||''));if(!a)return;const id=(a.getAttribute('href')||'').match(/\/submission(?:s)?\/(\d+)/)?.[1];const task=links.some(a=>{try{const target=new URL(a.getAttribute('href'),location.href),original=new URL(ctx.originalUrl);return target.origin===location.origin&&taskPath(target.pathname)===taskPath(original.pathname)}catch{return false}});const owner=!ctx.baselineOwner||links.some(a=>{try{const link=new URL(a.getAttribute('href'),location.href);return link.origin===location.origin&&link.pathname==='/profile/'+ctx.baselineOwner}catch{return false}});const verdict=[...row.querySelectorAll('.label,.submissionVerdictWrapper,.verdict,[data-verdict],.verdict-accepted,.verdict-rejected,.status-cell')].map(e=>normal(e.getAttribute('data-verdict')||e.getAttribute('verdict')||e.textContent)).find(Boolean);if(id&&task&&owner)rows.push({id,verdict});});return rows;}
function newerReceipt(id,baseline){
if(!/^\d+$/.test(id))return false;
const previous=[...baseline].filter(value=>/^\d+$/.test(value));
return !baseline.has(id)&&previous.every(value=>BigInt(id)>BigInt(value));
}
function inspect(){
if(login()||(ctx.platform==='牛客'&&window.globalInfo?.ownerId!=null&&Number(window.globalInfo.ownerId)<=0))return {status:'needs_login',message:'请先登录授权，完成后回到 TB 点击提交。'};
if(verification())return {status:'needs_verification',message:'官方要求验证，请完成验证后回到 TB 点击提交。'};
if(ncReceipt?.receipt)return ncReceipt.receipt;
if(ctx.attempted&&ctx.baselineKnown){const baseline=new Set(ctx.baseline||[]);const receipt=receipts().find(r=>newerReceipt(r.id,baseline));if(receipt?.verdict)return {status:receipt.verdict==='JUDGING'?'judging':'finished',submissionId:receipt.id,verdict:receipt.verdict==='JUDGING'?undefined:receipt.verdict,message:receipt.verdict==='JUDGING'?'原站已接收，正在评测。':'已读取原站本次新提交结果：'+receipt.verdict};}
return hasEditor()?{status:ctx.attempted?'submitted':'ready',message:ctx.attempted?'提交操作已发出，等待可靠原站回执；暂不宣称通过。':'官方编辑器已就绪；提交使用原站正常控件。'}:{status:ctx.attempted?'submitted':'loading',message:ctx.attempted?'等待原站回执；无可靠结果时不宣称通过。':'正在加载原站，可在当前面板登录或进入提交页。'};
}
async function submit(){
const state=inspect();if(['needs_login','needs_verification'].includes(state.status))return send(state);
if(!hasEditor())return send({status:'error',message:'没有找到原站代码编辑器，请进入本题提交页；不会点击其它表单。'});
let task=!ctx.problem,filled=0;
document.querySelectorAll('select').forEach(s=>{const field=(s.name||s.id||'').toLowerCase();if(/problem|task/.test(field)&&ctx.problem){const o=[...s.options].find(o=>o.value===ctx.problem);if(o){s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));task=true;}}});
if(['牛客','洛谷'].includes(ctx.platform))task=location.pathname===new URL(ctx.originalUrl).pathname;
if(!task)return send({status:'error',message:'未能准确选定本题，已停止；请在原站确认题目。'});
const compiler=await selectOfficialCompiler(ctx.code,ctx.platform);
if(!compiler)return send({status:'error',message:'没有找到支持当前代码的 C++17 / C++20 / C++23 编译器，请在原站确认语言后重试。'});
editors().forEach(e=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,ctx.code);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));filled++;});
document.querySelectorAll('.CodeMirror').forEach(e=>{if(e.CodeMirror){e.CodeMirror.setValue(ctx.code);filled++;}});document.querySelectorAll('.ace_editor').forEach(e=>{try{if(window.ace){window.ace.edit(e).setValue(ctx.code,-1);filled++;}}catch{}});try{window.monaco?.editor?.getModels?.().filter(m=>!m.isDisposed()&&/cpp|c\+\+/.test(m.getLanguageId?.()||'')).forEach(m=>{m.setValue(ctx.code);filled++;});}catch{}
if(!filled)return send({status:'error',message:'编辑器接口不可用，请手动粘贴并提交；未发出自动提交。'});
let baseline=[],baselineKnown=false,baselineOwner='';
if(ctx.platform==='Codeforces'){
const profile=[...document.querySelectorAll('#header a[href],.lang-chooser a[href]')].map(a=>{try{const url=new URL(a.getAttribute('href'),location.href);return url.origin===location.origin&&url.pathname.match(/^\/profile\/([A-Za-z0-9_.-]{1,64})$/)?.[1]}catch{return null}}).find(Boolean);
baselineOwner=profile||'';
}
try{let path=null;if(ctx.platform==='AtCoder')path=location.pathname.replace(/\/submit$/,'/submissions/me');if(ctx.platform==='Codeforces')path=location.pathname.replace(/\/submit$/,'/my');if(path){const r=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(r.ok&&new URL(r.url).origin===location.origin&&new URL(r.url).pathname===path){const html=await r.text();const doc=new DOMParser().parseFromString(html.slice(0,2000000),'text/html');const challenge=/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(doc.title+' '+(doc.body?.textContent||'').slice(0,1200));const table=doc.querySelector('table.status-frame-datatable')||[...doc.querySelectorAll('table')].some(t=>/submission|提出|提交|status|verdict|結果|时间|when/i.test([...t.querySelectorAll('th, tr:first-child td')].map(e=>e.textContent).join(' ')));if(!challenge&&table&&!doc.querySelector('input[type=password],iframe[src*=captcha],iframe[src*=challenge]')){baseline=receipts(doc).map(r=>r.id);baselineKnown=true;}}}}catch{}
// The official public API provides a bounded snapshot when the HTML list is
// unavailable. Only the authenticated page's own handle is used. A global ID
// lower bound prevents older records outside this snapshot from becoming AC.
if(ctx.platform==='Codeforces'&&!baselineKnown&&baselineOwner){
try{const r=await fetch('/api/user.status?handle='+encodeURIComponent(baselineOwner)+'&from=1&count=100',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(r.ok){const value=await r.json();if(value.status==='OK'&&Array.isArray(value.result)&&value.result.every(row=>Number.isSafeInteger(row.id)&&row.id>0)){baseline=value.result.map(row=>String(row.id));baselineKnown=true;}}}catch{}
}
const form=editors().map(e=>e.closest('form')).find(Boolean)||[...document.querySelectorAll('form')].find(f=>f.querySelector('.CodeMirror,.ace_editor,.monaco-editor'));
let button=form?.querySelector('button[type=submit],input[type=submit],#submit');if(!button&&['牛客','洛谷'].includes(ctx.platform))button=[...document.querySelectorAll('button,[role=button],.submit-btn,.submit-button')].find(b=>visible(b)&&!b.disabled&&/^(?:保存并)?提交(?:代码|题目|评测)?$/.test(b.textContent.trim()));
if(!button)return send({status:'error',message:'未找到与代码编辑器对应的官方提交控件，请手动提交；未点击其它按钮。'});
if(ncReceipt){ncReceipt.armed=true;ncReceipt.pending=null;ncReceipt.receipt=null;}
send({status:'submitted',message:'已选择 '+compiler.label+(baselineKnown||ncReceipt?'，等待原站回执。':'；已发出官方提交，但暂未取得可核对的提交记录，请在原站查看结果。'),compiler:compiler.label,baseline,baselineKnown,baselineOwner,attempted:true});button.click();return {status:'submitted'};
}
if(action==='submit'){submit().catch(e=>send({status:'error',message:'表单操作未完成：'+String(e).slice(0,160)}));return {status:'loading'};}
const state=inspect();
if(ctx.platform==='Codeforces'&&ctx.attempted&&ctx.baselineKnown&&ctx.baselineOwner&&state.status!=='finished'){
  (async()=>{try{
    const response=await fetch('/api/user.status?handle='+encodeURIComponent(ctx.baselineOwner)+'&from=1&count=100',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(!response.ok||new URL(response.url,location.href).origin!==location.origin)return;
    const value=await response.json(),original=new URL(ctx.originalUrl),match=taskPath(original.pathname).match(/^\/(?:contest|gym)\/(\d+)\/problem\/([A-Za-z]\d?)$/);
    if(value.status!=='OK'||!Array.isArray(value.result)||!match)return;
    const baseline=new Set(ctx.baseline||[]);
    const receipt=value.result.filter(row=>Number.isSafeInteger(row.id)&&newerReceipt(String(row.id),baseline)&&String(row.problem?.contestId)===match[1]&&row.problem?.index===match[2]&&row.author?.members?.some(member=>member.handle?.toLowerCase()===ctx.baselineOwner.toLowerCase())).sort((a,b)=>a.id-b.id)[0];
    if(!receipt)return;
    const verdict=normal(receipt.verdict)||'JUDGING';
    send({status:verdict==='JUDGING'?'judging':'finished',submissionId:String(receipt.id),...(verdict==='JUDGING'?{}:{verdict}),message:verdict==='JUDGING'?'原站已接收，正在评测。':'已读取原站本次新提交结果：'+verdict});
  }catch{}})();
}
return state;
})()'''.replace('COMPILER_SELECTION',languages,1).replace('NOWCODER_RECEIPTS',nowcoder,1).replace('ACTION',json.dumps(action),1).replace('CONTEXT',context,1)


class OfficialBridge:
    def __init__(self, main_window, guard=None, native_setup=None, on_receipt=None,
                 on_pending=None, resume_loader=None):
        self.main_window, self.guard, self.native_setup = main_window, guard, native_setup
        self.on_receipt, self.on_pending, self.resume_loader = on_receipt, on_pending, resume_loader
        self.lock = threading.RLock()
        self.sessions, self.views = {}, {}
        self.current = None
        self.panel = self.view = self.status_label = self.view_identity = None
        self.stopping = threading.Event()

    def _ui(self, action):
        from training import ServiceError
        form = getattr(self.main_window, 'native', None)
        if form is None or form.IsDisposed:
            raise ServiceError(503, '原生主窗口尚未就绪，请稍后重试')
        if not form.InvokeRequired:
            return action()
        from System import Action
        result = []
        form.Invoke(Action(lambda: result.append(action())))
        return result[0] if result else None

    def _eval(self, script, timeout=12, identity=None):
        from System import Action, String
        from System.Threading.Tasks import Task
        done, result = threading.Event(), []
        def completed(task):
            try:
                result.append(json.loads(str(task.Result)))
            except Exception:
                result.append(None)
            finally:
                done.set()
        def evaluate():
            entry = self.views.get(identity or self.view_identity)
            if not entry or entry['view'].IsDisposed or not entry['view'].CoreWebView2:
                done.set()
                return
            entry['view'].CoreWebView2.ExecuteScriptAsync(script).ContinueWith(Action[Task[String]](completed))
        self._ui(evaluate)
        return result[0] if done.wait(timeout) and result else None

    def _update(self, identity, value):
        if not isinstance(value, dict):
            return
        with self.lock:
            session = self.sessions.get(identity)
            if not session or session['status'] in ('closed', 'finished'):
                return
            # A navigation/inspection may finish after the submit response.
            if session.get('attempted') and value.get('status') in ('ready', 'loading'):
                return
            if session.get('submitting') and value.get('status') == 'ready':
                return
            if value.get('attempted') or value.get('status') in ('needs_login', 'needs_verification', 'error'):
                session['submitting'] = False
            for key in ('status', 'message', 'submissionId', 'verdict', 'attempted',
                        'baseline', 'baselineKnown', 'baselineOwner', 'compiler', 'acceptedAt'):
                if key in value:
                    session[key] = value[key]
            if session['status'] not in STATUSES:
                session['status'] = 'error'
            session['updatedAt'] = dt.datetime.now(dt.timezone.utc).isoformat()
            if session.get('attempted') and not session.get('acceptedAt'):
                session['acceptedAt'] = session['updatedAt']
            snapshot = dict(session)
        if snapshot.get('submissionId') and snapshot.get('acceptedAt') and self.on_pending and not snapshot.get('pendingSaved'):
            try:
                if self.on_pending(identity, snapshot) is not None:
                    with self.lock:
                        session['pendingSaved'] = True
            except Exception:
                logging.exception('Official pending could not be saved')
        if snapshot['status'] == 'finished' and self.on_receipt:
            try:
                saved = self.on_receipt(identity, snapshot)
            except Exception:
                logging.exception('Official receipt could not be saved')
                saved = False
            if saved is False:
                with self.lock:
                    session.update(status='judging', saveError=True,
                                   message='官方结果保存失败，正在重试。')
        def display():
            entry = self.views.get(identity)
            if entry and not entry['label'].IsDisposed:
                entry['label'].Text = session.get('message', '')[:240]
        try:
            self._ui(display)
        except Exception:
            logging.debug('Official session display unavailable', exc_info=True)

    def _try_submit(self, identity):
        with self.lock:
            session = self.sessions.get(identity)
            if not session or session.get('attempted') or session.get('submitting'):
                return
            if session['status'] != 'ready':
                session['intent'] = False
                return
            session['submitting'] = True
            snapshot = dict(session)
            session.update(status='loading', message='正在向官方提交代码。')
        try:
            if self.guard:
                self.guard(snapshot['originalUrl'])
            self._eval(page_script(snapshot, 'submit'), identity=identity)
        except Exception as error:
            self._update(identity, {'status': 'error', 'message': '提交已停止：' + str(error)[:180]})

    def _inspect(self, identity):
        with self.lock:
            session = self.sessions.get(identity)
            if not session or session['status'] in ('closed', 'finished'):
                return
            snapshot = dict(session)
        self._update(identity, self._eval(page_script(snapshot), identity=identity))
        with self.lock:
            intent = session.get('intent') and session['status'] == 'ready'
            if session['status'] in ('needs_login', 'needs_verification', 'error') or intent:
                session['intent'] = False
        if intent:
            self._try_submit(identity)

    def _watch_receipts(self, identity):
        deadline = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=15)
        while not self.stopping.wait(2.5):
            with self.lock:
                session = self.sessions.get(identity)
                if not session or session['status'] == 'closed':
                    return
                terminal = session['status'] in ('finished', 'error')
            if terminal:
                self.release(identity)
                return
            if dt.datetime.now(dt.timezone.utc) > deadline:
                self._update(identity, {'status': 'error', 'message': '等待官方结果超时。请核对官方提交记录后重试。'})
                return
            try:
                self._inspect(identity)
            except Exception:
                logging.debug('Official receipt not ready', exc_info=True)

    def _attach(self, identity, foreground=False):
        import System.Windows.Forms as Forms
        from System.Drawing import Color, ContentAlignment
        from Microsoft.Web.WebView2.WinForms import WebView2, CoreWebView2CreationProperties
        import webview
        form, session = self.main_window.native, self.sessions[identity]
        panel = Forms.TableLayoutPanel()
        panel.Dock = Forms.DockStyle.Fill
        panel.ColumnCount, panel.RowCount = 1, 2
        panel.Margin = panel.Padding = Forms.Padding(0)
        panel.BackColor = Color.FromArgb(246, 248, 251)
        panel.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Percent, 100))
        panel.RowStyles.Add(Forms.RowStyle(Forms.SizeType.Absolute, 54))
        panel.RowStyles.Add(Forms.RowStyle(Forms.SizeType.Percent, 100))
        bar = Forms.TableLayoutPanel()
        bar.Dock = Forms.DockStyle.Fill
        bar.ColumnCount, bar.RowCount = 2, 1
        bar.Padding = Forms.Padding(8, 7, 8, 7)
        bar.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Absolute, 190))
        bar.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Percent, 100))
        back = Forms.Button()
        back.Text, back.Dock = '完成授权 / 返回 TB (&B)', Forms.DockStyle.Fill
        back.BackColor, back.ForeColor = Color.White, Color.FromArgb(34, 48, 65)
        back.Click += lambda *_: self.close(identity)
        label = Forms.Label()
        label.Text = session['platform'] + ' · 请使用官方账号登录，完成后返回 TB 点击提交。'
        label.Dock, label.TextAlign = Forms.DockStyle.Fill, ContentAlignment.MiddleLeft
        label.ForeColor, label.AutoEllipsis = back.ForeColor, True
        bar.Controls.Add(back, 0, 0)
        bar.Controls.Add(label, 1, 0)
        view = WebView2()
        view.Dock, view.Margin = Forms.DockStyle.Fill, Forms.Padding(0)
        props = CoreWebView2CreationProperties()
        props.UserDataFolder = form.browser.user_data_folder
        props.set_IsInPrivateModeEnabled(webview._state['private_mode'])
        view.CreationProperties, view.DefaultBackgroundColor = props, Color.White
        panel.Controls.Add(bar, 0, 0)
        panel.Controls.Add(view, 0, 1)
        form.Controls.Add(panel)
        self.views[identity] = {'panel': panel, 'view': view, 'label': label}
        self.panel, self.view, self.status_label, self.view_identity = panel, view, label, identity
        panel.Visible = False
        if foreground:
            self._reopen(identity)
        def navigation(_, args):
            target = urlsplit(str(args.Uri))
            if target.scheme != 'https' or target.hostname not in LOGIN_HOSTS[session['platform']]:
                args.Cancel = True
                self._update(identity, {'status': 'error', 'message': '已阻止离开该平台官方登录与提交地址。'})
        def message(_, args):
            try:
                if urlsplit(str(args.Source)).hostname not in LOGIN_HOSTS[session['platform']]:
                    return
                value = json.loads(str(args.TryGetWebMessageAsString()))
                if value.get('tbOfficial') and value.get('sessionId') == identity:
                    self._update(identity, value)
            except Exception:
                logging.exception('Official native status message failed')
        def loaded(_, args):
            if args.IsSuccess:
                threading.Thread(target=self._inspect, args=(identity,), daemon=True).start()
            else:
                self._update(identity, {'status': 'error', 'message': '官方页面加载失败，请检查网络后重试。'})
        def initialized(_, args):
            if not args.IsSuccess:
                self._update(identity, {'status': 'error', 'message': '官方登录组件初始化失败，请检查 WebView2。'})
                return
            core = view.CoreWebView2
            core.Settings.AreDevToolsEnabled = core.Settings.IsStatusBarEnabled = False
            core.NavigationStarting += navigation
            core.WebMessageReceived += message
            def popup(_, event):
                event.Handled = True
                target = urlsplit(str(event.Uri))
                if target.scheme == 'https' and target.hostname in LOGIN_HOSTS[session['platform']]:
                    core.Navigate(str(event.Uri))
            core.NewWindowRequested += popup
            if self.native_setup:
                self.native_setup(view)
            core.Navigate(session['url'])
        view.CoreWebView2InitializationCompleted += initialized
        view.NavigationCompleted += loaded
        view.EnsureCoreWebView2Async(form.browser.webview.CoreWebView2.Environment)
        threading.Thread(target=self._watch_receipts, args=(identity,), daemon=True).start()

    def _open(self, url, code, title, intent):
        from training import ServiceError
        from insights import canonical_url
        target = submission_target(url)
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 65536:
            raise ServiceError(400, '请先输入不超过 64 KiB 的待提交代码')
        if self.guard:
            self.guard(url)
        with self.lock:
            existing = next((sid for sid, session in self.sessions.items()
                             if session['status'] not in ('closed', 'finished', 'error')
                             and canonical_url(session['originalUrl']) == canonical_url(url)), None)
            retired = None
            if existing and not self.sessions[existing].get('attempted') and not self.sessions[existing].get('submitting') and self.sessions[existing]['code'] != code:
                retired = existing
                self.sessions[existing]['status'] = 'closed'
                existing = None
            if existing:
                session = self.sessions[existing]
                if intent and (session.get('attempted') or session.get('submitting')):
                    raise ServiceError(409, '这道题已有提交正在处理，请等待官方结果后再提交。')
                if not session.get('attempted'):
                    session.update(code=code, intent=intent)
                ready = session['status'] == 'ready'
            else:
                if sum(s['status'] not in ('closed', 'finished', 'error') for s in self.sessions.values()) >= 8:
                    raise ServiceError(409, '当前仍有多个官方会话，请等待结果后再提交。')
                existing = 'official-' + uuid.uuid4().hex
                self.sessions[existing] = {**target, 'sessionId': existing, 'code': code, 'title': str(title),
                    'status': 'loading', 'message': '正在连接官方提交服务。', 'intent': intent,
                    'attempted': False, 'baseline': [], 'baselineKnown': False, 'baselineOwner': ''}
                ready = False
        if retired:
            self.release(retired)
        if existing not in self.views:
            self._ui(lambda: self._attach(existing, foreground=not intent))
        elif not intent:
            self._ui(lambda: self._reopen(existing))
        elif ready:
            with self.lock:
                self.sessions[existing]['intent'] = False
            threading.Thread(target=self._try_submit, args=(existing,), daemon=True).start()
        return self.status(existing, inspect=False)

    def open(self, url, code, title):
        return self._open(url, code, title, False)

    def submit(self, url, code, title):
        return self._open(url, code, title, True)

    def status(self, identity, inspect=True):
        from training import ServiceError
        with self.lock:
            if identity not in self.sessions:
                raise ServiceError(404, '没有找到本次官方提交会话')
            excluded = {'code', 'problem', 'originalUrl', 'title', 'intent', 'attempted', 'submitting',
                        'baseline', 'baselineKnown', 'baselineOwner', 'pendingSaved'}
            return {k: v for k, v in self.sessions[identity].items() if k not in excluded}

    def _hide_current(self):
        if self.current in self.views:
            self.views[self.current]['panel'].Visible = False
        self.current = None
        main = self.main_window.native.browser.webview
        main.Visible = True
        main.BringToFront()
        main.Focus()

    def _reopen(self, identity):
        if self.current and self.current != identity:
            self._hide_current()
        entry = self.views.get(identity)
        if not entry:
            return
        self.panel, self.view, self.status_label, self.view_identity = entry['panel'], entry['view'], entry['label'], identity
        self.current = identity
        entry['panel'].Visible = True
        entry['panel'].BringToFront()
        self.main_window.native.browser.webview.Visible = False
        session = self.sessions[identity]
        if session['status'] in ('needs_login', 'needs_verification'):
            entry['view'].CoreWebView2.Navigate(session['url'])

    def close(self, identity=None):
        from training import ServiceError
        if identity is not None and identity not in self.sessions:
            raise ServiceError(404, '没有找到本次官方提交会话')
        if self.current and (identity is None or identity == self.current):
            self._ui(self._hide_current)
        return self.status(identity, inspect=False) if identity else {'status': 'ready', 'message': '已返回 TB。'}

    def release(self, identity):
        def dispose():
            if self.current == identity:
                self._hide_current()
            entry = self.views.pop(identity, None)
            if entry:
                entry['panel'].Dispose()
            if self.view_identity == identity:
                self.panel = self.view = self.status_label = self.view_identity = None
        self._ui(dispose)
        with self.lock:
            session = self.sessions.get(identity)
            if session:
                session['code'] = ''
            terminal = [sid for sid, s in self.sessions.items() if s['status'] in ('closed', 'finished')]
            for sid in terminal[:-20]:
                self.sessions.pop(sid, None)

    def on_closing(self):
        self.stopping.set()
        if getattr(self.main_window, 'native', None) is not None:
            self.close()
