"""Pure, bounded analytics from actual submission and exact public problem evidence."""
from __future__ import annotations

from collections import defaultdict
import datetime as dt
import hashlib
import re
import statistics
from urllib.parse import urlsplit, unquote
from progression import SHANGHAI, qualified_contests

FAILURES = {"WA", "TLE", "MLE", "RE", "CE", "OLE", "ERROR"}


def canonical_url(value):
    """Only identity-preserving first-party URL normalization; no title guessing."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    host = parsed.hostname or ""
    host = host.lower().removeprefix("www.")
    path = unquote(parsed.path).rstrip("/")
    if host in {"codeforces.com", "m1.codeforces.com", "m2.codeforces.com"}:
        match = re.fullmatch(r"/(?:contest/(\d+)/problem|problemset/problem/(\d+))/([A-Za-z0-9]+)", path)
        if match:
            return f"codeforces.com/contest/{match[1] or match[2]}/problem/{match[3].upper()}"
    if host == "atcoder.jp":
        match = re.fullmatch(r"/contests/([\w-]+)/tasks/([\w-]+)", path)
        if match:
            return "atcoder.jp" + path.lower()
    if host == "luogu.com.cn":
        match = re.fullmatch(r"/problem/([A-Za-z]+\d+)", path)
        if match:
            return "luogu.com.cn/problem/" + match[1].upper()
    if host == "ac.nowcoder.com":
        match = re.fullmatch(r"/acm/contest/(\d+)/([A-Za-z0-9]+)", path)
        if match:
            return f"ac.nowcoder.com/acm/contest/{match[1]}/{match[2].upper()}"
    # Unknown domains can dedupe their own exact paths, but do not match platform facts.
    return host + path if parsed.scheme in {"http", "https"} and host else None


def _date(value):
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(SHANGHAI).date()
    except (ValueError, TypeError, AttributeError):
        try:
            return dt.date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return None


def build_insights(rows, submissions, history, workspace, hub, now):
    library = {row["id"]: row for row in rows}
    by_url = {}
    aliases = {}
    for row in rows:
        key = canonical_url(row.get("url"))
        if key:
            existing = by_url.get(key)
            if existing is None or existing.get("source") == "remote" and row.get("source") != "remote":
                by_url[key] = row
    for row in rows:
        key = canonical_url(row.get("url"))
        aliases[row["id"]] = by_url[key]["id"] if key else row["id"]
    records = [record for record in submissions if record.get("mode") == "submit" and record.get("finished_at")]
    personal = set()
    samples = set()
    independent = {}
    first_accepted = {}
    per_day = defaultdict(lambda: {"submissions": 0, "accepted": set(), "officialAccepted": set()})
    grouped = defaultdict(list)
    xp = 0
    credited_codes = set()
    viewed_codes = set()
    reviews = defaultdict(int)
    review_cursor = {}
    for record in records:
        identity = aliases.get(record["problem_id"], record["problem_id"])
        grouped[identity].append(record)
        day = _date(record.get("submitted_at"))
        if day:
            per_day[day]["submissions"] += 1
        if record.get("verdict") == "SAMPLE_PASS":
            samples.add(identity)
        if record.get("verdict") != "AC" or record.get("scope") != "local":
            continue
        code_key = (identity, hashlib.sha256(record.get("code", "").encode()).hexdigest())
        if record.get("solution_seen"):
            viewed_codes.add(code_key)
        timestamp = dt.datetime.fromisoformat(record["submitted_at"].replace("Z", "+00:00"))
        if identity not in personal:
            xp += 100
            first_accepted[identity] = record.get("submitted_at")
            review_cursor[identity] = timestamp
            if day:
                per_day[day]["accepted"].add(identity)
        elif not record.get("solution_seen") and code_key not in viewed_codes and code_key not in credited_codes and (timestamp - review_cursor[identity]).total_seconds() >= 86400 and reviews[identity] < 5:
            xp += 20
            reviews[identity] += 1
            review_cursor[identity] = timestamp
        credited_codes.add(code_key)
        personal.add(identity)
        difficulty = library.get(identity, {}).get("difficulty")
        if not record.get("solution_seen") and code_key not in viewed_codes and isinstance(difficulty, (int, float)) and not isinstance(difficulty, bool):
            independent.setdefault(identity, (difficulty, record.get("submitted_at")))

    official = set()
    official_dates = {}
    platforms = []
    for account in hub.get("accounts", []):
        platforms.append({key: account.get(key) for key in ("platform", "rating", "maxRating", "status")})
        for solved in account.get("solved", []):
            row = by_url.get(canonical_url(solved.get("url")))
            if not row:
                continue
            identity = row["id"]
            official.add(identity)
            day = _date(solved.get("acceptedAt"))
            if day:
                previous = official_dates.get(identity)
                official_dates[identity] = min(day, previous) if previous else day
    for identity, day in official_dates.items():
        per_day[day]["officialAccepted"].add(identity)

    active = {aliases.get(row["id"], row["id"]): row for row in workspace.get("training", [])}
    reviewed = {aliases.get(row["id"], row["id"]) for row in history if row.get("review_count", 0)}
    completed_contests = qualified_contests(workspace.get("contests", []), records)
    # A contest reward requires a newly accepted original problem in that session.
    # Replaying a set, or handing in an empty set, cannot generate more experience.
    credited_contests = {record.get("contest_id") for record in records if record.get("verdict") == "AC" and record.get("scope") == "local"
                         and first_accepted.get(aliases.get(record["problem_id"], record["problem_id"])) == record.get("submitted_at")}
    xp += 10 * sum(contest["id"] in credited_contests for contest in completed_contests)
    level = xp // 500 + 1
    names = ["初次启程", "持续练习", "稳步积累", "独立攻坚", "长期精进"]
    growth = {"xp": xp, "totalXp": xp, "level": level, "levelName": names[min(level - 1, len(names) - 1)], "currentLevelXp": xp % 500, "nextLevelXp": 500, "nextMilestone": f"再积累 {500 - xp % 500} XP 升至 {level + 1} 级"}
    today = now.astimezone(SHANGHAI).date()
    days = {day for day, value in per_day.items() if value["submissions"]}
    day = today if today in days else today - dt.timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= dt.timedelta(days=1)
    longest = current = 0
    previous = None
    for day in sorted(days):
        current = current + 1 if previous and day == previous + dt.timedelta(days=1) else 1
        longest = max(longest, current)
        previous = day
    start = today - dt.timedelta(days=1095)
    activity = [{"date": day.isoformat(), "submissions": value["submissions"], "accepted": len(value["accepted"]), "officialAccepted": len(value["officialAccepted"])} for day, value in sorted(per_day.items()) if start <= day <= today]

    tag_ids = defaultdict(set)
    for identity, row in library.items():
        canonical = aliases.get(identity, identity)
        row = library.get(canonical, row)
        for tag in row.get("tags", []):
            tag_ids[tag].add(canonical)
    knowledge = []
    for name, ids in tag_ids.items():
        participated = ids & active.keys()
        local = ids & personal
        public = ids & official
        accepted = local | public
        attempts = sum(len(grouped[identity]) for identity in ids)
        failures = sum(record.get("verdict") in FAILURES for identity in ids for record in grouped[identity])
        due_ids = [identity for identity in participated if active[identity].get("queue")]
        evidence = len(accepted)
        confidence = "none" if not attempts and not public else "low" if evidence < 3 else "medium" if evidence < 10 else "high"
        mastery = round(100 * len(accepted) / len(ids)) if attempts or public else None
        priority = min(100, len(due_ids) * 20 + (20 if participated and not accepted else 0) + min(10, failures))
        suggestions = sorted(due_ids) + sorted(ids - personal - official - set(due_ids), key=lambda identity: (library.get(identity, {}).get("difficulty") is None, library.get(identity, {}).get("difficulty") or 99999, identity))
        reason = f"有 {len(due_ids)} 道待办" if due_ids else "已有尝试，可继续独立验证" if participated and not accepted else "继续扩大通过覆盖" if accepted else "还没有个人提交证据"
        knowledge.append({"name": name, "tags": [name], "available": len(ids), "participated": len(participated), "accepted": len(accepted), "officialAccepted": len(public), "localAccepted": len(local), "attempts": attempts, "failures": failures, "due": len(due_ids), "reviewed": len(ids & reviewed), "mastery": mastery, "confidence": confidence, "label": "通过覆盖率" if mastery is not None else "暂无证据", "priority": priority, "reason": reason, "suggestedIds": suggestions[:6]})
    knowledge.sort(key=lambda item: (-item["priority"], item["name"]))
    recommendations = [{"name": item["name"], "reason": item["reason"], "priority": item["priority"], "ids": item["suggestedIds"]} for item in knowledge if item["suggestedIds"]][:6]

    first_dates = sorted(value for value in first_accepted.values() if value)
    achievements = []
    for target, name in ((1, "首次本地通过"), (10, "十题积累"), (50, "五十题积累"), (100, "百题积累")):
        achievements.append({"id": f"local-{target}", "name": name, "description": f"通过 {target} 道不同题目的本地审核评测；样例通过不计入", "unlocked": len(personal) >= target, "unlockedAt": first_dates[target - 1] if len(first_dates) >= target else None, "progress": min(target, len(personal)), "target": target})
    achievements.append({"id": "contest-1", "name": "完成模拟赛", "description": "完成一场至少训练一分钟并实际提交的计时模拟赛", "unlocked": bool(completed_contests), "unlockedAt": min((item.get("finishedAt") for item in completed_contests if item.get("finishedAt")), default=None), "progress": min(1, len(completed_contests)), "target": 1})
    evidence_count = len(independent)
    enough = evidence_count >= 5
    rating = int(round(statistics.median(value[0] for value in independent.values()) / 50) * 50) if enough else None
    trend = []
    seen_values = []
    for difficulty, timestamp in sorted(independent.values(), key=lambda value: value[1] or ""):
        seen_values.append(difficulty)
        day = _date(timestamp)
        if len(seen_values) >= 5 and day:
            point = {"date": day.isoformat(), "value": int(round(statistics.median(seen_values) / 50) * 50)}
            if trend and trend[-1]["date"] == point["date"]:
                trend[-1] = point
            else:
                trend.append(point)
    assessment = {"rating": rating, "band": "insufficient" if not enough else "low" if evidence_count < 10 else "medium" if evidence_count < 30 else "high", "label": "训练难度估算" if enough else "独立通过证据不足", "confidence": "none" if not enough else "low" if evidence_count < 10 else "medium" if evidence_count < 30 else "high", "evidenceCount": evidence_count, "explanation": "取至少五道独立通过本地审核题目的难度中位数，仅描述已验证训练范围，不是官方等级分；查看题解后提交、运行和样例通过不计入。", "platforms": platforms, "trend": trend[-365:]}
    recommendations, level, basis = recommend_problems(library, active, independent, personal, official, hub)
    assessment.update(recommendationLevel=level, recommendationBasis=basis)
    summary = {"active": len(active), "accepted": sum(bool(row.get("accepted")) for row in active.values()), "submissions": len(records), "activeDays": len(days), "streak": streak, "longestStreak": longest, "completedContests": len(completed_contests), "officialSolved": len(official), "localAccepted": len(personal), "samplePassed": len(samples - personal)}
    return {"summary": summary, "growth": growth, "activity": activity, "knowledge": knowledge, "recommendations": recommendations, "achievements": achievements, "assessment": assessment}


def recommend_problems(library, active, independent, personal, official, hub):
    """Practice targets are conservative training bands, never fabricated ratings."""
    values = [value[0] for value in independent.values()]
    cf = [account.get('rating') for account in hub.get('accounts', []) if account.get('platform') == 'codeforces' and account.get('status') == 'ready' and isinstance(account.get('rating'), (int, float)) and not isinstance(account.get('rating'), bool)]
    public = [library[identity]['difficulty'] for identity in official if identity in library and isinstance(library[identity].get('difficulty'), (int, float))]
    if len(values) >= 3:
        level = round(statistics.median(values) / 50) * 50
        basis = f'根据 {len(values)} 道独立本地通过题的难度选择邻近训练带；这不是官方等级分'
    elif cf:
        level = round((cf[0] - 100) / 50) * 50
        basis = '使用已绑定 Codeforces 官方等级分保守选择训练带；其它平台分数不混算'
    elif len(public) >= 5:
        level = round(statistics.median(public) / 50) * 50
        basis = '根据原站通过与题库精确匹配的题目难度选择训练带，独立完成情况未知'
    else:
        level = 1100
        basis = '独立证据不足，先从 1000–1250 的基础题起步；这是起步建议，不是能力测量'
    level = int(min(2100, max(1000, level)))
    lower, upper = max(1000, level - 150), min(2199, level + (150 if len(values) >= 5 else 100))
    if not values and not cf and len(public) < 5:
        lower, upper = 1000, 1250
    known = personal | official
    foundation = {'模拟', '枚举', '排序', '前缀和', '差分', '贪心', '双指针', '二分查找', '数组', '字符串'}
    graph = {'图论', 'BFS', 'DFS', '并查集', '树', '最短路'}
    basics = {identity for identity in known if foundation & set(library.get(identity, {}).get('tags', []))}
    graphs = {identity for identity in known if graph & set(library.get(identity, {}).get('tags', []))}
    def tier(row):
        text = ' '.join(row.get('tags', []))
        if any(word in text for word in ('Hall', '霍尔', '网络流', '最大流', '最小割', '二分图匹配', 'DFS序', 'DFS 序', '树链剖分', '后缀自动机', '线段树', '树状数组', '数位 DP', '状压 DP')):
            return 3
        if any(word in text for word in ('DP', '动态规划', '图论', 'BFS', 'DFS', '最短路', '并查集', '树')):
            return 2
        return 1
    ranked = []
    for identity, row in library.items():
        difficulty = row.get('difficulty')
        if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool) or not lower <= difficulty <= upper:
            continue
        due = active.get(identity, {}).get('queue')
        if identity in known and not due:
            continue
        order = tier(row)
        if order == 2 and len(basics) < 2 or order == 3 and (len(basics) < 5 or len(graphs) < 2 or level < 1700):
            continue
        score = (0 if due else 1, abs(difficulty - level), order, 0 if row.get('source') != 'remote' else 1, identity)
        ranked.append((score, row, due, order))
    ranked.sort(key=lambda item: item[0])
    result, seen_urls, seen_ids, main_tags = [], set(), set(), set()
    for _, row, due, order in ranked:
        identity = row['id']; key = canonical_url(row.get('url'))
        if identity in seen_ids or key and key in seen_urls:
            continue
        tag = (row.get('tags') or ['基础练习'])[0]
        # After the first pass, allow repeated topics when no varied candidate exists.
        if tag in main_tags and len(result) >= 3:
            continue
        seen_ids.add(identity); main_tags.add(tag)
        if key:seen_urls.add(key)
        stage = 'retry' if due else 'foundation' if order == 1 and len(basics) < 2 else 'stretch' if row['difficulty'] > level else 'consolidate'
        reason = f'优先完成当前待办，难度 {row["difficulty"]} 在适合的训练带内' if due else f'难度 {row["difficulty"]} 接近当前建议 {level}；先练基础技巧' if stage == 'foundation' else f'已有基础证据，选择邻近难度 {row["difficulty"]}，逐步提高' if stage == 'stretch' else f'难度 {row["difficulty"]} 接近当前训练带，可巩固 {tag}'
        result.append({'name':tag,'reason':reason,'priority':100-len(result)*5,'ids':[identity],
          'problem':{name:row.get(name) for name in ('id','title','difficulty','platform','contest','tags')},
          'stage':stage,'band':{'min':lower,'max':upper,'target':level}})
        if len(result) >= 6:break
    return result, level, basis
