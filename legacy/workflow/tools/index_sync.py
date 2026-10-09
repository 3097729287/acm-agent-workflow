# -*- coding: utf-8 -*-
r"""
index_sync —— 索引两表自动生成器
================================

    python index_sync.py [dry|apply] [--root <数据根>] [--mem <知识库目录>]

从**算法库记录 md 的头部字段**（单一事实来源）机械生成两张表：

  1. `<root>\索引\题解算法索引.md` 的场次小节 —— 每场一张 5 列表（题号 / 题名 / 难度 /
     算法 / 归档位置），全部字段来自记录 md；场次按 Round 升序、场内按题号字母升序。
     **反查表 / 说明 / 不带题目的资料三个小节不动**（反查表里每题链接与「（指针）」标记
     由 `archive_check.py` 兜底对账，不在这里生成）。
  2. `06-题解算法归档.md` 第五节的精简索引表 + 其中「共 N 条」与「（Round … 已全部回填）」。
     已有行**保持既有顺序**，新题追加到表尾；日期沿用旧表里该题的日期，
     新题读不到日期时用记录 md 的修改时间并打印提醒。顺手同步索引头部的「当前条数」。
     旧表行用 `toolutil.parse_contest` 认场次：非牛客的行跳过并打一行说明
     （本脚本只服务牛客周赛、路径写死，不泛化）；认不出的行打一行 ★。

记录 md 里没有的字段（场次号 / 题号 / 题名）从文件名解析：`牛客周赛Round155-D-小月的电台.md`。

**dry = 只打印 diff 不写盘（默认）；apply = 先按备份规则存进备份仓再写。**
幂等：连跑两遍，第二遍应 0 处 diff。
"""

import argparse
import datetime
import difflib
import glob
import os
import re
import sys

import toolutil               # 同目录：备份的唯一实现

BS = chr(92)                  # 反斜杠
CONT = "牛客周赛"
MEM_DEFAULT = os.path.join(toolutil.REPO_ROOT, "knowledge")


def rd(p):
    return open(p, encoding="utf-8").read()


def backup(path, src_root):
    """按备份规则：<原名>.<YYYYMMDD-HHMMSS>.bak 进 <backup_root>\\<来源目录镜像>\\

    实现统一在 `toolutil.backup_to_repo`。
    """
    return toolutil.backup_to_repo(path, src_root)


def field(txt, key):
    m = re.search(r"- \*\*%s\*\*：(.+)$" % key, txt, re.M)
    return m.group(1).strip() if m else None


def parse_record(p, root):
    """记录 md → dict；字段缺失 / 文件名或标题行不合模板返回错误字符串

    题名以**记录 md 的标题行**为准（`# 牛客周赛 Round 140 E - 小红的排序（hard）`，
    全角括号是牛客原题名）；文件名里的半角括号只是文件命名习惯，两者不同不算错。"""
    fn = os.path.basename(p)
    m = re.match(r"%sRound(\d+)-([A-Z])-(.+)\.md$" % CONT, fn)
    if not m:
        return None, "文件名不合「<比赛名>RoundN-<题号>-<题名>.md」：%s" % fn
    n, letter, fname = int(m.group(1)), m.group(2), m.group(3)
    t = rd(p)
    m2 = re.match(r"^# %s Round (\d+) ([A-Z]) - (.+?)\s*$" % CONT, t, re.M)
    if not m2:
        return None, "%s 缺 `# %s Round N X - 题名` 格式的标题行" % (fn, CONT)
    if (int(m2.group(1)), m2.group(2)) != (n, letter):
        return None, "%s 标题行的场次/题号与文件名不符（标题：Round %s %s）" % (
            fn, m2.group(1), m2.group(2))
    name = m2.group(3)
    diff, url, algo, fld = (field(t, "难度"), field(t, "原题链接"),
                            field(t, "数据结构与算法"), field(t, "归档文件夹"))
    miss = [k for k, v in (("难度", diff), ("原题链接", url),
                           ("数据结构与算法", algo), ("归档文件夹", fld)) if not v]
    if miss:
        return None, "%s 缺字段：%s" % (fn, "、".join(miss))
    mm = re.search(r"`([^`]+)`", fld)
    raw = (mm.group(1) if mm else fld).replace("/", BS).rstrip(BS)
    i = raw.rfind("算法" + BS)
    rel = raw[i + len("算法") + 1:] if i >= 0 else raw
    return {"n": n, "letter": letter, "name": name, "diff": diff, "url": url,
            "algo": algo, "rel": rel, "path": p}, None


# ---------------------------------------------------------------- 全量索引

def gen_index_block(recs, root):
    out = []
    for n in sorted({r["n"] for r in recs}):
        rs = sorted((r for r in recs if r["n"] == n), key=lambda r: r["letter"])
        # 题解位置写**相对数据根**（可移植：数据根换位置 / 换机器都不用改），
        # 不写数据根的绝对路径。
        sol = BS.join(["题解", CONT, "Round%d" % n, "Round%d题解.md" % n])
        rows = "\n".join(
            "| %s | [%s](%s) | %s | %s | `%s%s` |"
            % (r["letter"], r["name"], r["url"], r["diff"], r["algo"], r["rel"], BS) for r in rs)
        out.append("## %s Round %d\n\n题解：`%s` ｜ %d 题\n\n"
                   "| 题号 | 题名 | 难度 | 算法 / 数据结构 | 归档位置 |\n"
                   "|---|---|---|---|---|\n%s" % (CONT, n, sol, len(rs), rows))
    return "\n\n".join(out)


def sync_index(path, recs, root, apply_):
    if not recs:
        return None, "没有可生成的记录 md，未改动"
    lines = rd(path).split("\n")
    i0 = next((i for i, l in enumerate(lines) if l.startswith("## %s Round " % CONT)), None)
    i1 = next((i for i, l in enumerate(lines) if l.startswith("## 一、")), None)
    if i1 is None or (i0 is not None and i1 <= i0):
        return None, "找不到 `## 一、` 段边界（反查表小节），未改动"
    new_block = gen_index_block(recs, root)
    if i0 is None:
        # 全新数据根：还没有任何场次小节 —— 直接把小节插在 `## 一、` 之前
        new = "\n".join(lines[:i1]).rstrip("\n") + "\n\n" + new_block + "\n\n" + "\n".join(lines[i1:])
    else:
        # 场次段末尾 = `## 一、` 之前最后一个非空行；若那是分隔线 `---`，再往上找
        i2 = max(i for i in range(i0, i1) if lines[i].strip() and lines[i].strip() != "---")
        new = "\n".join(lines[:i0]) + "\n" + new_block + "\n" + "\n".join(lines[i2 + 1:])
    # 头部「当前条数」行
    n_round = len({r["n"] for r in recs})
    new = re.sub(r"(\*\*当前条数\*\*：)\d+ 条 = \d+ 场非签到题之和 = 算法库里 \d+ 份题目记录 md",
                 lambda m: "%s%d 条 = %d 场非签到题之和 = 算法库里 %d 份题目记录 md"
                           % (m.group(1), len(recs), n_round, len(recs)), new)
    if not apply_:
        return new, None
    b = backup(path, os.path.dirname(path))
    open(path, "w", encoding="utf-8", newline="\n").write(new)
    return new, ["已写盘（备份 %s）" % b]


# ------------------------------------------------------------------ 08 表

def parse_old_08(t08):
    """旧表 → 有序 [(比赛名, n, 字母)] 与日期映射 {(比赛名, n, 字母): date}。

    场次键走 toolutil.parse_contest：非牛客的行跳过并打一行说明（本脚本只服务
    牛客周赛、路径写死，不泛化）；场次认不出的行打一行 ★。
    """
    order, dates = [], {}
    unparsed, other = [], []
    for i, l in enumerate(t08.split("\n"), 1):
        m = re.match(r"^\| (\d{4}-\d{2}-\d{2}) \| ([^|]+?) \| ([A-Z]) \|", l)
        if not m:
            continue
        name, num = toolutil.parse_contest(m.group(2))
        if name is None:
            unparsed.append((i, m.group(2)))
            continue
        if name != CONT:
            other.append((i, m.group(2)))
            continue
        key = (name, int(num), m.group(3))
        order.append(key)
        dates[key] = m.group(1)
    for ln, txt in unparsed:
        print("★ 08 表第 %d 行场次认不出，跳过不参与生成：%s" % (ln, txt))
    for ln, txt in other:
        print("说明：08 表第 %d 行是别的比赛（%s），跳过不参与生成"
              % (ln, txt))
    return order, dates


def gen_08_rows(recs, old_order, old_dates, mem_dir):
    by_key = {(CONT, r["n"], r["letter"]): r for r in recs}
    notes = []
    rows, ordered_keys = [], []
    for key in old_order:
        if key in by_key:
            ordered_keys.append(key)
    new_keys = sorted(set(by_key) - set(ordered_keys),
                      key=lambda k: (old_dates.get(k, "9999"), k[1], k[2]))
    for key in new_keys:
        notes.append("新题 %s Round %d %s 在旧表里没有日期，"
                     "暂用记录 md 的修改时间，请核对" % (CONT, key[1], key[2]))
    for key in ordered_keys + new_keys:
        r = by_key[key]
        date = old_dates.get(key)
        if date is None:
            date = datetime.datetime.fromtimestamp(
                os.path.getmtime(r["path"])).strftime("%Y-%m-%d")
        rows.append("| %s | %s Round %d | %s | %s | `%s%s` |"
                    % (date, CONT, r["n"], r["letter"], r["algo"], r["rel"], BS))
    dropped = [k for k in old_order if k not in by_key]
    for k in dropped:
        notes.append("旧表里的 %s Round %d %s 找不到对应记录 md（生成时已丢行，请查）"
                     % (CONT, k[1], k[2]))
    return "".join(l + "\n" for l in rows).rstrip("\n"), notes


def sync_08(path, recs, mem_dir, apply_):
    if not recs:
        return None, "没有可生成的记录 md，未改动"
    t = rd(path)
    lines = t.split("\n")
    ih = next((i for i, l in enumerate(lines)
               if l.startswith("| 日期 | 比赛 | 题号 |")), None)
    if ih is None:
        return None, "找不到第五节表头 `| 日期 | 比赛 | 题号 | …`，未改动"
    i1 = ih + 2
    i2 = i1
    while i2 < len(lines) and lines[i2].startswith("|"):
        i2 += 1
    old_order, old_dates = parse_old_08(t)
    body, notes = gen_08_rows(recs, old_order, old_dates, mem_dir)
    new_lines = lines[:i1] + body.split("\n") + lines[i2:]
    new = "\n".join(new_lines)
    # 「共 N 条」与「（Round … 已全部回填）」
    rs = sorted({r["n"] for r in recs})
    rounds = " / ".join(["Round %d" % rs[0]] + ["%d" % n for n in rs[1:]]) if rs else ""
    new = re.sub(r"共 \d+ 条", lambda m: "共 %d 条" % len(recs), new)
    new = re.sub(r"（Round [^）]*已全部回填）",
                 lambda m: "（%s 已全部回填）" % rounds, new)
    if not apply_:
        return new, notes
    b = backup(path, os.path.dirname(path))
    open(path, "w", encoding="utf-8", newline="\n").write(new)
    return new, notes + ["已写盘（备份 %s）" % b]


# -------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="索引两表自动生成（记录 md → 索引 / 08）")
    ap.add_argument("mode", nargs="?", default="dry", choices=["dry", "apply"])
    ap.add_argument("--root", default=toolutil.DATA_ROOT)
    ap.add_argument("--mem", default=MEM_DEFAULT)
    a = ap.parse_args(argv)
    root = a.root.replace("\\", "/")
    apply_ = a.mode == "apply"

    recs, errs = [], []
    for p in sorted(glob.glob(os.path.join(root, "算法", "**", "%sRound*-*.md" % CONT),
                              recursive=True)):
        r, e = parse_record(p, root)
        (errs if e else recs).append(e or r)
    print("记录 md：%d 份可生成，%d 份有问题（场次 %d 个）"
          % (len(recs), len(errs), len({r["n"] for r in recs})))
    for e in errs:
        print("  [问题] " + e)

    jobs = [("索引", os.path.join(root, "索引", "题解算法索引.md"),
             lambda p: sync_index(p, recs, root, apply_)),
            ("06", os.path.join(a.mem, "06-题解算法归档.md"),
             lambda p: sync_08(p, recs, a.mem, apply_))]
    for tag, path, fn in jobs:
        if not os.path.exists(path):
            print("[%s] 找不到 %s" % (tag, path))
            continue
        old = rd(path)
        new, note = fn(path)
        if new is None:
            print("[%s] %s" % (tag, note))
            continue
        if new == old:
            print("[%s] 无 diff（已是最新）" % tag)
        else:
            d = list(difflib.unified_diff(old.split("\n"), new.split("\n"),
                                          "%s(旧)" % tag, "%s(新)" % tag, lineterm="", n=1))
            nd = sum(1 for x in d if x.startswith(("+", "-")) and not x.startswith(("+++", "---")))
            print("[%s] %d 行 diff" % (tag, nd))
            for x in d[:120]:
                print("    " + x)
            if len(d) > 120:
                print("    …（全 diff 共 %d 行，已截断）" % len(d))
        for x in ([note] if isinstance(note, str) else (note or [])):
            print("    [提醒] %s" % x)
    if errs:
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
