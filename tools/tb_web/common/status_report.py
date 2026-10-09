# -*- coding: utf-8 -*-
r"""
status_report —— 题目状态报告
=============================

    python status_report.py [--all] [--days N] [--file 路径] [--today 日期]

    python status_report.py --todo --knowledge DP                    # 筛选模式：还没做出来的 DP 题
    python status_report.py --status 未做,不会 --difficulty 1200-1600
    python status_report.py --knowledge 树形DP,换根             # 知识点可多词（逗号分隔）

读题目状态表（一题一行），按状态与日期输出五段：

  1. 待重写（最高优先）  —— 状态 = 待重写
  2. 待补题              —— 状态 = 不会
  3. D+7 复习队列        —— 状态 = 独立AC / 复现AC，且日期距今 >= N 天（N 默认 7）
  4. D+30 抽检           —— 状态 = 巩固，且日期距今 >= 30 天
  5. 统计                —— 各状态计数 + 最近 7 天变更为 独立AC / 复现AC / 巩固 的题数

「未做」默认不进 1~4 段（避免几十道旧题刷屏），只进统计；
加 `--all` 追加一段「全部题目」完整清单（含 未做）。

2026-10-03（用户口径）：状态从 8 个减到 6 个 —— 去掉「卡住 / 只读过」，
「卡住」的意思并入「不会」，「只读过」不再单列。

日期列 = 最后一次状态变更日（YYYY-MM-DD）；只有第 3 / 4 段需要它，
缺日期或日期填错的行进不了队列，会在末尾「提示」里点名。

场次列排序按「比赛名 + 场次号」两段键（多平台混排不撞号）；场次认不出的行
排到最后，并在末尾打一行 `★`（绝不按裸号处理）。纯标准库，无外部依赖。

筛选模式（2026-10-03 批次 C）：给了 --knowledge / --status / --todo / --difficulty
任意一个，就不打五段报告，只列命中清单（头部 + 条件 + 行）。三个条件之间是 AND：

  · --knowledge 词表：**任一**词在「知识点」列里出现即命中（子串、忽略空白与大小写，
    `区间dp` ≡ `区间 DP`；一个词里的空格保留，`--knowledge 区间 DP` 也对）。多个词用逗号
    分隔、取**并集**（跟状态多选 / 难度多值同一口径）——同一意思的几种写法一条命令查全：
    `--knowledge DP,动态规划`。不查词典、不做同义扩展（`DP` 只匹配真写了「DP」的行）。
  · --status 状态：∈ 集合（多值取并集）；--todo = 「还没做出来」的糖 =
    未做 / 不会 / 待重写 三个状态。
  · --difficulty：按难度列的数值，写 `1500`（等于）/ `1200-1600`（闭区间，
    写反了自动摆正）/ `<=1400` / `>=1800`；多值取并集（任一命中）。带 `>` 的写法
    在 cmd 里要加引号（`>` 是重定向）。有难度条件时「没有数字的行」算不命中；
    写法认不出的那一条**匹配不到任何题**，并在报告末尾打 `★`（不当「没写」）。

筛选结果按「比赛名 → 场次号 → 题号」排序；退出码 0 = 命令跑通（0 条命中也是 0）。
**status_gui.py 的筛选区 import 的就是本文件这一份实现**——两端同条件必然同一份结果，
GUI 不另写一套匹配规则（`tools/selfcheck_filter.py` 就是钉这件事的闸门）。
"""

import argparse
import datetime
import io
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402  （场次键的唯一解析实现）

DEFAULT_FILE = os.path.join(toolutil.DATA_ROOT, "题解", "TB.md")

HEADER = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]
STATES = ["未做", "不会", "待重写", "复现AC", "独立AC", "巩固"]

TODO_HARD = "待重写"                      # 第 1 段
TODO_FILL = ("不会",)                     # 第 2 段（v10：卡住并入不会）
REVIEW = ("独立AC", "复现AC")             # 第 3 段（D+N 重做）
KEEP = "巩固"                             # 第 4 段（D+30 抽检）
RECENT = ("独立AC", "复现AC", "巩固")     # 第 5 段「最近 7 天变更」
KEEP_DAYS = 30
RECENT_DAYS = 7
TODO_STATES = ("未做", "不会", "待重写")  # 筛选：--todo =「还没做出来」（批次 C）
DIFF_NEVER = (1, 0)                       # 筛选：认不出的难度写法 = 空区间（永不命中）


# ---------------------------------------------------------------- 小工具
def disp_width(s):
    """显示宽度：东亚宽 / 全角字符按 2 格算（终端对齐用）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, w):
    return s + " " * max(0, w - disp_width(s))


def split_cells(line):
    """切表格行；尊重转义的 \\| ，不当分隔符。不是表格行返回 None。"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s.strip("|")
    parts, buf, i = [], "", 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if s[i] == "|":
            parts.append(buf.strip())
            buf = ""
            i += 1
            continue
        buf += s[i]
        i += 1
    parts.append(buf.strip())
    return parts


# ---------------------------------------------------------------- 解析
def parse_table(path):
    """读状态表主表，返回 [dict(场次/题号/题名/知识点/难度/状态/日期, _i=行序)]。"""
    text = io.open(path, encoding="utf-8").read()
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if split_cells(ln) == HEADER:
            start = i
            break
    if start is None:
        raise SystemExit("★ 没找到表头「| %s |」：%s" % (" | ".join(HEADER), path))

    rows = []
    for ln in lines[start + 2:]:          # +2：表头下面紧跟一行分隔线
        c = split_cells(ln)
        if not c:
            break                          # 主表结束（后面是别的段落）
        if len(c) != len(HEADER):
            break
        if set("".join(c)) <= set("-: "):
            continue
        r = dict(zip(HEADER, c))
        r["_i"] = len(rows)
        rows.append(r)
    return rows


def sort_key(r):
    """先按比赛名、再按场次号；认不出的排最后（`_contest` 由 build() 预解析）。"""
    name, n = r["_contest"]
    if name is None:
        return (1, "", 0, r["题号"], r["_i"])
    return (0, name, n, r["题号"], r["_i"])


def parse_date(s):
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


# ---------------------------------------------------------------- 筛选（批次 C）
# 「列出所有没做的 DP 题」这类查询的唯一实现：status_gui.py 的筛选区也调这里，
# 两端同条件 = 同一份结果（GUI 不许另写一套匹配规则）。
def prep_contests(rows):
    """给每行挂 `_contest`（排序键要用），返回认不出场次的行对应的 `★` 文案。"""
    stars = []
    for r in rows:
        r["_contest"] = toolutil.parse_contest(r["场次"])
        if r["_contest"][0] is None:
            stars.append("★ 场次认不出（没按裸号处理、已排在最后）：第 %d 行「%s」%s"
                         % (r["_i"] + 1, r["场次"], r["题号"]))
    return stars


def tag_key(s):
    """筛选比对键：去掉全部空白 + 转小写（`区间 dp` ≡ `区间DP` ≡ `区间 dp`）。"""
    return re.sub(r"\s+", "", s or "").lower()


def split_terms(x):
    """一个参数值 → 词表：半角 / 全角逗号都算分隔；词里的空格保留（`区间 DP` 是一个词）。"""
    return [t.strip() for t in re.split(r"[,，]", x or "") if t.strip()]


def match_knowledge(cell, terms):
    """知识点列匹配：任一词在格子里出现即命中（子串、忽略空白大小写）；空词表 = 不筛。

    多词 = **并集**（跟「状态多选」「难度多值」一个口径，都是「选中的里任一个中即可」）——
    于是同一个意思的几种写法一条命令查全：`--knowledge DP,动态规划`。
    """
    if not terms:
        return True
    hay = tag_key(cell)
    return any(tag_key(t) in hay for t in terms)


def difficulty_num(cell):
    """难度列 → 数值（第一串数字）；没有数字（空 / 不是数字）→ None。"""
    m = re.search(r"\d+", cell or "")
    return int(m.group()) if m else None


def parse_difficulty(spec):
    """难度写法 → (lo, hi) 闭区间（None = 那一头不限）；认不出 → None。

    认这几种（空白随便写，`1200 - 1600` 行）：`1500` / `1200-1600`（写反自动摆正）/
    `<=1400` `≤1400` `<1400` / `>=1800` `≥1800` `>1800`。
    """
    t = re.sub(r"\s+", "", spec or "")
    m = re.fullmatch(r"(<=|≤|<|>=|≥|>)?(\d+)(?:-(\d+))?", t)
    if not m:
        return None
    op, a, b = m.group(1), int(m.group(2)), m.group(3)
    if b is not None:
        x, y = a, int(b)
        return (x, y) if x <= y else (y, x)
    if op in ("<=", "≤"):
        return (None, a)
    if op == "<":
        return (None, a - 1)
    if op in (">=", "≥"):
        return (a, None)
    if op == ">":
        return (a + 1, None)
    return (a, a)


def difficulty_specs(items):
    """词表 → (specs, bad)：bad = 认不出的原文（它按“空区间”参与——永不命中，不当没写）。"""
    specs, bad = [], []
    for x in items:
        s = parse_difficulty(x)
        if s is None:
            bad.append(x)
            specs.append(DIFF_NEVER)
        else:
            specs.append(s)
    return specs, bad


def match_difficulty(cell, specs):
    """难度列匹配：任一 spec 命中即可；有 spec 时「没有数字的行」算不命中。"""
    if not specs:
        return True
    n = difficulty_num(cell)
    if n is None:
        return False
    return any((lo is None or n >= lo) and (hi is None or n <= hi) for lo, hi in specs)


def filter_rows(rows, knowledge=(), statuses=(), difficulty=()):
    """多条件筛选（三条件 AND）：知识点（任一词中）/ 状态（∈）/ 难度（任一区间中）。

    空 = 那一项不筛。命令行的 `--todo` 只是把 statuses 填成 TODO_STATES 的糖。
    `rows` 里有 `_i` 就用它当稳定序（命令行 `build()` 之外调用时可能没有 `_contest`）。
    """
    return [r for r in rows
            if match_knowledge(r["知识点"], knowledge)
            and (not statuses or r["状态"] in statuses)
            and match_difficulty(r["难度"], difficulty)]


def build_filter(rows, today, path, knowledge=(), statuses=(), diff_raw=(), difficulty=()):
    """筛选模式的报告：头部三行 + 命中清单（0 条也明说）+ 写法不认的 `★` 提示。"""
    stars = prep_contests(rows)
    hits = sorted(filter_rows(rows, knowledge, statuses, difficulty), key=sort_key)
    cols = ["场次", "题号", "题名", "难度", "状态"]
    widths = [max([disp_width(h)] + [disp_width(r[h]) for r in hits]) for h in cols]

    cond = []
    if statuses:
        cond.append("状态 ∈ {%s}" % "、".join(statuses))
    if knowledge:
        cond.append("知识点 ∈ {%s}" % "、".join(knowledge))
    if diff_raw:
        cond.append("难度 ∈ %s" % "、".join(diff_raw))

    out = ["题目筛选  %s" % today.isoformat(),
           "表：%s（共 %d 题）" % (path, len(rows)),
           "条件：" + (" ｜ ".join(cond) if cond else "（无）"),
           "筛出 %d 题：" % len(hits)]
    if not hits:
        out.append("    （没有命中的题）")
    for r in hits:
        s = "    " + "  ".join(pad(r[h], widths[k]) for k, h in enumerate(cols))
        if r["知识点"]:
            s += "  " + r["知识点"]
        out.append(s.rstrip())

    for s in statuses:
        if s not in STATES:
            stars.append("★ 状态「%s」不在 %d 个状态里（这一条匹配不到任何题）：%s"
                         % (s, len(STATES), " / ".join(STATES)))
    for t in diff_raw:
        if parse_difficulty(t) is None:
            stars.append("★ 难度写法不认：「%s」（支持 1500 / 1200-1600 / <=1400 / >=1800；"
                         "这一条匹配不到任何题）" % t)
    if stars:
        out.append("")
        out.extend(stars)
    return out


# ---------------------------------------------------------------- 主逻辑
def build(rows, today, days, all_show, path):
    warns = []
    stars = prep_contests(rows)          # 场次键 + 「认不出」的 ★（与筛选模式同一份实现）
    for r in rows:
        if r["状态"] not in STATES:
            warns.append("状态「%s」不在 %d 个状态里：第 %d 行 %s %s"
                         % (r["状态"], len(STATES), r["_i"] + 1, r["场次"], r["题号"]))
        r["_date"] = parse_date(r["日期"]) if r["日期"] else None
        if r["日期"] and r["_date"] is None:
            warns.append("日期「%s」不是 YYYY-MM-DD：%s %s" % (r["日期"], r["场次"], r["题号"]))
        r["_ago"] = (today - r["_date"]).days if r["_date"] else None
        if r["_ago"] is not None and r["_ago"] < 0:
            warns.append("日期在未来（%s）：%s %s" % (r["日期"], r["场次"], r["题号"]))

    sec1 = sorted([r for r in rows if r["状态"] == TODO_HARD], key=sort_key)
    sec2 = sorted([r for r in rows if r["状态"] in TODO_FILL], key=sort_key)
    sec3 = sorted([r for r in rows if r["状态"] in REVIEW
                   and r["_ago"] is not None and r["_ago"] >= days],
                  key=lambda r: -r["_ago"])
    sec4 = sorted([r for r in rows if r["状态"] == KEEP
                   and r["_ago"] is not None and r["_ago"] >= KEEP_DAYS],
                  key=lambda r: -r["_ago"])

    for st in REVIEW + (KEEP,):
        for r in rows:
            if r["状态"] == st and r["_ago"] is None:
                warns.append("「%s」缺日期、进不了复习队列：%s %s" % (st, r["场次"], r["题号"]))

    counts = {s: sum(1 for r in rows if r["状态"] == s) for s in STATES}
    recent = sum(1 for r in rows if r["状态"] in RECENT
                 and r["_ago"] is not None and 0 <= r["_ago"] < RECENT_DAYS)

    cols = ["场次", "题号", "题名", "难度"]        # 定宽那几列；知识点挂行尾（可能较长）
    widths = [max([disp_width(h)] + [disp_width(r[h]) for r in rows]) for h in cols]

    def line(r, with_days=False):
        s = "    " + "  ".join(pad(r[h], widths[k]) for k, h in enumerate(cols))
        if with_days:
            s += "  " + pad(r["日期"], 10) + "  距今 %d 天" % r["_ago"]
        if r["知识点"]:
            s += "  " + r["知识点"]
        return s.rstrip()

    out = []
    out.append("题目状态报告  %s" % today.isoformat())
    out.append("表：%s（共 %d 题）｜ ③ 阈值 %d 天 ｜ ④ 阈值 %d 天" % (path, len(rows), days, KEEP_DAYS))
    out.append("")

    def section(title, items, with_days=False):
        out.append("%s：%d 题" % (title, len(items)))
        if not items:
            out.append("    （无）")
        for r in items:
            out.append(line(r, with_days))
        out.append("")

    section("① 待重写（最高优先，次日先做）", sec1)
    section("② 待补题（不会）", sec2)
    section("③ D+%d 复习队列（独立AC / 复现AC，距今 ≥ %d 天）" % (days, days), sec3, True)
    section("④ D+%d 抽检（巩固，距今 ≥ %d 天）" % (KEEP_DAYS, KEEP_DAYS), sec4, True)

    if all_show:
        section("★ 全部题目（含 未做）", sorted(rows, key=sort_key))

    out.append("⑤ 统计")
    out.append("    各状态：" + " ｜ ".join("%s %d" % (s, counts[s]) for s in STATES))
    out.append("    最近 %d 天变更为 %s 的：%d 题"
               % (RECENT_DAYS, " / ".join(RECENT), recent))
    out.append("")

    if warns:
        out.append("提示（%d 条，不影响上面的队列）：" % len(warns))
        for w in warns:
            out.append("    - " + w)
        out.append("")

    for s in stars:                      # 认不出场次的行：★ 报警（排最后、不按裸号处理）
        out.append(s)

    return out


def main(argv):
    ap = argparse.ArgumentParser(
        description="题目状态报告：读状态表，输出待重写 / 待补题 / D+7 复习 / D+30 抽检 / 统计；"
                    "给 --knowledge / --status / --todo / --difficulty 任意一个则改为筛选清单。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true",
                    help="追加「全部题目」清单（含 未做，默认被过滤掉）")
    ap.add_argument("--days", type=int, default=7, metavar="N",
                    help="③ 复习队列的间隔天数（默认 7）；④ 固定 30 天不随它变")
    ap.add_argument("--file", default=DEFAULT_FILE, help="状态表路径（默认 %s）" % DEFAULT_FILE)
    ap.add_argument("--today", metavar="YYYY-MM-DD", help="调试用：把「今天」当成这天")
    ap.add_argument("--knowledge", action="append", default=[], metavar="词",
                    help="筛「知识点」：任一出现即命中（子串、忽略空白大小写）；"
                         "逗号分隔多写取并集（--knowledge DP,动态规划）")
    ap.add_argument("--status", action="append", default=[], metavar="状态",
                    help="筛「状态」∈：%s；逗号分隔可多写（取并集）" % " / ".join(STATES))
    ap.add_argument("--todo", action="store_true",
                    help="= --status %s（还没做出来的）" % ",".join(TODO_STATES))
    ap.add_argument("--difficulty", action="append", default=[], metavar="难度",
                    help="筛「难度」（纯数字）：1500 / 1200-1600 / <=1400 / >=1800；"
                         "逗号分隔可多写（取并集）；带 > 的写法在 cmd 里要加引号")
    args = ap.parse_args(argv)

    if args.days < 0:
        ap.error("--days 不能是负数")
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()

    knowledge = [t for x in args.knowledge for t in split_terms(x)]
    statuses = [t for x in args.status for t in split_terms(x)]
    if args.todo:
        statuses += [s for s in TODO_STATES if s not in statuses]
    diff_raw = [t for x in args.difficulty for t in split_terms(x)]
    specs, _bad = difficulty_specs(diff_raw)

    try:
        rows = parse_table(args.file)
    except FileNotFoundError:
        print("★ 找不到状态表：%s" % args.file)
        return 2

    if knowledge or statuses or diff_raw:          # 筛选模式：不打五段报告
        for ln in build_filter(rows, today, args.file, knowledge, statuses, diff_raw, specs):
            print(ln)
        return 0

    for ln in build(rows, today, args.days, args.all, args.file):
        print(ln)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
