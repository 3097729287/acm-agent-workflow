"""Personal translation settings. DPAPI secrets never leave this machine/profile."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import threading
import datetime as dt
from urllib.parse import urlsplit, urlunsplit
from integrations import atomic,load
from training import ServiceError

PROVIDERS={'deepseek':{'name':'DeepSeek','baseUrl':'https://api.deepseek.com','keyEnv':'DEEPSEEK_API_KEY','defaultModel':'deepseek-chat'},'huoshan':{'name':'火山方舟 Agent Plan','baseUrl':'https://ark.cn-beijing.volces.com/api/plan/v3','keyEnv':'HUOSHAN_API_KEY','defaultModel':''},'custom':{'name':'自定义 OpenAI 兼容 API','baseUrl':'','keyEnv':'TB_TRANSLATION_API_KEY','defaultModel':''}}


class _Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data,decrypt=False):
    if os.name!='nt':raise ServiceError(422,'此系统请使用环境变量配置密钥，不写入明文')
    buffer=ctypes.create_string_buffer(data);source=_Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));output=_Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(_Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(_Blob)];function.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output)):
        raise ServiceError(503,'本机密钥保护/解密失败，请重新配置；不会保存明文')
    try:return ctypes.string_at(output.data,output.size)
    finally:kernel.LocalFree(output.data)


def local_key(reference,home=None):
    key=os.environ.get(reference,'').strip()
    if not key:
        path=Path(home or os.environ.get('DSH_HOME') or Path.home()/'.dsh')/'.credentials.yaml'
        if path.is_file() and path.stat().st_size<1024*1024:
            text=path.read_text(encoding='utf-8')
            block=re.search(r'(?m)^refs:[ \t]*\r?\n((?:[ \t]+\S.*(?:\r?\n|$))*)',text)
            match=re.search(r'(?m)^  '+re.escape(reference)+r':[ \t]*(.*)$',block[1] if block else '')
            if match:
                value=match[1].strip()
                try:key=json.loads(value) if value.startswith('"') else value.strip("'")
                except ValueError:key=''
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{20,512}',key):raise ServiceError(503,'未找到有效本机 API 配置，请在翻译设置中填写密钥或使用环境变量')
    return key


def existing_provider(home=None):
    """Recognize only the explicitly configured, supported endpoint/reference pair."""
    path=Path(home or os.environ.get('DSH_HOME') or Path.home()/'.dsh')/'profiles'/'dsh-tui-safe'/'cordis.patch.yml'
    try:
        if path.stat().st_size>1024*1024:return {}
        text=path.read_text(encoding='utf-8')
    except OSError:return {}
    lines=text.splitlines()
    for index,line in enumerate(lines):
        match=re.fullmatch(r'( +)huoshan:\s*',line)
        if not match:continue
        indent=len(match[1]);block=[]
        for following in lines[index+1:]:
            if following.strip() and len(following)-len(following.lstrip())<=indent:break
            block.append(following)
        value='\n'.join(block)
        fields={}
        for name in ('baseURL','apiKeyEnv'):
            found=re.search(r'(?m)^\s*'+name+r':\s*([^\n]+)$',value)
            if found:fields[name]=found[1].strip().strip('\"\'')
        models=re.search(r'(?ms)^\s*models:\s*\n\s*-\s*id:\s*([^\n]+)',value)
        model=models[1].strip().strip('\"\'') if models else ''
        spec=PROVIDERS['huoshan']
        if fields.get('baseURL')==spec['baseUrl'] and fields.get('apiKeyEnv')==spec['keyEnv'] and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}',model):
            return {'provider':'huoshan','model':model}
    return {}


def normalize_base_url(value):
    if not isinstance(value,str) or not value.strip() or len(value)>2048:
        raise ServiceError(422,'请填写完整的 API Base URL')
    try:
        parsed=urlsplit(value.strip())
        port=parsed.port
    except ValueError:
        raise ServiceError(422,'API Base URL 格式无效') from None
    if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ServiceError(422,'Base URL 请使用 HTTP/HTTPS 地址，不包含账号、查询参数或片段')
    if any(ord(char)<33 for char in value.strip()):
        raise ServiceError(422,'Base URL 不能包含空白字符')
    path=parsed.path.rstrip('/')
    if path.endswith('/chat/completions'):path=path[:-len('/chat/completions')]
    return urlunsplit((parsed.scheme,parsed.netloc,path,'',''))


def valid_key(value):
    return isinstance(value,str) and bool(re.fullmatch(r'[^\s\x00-\x1f\x7f]{1,4096}',value))


class ProviderSettings:
    def __init__(self,state_dir):self.path=Path(state_dir)/'translation-settings.json';self.lock=threading.RLock();self.error=''
    def _read(self):
        value=load(self.path,{})
        return value if isinstance(value,dict) and value.get('provider') else existing_provider()
    @staticmethod
    def _base(value,spec):
        return value.get('baseUrl','') if value.get('provider')=='custom' else spec['baseUrl']
    def status(self):
        with self.lock:
            value=self._read();provider=value.get('provider','deepseek');spec=PROVIDERS.get(provider,PROVIDERS['deepseek'])
            detected=False
            try:local_key(spec['keyEnv']);detected=True
            except ServiceError:pass
            base=self._base(value,spec);model=value.get('model') or spec['defaultModel']
            return {'provider':provider,'providerName':spec['name'],'baseUrl':base,'model':model,
                    'configured':bool((value.get('protectedKey') or detected) and model and base),
                    'keyStored':bool(value.get('protectedKey')),
                    'keySource':'本机加密配置' if value.get('protectedKey') else '本机已有配置' if detected else '未配置',
                    'lastError':self.error,'verified':bool(value.get('verifiedAt')),'verifiedAt':value.get('verifiedAt'),
                    'providers':[{'id':i,**{k:s[k] for k in ('name','baseUrl','defaultModel')}} for i,s in PROVIDERS.items()],
                    'notice':'只发送公开英文题面；填写 Base URL、模型与自己的 API Key 即可使用兼容接口。'}
    def configure(self,body):
        if not isinstance(body,dict) or set(body)-{'provider','baseUrl','model','apiKey'}:raise ServiceError(422,'未知翻译设置')
        with self.lock:
            previous=self._read();provider=body.get('provider',previous.get('provider','deepseek'))
            if provider not in PROVIDERS:raise ServiceError(422,'请选翻译服务或自定义 API')
            spec=PROVIDERS[provider]
            model=body.get('model',previous.get('model') if previous.get('provider')==provider else spec['defaultModel'])
            if not isinstance(model,str) or not re.fullmatch(r'[^\s\x00-\x1f\x7f]{1,128}',model):raise ServiceError(422,'请填写原服务可用的模型 ID')
            if provider=='custom':
                base=normalize_base_url(body.get('baseUrl',previous.get('baseUrl','') if previous.get('provider')==provider else ''))
            else:
                base=spec['baseUrl']
                if 'baseUrl' in body and normalize_base_url(body['baseUrl'])!=base:raise ServiceError(422,'更改接口地址请先选择自定义 API')
            value={'provider':provider,'model':model,'baseUrl':base}
            same_endpoint=previous.get('provider')==provider and self._base(previous,spec)==base
            if same_endpoint and previous.get('protectedKey'):value['protectedKey']=previous['protectedKey']
            if 'apiKey' in body:
                key=body['apiKey']
                if key!='' and not valid_key(key):raise ServiceError(422,'API Key 不能包含空白或控制字符')
                if key:value['protectedKey']=base64.b64encode(_crypt(key.encode())).decode()
                else:value.pop('protectedKey',None)
            atomic(self.path,value);self.error=''
            return self.status()
    def mark_verified(self):
        with self.lock:
            value=self._read()
            value['verifiedAt']=dt.datetime.now(dt.timezone.utc).isoformat()
            atomic(self.path,value);self.error=''
    def credentials(self):
        with self.lock:
            value=self._read();provider=value.get('provider','deepseek');spec=PROVIDERS.get(provider)
            if not spec:raise ServiceError(503,'翻译服务配置无法识别')
            model=value.get('model') or spec['defaultModel'];base=self._base(value,spec)
            if not model or not base:raise ServiceError(503,'请先填写服务的 Base URL 与模型 ID')
            base=normalize_base_url(base)
            key=_crypt(base64.b64decode(value['protectedKey']),True).decode() if value.get('protectedKey') else local_key(spec['keyEnv'])
            if not valid_key(key):raise ServiceError(503,'翻译密钥不可用，请重新配置')
            return spec['name'],base+'/chat/completions',model,key
