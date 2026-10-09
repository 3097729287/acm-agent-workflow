"""Async public accounts, ended-contest overlay and release notifications.

The archive is read-only. Network and personal cache failures retain prior evidence.
Only whitelisted first-party HTTPS GETs are permitted; no credentials are stored.
"""
import base64
import copy
import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote,urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
import public_platforms as P

from version import VERSION
LOG=logging.getLogger('tb.integrations')
HOSTS={'codeforces.com','atcoder.jp','ac.nowcoder.com','www.luogu.com.cn','api.github.com','github.com','kenkoooo.com'}
KNOWN_REPO='3097729287/acm-agent-workflow'
DEFAULTS={'githubRepo':KNOWN_REPO,'autoSync':True,'intervalHours':6,'minDifficulty':1000,'maxDifficulty':2199,'includePrereleases':True,'accounts':{p:'' for p in P.LABELS}}

def now():return dt.datetime.now(dt.timezone.utc)
def stamp(value=None):return (value or now()).isoformat()

def version_number(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?',str(value))
    return tuple(map(int,match.groups())) if match else None

def fail(status,message):
    from training import ServiceError
    raise ServiceError(status,message)

def safe_url(url):
    parsed=urlsplit(str(url))
    if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('只允许已知原站的公开 HTTPS 地址')
    return url

def canonical(url):
    if not url:return None
    parsed=urlsplit(url);host=(parsed.hostname or '').lower();path=parsed.path.rstrip('/')
    if host in ('www.codeforces.com','mirror.codeforces.com'):host='codeforces.com'
    if host=='luogu.com.cn':host='www.luogu.com.cn'
    match=re.fullmatch(r'/problemset/problem/(\d+)/([A-Z]\d?)',path)
    if host=='codeforces.com' and match:path='/contest/'+match[1]+'/problem/'+match[2]
    return 'https://'+host+path if host else None

def atomic(path,value):
    from persistence import save_document
    save_document(path,value)


def load(path,default):
    from persistence import load_document
    return load_document(path,default)


def recover_catalog_targets(path,state,snapshot_paths=None):
    """Recover only a proven append transition and its exact catalog digest."""
    missing=[n for n in state.get('notifications',[]) if n.get('id','').startswith('catalog:') and not any(n.get(k) for k in ('problemIds','solutionIds','problemUrls'))]
    if not missing:return 0
    path=Path(path)
    if snapshot_paths is None:
        import toolutil
        mirror=str(path.resolve().parent).replace(':','').replace('\\','_').replace('/','_')
        directory=Path(toolutil.BACKUP_ROOT)/mirror
        snapshot_paths=sorted(directory.glob(path.name+'.*.bak'))
    def order(p):
        match=re.search(r'\.(\d{8}-\d{6})(?:-(\d+))?\.bak$',Path(p).name)
        return (match[1],int(match[2] or 0)) if match else (Path(p).name,0)
    history=[]
    for candidate in sorted(snapshot_paths,key=order):
        value=load(candidate,{})
        if isinstance(value.get('rows'),dict) and isinstance(value.get('notifications'),list):history.append(value)
    history.append(state)
    recovered=0
    for notice in missing:
        parts=notice['id'].split(':')
        if len(parts)!=3:continue
        platform,digest=parts[1:];possibilities={}
        for before,after in zip(history,history[1:]):
            if any(n.get('id')==notice['id'] for n in before['notifications']):continue
            evidence=next((n for n in after['notifications'] if n.get('id')==notice['id']),None)
            if not evidence or any(evidence.get(k)!=notice.get(k) for k in ('type','title','body','createdAt','count')):continue
            previous=set(before['rows']);following=set(after['rows']);added=sorted(following-previous)
            if previous-following or not added or len(added)!=notice.get('count'):continue
            if hashlib.sha256(json.dumps(sorted(after['rows'])).encode()).hexdigest()[:16]!=digest:continue
            values=[after['rows'][identity] for identity in added]
            if any(not isinstance(r,dict) or r.get('id')!=identity or r.get('platform') not in (platform,P.LABELS.get(platform)) for identity,r in zip(added,values)):continue
            if any(identity not in state['rows'] or canonical(state['rows'][identity].get('url'))!=canonical(row.get('url')) for identity,row in zip(added,values)):continue
            possibilities[tuple(added)]=values
        if len(possibilities)!=1:continue
        ids,values=next(iter(possibilities.items()))
        links=[]
        for row in values:
            try:safe_url(row.get('url'))
            except (ValueError,TypeError):continue
            links.append(row['url'])
        notice.update(problemIds=list(ids),solutionIds=[],problemUrls=list(dict.fromkeys(links)),targets=[{'id':i,'kind':'problem'} for i in ids],targetEvidence='统一备份前后差集与通知摘要核对')
        notice.pop('targetNotice',None);recovered+=1
    return recovered

class _Redirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        safe_url(newurl)
        if urlsplit(newurl).hostname!=urlsplit(request.full_url).hostname:raise ValueError('原站跳转到登录/其它站点；不继续读取')
        return super().redirect_request(request,fp,code,msg,headers,newurl)

class PublicClient:
    def __init__(self,state_dir,stop=None,transport=None,spacing=2):
        self.directory=Path(state_dir)/'http';self.stop=stop or threading.Event();self.transport=transport;self.spacing=spacing
        self.lock=threading.RLock();self.pacing={};self.backoff={};self.opener=build_opener(_Redirect())
    def _get(self,url,headers=None):
        safe_url(url);host=urlsplit(url).hostname;path=self.directory/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        with self.lock:
            saved=load(path,{})
            if saved and time.time()-saved.get('at',0)<300:return saved['text']
            if self.stop.is_set():raise RuntimeError('同步已停止')
            if time.monotonic()<self.backoff.get(host,(0,0))[0]:raise RuntimeError('原站暂不可用，正在退避等待')
            delay=self.spacing-(time.monotonic()-self.pacing.get(host,-1000))
            if delay>0 and self.stop.wait(delay):raise RuntimeError('同步已停止')
            request_headers={'User-Agent':'TB/'+VERSION+' public-practice (+read-only)','Accept':'application/json,text/html;q=0.9'}
            if headers:request_headers.update(headers)
            if saved.get('etag'):request_headers['If-None-Match']=saved['etag']
            try:
                if self.transport:body,etag=self.transport(url,request_headers)
                else:
                    with self.opener.open(Request(url,headers=request_headers,method='GET'),timeout=8) as response:
                        safe_url(response.url);body=response.read(32*1024*1024+1);etag=response.headers.get('ETag')
                if len(body)>32*1024*1024:raise ValueError('公开响应超过大小限制')
                text=body.decode('utf-8','replace')
                self.pacing[host]=time.monotonic();self.backoff.pop(host,None)
                if not self.stop.is_set():atomic(path,{'url':url,'text':text,'etag':etag,'at':time.time()})
                return text
            except HTTPError as error:
                if error.code==304 and saved:
                    saved['at']=time.time();atomic(path,saved);self.pacing[host]=time.monotonic();return saved['text']
                count=self.backoff.get(host,(0,0))[1]+1
                self.backoff[host]=(time.monotonic()+min(3600,15*2**min(count,8)),count)
                raise RuntimeError(f'原站公开 GET 返回 HTTP {error.code}；保留已有缓存') from error
            except (OSError,ValueError,RuntimeError) as error:
                count=self.backoff.get(host,(0,0))[1]+1
                self.backoff[host]=(time.monotonic()+min(3600,15*2**min(count,8)),count)
                raise RuntimeError(str(error)[:250]) from error
    def text(self,url,headers=None):return self._get(url,headers)
    def json(self,url,headers=None):return json.loads(self._get(url,headers))

class IntegrationService:
    def __init__(self,store,state_dir,auto_start=True,client=None,clock=None):
        self.store=store;self.state_dir=Path(state_dir);self.state_dir.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.stop=threading.Event();self.wake=threading.Event();self.clock=clock or now
        self.client=client or PublicClient(self.state_dir,self.stop);self.path=self.state_dir/'integrations.json'
        default={'settings':copy.deepcopy(DEFAULTS),'accounts':{},'rows':{},'pendingDiscovery':{},'difficultyMetadata':{},'notifications':[],'localBaseline':None,'manifestIds':{},'updates':{'configured':False,'currentVersion':VERSION,'latestVersion':None,'url':None,'notes':'','checkedAt':None,'error':''},'sync':{'busy':False,'lastCheckedAt':None,'lastSuccessAt':None,'nextCheckAt':None,'message':'尚未同步','providers':[]}}
        self.state=load(self.path,default)
        if not isinstance(self.state,dict):self.state=copy.deepcopy(default)
        legacy_source=not self.state.get('githubSourceInitialized',False)
        for key,value in default.items():
            if key not in self.state or value is not None and not isinstance(self.state[key],type(value)):
                self.state[key]=copy.deepcopy(value)
        self.state['sync']['busy']=False;self.state['settings']={**copy.deepcopy(DEFAULTS),**self.state['settings']}
        self.state['settings']['accounts']={**DEFAULTS['accounts'],**self.state['settings'].get('accounts',{})}
        if legacy_source and not self.state['settings']['githubRepo']:self.state['settings']['githubRepo']=KNOWN_REPO
        self.state['githubSourceInitialized']=True
        from paths import resource
        seed=json.loads(resource('public-problem-metadata.json').read_text(encoding='utf-8'))
        if isinstance(seed,dict):
            for url,value in seed.items():
                if url not in self.state['difficultyMetadata'] and isinstance(value,dict):self.state['difficultyMetadata'][url]=value
        from contestmeta import ContestDates
        self.dates=ContestDates(store)
        self.dates.by_url=copy.deepcopy(self.state.get('contestDates') or {})
        for row in self.state['rows'].values():
            if isinstance(row,dict):self.dates.observe(row)
        self.archived_contests={}
        recover_catalog_targets(self.path,self.state)
        for item in self.state['notifications']:
            if not any(key in item for key in ('problemIds','solutionIds','problemUrls')):
                item.update(problemIds=[],solutionIds=[],problemUrls=[],targets=[],targetNotice='这条旧通知没有保存精确题目目标；请查看公开来源。')
        self.pending=set();self.worker=None;self.auto_start=auto_start;self.closed=False
        if auto_start and self.state['settings']['autoSync']:self.sync()

    def _save(self):
        if not self.closed:atomic(self.path,self.state)

    def snapshot(self):
        with self.lock:
            result={key:copy.deepcopy(self.state[key]) for key in ('settings','sync','updates','notifications')};result['version']=VERSION
            result['accounts']=[copy.deepcopy(self.state['accounts'].get(p) or P.profile(p,self.state['settings']['accounts'][p])) for p in P.LABELS]
            result['updates']['configured']=bool(result['settings']['githubRepo']);result['updates']['currentVersion']=VERSION
            result['updates']['sourceNotice']='项目源代码与 TB 安装包；版本与下载入口以 GitHub Releases 为准。' if result['settings']['githubRepo']==KNOWN_REPO else '自定义公开来源；仅通知，不自动安装。'
            return result

    def contest_metadata(self,raw,url=None):
        return self.dates.for_row(raw,url)

    def problem_metadata(self,raw,url=None):
        key=canonical(url or raw.get('_url'))
        with self.lock:value=copy.deepcopy(self.state['difficultyMetadata'].get(key,{}))
        if value:return value
        remote=bool(raw.get('_remote'))
        return {'difficultySource':'公开同步记录' if remote else '归档训练难度（联网后核对最新资料）',
                'difficultyConfidence':'UNKNOWN','difficultyEstimated':True}

    def _observe_difficulty(self,row):
        key=canonical(row.get('url'));rating=row.get('difficulty')
        if not key or not isinstance(rating,int) or isinstance(rating,bool) or not 0<rating<=10000:return
        platform=row.get('platform');official=platform in ('Codeforces','codeforces') and '官方' in row.get('difficultySource','')
        fields={'difficulty':rating,'difficultySource':row.get('difficultySource') or '公开难度资料',
                'difficultyConfidence':'HIGH' if official else row.get('difficultyConfidence','MEDIUM' if platform in ('AtCoder','atcoder') else 'LOW'),
                'difficultyEstimated':not official,'difficultyBand':[rating,rating] if official else row.get('difficultyBand'),
                'difficultyCheckedAt':stamp(self.clock()),'nativeDifficulty':row.get('nativeDifficulty',rating),
                'officialTags':row.get('tags',[])}
        with self.lock:self.state['difficultyMetadata'][key]=fields

    def _refresh_difficulties(self,platform):
        # Update old archive rows too; discovery-only scans skip local duplicates
        # and leave their difficulty frozen even when the official rating changes.
        if platform not in ('codeforces','atcoder'):return
        urls={}
        for raw in self.store.raw_rows():
            encoded=self.store.encode_row(raw,self.clock().date());key=canonical(encoded.get('url'))
            if key:urls[key]=encoded
        with self.lock:
            for value in self.state['rows'].values():
                key=canonical(value.get('url'))
                if key:urls[key]=value
        if platform=='codeforces':
            result=P.cf_result(self.client,'problemset.problems')
            for item in result.get('problems',[]):
                cid,index=item.get('contestId'),item.get('index');rating=P.integer(item.get('rating'))
                if cid is None or not index or rating is None:continue
                url=f'https://codeforces.com/contest/{cid}/problem/{index}'
                if canonical(url) not in urls:continue
                self._observe_difficulty({'url':url,'platform':'Codeforces','difficulty':rating,
                    'difficultySource':'Codeforces 官方 rating','tags':[P.CF_TAGS[tag] for tag in item.get('tags',[]) if tag in P.CF_TAGS]})
        else:
            import cf_eq
            models=self.client.json('https://kenkoooo.com/atcoder/resources/problem-models.json')
            for key,row in urls.items():
                if urlsplit(key).hostname!='atcoder.jp':continue
                task=urlsplit(key).path.rsplit('/',1)[-1];native=P.integer((models.get(task) or {}).get('difficulty'))
                if native is None:continue
                result=cf_eq.cf_eq_atcoder(native)
                self._observe_difficulty({'url':key,'platform':'AtCoder','difficulty':result['cf_eq_rating'],
                    'nativeDifficulty':native,'difficultyBand':result['cf_eq_band'],
                    'difficultySource':'CF-EQ · AtCoder Problems 最新模型估算','tags':[]})

    def configure(self,body):
        if not isinstance(body,dict):fail(422,'配置必须是对象')
        allowed=set(DEFAULTS)
        if set(body)-allowed:fail(422,'未知同步设置')
        with self.lock:
            settings=copy.deepcopy(self.state['settings']);old=copy.deepcopy(settings)
            updated_accounts=copy.deepcopy(self.state['accounts'])
            if 'githubRepo' in body:
                repo=str(body['githubRepo']).strip().rstrip('/')
                if repo.startswith('https://github.com/'):repo=repo[len('https://github.com/'):]
                if repo.endswith('.git'):repo=repo[:-4]
                if repo and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',repo):fail(422,'GitHub 仓库请填 owner/repo 或公开仓库地址')
                settings['githubRepo']=repo
            for key in ('autoSync','includePrereleases'):
                if key in body:
                    if not isinstance(body[key],bool):fail(422,'同步开关必须为布尔值')
                    settings[key]=body[key]
            for key,lo,hi in [('intervalHours',1,168),('minDifficulty',1000,2199),('maxDifficulty',1000,2199)]:
                if key in body:
                    number=body[key]
                    if not isinstance(number,int) or isinstance(number,bool) or not lo<=number<=hi:fail(422,'同步周期或收录难度超出允许范围')
                    settings[key]=number
            if settings['minDifficulty']>settings['maxDifficulty']:fail(422,'最低难度不能大于最高难度')
            if 'accounts' in body:
                if not isinstance(body['accounts'],dict) or set(body['accounts'])-set(P.LABELS):fail(422,'未知账号平台')
                for platform,value in body['accounts'].items():
                    if not isinstance(value,str):fail(422,'账号必须是文本')
                    handle=value.strip()
                    if handle.startswith('https://'):
                        expected=P.profile(platform,'')['url'];handle=handle[len(expected):].rstrip('/') if handle.startswith(expected) else '!'
                    regex=r'\d{1,20}' if platform in ('luogu','nowcoder') else r'[A-Za-z0-9_.-]{1,64}'
                    if handle and not re.fullmatch(regex,handle):fail(422,'牛客/洛谷请填公开用户 ID 或主页地址；CF/AtCoder 请填公开用户名')
                    settings['accounts'][platform]=handle
                    if handle!=old['accounts'][platform]:updated_accounts[platform]=P.profile(platform,handle)
            if settings['githubRepo']!=old['githubRepo']:
                self.state['updates']={'configured':bool(settings['githubRepo']),'currentVersion':VERSION,'latestVersion':None,'url':None,'notes':'','checkedAt':None,'error':''};self.state['manifestIds']={}
            self.state['settings']=settings;self.state['accounts']=updated_accounts;self._save()
        return self.sync()

    def _ensure_worker(self):
        if self.worker is None or not self.worker.is_alive():
            self.worker=threading.Thread(target=self._loop,name='tb-public-sync',daemon=True);self.worker.start()

    def sync(self,body=None):
        body=body or {}
        if not isinstance(body,dict) or set(body)-{'platform'}:fail(422,'同步参数无效')
        platform=body.get('platform')
        if platform is not None and platform not in (*P.LABELS,'github','local'):fail(422,'未知同步平台')
        with self.lock:
            if self.closed:fail(503,'同步服务已关闭')
            self.pending.add(platform or 'all');self.state['sync']['busy']=True;self._ensure_worker();self.wake.set()
        return self.snapshot()

    def dismiss(self,identity):
        with self.lock:
            item=next((n for n in self.state['notifications'] if n['id']==identity),None)
            if not item:fail(404,'没有找到这条通知')
            item['read']=True;self._save()
        return self.snapshot()

    def rows(self):
        with self.lock:
            settings=self.state['settings'];rows=copy.deepcopy(list(self.state['rows'].values()))
            metadata=copy.deepcopy(self.state['difficultyMetadata'])
        from knowledge import enrich_row
        result=[]
        for row in rows:
            row.update(metadata.get(canonical(row.get('url')),{}))
            if isinstance(row.get('difficulty'),int) and settings['minDifficulty']<=row['difficulty']<=settings['maxDifficulty']:
                result.append(enrich_row(row,official_tags=row.get('officialTags')))
        return result

    def row(self,identity):
        with self.lock:
            value=self.state['rows'].get(identity)
            if not value:return None
            return {'场次':value['contest'],'题号':value['problem'],'题名':value['title'],'知识点':value['knowledge'],'难度':str(value['difficulty']),'状态':'未做','日期':'','_remote':True,'_url':value['url'],'_id':value['id'],'_platform':value['platform'],'_series':value['series']}

    def statement(self,identity,fetch=False):
        raw=self.row(identity)
        if not raw:fail(404,'没有找到远端题目')
        path=self.state_dir/'statements'/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
        saved=load(path,{})
        if saved.get('id')==identity and saved.get('url')==raw['_url'] and saved.get('statementAvailable'):return saved
        value={'id':identity,'title':raw['题名'],'url':raw['_url'],'markdown':None,'samples':[],'limits':{'timeMs':2000,'memoryMb':256},'statementAvailable':False}
        if fetch:
            try:
                value=P.statement(self.client,identity,raw['题名'],raw['_url'])
                if not self.stop.is_set():atomic(path,value)
            except (OSError,ValueError,RuntimeError) as error:value['error']=str(error)[:250]
        return value

    def _notice(self,identity,kind,title,body,url=None,count=None,problem_ids=None,solution_ids=None,problem_urls=None):
        if any(n['id']==identity for n in self.state['notifications']):return
        value={'id':identity,'type':kind,'title':title,'body':body,'createdAt':stamp(self.clock()),'read':False}
        value.update(problemIds=list(dict.fromkeys(problem_ids or [])),solutionIds=list(dict.fromkeys(solution_ids or [])),problemUrls=list(dict.fromkeys(problem_urls or [])))
        value['targets']=[{'id':i,'kind':'problem'} for i in value['problemIds']]+[{'id':i,'kind':'solution'} for i in value['solutionIds']]
        if url:value['url']=url
        if count is not None:value['count']=count
        self.state['notifications'].insert(0,value);self.state['notifications']=self.state['notifications'][:200]

    def _local(self):
        rows=self.store.raw_rows();current={};urls=set();by_id={}
        for raw in rows:
            identity=raw['场次']+'::'+raw['题号'];encoded=self.store.encode_row(raw,self.clock().date())
            current[identity]=bool(encoded.get('solutionAvailable',False))
            by_id[identity]=encoded
            if encoded.get('url'):self.archived_contests[self.dates.contest_url(encoded['url'])]=raw['场次']
            if encoded.get('url'):urls.add(canonical(encoded['url']))
        with self.lock:
            previous=self.state['localBaseline'];self.state['localBaseline']=current
            if previous is not None:
                added=[i for i in current if i not in previous];solutions=[i for i,present in current.items() if present and not previous.get(i,False)]
                if added or solutions:
                    digest=hashlib.sha256(json.dumps(sorted(current.items())).encode()).hexdigest()[:16]
                    self._notice('local:'+digest,'content','本地题库有更新',f'新增 {len(added)} 道题，新增可用题解 {len(solutions)} 道。',count=len(set(added+solutions)),problem_ids=added,solution_ids=solutions,problem_urls=[by_id[i]['url'] for i in dict.fromkeys(added+solutions) if by_id[i].get('url')])
        return urls

    def _catalog(self,platform,local_urls):
        rows,pending,message=P.DISCOVERY_ADAPTERS[platform](self.client,self.clock());added=0;added_ids=[];added_urls=[]
        if platform=='codeforces':
            try:
                listing=self.client.json('https://codeforces.com/api/contest.list?gym=false')
                if listing.get('status')=='OK':self.dates.observe_cf(listing['result'])
            except (OSError,ValueError,RuntimeError,KeyError):pass
        if platform=='nowcoder':
            # Bounded background supplementation; never network during data/row encoding.
            candidates=[u for u in self.archived_contests if u and urlsplit(u).hostname=='ac.nowcoder.com' and u not in self.dates.by_url]
            candidates.sort(key=lambda u:int(u.rsplit('/',1)[-1]),reverse=True)
            for url in candidates[:6]:
                if self.stop.is_set():break
                try:
                    from contestmeta import parse
                    value=parse(self.client.text(url),url)
                    if value['startedAt']:
                        with self.dates.lock:self.dates.by_url[url]=value
                except (OSError,ValueError,RuntimeError):continue
        with self.lock:
            settings=self.state['settings']
            self.state['pendingDiscovery'][platform]=pending[:500]
            self.state['contestDates']=copy.deepcopy(self.dates.by_url)
            for value in rows:
                value=copy.deepcopy(value)
                self._observe_difficulty(value)
                self.dates.observe(value)
                difficulty=value.get('difficulty');ended=P.utc(value.get('endedAt'))
                if not isinstance(difficulty,int) or isinstance(difficulty,bool) or not ended or dt.datetime.fromisoformat(ended)>self.clock():continue
                existing=self.state['rows'].get(value['id'])
                if existing and 'addedAt' in existing:value['addedAt']=existing['addedAt']
                if existing:self.state['rows'][value['id']]=value
                if not settings['minDifficulty']<=difficulty<=settings['maxDifficulty'] or canonical(value['url']) in local_urls:continue
                if value['id'] not in self.state['rows']:
                    value['addedAt']=stamp(self.clock());added+=1;added_ids.append(value['id']);added_urls.append(value['url'])
                self.state['rows'][value['id']]=value
            if added:self._notice('catalog:'+platform+':'+hashlib.sha256(json.dumps(sorted(self.state['rows'])).encode()).hexdigest()[:16],'catalog',P.LABELS[platform]+' 新结束赛题目',f'新增 {added} 道有难度证据的题；题解尚未生成，不自动加入个人训练。',count=added,problem_ids=added_ids,problem_urls=added_urls)
        return {'platform':platform,'status':'partial' if pending else 'ready','message':message,'added':added,'pending':len(pending)}

    def _account(self,platform):
        with self.lock:handle=self.state['settings']['accounts'][platform]
        if not handle:return
        try:
            value=P.ACCOUNT_ADAPTERS[platform](self.client,handle);value['updatedAt']=stamp(self.clock())
            if value.get('status')=='partial':
                with self.lock:previous=copy.deepcopy(self.state['accounts'].get(platform) or {})
                if previous.get('handle')==handle:
                    observed={canonical(s.get('url')):s for s in previous.get('solved',[]) if s.get('url')}
                    for solved in value.get('solved',[]):
                        key=canonical(solved.get('url'));old=observed.get(key)
                        if not old or solved.get('acceptedAt') and solved['acceptedAt']<(old.get('acceptedAt') or solved['acceptedAt']):observed[key]=solved
                    value['solved']=list(observed.values())
        except (OSError,ValueError,RuntimeError,KeyError,IndexError) as error:
            with self.lock:value=copy.deepcopy(self.state['accounts'].get(platform) or P.profile(platform,handle))
            value.update(status='error',error=str(error)[:250])
        with self.lock:
            if self.state['settings']['accounts'][platform]==handle and not self.closed:self.state['accounts'][platform]=value

    def _github(self):
        with self.lock:settings=copy.deepcopy(self.state['settings']);previous=copy.deepcopy(self.state['updates'])
        repo=settings['githubRepo']
        if not repo:return
        updates=previous;updates.update(configured=True,currentVersion=VERSION,checkedAt=stamp(self.clock()),error='')
        try:
            releases=self.client.json('https://api.github.com/repos/'+repo+'/releases?per_page=20')
            with self.lock:
                if self.state['settings']['githubRepo']!=repo:return False
            allowed=[r for r in releases if not r.get('draft') and (settings['includePrereleases'] or not r.get('prerelease'))]
            allowed.sort(key=lambda r:r.get('published_at') or '',reverse=True)
            if allowed:
                release=allowed[0];version=str(release.get('tag_name',''))[:100];link='https://github.com/'+repo+'/releases/tag/'+quote(version,safe='')
                updates.update(latestVersion=version,url=link,notes=str(release.get('body') or '')[:10000])
                numeric=version_number(version);current=version_number(VERSION)
                if numeric and current and numeric>current:
                    with self.lock:
                        if self.state['settings']['githubRepo']==repo:self._notice('release:'+repo+':'+str(release['id']),'release','TB 有新版本 '+version,'查看发布说明并手动更新；不会自动下载或执行。',link)
            try:manifest=self.client.json('https://api.github.com/repos/'+repo+'/contents/tb-update.json')
            except RuntimeError as error:
                if 'HTTP 404' not in str(error):raise
            else:
                if manifest.get('encoding')!='base64' or manifest.get('size',0)>1024*1024:raise ValueError('题解更新清单格式或体积不支持')
                data=json.loads(base64.b64decode(manifest['content']).decode('utf-8'));items=data.get('contents') or []
                if data.get('schema')!=1 or not isinstance(items,list) or len(items)>10000:raise ValueError('题解更新清单 schema 不支持')
                changed=[];ids={}
                with self.lock:old=self.state['manifestIds']
                for item in items:
                    if not isinstance(item,dict) or not isinstance(item.get('id'),str):continue
                    fingerprint=str(item.get('sha256') or item.get('updatedAt') or item['id']);ids[item['id']]=fingerprint
                    if old.get(item['id'])!=fingerprint:changed.append(item)
                with self.lock:
                    if self.state['settings']['githubRepo']!=repo:return False
                    if changed:
                        digest=hashlib.sha256(json.dumps(sorted(ids.items())).encode()).hexdigest()[:16]
                        exact=[item.get('problemId') or item['id'] for item in changed if isinstance(item.get('problemId') or item['id'],str) and '::' in (item.get('problemId') or item['id'])]
                        links=[item['url'] for item in changed if isinstance(item.get('url'),str) and canonical(item['url']) and urlsplit(item['url']).hostname in HOSTS]
                        self._notice('github-content:'+repo+':'+digest,'content','GitHub 题解内容有更新',f'{len(changed)} 项新增或更新内容可查看；不会自动修改原归档。','https://github.com/'+repo+'/blob/HEAD/tb-update.json',len(changed),solution_ids=exact,problem_urls=links)
                    self.state['manifestIds']=ids
        except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:updates['error']=str(error)[:250]
        with self.lock:
            if self.state['settings']['githubRepo']==repo:self.state['updates']=updates
        return not updates['error']

    def _refresh(self,selected):
        with self.lock:self.state['sync'].update(lastCheckedAt=stamp(self.clock()),message='正在读取公开信息')
        providers=[];success=False
        try:
            local_urls=self._local()
            if selected=={'local'}:success=True
        except Exception as error:local_urls=set();providers.append({'platform':'local','status':'error','message':str(error)[:200],'added':0,'pending':0})
        for platform in P.LABELS:
            if self.stop.is_set():break
            if 'all' not in selected and platform not in selected:continue
            self._account(platform)
            try:
                providers.append(self._catalog(platform,local_urls));success=True
                try:self._refresh_difficulties(platform)
                except (OSError,ValueError,RuntimeError,KeyError,TypeError):LOG.debug('Latest difficulty data unavailable; retain prior evidence',exc_info=True)
            except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:providers.append({'platform':platform,'status':'error','message':str(error)[:250],'added':0,'pending':0})
        if not self.stop.is_set() and ('all' in selected or 'github' in selected):success=bool(self._github()) or success
        with self.lock:
            if self.closed:return
            sync=self.state['sync'];sync.update(providers=providers,nextCheckAt=stamp(self.clock()+dt.timedelta(hours=self.state['settings']['intervalHours'])),message='公开同步完成；不可用字段保留未知' if success else '网络暂不可用，保留上次数据')
            if selected=={'github'} and not self.state['settings']['githubRepo']:sync['message']='GitHub 仓库尚未配置'
            if success:sync['lastSuccessAt']=stamp(self.clock())
            self._save()

    def _loop(self):
        while not self.stop.is_set():
            with self.lock:
                selected=set(self.pending);self.pending.clear()
            if selected:
                try:self._refresh(selected)
                except Exception as error:LOG.exception('Public sync failed');self.state['sync']['message']=str(error)[:250]
                with self.lock:
                    self.state['sync']['busy']=bool(self.pending)
            with self.lock:
                self.wake.clear()
                if self.pending:continue
                settings=self.state['settings'];next_at=self.state['sync'].get('nextCheckAt')
                periodic=self.auto_start and settings['autoSync']
                delay=max(.1,(dt.datetime.fromisoformat(next_at)-self.clock()).total_seconds()) if next_at and periodic else 3600
            if self.wake.wait(min(delay,3600)):continue
            if periodic and next_at and self.clock()>=dt.datetime.fromisoformat(next_at):
                with self.lock:self.pending.add('all');self.state['sync']['busy']=True

    def close(self):
        with self.lock:self.closed=True
        self.stop.set();self.wake.set()
        if self.worker and self.worker is not threading.current_thread():self.worker.join(.2)
