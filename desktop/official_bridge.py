"""Native official submission in a docked WebView2 on the existing main Form."""
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
STATUSES={'loading','needs_login','needs_verification','ready','submitted','judging','finished','error','closed'}

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
    context=json.dumps({k:session.get(k) for k in ('sessionId','platform','problem','code','originalUrl','attempted','baseline','baselineKnown')},ensure_ascii=True)
    asset_root=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    languages=(asset_root/'official_languages.js').read_text(encoding='utf-8')
    return r'''(()=>{
const ctx=CONTEXT,action=ACTION;
COMPILER_SELECTION

const send=value=>{chrome.webview.postMessage(JSON.stringify({tbOfficial:true,sessionId:ctx.sessionId,...value}));return value;};
const visible=e=>e&&e.getClientRects().length>0;
const editors=()=>[...document.querySelectorAll('textarea')].filter(e=>/source|code|editor/i.test((e.name||'')+' '+(e.id||'')));
const hasEditor=()=>editors().length||document.querySelector('.CodeMirror,.ace_editor,.monaco-editor');
const login=()=>[...document.querySelectorAll('input[type=password]')].some(visible)||/\/login|\/enter(?:\/|$)|\/auth\/login/i.test(location.pathname);
const verification=()=>!hasEditor()&&(/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(document.title+' '+(document.body?.innerText||'').slice(0,1200))||[...document.querySelectorAll('iframe')].some(e=>visible(e)&&/captcha|challenge/i.test(e.src)));
function normal(text){text=(text||'').trim();const map={'AC':'AC','Accepted':'AC','通过':'AC','WA':'WA','Wrong Answer':'WA','答案错误':'WA','TLE':'TLE','Time Limit Exceeded':'TLE','超时':'TLE','MLE':'MLE','Memory Limit Exceeded':'MLE','内存超限':'MLE','RE':'RE','Runtime Error':'RE','运行错误':'RE','CE':'CE','Compilation Error':'CE','Compile Error':'CE','编译错误':'CE','OLE':'OLE','Output Limit Exceeded':'OLE'};return map[text]||(/^(WJ|WR|Judging|Running|Waiting|Pending|Queuing|评测中|等待评测)(\b|$)/i.test(text)?'JUDGING':null);}
function taskPath(path){return path.replace(/^\/problemset\/problem\/(\d+)\/([A-Za-z]\d?)$/,'/contest/$1/problem/$2');}
function receipts(doc=document){const rows=[];doc.querySelectorAll('tr').forEach(row=>{const a=[...row.querySelectorAll('a[href]')].find(a=>/\/submission(?:s)?\/\d+/.test(a.getAttribute('href')||''));if(!a)return;const id=(a.getAttribute('href')||'').match(/\/submission(?:s)?\/(\d+)/)?.[1];const task=[...row.querySelectorAll('a[href]')].some(a=>{try{const target=new URL(a.getAttribute('href'),location.href),original=new URL(ctx.originalUrl);return target.origin===location.origin&&taskPath(target.pathname)===taskPath(original.pathname)}catch{return false}});const verdict=[...row.querySelectorAll('.label,.submissionVerdictWrapper,.verdict,[data-verdict]')].map(e=>normal(e.getAttribute('data-verdict')||e.textContent)).find(Boolean);if(id&&task)rows.push({id,verdict});});return rows;}
function inspect(){
if(login())return {status:'needs_login',message:'请在当前官方面板登录，然后明确点击“提交到官方”重试。'};
if(verification())return {status:'needs_verification',message:'原站要求 CAPTCHA 或登录验证，请在当前面板完成后重试。'};
if(ctx.attempted&&ctx.baselineKnown){const baseline=new Set(ctx.baseline||[]);const receipt=receipts().find(r=>!baseline.has(r.id));if(receipt?.verdict)return {status:receipt.verdict==='JUDGING'?'judging':'finished',submissionId:receipt.id,verdict:receipt.verdict==='JUDGING'?undefined:receipt.verdict,message:receipt.verdict==='JUDGING'?'原站已接收，正在评测。':'已读取原站本次新提交结果：'+receipt.verdict};}
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
let baseline=[],baselineKnown=false;try{let path=null;if(ctx.platform==='AtCoder')path=location.pathname.replace(/\/submit$/,'/submissions/me');if(ctx.platform==='Codeforces')path=location.pathname.replace(/\/submit$/,'/my');if(path){const r=await fetch(path,{credentials:'same-origin',cache:'no-store'});if(r.ok&&new URL(r.url).origin===location.origin&&new URL(r.url).pathname===path){const html=await r.text();const doc=new DOMParser().parseFromString(html.slice(0,2000000),'text/html');const challenge=/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(doc.title+' '+(doc.body?.textContent||'').slice(0,1200));const table=[...doc.querySelectorAll('table')].some(t=>/submission|提出|提交|status|verdict|結果|时间|when/i.test([...t.querySelectorAll('th')].map(e=>e.textContent).join(' ')));if(!challenge&&table&&!doc.querySelector('input[type=password],iframe[src*=captcha],iframe[src*=challenge]')){baseline=receipts(doc).map(r=>r.id);baselineKnown=true;}}}}catch{}
const form=editors().map(e=>e.closest('form')).find(Boolean)||[...document.querySelectorAll('form')].find(f=>f.querySelector('.CodeMirror,.ace_editor,.monaco-editor'));
let button=form?.querySelector('button[type=submit],input[type=submit],#submit');if(!button&&['牛客','洛谷'].includes(ctx.platform))button=[...document.querySelectorAll('button,[role=button],.submit-btn,.submit-button')].find(b=>visible(b)&&!b.disabled&&/^(?:保存并)?提交(?:代码|题目|评测)?$/.test(b.textContent.trim()));
if(!button)return send({status:'error',message:'未找到与代码编辑器对应的官方提交控件，请手动提交；未点击其它按钮。'});
send({status:'submitted',message:'已选择 '+compiler.label+'，等待原站回执。',compiler:compiler.label,baseline,baselineKnown,attempted:true});button.click();return {status:'submitted'};
}
if(action==='submit'){submit().catch(e=>send({status:'error',message:'表单操作未完成：'+String(e).slice(0,160)}));return {status:'loading'};}
return inspect();
})()'''.replace('COMPILER_SELECTION',languages,1).replace('ACTION',json.dumps(action),1).replace('CONTEXT',context,1)

class OfficialBridge:
    def __init__(self,main_window,guard=None,native_setup=None):
        self.main_window=main_window;self.guard=guard;self.native_setup=native_setup;self.lock=threading.RLock();self.sessions={};self.current=None;self.panel=None;self.view=None;self.status_label=None
    def _ui(self,action):
        form=getattr(self.main_window,'native',None)
        if form is None or form.IsDisposed:
            from training import ServiceError
            raise ServiceError(503,'原生主窗口尚未就绪，请稍后重试')
        if not form.InvokeRequired:return action()
        from System import Action
        value=[];form.Invoke(Action(lambda:value.append(action())))
        return value[0] if value else None
    def _eval(self,script,timeout=5,identity=None):
        from System import Action,String
        from System.Threading.Tasks import Task
        event=threading.Event();result=[]
        def done(task):
            try:result.append(json.loads(str(task.Result)))
            except Exception:result.append(None)
            finally:event.set()
        def evaluate():
            if self.view is None or identity is not None and self.current!=identity:
                event.set();return
            self.view.CoreWebView2.ExecuteScriptAsync(script).ContinueWith(Action[Task[String]](done))
        self._ui(evaluate)
        return result[0] if event.wait(timeout) and result else None
    def _update(self,identity,value):
        if not isinstance(value,dict):return
        with self.lock:
            session=self.sessions.get(identity)
            if not session or session['status']=='closed':return
            for key in ('status','message','submissionId','verdict','attempted','baseline','baselineKnown','compiler'):
                if key in value:session[key]=value[key]
            if session['status'] not in STATUSES:session['status']='error'
            session['updatedAt']=dt.datetime.now(dt.timezone.utc).isoformat()
            message=str(session.get('message',''))[:240]
        def display():
            if self.current==identity and self.status_label is not None and not self.status_label.IsDisposed:self.status_label.Text=message
        try:self._ui(display)
        except Exception:logging.debug('Official status label unavailable',exc_info=True)
    def _try_submit(self,identity):
        try:
            with self.lock:
                if self.current!=identity or self.sessions[identity]['status']=='closed':return
                session=dict(self.sessions[identity])
            if self.guard:self.guard(session['originalUrl'])
            self._eval(page_script(session,'submit'),identity=identity)
        except Exception as error:self._update(identity,{'status':'error','message':'提交已停止：'+str(error)[:180]})
    def _bind_accelerators(self,view,identity):
        from System import Action
        from System.Reflection import BindingFlags
        from System.Windows.Forms import Control,Keys
        # WinForms does not publicly expose its controller. The shipped WebView2
        # assembly owns this exact field; inspect its type before using it.
        field=view.GetType().GetField('_coreWebView2Controller',BindingFlags.Instance|BindingFlags.NonPublic)
        controller=field.GetValue(view) if field is not None else None
        if controller is None or str(controller.GetType().FullName)!='Microsoft.Web.WebView2.Core.CoreWebView2Controller':
            raise RuntimeError('当前 WebView2 组件不支持官方面板快捷键，请使用 Tab 到工具栏')
        def accelerator(_,event):
            if str(event.KeyEventKind) not in ('KeyDown','SystemKeyDown'):return
            if Control.ModifierKeys!=Keys.Alt or int(event.VirtualKey) not in (66,83):return
            event.Handled=True
            if event.PhysicalKeyStatus.WasKeyDown:return
            if int(event.VirtualKey)==66:
                self.main_window.native.BeginInvoke(Action(lambda:self.close(identity)))
            else:threading.Thread(target=self._try_submit,args=(identity,),daemon=True).start()
        controller.AcceleratorKeyPressed+=accelerator
    def _attach(self,identity):
        import System.Windows.Forms as Forms
        from System.Drawing import Color
        from Microsoft.Web.WebView2.WinForms import WebView2,CoreWebView2CreationProperties
        import webview
        form=self.main_window.native
        if self.panel is not None:self._hide_current()
        session=self.sessions[identity]
        panel=Forms.TableLayoutPanel();panel.Dock=Forms.DockStyle.Fill
        panel.ColumnCount=1;panel.RowCount=2;panel.Margin=Forms.Padding(0);panel.Padding=Forms.Padding(0)
        panel.BackColor=Color.FromArgb(246,248,251)
        panel.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Percent,100))
        panel.RowStyles.Add(Forms.RowStyle(Forms.SizeType.Absolute,54))
        panel.RowStyles.Add(Forms.RowStyle(Forms.SizeType.Percent,100))
        bar=Forms.TableLayoutPanel();bar.Dock=Forms.DockStyle.Fill;bar.ColumnCount=3;bar.RowCount=1
        bar.Margin=Forms.Padding(0);bar.Padding=Forms.Padding(8,7,8,7);bar.BackColor=panel.BackColor
        for width in (126,154):bar.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Absolute,width))
        bar.ColumnStyles.Add(Forms.ColumnStyle(Forms.SizeType.Percent,100))
        submit=Forms.Button();submit.Text='提交到官方 (&S)';submit.Dock=Forms.DockStyle.Fill
        back=Forms.Button();back.Text='返回 TB (&B)';back.Dock=Forms.DockStyle.Fill
        for button in (back,submit):
            button.BackColor=Color.White;button.ForeColor=Color.FromArgb(34,48,65)
            button.FlatStyle=Forms.FlatStyle.Flat;button.FlatAppearance.BorderColor=Color.FromArgb(202,213,227)
            button.UseVisualStyleBackColor=False;button.Margin=Forms.Padding(0,0,8,0)
        submit.Click+=lambda *_:threading.Thread(target=self._try_submit,args=(identity,),daemon=True).start()
        back.Click+=lambda *_:self.close(identity)
        label=Forms.Label();label.Text=session['platform']+' · 在原站登录后提交'
        label.Dock=Forms.DockStyle.Fill;label.AutoEllipsis=True
        label.TextAlign=__import__('System.Drawing',fromlist=['ContentAlignment']).ContentAlignment.MiddleLeft
        label.ForeColor=Color.FromArgb(34,48,65);label.Margin=Forms.Padding(4,0,0,0)
        bar.Controls.Add(back,0,0);bar.Controls.Add(submit,1,0);bar.Controls.Add(label,2,0)
        view=WebView2();view.Dock=Forms.DockStyle.Fill;view.Margin=Forms.Padding(0)
        props=CoreWebView2CreationProperties();props.UserDataFolder=form.browser.user_data_folder
        props.set_IsInPrivateModeEnabled(webview._state['private_mode']);view.CreationProperties=props;view.DefaultBackgroundColor=Color.White
        # Separate layout rows reserve real space for the toolbar. A Fill-docked
        # browser behind a Top-docked overlay hides the website account header.
        panel.Controls.Add(bar,0,0);panel.Controls.Add(view,0,1);form.Controls.Add(panel)
        self.panel,self.view,self.current,self.status_label=panel,view,identity,label
        form.browser.webview.Visible=False;panel.BringToFront()
        def navigation(_,args):
            p=urlsplit(str(args.Uri))
            if p.scheme!='https' or p.hostname not in LOGIN_HOSTS[session['platform']]:args.Cancel=True;self._update(identity,{'status':'error','message':'已阻止离开原站的跳转；面板只支持该平台官方登录与提交。'})
        def message(_,args):
            try:
                if urlsplit(str(args.Source)).hostname not in LOGIN_HOSTS[session['platform']]:return
                value=json.loads(str(args.TryGetWebMessageAsString()))
                if value.get('tbOfficial') and value.get('sessionId')==identity:self._update(identity,value)
            except Exception:logging.exception('Official native status message failed')
        def loaded(_,args):
            if not args.IsSuccess:self._update(identity,{'status':'error','message':'原站页面未能加载，请检查网络或在当前面板重试。'});return
            def inspect():
                try:
                    self._update(identity,self._eval(page_script(dict(self.sessions[identity])),identity=identity))
                    if self.sessions[identity].pop('intent',False):self._try_submit(identity)
                except Exception:logging.exception('Official native page inspection failed')
            threading.Thread(target=inspect,daemon=True).start()
        def initialized(_,args):
            if not args.IsSuccess:self._update(identity,{'status':'error','message':'原生提交面板初始化失败，请检查 WebView2。'});return
            core=view.CoreWebView2;core.Settings.AreDevToolsEnabled=False;core.Settings.IsStatusBarEnabled=False;core.NavigationStarting+=navigation;core.WebMessageReceived+=message
            try:self._bind_accelerators(view,identity)
            except Exception:logging.exception('Official native keyboard binding unavailable')
            def popup(_,event):
                event.Handled=True
                if urlsplit(str(event.Uri)).hostname in LOGIN_HOSTS[session['platform']]:core.Navigate(str(event.Uri))
            core.NewWindowRequested+=popup
            if self.native_setup:self.native_setup(view)
            core.Navigate(session['url'])
        view.CoreWebView2InitializationCompleted+=initialized;view.NavigationCompleted+=loaded;view.EnsureCoreWebView2Async(form.browser.webview.CoreWebView2.Environment)
    def _open(self,url,code,title,intent):
        from training import ServiceError
        target=submission_target(url)
        if not isinstance(code,str) or not code.strip() or len(code.encode('utf-8'))>65536:raise ServiceError(400,'请先输入不超过 64 KiB 的待提交代码')
        if self.guard:self.guard(url)
        identity='official-'+uuid.uuid4().hex
        with self.lock:
            self.sessions[identity]={**target,'sessionId':identity,'code':code,'title':str(title),'status':'loading','message':'正在主窗口打开官方原生提交面板。','intent':intent,'attempted':False,'baseline':[],'baselineKnown':False}
            if len(self.sessions)>30:
                for old in list(self.sessions):
                    if self.sessions[old]['status']=='closed':self.sessions.pop(old)
                    if len(self.sessions)<=20:break
        self._ui(lambda:self._attach(identity));return self.status(identity,inspect=False)
    def open(self,url,code,title):return self._open(url,code,title,False)
    def submit(self,url,code,title):return self._open(url,code,title,True)
    def status(self,identity,inspect=True):
        from training import ServiceError
        with self.lock:
            if identity not in self.sessions:raise ServiceError(404,'没有找到本次原站提交会话')
            session=dict(self.sessions[identity])
        if inspect and identity==self.current and self.view is not None and session['status'] not in ('loading','closed','error','finished'):
            try:self._update(identity,self._eval(page_script(session),identity=identity))
            except Exception:pass
        with self.lock:return {k:v for k,v in self.sessions[identity].items() if k not in ('code','problem','originalUrl','title','intent','attempted','baseline','baselineKnown')}
    def _hide_current(self):
        if self.panel is not None:self.main_window.native.Controls.Remove(self.panel);self.panel.Dispose();self.panel=self.view=self.status_label=None
        if self.current:self.sessions[self.current].update(status='closed',message='已返回 TB。',code='');self.current=None
        main=self.main_window.native.browser.webview;main.Visible=True;main.BringToFront();main.Focus()
    def close(self,identity=None):
        from training import ServiceError
        if identity is not None and identity not in self.sessions:raise ServiceError(404,'没有找到本次原站提交会话')
        if self.current and (identity is None or identity==self.current):self._ui(self._hide_current)
        return {'status':'closed','message':'已返回 TB。'} if identity is None else self.status(identity,inspect=False)
    def on_closing(self):
        # pywebview hashes event return values; API response dictionaries cannot
        # be returned from a native window lifecycle callback.
        self.close()
