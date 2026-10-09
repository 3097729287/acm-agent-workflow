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

class LegacyAssetLibrary:
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
        import archive_import as status_gui
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
        url,_=status_gui.parse_problem_url(SimpleNamespace(data_root=self.store.data_root),row)
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
