# -*- coding: utf-8 -*-
r"""selfcheck_filter —— 多条件筛选（知识点 / 状态 / 难度）的机器闸门

    python tools\selfcheck_filter.py            # 全跑（秒级）
    python tools\selfcheck_filter.py --keep     # 留着临时目录（排查用）

两段验收，全在一份**临时状态表**上跑（不碰 config.json 指的数据根、不写任何真表）：

  ① 匹配函数单元断言：子串 / 忽略空白大小写 / 多词并集 / 难度五种写法（单值、区间、
     写反、<=、>=、严格 < >）/ 认不出的写法 = 空区间（永不命中）/ 三条件 AND。
     期望值一律**手写**（不从被测函数反推），错了就是错了。
  ② 命令行端到端：真起子进程跑 `status_report.py --knowledge/--status/--todo/
     --difficulty`，解析「筛出 N 题」与命中行，跟 ① 同一批手写期望逐题比。
     用户就是这么敲的，所以验收面就是命令行本身。

GUI 那半边的「跟命令行同源」由 `python tools\status_gui.py --smoke` 的 (zz) 段守：
它拿 11 组条件逐组起子进程跑同一个 `status_report.py`、比对命中集合，并与
窗口里 `visible_rows()` 的结果一字不差——两边都走 `status_report.filter_rows` 这一个实现。

退出码：0 = 两段都过；1 = 有验收没过；2 = 环境不对（连不带筛选的报告都跑不起来）。
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status_report as SR  # noqa: E402
import toolutil  # noqa: E402

TOOLS = os.path.join(toolutil.REPO_ROOT, "tools")
COLS = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]

# 夹具：8 行，覆盖「知识点同义多写法 / 六个状态 / 难度有、没有、超界」三种情况。
# 写成字面量而不是从真表抽：自检不该依赖用户数据长什么样。
ROWS = [
    ("牛客周赛 Round 203", "D", "小红的路径", "区间 DP ｜ 前缀和", "CF 1500", "未做", ""),
    ("牛客周赛 Round 203", "E", "小红的树", "树形 DP", "CF 1800", "不会", ""),
    ("牛客周赛 Round 208", "E", "小月的期望", "动态规划 ｜ 期望DP", "CF 2100", "待重写", ""),
    ("牛客周赛 Round 210", "A", "签到", "模拟", "CF 800", "独立AC", "2026-09-30"),
    ("牛客周赛 Round 210", "B", "二分边界", "二分 ｜ 贪心", "CF 1200", "复现AC", "2026-09-28"),
    ("牛客周赛 Round 199", "C", "图示", "图论 ｜ 最短路", "CF 1600", "未做", ""),
    ("牛客周赛 Round 199", "D", "没标难度", "二分", "", "不会", ""),
    ("牛客周赛 Round 188", "D", "树上路径", "树链剖分 ｜ 线段树", "CF 1900", "巩固", "2026-09-01"),
]

R203D = ("牛客周赛 Round 203", "D")
R203E = ("牛客周赛 Round 203", "E")
R208E = ("牛客周赛 Round 208", "E")
R210A = ("牛客周赛 Round 210", "A")
R210B = ("牛客周赛 Round 210", "B")
R199C = ("牛客周赛 Round 199", "C")
R199D = ("牛客周赛 Round 199", "D")
R188D = ("牛客周赛 Round 188", "D")

# (命令行参数, 手写命中集合, 输出里必须出现的话)
CASES = [
    (["--knowledge", "DP"], {R203D, R203E, R208E}, []),
    (["--knowledge", "区间 dp"], {R203D}, []),                  # 大小写 / 空格无关
    (["--knowledge", "前缀和,最短路"], {R203D, R199C}, []),     # 多词并集（逗号）
    (["--knowledge", "树形，动态规划"], {R203E, R208E}, []),    # 全角逗号也是分隔
    (["--knowledge", "二分"], {R210B, R199D}, []),              # 子串：命中两行
    (["--todo"], {R203D, R203E, R208E, R199C, R199D}, []),      # = 未做 / 不会 / 待重写
    (["--status", "未做,独立AC"], {R203D, R199C, R210A}, []),   # 状态多选 = 并集
    (["--status", "未做", "--status", "独立AC"], {R203D, R199C, R210A}, []),  # 拆成两次写一样
    (["--difficulty", "1500"], {R203D}, []),
    (["--difficulty", "1200-1600"], {R203D, R210B, R199C}, []),
    (["--difficulty", "1600-1200"], {R203D, R210B, R199C}, []),   # 写反自动摆正
    (["--difficulty", "<=1400"], {R210A, R210B}, []),
    (["--difficulty", "<1500"], {R210A, R210B}, []),            # 严格小于：1500 那行不算
    (["--difficulty", ">=1800"], {R203E, R208E, R188D}, []),    # 端点含：1800 那行算
    (["--difficulty", "1200,1800"], {R210B, R203E}, []),        # 难度多值并集
    (["--todo", "--knowledge", "DP"], {R203D, R203E, R208E}, []),           # 三条件 AND
    (["--todo", "--knowledge", "DP", "--difficulty", "1500-1800"], {R203D, R203E}, []),
    (["--knowledge", "不存在的算法"], set(), ["（没有命中的题）"]),
    (["--difficulty", "HARD"], set(), ["★ 难度写法不认：「HARD」"]),
    (["--status", "卡住"], set(), ["★ 状态「卡住」不在"]),
]


def key_of(r):
    return (r["场次"], r["题号"])


def fixture_text():
    lines = ["# 临时状态表（自检用；格式照真表：表头 + 分隔线 + 7 列）", "",
             "| " + " | ".join(COLS) + " |",
             "|" + "|".join(["---"] * len(COLS)) + "|"]
    for r in ROWS:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines + [""]) + "\n"


def run(args):
    """跑一个同目录脚本 → (退出码, stdout+stderr)。"""
    cmd = [sys.executable, os.path.join(TOOLS, args[0])] + args[1:]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=toolutil.REPO_ROOT,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def parse_hits(out):
    """筛选报告 → (筛出数, 命中集合, 条件行)。「筛出 N 题：」下面那几行就是清单。"""
    counts, cond, hits, in_rows = None, None, [], False
    for ln in out.splitlines():
        m = re.match(r"^筛出 (\d+) 题：$", ln)
        if m:
            counts, in_rows = int(m.group(1)), True
            continue
        if ln.startswith("条件："):
            cond = ln
            continue
        if not in_rows:
            continue
        s = ln.strip()
        if not s or s.startswith(("（", "★")):
            in_rows = False
            continue
        cells = re.split(r"\s{2,}", s)
        if len(cells) >= 2:
            hits.append((cells[0], cells[1]))
    return counts, set(hits), cond


# ---------------------------------------------------------------- ① 单元
def t_units():
    """匹配函数的手写期望（返回 (ok, 说明)）。"""
    bad = []
    n = [0]

    def eq(name, got, want):
        n[0] += 1
        if got != want:
            bad.append("%s：得到 %r，应为 %r" % (name, got, want))

    eq("tag_key：去空白 + 小写", SR.tag_key(" 区间 DP\t"), "区间dp")
    eq("split_terms：半角逗号", SR.split_terms("DP, 动态规划"), ["DP", "动态规划"])
    eq("split_terms：全角逗号", SR.split_terms("DP，动态规划"), ["DP", "动态规划"])
    eq("split_terms：空串", SR.split_terms(""), [])

    eq("知识点：子串命中（空格无关）", SR.match_knowledge("区间 DP ｜ 前缀和", ["区间dp"]), True)
    eq("知识点：大小写无关", SR.match_knowledge("区间 DP", ["dp"]), True)
    eq("知识点：多词并集（中任一个）", SR.match_knowledge("树链剖分 ｜ 线段树", ["树形DP", "线段树"]), True)
    eq("知识点：不中", SR.match_knowledge("模拟", ["DP"]), False)
    eq("知识点：空词表 = 不筛", SR.match_knowledge("随便什么", []), True)

    eq("难度取数字", SR.difficulty_num("CF 1500"), 1500)
    eq("难度没数字 = None", SR.difficulty_num(""), None)

    eq("难度 单值", SR.parse_difficulty("1500"), (1500, 1500))
    eq("难度 区间", SR.parse_difficulty("1200-1600"), (1200, 1600))
    eq("难度 写反自动摆正", SR.parse_difficulty("1600-1200"), (1200, 1600))
    eq("难度 带空格", SR.parse_difficulty("1200 - 1600"), (1200, 1600))
    eq("难度 <=", SR.parse_difficulty("<=1400"), (None, 1400))
    eq("难度 ≤（全角）", SR.parse_difficulty("≤1400"), (None, 1400))
    eq("难度 <（严格）", SR.parse_difficulty("<1400"), (None, 1399))
    eq("难度 >=", SR.parse_difficulty(">=1800"), (1800, None))
    eq("难度 >（严格）", SR.parse_difficulty(">1800"), (1801, None))
    eq("难度 认不出 = None", SR.parse_difficulty("HARD"), None)

    specs, badw = SR.difficulty_specs(["1500", "HARD"])
    eq("写法不认 = 空区间 + 记名", (specs[0], specs[1], badw),
       ((1500, 1500), SR.DIFF_NEVER, ["HARD"]))
    eq("空区间永不命中", SR.match_difficulty("CF 1500", [SR.DIFF_NEVER]), False)
    eq("难度：空 spec = 不筛", SR.match_difficulty("", []), True)
    eq("难度：有 spec 时没数字的行不命中", SR.match_difficulty("", [(1200, 1600)]), False)

    rows = [dict(zip(COLS, r)) for r in ROWS]
    eq("filter_rows：空 = 全过", len(SR.filter_rows(rows)), len(ROWS))
    eq("filter_rows：三条件 AND",
       {key_of(r) for r in SR.filter_rows(rows, ["DP"], ["未做"], [(1500, 1500)])}, {R203D})
    eq("filter_rows：状态 ∈ 并集",
       {key_of(r) for r in SR.filter_rows(rows, [], ["未做", "独立AC"])}, {R203D, R199C, R210A})

    if bad:
        return False, "★ %d 项对不上：\n        %s" % (len(bad), "\n        ".join(bad))
    return True, "手写期望全部吻合（%d 组断言：匹配函数 + filter_rows）" % n[0]


# ---------------------------------------------------------------- ② 命令行
def t_cli(fixture):
    """真跑命令行，命中集合逐组跟手写期望比（返回 (ok, 说明)）。"""
    bad = []
    for args, want, must in CASES:
        rc, out = run(["status_report.py", "--file", fixture] + args)
        if rc != 0:
            bad.append("%s：退出码 %d\n%s" % (" ".join(args), rc, out))
            continue
        counts, hits, cond = parse_hits(out)
        if counts is None:
            bad.append("%s：输出里没有「筛出 N 题：」\n%s" % (" ".join(args), out))
            continue
        if hits != want:
            extra = sorted(hits - want)
            miss = sorted(want - hits)
            bad.append("%s：命中集合不符（多 %r / 少 %r）" % (" ".join(args), extra, miss))
            continue
        if counts != len(hits) or not (cond or "").startswith("条件："):
            bad.append("%s：计数 %r ≠ 实际 %d 行 / 没有条件行（%r）"
                       % (" ".join(args), counts, len(hits), cond))
            continue
        for s in must:
            if s not in out:
                bad.append("%s：输出里该有 %r" % (" ".join(args), s))

    if bad:
        return False, "★ %d 组没过：\n        %s" % (len(bad), "\n        ".join(bad))
    return True, "%d 组命令的命中集合 = 手写期望（含写反区间、全角逗号、认不出的写法）" % len(CASES)


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="多条件筛选 机器闸门（自检）")
    ap.add_argument("--keep", action="store_true", help="留着临时目录（排查用）")
    a = ap.parse_args(argv)
    base = tempfile.mkdtemp(prefix="selfcheck-filter-")
    print("自检沙箱：%s%s" % (base, "（--keep，跑完不删）" if a.keep else ""))
    ok1 = ok2 = False
    try:
        fixture = os.path.join(base, "题目状态.md")
        with io.open(fixture, "w", encoding="utf-8", newline="\n") as f:
            f.write(fixture_text())
        rc, out = run(["status_report.py", "--file", fixture])      # 对照：不带筛选的五段报告
        if rc != 0 or "题目状态报告" not in out:
            print("★ 环境不对：连不带筛选的报告都跑不起来（退出码 %d）\n%s" % (rc, out))
            return 2
        ok1, msg1 = t_units()
        print("[%s] ① 匹配函数单元（手写期望）" % ("通过" if ok1 else "★未通过"))
        print("        " + msg1.replace("\n", "\n        "))
        ok2, msg2 = t_cli(fixture)
        print("[%s] ② 命令行端到端（子进程真跑 status_report.py）" % ("通过" if ok2 else "★未通过"))
        print("        " + msg2.replace("\n", "\n        "))
    finally:
        if not a.keep:
            shutil.rmtree(base, ignore_errors=True)
    print("-" * 74)
    if ok1 and ok2:
        print("结论：筛选逻辑两段验收全过——一条命令就能查「没做的 DP 题」这种问题")
        return 0
    print("结论：★有验收没过（见上面 ★ 那行的报错）★")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
