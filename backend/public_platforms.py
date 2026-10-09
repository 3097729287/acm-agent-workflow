"""First-party public GET adapters. Missing evidence stays missing."""
import datetime as dt
import html
import json
import re
from urllib.parse import quote,urlsplit

LABELS={'codeforces':'Codeforces','atcoder':'AtCoder','nowcoder':'牛客','luogu':'洛谷'}
CF_TAGS={'binary search':'二分查找','brute force':'枚举','combinatorics':'组合计数','constructive algorithms':'构造','data structures':'数据结构','dfs and similar':'DFS','dp':'动态规划（官方宽标签）','dsu':'并查集','geometry':'计算几何','graph matchings':'二分图匹配','graphs':'图论','greedy':'贪心','hashing':'哈希','implementation':'模拟','math':'数学','number theory':'数论','shortest paths':'最短路','sortings':'排序','strings':'字符串','trees':'树','two pointers':'双指针','bitmasks':'位运算','flows':'网络流','fft':'FFT'}

def utc(value):
    if isinstance(value,str):
        try:return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(dt.timezone.utc).isoformat()
        except ValueError:return None
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        try:return dt.datetime.fromtimestamp(value/1000 if value>10**11 else value,dt.timezone.utc).isoformat()
        except (ValueError,OSError,OverflowError):return None
    return None

def integer(value):return value if isinstance(value,int) and not isinstance(value,bool) else None

def text(value):return html.unescape(re.sub(r'<[^>]*>','',str(value or ''))).strip()

def profile(platform,handle):
    url={'codeforces':'https://codeforces.com/profile/','atcoder':'https://atcoder.jp/users/','nowcoder':'https://ac.nowcoder.com/acm/contest/profile/','luogu':'https://www.luogu.com.cn/user/'}[platform]+quote(handle,safe='')
    return {'platform':platform,'handle':handle,'displayName':handle,'url':url,'status':'unconfigured' if not handle else 'partial','rating':None,'maxRating':None,'rank':None,'solvedCount':None,'submissionCount':None,'updatedAt':None,'error':'','history':[],'solved':[],'activity':[]}

def cf_result(client,path):
    value=client.json('https://codeforces.com/api/'+path)
    if value.get('status')!='OK':raise ValueError('Codeforces: '+str(value.get('comment','公开 API 未成功'))[:200])
    return value['result']

def account_cf(client,handle):
    value=profile('codeforces',handle)
    info=cf_result(client,'user.info?handles='+quote(handle))[0]
    value.update(displayName=info.get('handle',handle),rating=integer(info.get('rating')),maxRating=integer(info.get('maxRating')),rank=info.get('rank'),status='ready')
    history=cf_result(client,'user.rating?handle='+quote(handle))
    value['history']=[{'date':utc(x.get('ratingUpdateTimeSeconds')),'rating':x.get('newRating'),'contest':x.get('contestName'),'rank':x.get('rank')} for x in history[-1000:] if integer(x.get('newRating')) is not None]
    # Public submissions are paginated. A bound is honest partial evidence, not a full count.
    submissions=[];complete=False
    for offset in (1,1001,2001):
        page=cf_result(client,'user.status?handle='+quote(handle)+f'&from={offset}&count=1000')
        submissions+=page
        if len(page)<1000:complete=True;break
    solved={};days={}
    for submission in submissions:
        date=utc(submission.get('creationTimeSeconds'))
        if date:
            day=days.setdefault(date[:10],{'date':date[:10],'submissions':0,'accepted':0});day['submissions']+=1
        problem=submission.get('problem') or {};cid=problem.get('contestId');index=problem.get('index')
        if submission.get('verdict')!='OK' or not cid or not index:continue
        key=f'{cid}:{index}';url=f'https://codeforces.com/contest/{cid}/problem/{index}'
        record={'key':key,'url':url,'title':problem.get('name'),'tags':[CF_TAGS[t] for t in problem.get('tags',[]) if t in CF_TAGS],'difficulty':integer(problem.get('rating')),'acceptedAt':date}
        if key not in solved or date and date<(solved[key].get('acceptedAt') or date):solved[key]=record
    for record in solved.values():
        date=record.get('acceptedAt')
        if date and date[:10] in days:days[date[:10]]['accepted']+=1
    value.update(solved=list(solved.values()),activity=sorted(days.values(),key=lambda d:d['date'])[-1096:])
    value['submissionCount']=len(submissions) if complete else None
    value['solvedCount']=len(solved) if complete else None
    if not complete:value.update(status='partial',error='仅读取最近 3000 次公开提交；已证实通过题保留，完整数量未知')
    return value

def account_at(client,handle):
    value=profile('atcoder',handle)
    history=client.json('https://atcoder.jp/users/'+quote(handle)+'/history/json')
    if not isinstance(history,list):raise ValueError('AtCoder 官方历史结构无法识别')
    page=client.text(value['url']+'?lang=en')
    if not re.search(r'/users/'+re.escape(handle)+r'(?:["/?])',page,re.I):raise ValueError('AtCoder 公开账号不存在或不可读取')
    rated=[x for x in history if x.get('IsRated') and integer(x.get('NewRating')) is not None]
    value['history']=[{'date':utc(x.get('EndTime')),'rating':x['NewRating'],'contest':x.get('ContestName'),'rank':x.get('Place')} for x in rated[-1000:]]
    if rated:value.update(rating=rated[-1]['NewRating'],maxRating=max(x['NewRating'] for x in rated))
    value.update(status='partial',error='官方评级历史已同步；完整通过题/提交总数尚未确认')
    try:
        ac=client.json('https://kenkoooo.com/atcoder/atcoder-api/v3/user/ac_rank?user='+quote(handle))
        if isinstance(ac,dict) and integer(ac.get('count')) is not None:
            value['solvedCount']=ac['count'];value['solvedCountSource']='AtCoder Problems 公开统计'
        cursor=0;submissions=[];seen=set();complete=False
        for batch in range(6):
            page=client.json('https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user='+quote(handle)+'&from_second='+str(cursor))
            if not isinstance(page,list):break
            for item in page:
                if not isinstance(item,dict) or item.get('user_id','').lower()!=handle.lower():continue
                identity=integer(item.get('id'))
                if identity is not None and identity not in seen:submissions.append(item);seen.add(identity)
            if len(page)<500:complete=True;break
            times=[integer(item.get('epoch_second')) for item in page if isinstance(item,dict)]
            last=max((value for value in times if value is not None),default=cursor)
            if last<cursor:break
            # Inclusive re-read at the boundary preserves multiple submissions
            # in the same second; IDs remove duplicates. No progress means stop.
            if last==cursor:break
            cursor=last
        solved={};days={}
        for item in submissions:
            date=utc(item.get('epoch_second'))
            if date:days.setdefault(date[:10],{'date':date[:10],'submissions':0,'accepted':0})['submissions']+=1
            cid,task=item.get('contest_id'),item.get('problem_id')
            if item.get('result')!='AC' or not cid or not task or not re.fullmatch(r'[a-zA-Z0-9_-]+',str(cid)+str(task)):continue
            key=str(task)
            record={'key':key,'url':f'https://atcoder.jp/contests/{cid}/tasks/{task}','title':task,'acceptedAt':date}
            if key not in solved or date and date<(solved[key].get('acceptedAt') or date):solved[key]=record
        for record in solved.values():
            date=record.get('acceptedAt')
            if date and date[:10] in days:days[date[:10]]['accepted']+=1
        value.update(solved=list(solved.values()),activity=sorted(days.values(),key=lambda day:day['date'])[-1096:],
                     submissionCount=len(submissions) if complete else None,submissionCountSource='AtCoder Problems 公开提交' if complete else None)
        if complete:
            if value['solvedCount'] is None:value['solvedCount']=len(solved)
            value.update(status='ready',error='官方评级 + AtCoder Problems 公开通过/提交记录',statisticsSource='AtCoder 官方 / AtCoder Problems')
        else:value['error']='官方评级已更新；公开通过统计来自 AtCoder Problems，提交明细最多读取 3000 条'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):pass
    return value

def account_lg(client,handle):
    value=profile('luogu',handle);data=lg_data(client.json(value['url'],headers={'x-lentille-request':'content-only'}))
    user=data.get('user') or {}
    if str(user.get('uid'))!=handle:raise ValueError('洛谷公开账号不存在或需要登录')
    history=data.get('elo') or []
    value.update(displayName=user.get('name',handle),rating=integer(user.get('eloValue')),rank=integer(user.get('ranking')),solvedCount=integer(user.get('passedProblemCount')),submissionCount=None)
    value['history']=[{'date':utc(x.get('time')),'rating':x.get('rating'),'contest':(x.get('contest') or {}).get('name')} for x in history if integer(x.get('rating')) is not None]
    if value['history']:value['maxRating']=max(x['rating'] for x in value['history'])
    # gu.rating is social/luogu score, deliberately never treated as contest Elo.
    daily=data.get('dailyCounts') or []
    value['activity']=[{'date':utc(x.get('date') or x.get('time'))[:10],'submissions':x['count'],'accepted':0} for x in daily if isinstance(x,dict) and utc(x.get('date') or x.get('time')) and integer(x.get('count')) is not None]
    value.update(status='partial',error='洛谷公开主页提供的比赛评级/统计已读取；私有通过记录不推测，提交总数未知')
    return value

def account_nc(client,handle):
    value=profile('nowcoder',handle);page=client.text(value['url'])
    # The public server renders account heading and explicit Rating text. Do not
    # read embedded cookies, login payloads, generic scores, or unrelated ranking.
    name=re.search(r'<(?:h1|h2)[^>]*class=["\'][^"\']*(?:profile|user-name)[^"\']*["\'][^>]*>(.*?)</',page,re.S)
    rating=re.search(r'(?:Rating|rating)\s*(?:</[^>]+>\s*<[^>]+>|[:：])\s*(\d+)',page)
    if not name and not rating:raise ValueError('牛客公开主页未提供可识别账号统计；请使用原站查看或等待接口恢复')
    if name:value['displayName']=text(name[1])
    if rating:value['rating']=int(rating[1])
    value.update(status='partial',error='仅采用公开主页明确显示的字段；通过题、提交总数与评级历史未知')
    return value

ACCOUNT_ADAPTERS={'codeforces':account_cf,'atcoder':account_at,'nowcoder':account_nc,'luogu':account_lg}

def row(platform,contest,index,title,url,difficulty,source,tags=()):
    cid=str(contest['id']);name=contest.get('name') or cid
    result={'id':f'remote:{platform}:{cid}::{index}','contest':name,'problem':str(index),'title':title,'tags':list(tags),'knowledge':'、'.join(tags),'difficulty':difficulty,'difficultySource':source,'status':'未做','date':'','platform':LABELS[platform],'series':contest.get('series') or LABELS[platform],'queue':None,'url':url,'source':'remote','solutionAvailable':False,'solutionState':'missing','contestId':cid,'startedAt':utc(contest.get('start')),'endedAt':utc(contest.get('end')),'contestDate':utc(contest.get('start')),'contestDateSource':'原站公开比赛时间'}
    from knowledge import enrich_row
    return enrich_row(result,official_tags=tags)


def discover_cf(client,now):
    contests=cf_result(client,'contest.list?gym=false')
    ended=[c for c in contests if c.get('phase')=='FINISHED' and integer(c.get('startTimeSeconds')) is not None and integer(c.get('durationSeconds')) is not None and c['startTimeSeconds']+c['durationSeconds']<=now.timestamp()][:30]
    ids={c['id']:c for c in ended}
    problems=cf_result(client,'problemset.problems')['problems'];rows=[];pending=[]
    for p in problems:
        c=ids.get(p.get('contestId'))
        if not c:continue
        contest={'id':c['id'],'name':c['name'],'start':c['startTimeSeconds'],'end':c['startTimeSeconds']+c['durationSeconds'],'series':'Codeforces'}
        item=row('codeforces',contest,p['index'],p['name'],f"https://codeforces.com/contest/{c['id']}/problem/{p['index']}",integer(p.get('rating')),'Codeforces 官方 rating',[CF_TAGS[t] for t in p.get('tags',[]) if t in CF_TAGS])
        (rows if item['difficulty'] is not None else pending).append(item)
    return rows,pending,'已检查最近 30 场已结束比赛；缺官方评级的题等待评级发布'

def lg_data(value):
    if not isinstance(value,dict) or value.get('status',200)!=200:raise ValueError('洛谷公开页面暂不可用或需要登录')
    return value.get('data') or {}

def discover_lg(client,now):
    data=lg_data(client.json('https://www.luogu.com.cn/contest/list',headers={'x-lentille-request':'content-only'}));contests=((data.get('contests') or {}).get('result') or [])
    ended=[c for c in contests if integer(c.get('endTime')) is not None and c['endTime']<=now.timestamp() and (c.get('host') or {}).get('id')==1000][:6]
    import cf_eq
    rows=[];pending=[]
    for c in ended:
        detail=lg_data(client.json('https://www.luogu.com.cn/contest/'+str(c['id']),headers={'x-lentille-request':'content-only'}))
        verified=detail.get('contest') or {}
        if not integer(verified.get('endTime')) or verified['endTime']>now.timestamp():continue
        contest={'id':c['id'],'name':verified.get('name',c['name']),'start':verified.get('startTime'),'end':verified['endTime'],'series':'洛谷官方赛'}
        for index,entry in enumerate(detail.get('contestProblems') or []):
            p=entry.get('problem') or {};pid=p.get('pid')
            if not pid:continue
            level=integer(p.get('difficulty'));evaluation=cf_eq.cf_eq_luogu(level)
            item=row('luogu',contest,entry.get('no') or chr(65+index),p.get('name') or pid,'https://www.luogu.com.cn/problem/'+pid,evaluation['cf_eq_rating'],'CF-EQ v1.0 / 洛谷官方难度档 '+str(level))
            (rows if item['difficulty'] is not None else pending).append(item)
    return rows,pending,'洛谷官方结束赛；难度按已有 CF-EQ 档位规则换算，非官方 CF rating'

def discover_at(client,now):
    import cf_eq
    page=client.text('https://atcoder.jp/contests/archive?lang=en');pending=[];contests=[];rows=[]
    # Existing, explicitly authorized AtCoder Problems model and CF-EQ rules.
    # Estimates remain labelled; never use official point values as difficulty.
    try:models=client.json('https://kenkoooo.com/atcoder/resources/problem-models.json')
    except (OSError,ValueError,RuntimeError):models={}
    for block in re.findall(r'<tr\b[^>]*>.*?</tr>',page,re.S):
        cid=re.search(r'href=["\']/contests/([a-z0-9_-]+)["\']',block)
        start=re.search(r'<time[^>]*>([^<]+)</time>',block)
        duration=re.findall(r'<td[^>]*>\s*(\d+):(\d\d)\s*</td>',block)
        if not cid or not start or not duration:continue
        if not re.fullmatch(r'(abc|arc)\d+',cid[1]):continue
        try:started=dt.datetime.strptime(start[1],'%Y-%m-%d %H:%M:%S%z');ended=started+dt.timedelta(hours=int(duration[0][0]),minutes=int(duration[0][1]))
        except ValueError:continue
        if ended>now:continue
        contests.append({'id':cid[1],'name':text(re.search(r'<a href=["\']/contests/[^"\']+["\']>(.*?)</a>',block,re.S)[1]),'start':started.timestamp(),'end':ended.timestamp(),'series':re.match(r'[a-z]+',cid[1])[0].upper()})
        if len(contests)>=6:break
    for contest in contests:
        cid=contest['id'];tasks=client.text('https://atcoder.jp/contests/'+cid+'/tasks?lang=en')
        matches=re.findall(r'<td class="text-center no-break"><a href="/contests/[^"/]+/tasks/([^"]+)">([^<]+)</a></td>\s*<td><a href="[^"]+">([^<]+)</a></td>',tasks)
        if not matches:
            pending.append({'id':cid,'title':contest['name'],'reason':'官方任务表尚未公开或无法读取'});continue
        for task,index,title in matches:
            native=integer((models.get(task) or {}).get('difficulty'))
            evaluation=cf_eq.cf_eq_atcoder(native)
            value=row('atcoder',contest,index.strip(),html.unescape(title.strip()),f'https://atcoder.jp/contests/{cid}/tasks/{task}',evaluation['cf_eq_rating'],'CF-EQ · AtCoder Problems估算')
            value['nativeDifficulty']=native;value['difficultyEvidence']=evaluation['difficulty_evidence']
            (rows if native is not None else pending).append(value)
    return rows,pending,'官方已结束 ABC/ARC；按既有 CF-EQ 换算 AtCoder Problems 模型估算，模型未出则待定'

def discover_nc(client,now):
    page=client.text('https://ac.nowcoder.com/acm/contest/vip-index');pending=[]
    for block in re.findall(r'<div\b[^>]*data-id="(\d+)"[^>]*data-json="([^"]+)"[^>]*>(.*?)(?=<div\b[^>]*data-id=|$)',page,re.S):
        cid,encoded,body=block
        try:meta=json.loads(html.unescape(html.unescape(encoded)))
        except ValueError:continue
        end=meta.get('contestEndTime');start=meta.get('contestStartTime')
        if not integer(end) or end/1000>now.timestamp():continue
        name=re.search(r'<h4>.*?<a[^>]*>(.*?)</a>',body,re.S)
        problems=client.json('https://ac.nowcoder.com/acm/contest/problem-list?token=&id='+cid)
        if problems.get('code')!=0:raise ValueError('牛客公开题单不可用或比赛未公开')
        for p in (problems.get('data') or {}).get('data') or []:
            pending.append({'id':f"remote:nowcoder:{cid}::{p.get('index')}",'contest':text(name[1]) if name else cid,'title':p.get('title'),'url':f"https://ac.nowcoder.com/acm/contest/{cid}/{p.get('index')}",'startedAt':utc(start),'endedAt':utc(end),'reason':'牛客未提供可靠数值难度；分值/通过率不作为难度'})
        if len(pending)>=60:break
    return [],pending,'牛客公开结束赛题单已发现；无可靠数值难度，等待明确估值证据'

DISCOVERY_ADAPTERS={'codeforces':discover_cf,'luogu':discover_lg,'atcoder':discover_at,'nowcoder':discover_nc}

def statement(client,identity,title,url):
    import fetch_problem as adapter
    parsed=urlsplit(url);host=parsed.hostname;limits={'timeMs':2000,'memoryMb':256};body='';samples=[]
    if host=='www.luogu.com.cn':
        pid=parsed.path.rsplit('/',1)[-1];p=lg_data(client.json(url,headers={'x-lentille-request':'content-only'})).get('problem') or {}
        if p.get('pid')!=pid:raise ValueError('原题编号不匹配或题面尚未公开')
        content=p.get('content') or p.get('contenu') or {};body='\n\n'.join('## '+label+'\n\n'+content[key] for key,label in adapter.LG_SECTIONS if content.get(key))
        samples=[{'name':'样例 '+str(i+1),'input':x[0],'output':x[1]} for i,x in enumerate(p.get('samples') or [])]
        raw=p.get('limits') or {};times=raw.get('time') or [];memories=raw.get('memory') or []
        if times:limits['timeMs']=int(times[0])
        if memories:limits['memoryMb']=max(1,round(memories[0]/1000))
    elif host=='atcoder.jp':
        page=client.text(url+('&' if '?' in url else '?')+'lang=en');english=adapter.at_span(page,'lang-en')
        if not english:raise ValueError('AtCoder 英文原题面暂不可读取')
        body,raw=adapter.at_statement(english);samples=[{'name':x['name'],'input':x['in'],'output':x['out']} for x in raw]
        tl=re.search(r'Time Limit:\s*([\d.]+)\s*sec',text(page));ml=re.search(r'Memory Limit:\s*(\d+)\s*MiB',text(page))
        if tl:limits['timeMs']=round(float(tl[1])*1000)
        if ml:limits['memoryMb']=int(ml[1])
    elif host=='codeforces.com':
        page=client.text(url);_,body,raw=adapter.cf_statement(page);samples=[{'name':x['name'],'input':x['in'],'output':x['out']} for x in raw]
        tl=re.search(r'Time limit:\s*([\d.]+)\s*seconds?',body,re.I);ml=re.search(r'Memory limit:\s*(\d+)\s*megabytes',body,re.I)
        if tl:limits['timeMs']=round(float(tl[1])*1000)
        if ml:limits['memoryMb']=int(ml[1])
    elif host=='ac.nowcoder.com':
        page=client.text(url);body=adapter.cut_body(adapter.strip_tags(page));samples=[{'name':x['name'],'input':x['in'],'output':x['out']} for x in adapter.extract_samples(page)]
        if '题目描述' not in body:body=''
    else:raise ValueError('不支持的原题站点')
    if not body or not samples or not all(x['input'] and x['output'] for x in samples):raise ValueError('原站未返回完整公开题面与官方样例')
    return {'id':identity,'title':title,'url':url,'markdown':'# '+title+'\n\n'+body,'samples':samples,'limits':limits,'statementAvailable':True}
