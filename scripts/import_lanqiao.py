"""Import explicitly labelled C/C++ university B originals from Luogu's public OJ.

Anonymous GET only. Missing years/rounds remain visible in the coverage report.
The source name and attribution are retained; no solutions are fabricated.
"""
import argparse
import http.cookiejar
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request,build_opener,HTTPCookieProcessor

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/common')]
from library import LibraryDatabase
import cf_eq
from fetch_problem import LG_SECTIONS


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--database',type=Path,default=ROOT/'data/library.sqlite3')
    args=parser.parse_args();args.cache.mkdir(parents=True,exist_ok=True)
    opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def fetch(path,label):
        destination=args.cache/(label+'.json')
        if destination.is_file():return json.loads(destination.read_text(encoding='utf-8'))
        for attempt in range(3):
            try:
                request=Request('https://www.luogu.com.cn'+path,headers={'User-Agent':'Mozilla/5.0 TB public historical problem importer','x-lentille-request':'content-only'})
                with opener.open(request,timeout=25) as response:value=json.load(response)
                if value.get('status')!=200:raise ValueError('Public content not available')
                data=value['data']
                destination.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');time.sleep(.8)
                return data
            except Exception:
                if attempt==2:raise
                time.sleep(1+attempt)
    discovered={};page=1;pages=1
    while page<=pages:
        data=fetch('/problem/list?'+urlencode({'keyword':'蓝桥杯','page':page}),f'list-{page}')['problems']
        pages=math.ceil(data['count']/data['perPage'])
        for problem in data['result']:
            match=re.match(r'^\[蓝桥杯 (20\d{2}) (省|国) B([^\]]*)\]',problem.get('name',''))
            if match:discovered[problem['pid']]=(problem,match.groups())
        print('list',page,'/',pages,'B originals',len(discovered),flush=True);page+=1
    records=[];errors=[];coverage={}
    for index,(pid,(metadata,(year,stage,variant))) in enumerate(discovered.items()):
        try:
            problem=fetch('/problem/'+pid,pid).get('problem') or {}
            if problem.get('pid')!=pid or problem.get('name')!=metadata['name']:raise ValueError('Source identity mismatch')
            content=problem.get('content') or problem.get('contenu') or {}
            body='\n\n'.join('## '+label+'\n\n'+content[key] for key,label in LG_SECTIONS if content.get(key))
            if not body or len(body)<30:raise ValueError('Incomplete public statement')
            # OJ source explicitly identifies year, stage and B. Keep second rounds distinct.
            contest=f'蓝桥杯 {year} C/C++大学B组 '+('初赛' if stage=='省' else '决赛')+((' · '+variant.strip()) if variant.strip() else '')
            title=re.sub(r'^\[[^\]]+\]\s*','',metadata['name']);identity='lanqiao:'+year+':'+stage+':'+variant+'::'+pid
            url='https://www.luogu.com.cn/problem/'+pid
            native=problem.get('difficulty');evaluation=cf_eq.cf_eq_luogu(native)
            difficulty=evaluation['cf_eq_rating']
            raw={'场次':contest,'题号':pid,'题名':title,'知识点':'','难度':str(difficulty) if difficulty is not None else '—','状态':'未做','日期':'','_id':identity,'_url':url,'_platform':'洛谷','_series':'蓝桥杯 C/C++大学B'}
            encoded={'id':identity,'contest':contest,'problem':pid,'title':title,'knowledge':'','tags':[],'difficulty':difficulty,
                     'platform':'洛谷','series':'蓝桥杯 C/C++大学B','url':url,'source':'lanqiao-history','status':'未做','date':'','queue':None,
                     'solutionAvailable':False,'solutionState':'missing','nativeDifficulty':native,'difficultySource':'CF-EQ / 洛谷官方难度档 '+str(native),
                     'examYear':int(year),'examStage':'初赛' if stage=='省' else '决赛','examGroup':'C/C++大学B','originalTitle':metadata['name'],
                     'collectionSource':url,'collectionNotice':'按洛谷原题标题核对；填空题可能合并在一道 OJ 题中，题单不代表原卷题数或题序。'}
            samples=[{'name':'样例 '+str(i+1),'input':sample[0],'output':sample[1]} for i,sample in enumerate(problem.get('samples') or []) if len(sample)>=2]
            limits=problem.get('limits') or {};times=limits.get('time') or [];memory=limits.get('memory') or []
            statement={'id':identity,'title':title,'url':url,'markdown':'# '+metadata['name']+'\n\n来源：[洛谷收录原题]('+url+')\n\n'+body,
                       'samples':samples,'limits':{'timeMs':int(times[0]) if times else 2000,'memoryMb':max(1,round(memory[0]/1024)) if memory else 256},
                       'statementAvailable':True}
            records.append((raw,encoded,None,statement));coverage.setdefault(year,{}).setdefault(stage,[]).append(pid)
        except Exception as error:errors.append({'pid':pid,'error':type(error).__name__})
        print('statement',index+1,'/',len(discovered),'importable',len(records),'missing',len(errors),flush=True)
    database=LibraryDatabase(args.database)
    database.backup('before-lanqiao-import')
    database.import_records(records,{}, {},{'lanqiao_source':'https://www.luogu.com.cn/problem/list?keyword=蓝桥杯','lanqiao_group':'C/C++大学B'})
    report={'group':'C/C++大学B','problems':len(records),'coverage':coverage,'missing':errors,'notice':'OJ 收录题；未公开内容不捏造，不把其他组别混入 B 组。'}
    (ROOT/'backend/resources/lanqiao-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'imported':len(records),'missing':len(errors),'years':sorted(coverage)}),flush=True)


if __name__=='__main__':main()
