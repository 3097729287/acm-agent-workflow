# -*- coding: utf-8 -*-
r"""
status_report —— 题目状态报告
=============================

    python status_report.py [--all] [--days N] [--file 路径] [--today 日期]

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
"""

import argparse
import datetime
import io
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402  （场次键的唯一解析实现）

DEFAULT_FILE = os.path.join(toolutil.DATA_ROOT, "题解", "题目状态.md")

HEADER = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]
STATES = ["未做", "不会", "待重写", "复现AC", "独立AC", "巩固"]

TODO_HARD = "待重写"                      # 第 1 段
TODO_FILL = ("不会",)                     # 第 2 段（v10：卡住并入不会）
REVIEW = ("独立AC", "复现AC")             # 第 3 段（D+N 重做）
KEEP = "巩固"                             # 第 4 段（D+30 抽检）
RECENT = ("独立AC", "复现AC", "巩固")     # 第 5 段「最近 7 天变更」
KEEP_DAYS = 30
RECENT_DAYS = 7


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


# ---------------------------------------------------------------- 主逻辑
def build(rows, today, days, all_show, path):
    warns, stars = [], []
    for r in rows:
        r["_contest"] = toolutil.parse_contest(r["场次"])
        if r["_contest"][0] is None:
            stars.append("★ 场次认不出（没按裸号处理、已排在最后）：第 %d 行「%s」%s"
                         % (r["_i"] + 1, r["场次"], r["题号"]))
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
        description="题目状态报告：读状态表，输出待重写 / 待补题 / D+7 复习 / D+30 抽检 / 统计。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true",
                    help="追加「全部题目」清单（含 未做，默认被过滤掉）")
    ap.add_argument("--days", type=int, default=7, metavar="N",
                    help="③ 复习队列的间隔天数（默认 7）；④ 固定 30 天不随它变")
    ap.add_argument("--file", default=DEFAULT_FILE, help="状态表路径（默认 %s）" % DEFAULT_FILE)
    ap.add_argument("--today", metavar="YYYY-MM-DD", help="调试用：把「今天」当成这天")
    args = ap.parse_args(argv)

    if args.days < 0:
        ap.error("--days 不能是负数")
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()

    try:
        rows = parse_table(args.file)
    except FileNotFoundError:
        print("★ 找不到状态表：%s" % args.file)
        return 2

    for ln in build(rows, today, args.days, args.all, args.file):
        print(ln)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
