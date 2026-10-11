"""Editable practice defaults; the original event's published rules take precedence."""
import re
from training import ServiceError

RULE_SOURCE='https://wf.icpc.global/2026/about/'


def is_xcpc(row):
    return bool(re.search(r'(?i)(?<![A-Za-z])(?:ICPC|CCPC|XCPC)(?![A-Za-z])',str(row.get('contest',''))+' '+str(row.get('series',''))))


def rules(body):
    preset=body.get('rules','acm')
    if preset not in ('acm','xcpc'):raise ServiceError(400,'请选择 ACM 或 XCPC 赛制')
    try:
        penalty=int(body.get('wrongPenalty',20))
    except (ValueError,TypeError):raise ServiceError(400,'罚时须为整数分钟')
    compile_penalty=body.get('compilePenalty',False)
    if not 0<=penalty<=120 or not isinstance(compile_penalty,bool):raise ServiceError(400,'罚时须为 0–120 分钟，编译错误罚时选项须有效')
    return {'rules':preset,'wrongPenalty':penalty,'compilePenalty':compile_penalty}


def event_info(name,rows):
    xcpc=any(is_xcpc(row) for row in rows)
    duration=None;source='时长待核对，使用可调整的训练默认值'
    from training import parse_time
    for row in rows:
        try:
            observed=int((parse_time(row['endedAt'])-parse_time(row['startedAt'])).total_seconds()/60)
            if 1<=observed<=1440:duration=observed;source='原站公开比赛时间';break
        except (KeyError,TypeError,ValueError,AttributeError):pass
    if duration is None:duration=300 if xcpc else 120
    expected=max([int(row.get('contestProblemCount') or 0) for row in rows] or [0])
    return {'name':name,'count':len(rows),'expectedCount':expected or None,'complete':len(rows)==expected if expected else None,
            'duration':duration,'durationSource':source,'rules':'xcpc' if xcpc else 'acm'}
