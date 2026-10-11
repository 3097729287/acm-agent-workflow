"""Deadline plans with explicit workload assumptions and real acceptance evidence."""
import datetime as dt
import json
import math
import re
import uuid
from training import ServiceError, iso
from progression import SHANGHAI, parse_time
from insights import canonical_url

DISCLAIMER='题量是训练安排，不保证评级或奖项；每周还需比赛、复盘与专项学习。区域赛另需队伍配合。'


class Goals:
    def __init__(self,training):self.training=training

    def save(self,body):
        if not isinstance(body,dict):raise ServiceError(422,'目标参数无效')
        title=body.get('title','').strip() if isinstance(body.get('title',''),str) else ''
        if not title or len(title)>160:raise ServiceError(422,'请填写 1–160 字的具体目标')
        kind=body.get('kind','custom')
        match=re.search(r'(?i)\bcf\s*(\d{3,4})\b',title)
        if match and kind=='custom':kind='cf';body={**body,'targetRating':int(match[1])}
        if kind not in ('cf','xcpc','lanqiao','custom'):raise ServiceError(422,'目标类型无效')
        today=self.training._now().astimezone(SHANGHAI).date()
        try:
            deadline=dt.date.fromisoformat(body['deadline'])
            baseline=int(body.get('currentRating',1000))
            minutes=int(body.get('dailyMinutes',90))
            target=int(body.get('targetRating',2200 if kind=='cf' else 2000 if kind=='xcpc' else 1800))
            total=int(body.get('totalProblems',100)) if kind=='custom' else max(30,math.ceil(max(0,target-baseline)/100)*30)
        except (ValueError,TypeError,KeyError,OverflowError):raise ServiceError(422,'请填写具体截止日期、起点和每日可用分钟数')
        if not today<=deadline<=today+dt.timedelta(days=1826):raise ServiceError(422,'截止日期须在今天至五年内；过期目标请调整日期')
        if not 0<=baseline<=4000 or not 200<=target<=4000 or not 15<=minutes<=720 or not 1<=total<=10000:
            raise ServiceError(422,'起点须为 0–4000，目标参考值为 200–4000，每日 15–720 分钟，自定义题量 1–10000')
        t=self.training
        with t.lock:
            identity=body.get('id') or 'goal-'+uuid.uuid4().hex
            previous=t.connection.execute('SELECT * FROM goals WHERE id=?',(identity,)).fetchone()
            if body.get('id') and not previous:raise ServiceError(404,'目标不存在')
            if not previous and t.connection.execute("SELECT COUNT(*) FROM goals WHERE archived=0").fetchone()[0]>=10:raise ServiceError(422,'最多同时规划 10 个目标，请先归档已结束目标')
            start=previous['created_at'] if previous else iso(t._now())
            config={'title':title,'kind':kind,'deadline':deadline.isoformat(),'currentRating':baseline,'targetRating':target,
                    'dailyMinutes':minutes,'totalProblems':total,'minutesPerProblem':60 if kind in ('cf','xcpc') else 45,
                    'assumption':'参考值每提高 100，安排 30 道新题；最低 30 题。' if kind!='custom' else '按你填写的题量安排。',
                    'disclaimer':DISCLAIMER}
            with t._write() as db:
                db.execute('INSERT INTO goals(id,created_at,config,archived) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET config=excluded.config',
                           (identity,start,json.dumps(config,ensure_ascii=False)))
            return self.list()

    def archive(self,identity):
        t=self.training
        with t.lock:
            if not t.connection.execute('SELECT 1 FROM goals WHERE id=?',(identity,)).fetchone():raise ServiceError(404,'目标不存在')
            with t._write() as db:db.execute('UPDATE goals SET archived=1 WHERE id=?',(identity,))
        return self.list()

    def list(self):
        t=self.training
        with t.lock:
            now=t._now();today=now.astimezone(SHANGHAI).date()
            rows=t._library();metadata={row['id']:row for row in rows}
            accepted={}
            for record in t.connection.execute("SELECT * FROM submissions WHERE mode='submit' AND verdict='AC' AND scope='official' AND finished_at IS NOT NULL ORDER BY submitted_at,rowid"):
                row=metadata.get(record['problem_id'],{})
                key=canonical_url(row.get('url')) or record['problem_id']
                accepted.setdefault(key,{'id':record['problem_id'],'at':parse_time(record['submitted_at'])})
            extension=getattr(t.store,'extensions',None)
            if extension:
                for account in extension.snapshot().get('accounts',[]):
                    for item in account.get('solved',[]):
                        stamp=parse_time(item.get('acceptedAt'));key=canonical_url(item.get('url'))
                        if key and stamp and (key not in accepted or stamp<accepted[key]['at']):accepted[key]={'id':None,'at':stamp}
            locked=set(t._locked_ids(t.connection.execute("SELECT * FROM contests WHERE status='running'").fetchone())) if t.active_contest() else set()
            result=[]
            for record in t.connection.execute('SELECT * FROM goals WHERE archived=0 ORDER BY created_at,id'):
                goal=json.loads(record['config']);start=parse_time(record['created_at']);first=start.astimezone(SHANGHAI).date();end=dt.date.fromisoformat(goal['deadline'])
                days=max(1,(end-first).days+1);total=goal['totalProblems']
                evidence=[item for item in accepted.values() if start<item['at']<=now and item['at'].astimezone(SHANGHAI).date()<=end]
                done=len(evidence);elapsed=max(0,min(days,(today-first).days));expected=math.ceil(total*elapsed/days)
                due=math.ceil(total*min(days,elapsed+1)/days);daily=max(0,due-expected)
                today_done=sum(item['at'].astimezone(SHANGHAI).date()==today for item in evidence)
                left=max(0,(end-today).days+1);remaining=max(0,total-done);weekly=math.ceil(remaining*min(7,left)/max(1,left))
                # Reserve 30% of study time for reviewing and contest participation.
                capacity=math.floor(left*goal['dailyMinutes']*.7/goal['minutesPerProblem']);warnings=[]
                if today>end and remaining:warnings.append('截止日期已过，训练题量尚未完成。请复盘并调整目标。')
                if remaining>capacity:warnings.append(f'时间压力：剩余 {remaining} 题超出预计容量 {capacity} 题，建议延后截止日期或调整目标。')
                if done<expected:warnings.append(f'进度落后 {expected-done} 题；本周需安排约 {weekly} 题。')
                if left<=14 and goal['kind']!='custom' and goal['targetRating']-goal['currentRating']>=300:warnings.append('期限明显偏紧，短期题量不能替代持续参赛与能力积累。')
                if goal['kind']=='cf' and goal['targetRating']<=goal['currentRating']:warnings.append('填写的起点已达到目标参考值，可改为巩固目标；评级结果需原站核验。')
                def score(row):
                    preferred=(goal['kind']=='lanqiao' and '蓝桥' in row['contest']) or (goal['kind']=='cf' and row.get('platform')=='Codeforces') or (goal['kind']=='xcpc' and re.search(r'(?i)(ICPC|CCPC)',row['contest']))
                    difficulty=row.get('difficulty');fit=abs(difficulty-goal['currentRating']-150) if isinstance(difficulty,(int,float)) else 500
                    return (not preferred,fit,row['id'])
                candidates=[row for row in rows if row['id'] not in locked and (canonical_url(row.get('url')) or row['id']) not in accepted]
                candidates.sort(key=score)
                weekly_plan=[]
                cursor=max(first,today);offset=0
                while cursor<=end and len(weekly_plan)<260:
                    stop=min(end,cursor+dt.timedelta(days=6));span=(stop-cursor).days+1
                    amount=math.ceil(remaining*(offset+span)/max(1,left))-math.ceil(remaining*offset/max(1,left))
                    weekly_plan.append({'start':cursor.isoformat(),'end':stop.isoformat(),'target':amount});offset+=span;cursor=stop+dt.timedelta(days=1)
                before_today=max(0,total-done+today_done)
                task_target=min(before_today,max(daily,math.ceil(before_today/max(1,left)))) if left else 0
                result.append({**goal,'id':record['id'],'createdAt':record['created_at'],'progress':done,'remaining':remaining,
                    'remainingDays':left,'weeklyTarget':weekly,'weeklyPlan':weekly_plan,'capacity':capacity,'warnings':warnings,'workloadCompleted':done>=total,
                    'dailyTask':{'date':today.isoformat(),'target':task_target,'progress':today_done,'completed':today_done>=task_target,
                                 'problems':[{key:row.get(key) for key in ('id','title','contest','difficulty')} for row in candidates[:min(8,max(1,task_target))]]}})
            return {'goals':result,'date':today.isoformat(),'notice':DISCLAIMER}
