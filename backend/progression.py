"""Evidence rules shared by daily missions, achievements and ranking exports."""
from __future__ import annotations

import datetime as dt
import hashlib

SHANGHAI = dt.timezone(dt.timedelta(hours=8), name="Asia/Shanghai")

# Rewards are explicit and versioned; a claimed row retains its original reward.
TASKS = (
    {"id": "solve-1", "title": "今日首题", "description": "官方 AC 一道题目", "kind": "solve", "target": 1, "minDifficulty": 0, "xp": 25, "scope": "official", "version": 2},
    {"id": "solve-3", "title": "三题积累", "description": "官方 AC 三道不同的题目", "kind": "solve", "target": 3, "minDifficulty": 0, "xp": 60, "scope": "official", "version": 2},
    {"id": "independent-2", "title": "独立完成", "description": "独立官方 AC 两道题目；看题解后的 AC 不计入", "kind": "independent", "target": 2, "minDifficulty": 0, "xp": 70, "scope": "official", "version": 2},
    {"id": "hard-1500", "title": "进阶挑战", "description": "官方 AC 一道难度至少 1500 的题目", "kind": "solve", "target": 1, "minDifficulty": 1500, "xp": 80, "scope": "official", "version": 2},
    {"id": "hard-1800", "title": "攻坚挑战", "description": "官方 AC 一道难度至少 1800 的题目", "kind": "solve", "target": 1, "minDifficulty": 1800, "xp": 130, "scope": "official", "version": 2},
    {"id": "hard-2100", "title": "高难挑战", "description": "官方 AC 一道难度至少 2100 的题目", "kind": "solve", "target": 1, "minDifficulty": 2100, "xp": 200, "scope": "official", "version": 2},
)


def official_first_xp(difficulty):
    """官方首次 AC 经验：<1500→100；1500–1799→150；1800–2099→200；≥2100→300；未知→0（待定级补发）。"""
    if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool):
        return 0
    value = int(difficulty)
    if value < 1500:
        return 100
    if value < 1800:
        return 150
    if value < 2100:
        return 200
    return 300


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
    """One first reviewed acceptance per original problem, including removed training.

    2026-10-10 起这只服务旧 local-reviewed 排行榜口径的隔离读取；成长/任务用
    official_reward_evidence。
    """
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


def official_reward_evidence(rows, submissions, hub=None):
    """官方首次 AC 证据（成长/每日任务/成就唯一口径）。

    - 只收 mode=submit + verdict=AC + scope=official + finished_at。
    - hub.solved（公开同步历史）可计入官方 AC 与基础 XP，但缺真实接受时间的
      不给 day（不虚记当天任务）；independent 只信本机 solution_seen 字段，
      hub 来的独立完成情况未知，不默认独立。
    - 同一规范原题 URL 只取最早一次。
    """
    from insights import canonical_url
    metadata = {row["id"]: row for row in rows}
    result = {}
    records = sorted(submissions, key=lambda record: (record.get("submitted_at", ""), record.get("id", "")))
    for record in records:
        if record.get("mode") != "submit" or record.get("verdict") != "AC" or record.get("scope") != "official" or not record.get("finished_at"):
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
                       "day": local_date(timestamp).isoformat(), "difficulty": difficulty,
                       "independent": not bool(record.get("solution_seen")), "independentKnown": True,
                       "platform": row.get("platform"), "tags": row.get("tags", []), "source": "submission", "scope": "official"}
    if isinstance(hub, dict):
        for account in hub.get("accounts", []):
            for solved in account.get("solved", []):
                key = canonical_url(solved.get("url"))
                if not key:
                    continue
                stamp = parse_time(solved.get("acceptedAt"))
                previous = result.get(key)
                if previous and previous.get("source") == "submission":
                    continue  # 本机官方回执优先
                if previous and stamp and stamp >= previous["timestamp"]:
                    continue
                if not previous and not stamp:
                    # hub 无日期：仍记 AC 但 day=None（不计当天任务）
                    result[key] = {"key": key, "problemKey": hashlib.sha256(key.encode("utf-8")).hexdigest(), "problemId": None,
                                   "timestamp": None, "acceptedAt": None, "day": None, "difficulty": None,
                                   "independent": False, "independentKnown": False,
                                   "platform": account.get("platform"), "tags": [], "source": "hub", "scope": "official"}
                    continue
                if not stamp:
                    continue
                difficulty = None
                for row in rows:
                    if canonical_url(row.get("url")) == key:
                        difficulty = row.get("difficulty")
                        break
                if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool):
                    difficulty = None
                result[key] = {"key": key, "problemKey": hashlib.sha256(key.encode("utf-8")).hexdigest(), "problemId": None,
                               "timestamp": stamp, "acceptedAt": stamp.astimezone(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                               "day": local_date(stamp).isoformat(), "difficulty": difficulty,
                               "independent": False, "independentKnown": False,
                               "platform": account.get("platform"), "tags": [], "source": "hub", "scope": "official"}
    ordered = sorted((item for item in result.values() if item["timestamp"]), key=lambda item: (item["timestamp"], item["key"]))
    # 无日期的 hub 条目排最后（它们没有 day，不参与当日任务）
    undated = [item for item in result.values() if not item["timestamp"]]
    return ordered + undated


def task_progress(task, evidence, date):
    eligible = [item for item in evidence if item.get("day") == date
                and (not task.get("minDifficulty") or item.get("difficulty") is not None and item["difficulty"] >= task["minDifficulty"])
                and (task.get("kind") != "independent" or item.get("independent"))]
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
        add("difficulty-" + str(difficulty), name, f"官方首次 AC 一道难度至少 {difficulty} 的题目", [item["acceptedAt"] for item in evidence if item.get("difficulty") is not None and item["difficulty"] >= difficulty and item.get("acceptedAt")], 1)
    add("independent-5", "独立五题", "独立官方 AC 五道不同题目；看题解后的 AC 不计入", [item["acceptedAt"] for item in evidence if item.get("independent") and item.get("acceptedAt")], 5)
    add("independent-25", "独立积累", "独立官方 AC 二十五道不同题目", [item["acceptedAt"] for item in evidence if item.get("independent") and item.get("acceptedAt")], 25)
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
    platforms = {item["platform"] for item in evidence if item.get("platform")}
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
