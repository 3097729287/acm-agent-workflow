"""Evidence rules shared by daily missions, achievements and ranking exports."""
from __future__ import annotations

import datetime as dt
import hashlib

SHANGHAI = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")

# Rewards are explicit and versioned; a claimed row retains its original reward.
TASKS = (
    {"id": "solve-1", "title": "今日首题", "description": "首次通过一道本地审核题目", "kind": "solve", "target": 1, "minDifficulty": 0, "xp": 25},
    {"id": "solve-3", "title": "三题积累", "description": "首次通过三道不同的本地审核题目", "kind": "solve", "target": 3, "minDifficulty": 0, "xp": 60},
    {"id": "independent-2", "title": "独立完成", "description": "独立首次通过两道题目；看题解后的通过不计入", "kind": "independent", "target": 2, "minDifficulty": 0, "xp": 70},
    {"id": "hard-1500", "title": "进阶挑战", "description": "首次通过一道难度至少 1500 的本地审核题目", "kind": "solve", "target": 1, "minDifficulty": 1500, "xp": 80},
    {"id": "hard-1800", "title": "攻坚挑战", "description": "首次通过一道难度至少 1800 的本地审核题目", "kind": "solve", "target": 1, "minDifficulty": 1800, "xp": 130},
    {"id": "hard-2100", "title": "高难挑战", "description": "首次通过一道难度至少 2100 的本地审核题目", "kind": "solve", "target": 1, "minDifficulty": 2100, "xp": 200},
)


def parse_time(value):
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=dt.timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return None


def local_date(value):
    timestamp = parse_time(value) if isinstance(value, str) else value
    return timestamp.astimezone(SHANGHAI).date() if timestamp else None


def accepted_evidence(rows, submissions):
    """One first reviewed acceptance per original problem, including removed training."""
    from insights import canonical_url
    metadata = {row["id"]: row for row in rows}
    result = {}
    records = sorted(submissions, key=lambda record: (record.get("submitted_at", ""), record.get("id", "")))
    for record in records:
        if record.get("mode") != "submit" or record.get("verdict") != "AC" or record.get("scope") != "local" or not record.get("finished_at"):
            continue
        timestamp = parse_time(record.get("submitted_at"))
        if not timestamp:
            continue
        row = metadata.get(record["problem_id"], {})
        key = canonical_url(row.get("url")) or record["problem_id"]
        previous = result.get(key)
        if previous and timestamp >= previous["timestamp"]:
            continue
        difficulty = row.get("difficulty")
        if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool):
            difficulty = None
        result[key] = {"key": key, "problemKey": hashlib.sha256(key.encode("utf-8")).hexdigest(), "problemId": record["problem_id"],
                       "timestamp": timestamp, "acceptedAt": timestamp.astimezone(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                       "day": local_date(timestamp).isoformat(), "difficulty": difficulty, "independent": not bool(record.get("solution_seen")),
                       "platform": row.get("platform"), "tags": row.get("tags", [])}
    return sorted(result.values(), key=lambda item: (item["timestamp"], item["key"]))


def task_progress(task, evidence, date):
    eligible = [item for item in evidence if item["day"] == date
                and (not task["minDifficulty"] or item["difficulty"] is not None and item["difficulty"] >= task["minDifficulty"])
                and (task["kind"] != "independent" or item["independent"])]
    return min(task["target"], len(eligible)), [item["problemKey"] for item in eligible]


def qualified_contests(contests, submissions):
    """An empty immediate hand-in is an aborted attempt, not an earned achievement."""
    meaningful = {record.get("contest_id") for record in submissions if record.get("mode") == "submit" and record.get("finished_at")
                  and record.get("verdict") in {"AC", "SAMPLE_PASS", "WA", "TLE", "MLE", "RE", "OLE"}}
    result = []
    for contest in contests:
        start, finish = parse_time(contest.get("startedAt")), parse_time(contest.get("finishedAt"))
        if contest.get("status") == "finished" and contest["id"] in meaningful and start and finish and (finish - start).total_seconds() >= 60:
            result.append(contest)
    return result


def extra_achievements(evidence, records, completed, longest_streak, claimed_dates=()):
    result = []
    def add(identity, name, description, values, target):
        values = sorted(value for value in values if value)
        result.append({"id": identity, "name": name, "description": description, "unlocked": len(values) >= target,
                       "unlockedAt": values[target - 1] if len(values) >= target else None, "progress": min(target, len(values)), "target": target})
    for difficulty, name in ((1500, "进阶第一步"), (1800, "攻坚突破"), (2100, "高难突破")):
        add("difficulty-" + str(difficulty), name, f"首次通过难度至少 {difficulty} 的一道本地审核题目", [item["acceptedAt"] for item in evidence if item["difficulty"] is not None and item["difficulty"] >= difficulty], 1)
    add("independent-5", "独立五题", "独立通过五道不同题目；题解后通过不计入", [item["acceptedAt"] for item in evidence if item["independent"]], 5)
    add("independent-25", "独立积累", "独立通过二十五道不同题目", [item["acceptedAt"] for item in evidence if item["independent"]], 25)
    add("contest-5", "模拟赛常客", "完成五场至少训练一分钟并实际提交的模拟赛", [item.get("finishedAt") for item in completed], 5)
    training_days = {}
    for record in records:
        day = local_date(record.get("submitted_at"))
        if record.get("mode") == "submit" and day:
            training_days.setdefault(day, record.get("submitted_at"))
    for target in (3, 7, 30):
        previous, current, unlocked_at = None, 0, None
        for day in sorted(training_days):
            current = current + 1 if previous and day == previous + dt.timedelta(days=1) else 1
            if current >= target and unlocked_at is None:
                unlocked_at = training_days[day]
            previous = day
        result.append({"id": "streak-" + str(target), "name": f"连续训练 {target} 天", "description": "以正式提交记录计算连续训练日期", "unlocked": longest_streak >= target,
                       "unlockedAt": unlocked_at, "progress": min(target, longest_streak), "target": target})
    platforms = {item["platform"] for item in evidence if item["platform"]}
    encountered, platform_at = set(), None
    for item in evidence:
        if item["platform"]:
            encountered.add(item["platform"])
            if len(encountered) >= 2:
                platform_at = item["acceptedAt"]
                break
    result.append({"id": "platforms-2", "name": "跨平台练习", "description": "通过来自两个平台的本地审核题目", "unlocked": len(platforms) >= 2, "unlockedAt": platform_at, "progress": min(2, len(platforms)), "target": 2})
    for target, name in ((1, "领取每日奖励"), (10, "任务积累"), (50, "日积月累")):
        add("missions-" + str(target), name, f"完成并领取 {target} 项每日任务奖励", claimed_dates, target)
    return result
