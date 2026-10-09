"""Actual contest times from cached official payloads; no file dates or guessed rounds."""
import datetime as dt
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit
import toolutil


def iso(value):
    try:
        if isinstance(value,str):
            parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
            if parsed.tzinfo is None:return None
        elif isinstance(value,(int,float)) and not isinstance(value,bool):parsed=dt.datetime.fromtimestamp(value/1000 if value>10**11 else value,dt.timezone.utc)
        else:return None
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except (ValueError,OSError,OverflowError):return None


def parse(payload,url):
    host=urlsplit(url or '').hostname
    result={'startedAt':None,'endedAt':None,'contestDate':None}
    if host=='ac.nowcoder.com' and isinstance(payload,str):
        marker=re.search(r'\bwindow\.pageInfo\s*=\s*',payload)
        if marker:
            try:payload=json.JSONDecoder().raw_decode(payload[marker.end():].lstrip())[0]
            except ValueError:payload={}
    if host=='atcoder.jp' and isinstance(payload,str):
        start=re.search(r'\bvar\s+startTime\s*=\s*moment\(["\']([^"\']+)',payload)
        end=re.search(r'\bvar\s+endTime\s*=\s*moment\(["\']([^"\']+)',payload)
        if start:result['startedAt']=iso(start[1])
        if end:result['endedAt']=iso(end[1])
    if isinstance(payload,dict):
        def sources(value):
            if isinstance(value,dict):
                for key,child in value.items():
                    if key in ('contestOrigin','contest','contestInfo') and isinstance(child,dict):yield child
                    if isinstance(child,(dict,list)):yield from sources(child)
            elif isinstance(value,list):
                for child in value:yield from sources(child)
        candidates=list(sources(payload))
        if host=='codeforces.com' and payload.get('phase') or host=='ac.nowcoder.com' and payload.get('startTime'):candidates.insert(0,payload)
        for source in candidates:
            start=source.get('startTimeSeconds',source.get('contestStartTime',source.get('startTime')))
            end=source.get('contestEndTime',source.get('endTime'))
            if host=='codeforces.com' and isinstance(start,int) and isinstance(source.get('durationSeconds'),int):end=start+source['durationSeconds']
            if iso(start):result.update(startedAt=iso(start),endedAt=iso(end));break
    result['contestDate']=result['startedAt']
    if result['startedAt']:result['contestDateSource']='原站公开比赛时间'
    return result


class ContestDates:
    def __init__(self,store):
        self.store=store;self.lock=threading.RLock();self.cache={};self.public={};self.by_url={}
        from paths import resource
        seed=resource('public-contest-dates.json')
        if seed.is_file():self.public.update(json.loads(seed.read_text(encoding='utf-8')))

    @staticmethod
    def contest_url(url):
        parsed=urlsplit(url or '');host=parsed.hostname;path=parsed.path
        patterns={'codeforces.com':r'/contest/(\d+)','atcoder.jp':r'/contests/([a-z0-9_-]+)','ac.nowcoder.com':r'/acm/contest/(\d+)'}
        match=re.match(patterns.get(host,r'(?!)'),path)
        return 'https://'+host+match[0] if match else None

    def observe_cf(self,contests):
        with self.lock:
            for contest in contests:
                url='https://codeforces.com/contest/'+str(contest.get('id'))
                value=parse(contest,url)
                if value['startedAt']:self.by_url[url]=value

    def observe(self,row):
        if row.get('startedAt'):
            with self.lock:self.public[row['contest']]=dict((k,row.get(k)) for k in ('startedAt','endedAt','contestDate','contestDateSource'))

    def for_row(self,raw,url=None):
        if raw.get('_remote'):
            with self.lock:return dict(self.public.get(raw['场次'],{}))
        if hasattr(self.store,'library'):
            value=raw.get('_library_metadata')
            if value is None:
                stored=self.store.library.find(raw['场次']+'::'+raw['题号'])
                value=stored['encoded'] if stored else {}
            metadata={key:value.get(key) for key in ('startedAt','endedAt','contestDate','contestDateSource')}
            return dict(self.by_url.get(self.contest_url(url),metadata if metadata.get('startedAt') else self.public.get(raw['场次'],metadata)))
        series,number=toolutil.parse_contest(raw['场次'])
        if not series:return parse(None,url)
        directory,_=toolutil.contest_paths(self.store.data_root,series,number)
        if not directory:return parse(None,url)
        directory=Path(directory);files=sorted((directory/'_work'/'raw').glob('*'))
        files=[p for p in files if p.suffix in ('.html','.json') and p.is_file()][:8]
        signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files)
        with self.lock:
            cached=self.cache.get(raw['场次'])
            if cached and cached[0]==signature:
                value=cached[1]
                return dict(value if value.get('startedAt') else self.by_url.get(self.contest_url(url),self.public.get(raw['场次'],value)))
            result=parse(None,url)
            for path in files:
                if path.stat().st_size>4*1024*1024:continue
                try:
                    text=path.read_text(encoding='utf-8-sig');value=json.loads(text) if path.suffix=='.json' else text
                    observed=parse(value,url)
                    if observed['startedAt']:result=observed;break
                except (OSError,ValueError):continue
            if not result['startedAt']:result=self.by_url.get(self.contest_url(url),self.public.get(raw['场次'],result))
            self.cache[raw['场次']]=(signature,result)
            return dict(result)
