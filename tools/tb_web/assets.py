"""Read-only original statements and AST samples; explicit reviewed local profiles."""
import ast
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
import reviewed_cases

class AssetLibrary:
    def __init__(self,store,cache_dir=None):
        self.store=store
        self.lock=threading.RLock()
        self.cache_dir=Path(cache_dir) if cache_dir else Path(__file__).resolve().parents[2]/'state'/'tb-problem-assets'
        self.failures={}
        self._candidate_rows=None
        self._public_client=None

    def _cache_path(self,identity):
        return self.cache_dir/(hashlib.sha256(identity.encode('utf-8')).hexdigest()+'.json')

    def _paths(self,identity):
        import toolutil
        row=(self._candidate_rows or {}).get(identity)
        if row is None:row=self.store.row(identity)
        if row.get('_remote'):return row,None
        series,number=toolutil.parse_contest(row['场次'])
        directory,_=toolutil.contest_paths(self.store.data_root,series,number)
        return row,Path(directory) if directory else None

    @lru_cache(maxsize=256)
    def _cached(self,identity):
        row,directory=self._paths(identity)
        if row.get('_remote'):
            return self.store.extensions.statement(identity,fetch=False)
        import status_gui
        samples=[];statement=None;limits={'timeMs':2000,'memoryMb':256}
        if directory:
            letter=row['题号']
            target=directory/'_work'/'题面'/(letter+'.txt')
            if target.is_file():statement=target.read_text(encoding='utf-8-sig')
            sample_path=directory/'_work'/'samples.py'
            if sample_path.is_file():
                tree=ast.parse(sample_path.read_text(encoding='utf-8-sig'))
                for node in tree.body:
                    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SAMPLES' for t in node.targets):
                        for item in ast.literal_eval(node.value):
                            if isinstance(item,(tuple,list)) and len(item)==3 and re.match(r'^'+re.escape(letter)+r'\b',str(item[0])):
                                samples.append({'name':str(item[0]),'input':str(item[1]),'output':str(item[2])})
        url,_=status_gui.StatusGui.parse_problem_url(SimpleNamespace(data_root=self.store.data_root),row)
        # Personal fetched assets supplement missing disposable archive caches only.
        cache=self._cache_path(identity)
        if cache.is_file() and (not statement or not samples):
            try:
                saved=json.loads(cache.read_text(encoding='utf-8'))
                if saved.get('id')==identity and saved.get('url')==url:
                    statement=statement or saved.get('markdown')
                    samples=samples or saved.get('samples',[])
                    for key,value in (saved.get('limits') or {}).items():
                        if key in limits and isinstance(value,int) and not isinstance(value,bool) and value>0:
                            limits[key]=value
            except (OSError,ValueError):pass
        if statement:
            time=re.search(r'[Tt]ime [Ll]imit:\s*([\d.]+)\s*(?:seconds?|sec)',statement)
            memory=re.search(r'[Mm]emory [Ll]imit:\s*(\d+)\s*(?:MiB|megabytes|MB)',statement)
            if time:limits['timeMs']=round(float(time[1])*1000)
            if memory:limits['memoryMb']=int(memory[1])
        return {'id':identity,'title':row['题名'],'markdown':statement,'url':url,'samples':samples,
                'limits':limits,'statementAvailable':bool(statement)}

    def problem(self,identity):
        with self.lock:
            value=dict(self._cached(identity))
            if (not value['statementAvailable'] or not value['samples']) and value['url']:
                if identity.startswith('remote:'):
                    self.store.extensions.statement(identity,fetch=True)
                    self._cached.cache_clear();self.bundle.cache_clear()
                else:self._fetch_missing(identity,value)
                value=dict(self._cached(identity))
        bundle=self.bundle(identity)
        value.update(judge={'scope':bundle['scope'],'label':'本地审核测试' if bundle['scope']=='local' else '仅官方样例', 'cases':len(bundle['cases'])},locked=False,draft='',submissions=[])
        return value

    def _fetch_missing(self,identity,value):
        """Only an explicit single-problem opening fetches; preview never does network I/O."""
        parsed=urlsplit(value['url'])
        if parsed.hostname in ('codeforces.com','atcoder.jp','www.luogu.com.cn'):
            if time.monotonic()-self.failures.get(identity,-1000)<300:return
            try:
                from integrations import PublicClient
                from public_platforms import statement
                if self._public_client is None:self._public_client=PublicClient(self.cache_dir)
                saved=statement(self._public_client,identity,value['title'],value['url'])
                self.cache_dir.mkdir(parents=True,exist_ok=True)
                destination=self._cache_path(identity)
                import toolutil
                if destination.exists():toolutil.backup_to_repo(str(destination))
                toolutil.write_text_atomic(str(destination),json.dumps(saved,ensure_ascii=False))
                self._cached.cache_clear();self.bundle.cache_clear()
            except (OSError,ValueError,RuntimeError):self.failures[identity]=time.monotonic()
            return
        if parsed.hostname!='ac.nowcoder.com' or not re.fullmatch(r'/acm/contest/\d+/[A-Z]\d?',parsed.path):return
        if time.monotonic()-self.failures.get(identity,-1000)<300:return
        try:
            import fetch_problem as adapter
            request=Request(value['url'],headers={'User-Agent':'Mozilla/5.0 TB local practice','Accept':'text/html'})
            with urlopen(request,timeout=15) as response:
                if urlsplit(response.url).hostname!='ac.nowcoder.com':raise ValueError('原站要求登录，无法读取公开题面')
                raw=response.read(4*1024*1024+1)
                if len(raw)>4*1024*1024:raise ValueError('原题面过大')
            html=raw.decode('utf-8','replace')
            entries=adapter.extract_samples(html)
            body=adapter.cut_body(adapter.strip_tags(html))
            if '题目描述' not in body or not entries or not all(e['in'] and e['out'] for e in entries):
                raise ValueError('原站未返回完整题面与样例')
            saved={'id':identity,'url':value['url'],'markdown':f"# {value['title']}\n\n原题：{value['url']}\n\n"+body,
                   'samples':[{'name':e['name'],'input':e['in'],'output':e['out']} for e in entries]}
            self.cache_dir.mkdir(parents=True,exist_ok=True)
            destination=self._cache_path(identity)
            import toolutil
            if destination.exists():toolutil.backup_to_repo(str(destination))
            toolutil.write_text_atomic(str(destination),json.dumps(saved,ensure_ascii=False))
            self._cached.cache_clear();self.bundle.cache_clear()
        except (OSError,ValueError,RuntimeError):
            self.failures[identity]=time.monotonic()

    @lru_cache(maxsize=32)
    def bundle(self,identity):
        base=self._cached(identity)
        cases=list(base['samples']);checker=None
        local=False
        # A profile alone is insufficient: original statement and samples must also exist.
        if identity in reviewed_cases.PROFILES and base['statementAvailable'] and cases:
            extra,checker=reviewed_cases.build(identity)
            if extra:cases+=extra;local=True
        return {'scope':'local' if local else 'samples','cases':cases,'limits':dict(base['limits']),
                'checker':checker,'nonunique':bool(re.search(r'(?:multiple (?:sequences|solutions)|output any|any (?:valid|solution)|Special Judge|absolute.{0,20}error|relative error|误差|输出任意|多种答案|任意.*(?:排列|方案|答案))',base['markdown'] or '',re.I)) or '构造' in self.store.row(identity)['知识点'],
                'caseInsensitive':bool(re.search(r'(?:any case|case.insensitive|任意大小写|不区分大小写)',base['markdown'] or '',re.I)),
                'coverage':reviewed_cases.PROFILES.get(identity) if local else '仅样例，不代表完整评测'}

    def candidates(self,rows):
        # One request-scoped snapshot avoids re-parsing the full table per problem.
        # It is discarded after scanning, so later requests still read current rows.
        with self.lock:
            result=[]
            if hasattr(self.store,'raw_rows'):
                self._candidate_rows={r['场次']+'::'+r['题号']:r for r in self.store.raw_rows()}
                extensions=getattr(self.store,'extensions',None)
                if extensions:
                    for row in rows:
                        if row['id'].startswith('remote:'):
                            remote=extensions.row(row['id'])
                            if remote:self._candidate_rows[row['id']]=remote
            try:
                for row in rows:
                    try:base=self._cached(row['id'])
                    except (OSError,ValueError,SyntaxError):continue
                    if base['statementAvailable'] and base['samples']:
                        result.append(dict(row,judgeScope='local' if row['id'] in reviewed_cases.PROFILES else 'samples'))
                return result
            finally:self._candidate_rows=None
