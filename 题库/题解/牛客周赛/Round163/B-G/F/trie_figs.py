# -*- coding: utf-8 -*-
r"""
牛客周赛 Round 163 F - 小月的前缀：这一节的 5 张配图（终端字符画版）
====================================================================

背景
----
这一节原先配了 5 张 PNG（`figs\`，`make_figs.py` 用 Pillow 画的）。
2026-09-30 用户拍板：**图默认用「可跑的终端字符画脚本」，PNG 全删**，
于是把 5 张图逐张改写成字符画，就是本脚本。

和 `trie_visual.py` 的分工
--------------------------
* `trie_visual.py`：**过程回放**，从空树开始把整场 5 次操作全跑一遍（220 行输出）。
* `trie_figs.py`（本脚本）：**讲解插图**，每张图只盯一个点（树怎么长 / 表与树怎么对应 /
  牌子怎么拆 / 查询三步 / 两种选不了），输出短、可直接嵌进题解。

用法
----
    python trie_figs.py            # 五张图全打印
    python trie_figs.py 2          # 只打印第 2 张
    set PYTHONIOENCODING=utf-8 && python trie_figs.py    # 终端不是 UTF-8 时

**嵌进 md 的片段必须逐字来自本脚本的实跑输出**，不许手打（见知识库《配图》）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_tools():
    """工具目录：AGENT_CP_TOOLS 环境变量优先；否则向上找含 tools/toolutil.py 的目录。"""
    p = os.environ.get("AGENT_CP_TOOLS")
    if p:
        return p
    p = HERE
    while not os.path.isfile(os.path.join(p, "tools", "toolutil.py")):
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit("没找到仓库 tools/：把 AGENT_CP_TOOLS 环境变量指向它的绝对路径")
        p = q
    return os.path.join(p, "tools")


sys.path.insert(0, find_tools())
from vizgrid import (H_LINE, V_LINE, render_tree, render_array,  # noqa: E402
                     pad, dwidth)


def hdr(title, n=70):
    """一节的开头。**不用 vizgrid.banner()** —— 那个是"打印并返回 None"，
    本脚本要先把整段攒好再一次打印（嵌进 md 时才不会混进别的东西）。"""
    return ["", "=" * n, title, "=" * n]


def table_lines(headers, rows, indent=2):
    """自己排一张表，**只返回行、不打印**（vizgrid.table() 是打印并返回字符串，
    混用会让同一张表被打印两遍）。列宽照 vizgrid 的规矩用 dwidth 算，中文不错位。"""
    cols = len(headers)
    w = [dwidth(str(h)) for h in headers]
    for r in rows:
        for i in range(min(cols, len(r))):
            w[i] = max(w[i], dwidth(str(r[i])))
    out = [" " * indent + "  ".join(pad(str(headers[i]), w[i], "^")
                                    for i in range(cols)).rstrip()]
    out.append(" " * indent + "  ".join(H_LINE * w[i] for i in range(cols)))
    for r in rows:
        out.append(" " * indent + "  ".join(pad(str(r[i]), w[i])
                                            for i in range(min(cols, len(r)))).rstrip())
    return out

# ---------------------------------------------------------------- 样例数据
# 样例 1：3 种串，a 有 2 个、ab 有 1 个、abc 有 0 个。
# 和 trie_visual.py / f.cpp 用的是同一组数据。
SNAME = ["", "a", "ab", "abc"]
IDV = [0, 1, 2, 3]                 # id[v]：v 号结点上挂几号牌
CNT0 = [0, 2, 1, 0]                # cnt[i]：i 号串还剩几个（建树完成时）
# ch[v] 只列 'a' 'b' 'c' 三列（列号 = 字符 - 'a' 的前三列）
CH = [[1, 0, 0],
      [0, 2, 0],
      [0, 0, 3],
      [0, 0, 0]]
LETTERS = ["a", "b", "c"]


def kids(v, ch=None, cnt=None, idv=None, mark_new=()):
    """vizgrid.render_tree 要的 children_of(v)：返回 [(边上的字符, 子结点), ...]"""
    ch = CH if ch is None else ch
    out = []
    for j, ltr in enumerate(LETTERS):
        u = ch[v][j]
        if u:
            out.append((ltr, u))
    return out


def label(v, cnt=None, idv=None, sname=None):
    """结点右边那段文字：v=2 「ab」id=2 剩1"""
    cnt = CNT0 if cnt is None else cnt
    idv = IDV if idv is None else idv
    sname = SNAME if sname is None else sname
    tag = ""
    if idv[v]:
        tag = " 「%s」id=%d 剩%d" % (sname[idv[v]], idv[v], cnt[idv[v]])
    return "v=%d%s" % (v, tag)


def tree_lines(ch=None, cnt=None, idv=None, sname=None, mark=()):
    ch = CH if ch is None else ch
    cnt = CNT0 if cnt is None else cnt
    idv = IDV if idv is None else idv
    sname = SNAME if sname is None else sname
    return render_tree(lambda v: kids(v, ch), lambda v: label(v, cnt, idv, sname),
                       root=0, root_label="根 v=0", mark=mark)


def ch_table():
    """ch 表（只列 a b c 三列）"""
    rows = []
    for v in range(len(CH)):
        rows.append(["ch[%d]" % v] + ["%d" % x for x in CH[v]])
    return table_lines(["", "'a'", "'b'", "'c'"], rows, indent=2)


# ================================================================ 图 1
def fig1():
    """树是怎么「长」出来的：三棵树叠着看"""
    out = hdr("图 1  三个串一个一个插进去，树是怎么长出来的") + [""]
    steps = [
        (1, "插入 「a」（2 个）", "新建结点 v=1", [1]),
        (2, "插入 「ab」（1 个）", "v=1 已有（复用），再从 v=1 新建结点 v=2", [2]),
        (3, "插入 「abc」（0 个）", "v=1、v=2 已有（复用），再从 v=2 新建结点 v=3", [3]),
    ]
    for k, (n, title, why, new) in enumerate(steps):
        out.append("  ── 第 %d 步：%s ──" % (n, title))
        out.append("     %s" % why)
        out.append("")
        # 每张图只画到「已经插入前 n 个串」为止
        ch = [[0, 0, 0] for _ in range(4)]
        idv = [0] * 4
        cnt = [0, 0, 0, 0]
        for i in range(1, n + 1):
            s = SNAME[i]
            v = 0
            for depth, c in enumerate(s):
                j = ord(c) - ord("a")
                if j >= 3:
                    continue
                if depth < len(s) - 1:
                    # 中途的边前面已经建好了
                    v = ch[v][j] if ch[v][j] else 0
                else:
                    if not ch[v][j]:
                        ch[v][j] = i
                    v = ch[v][j]
            idv[v] = i
        cnt = [0, 2, 1, 0]
        for i in range(n + 1, 4):
            cnt[i] = 0
        for ln in tree_lines(ch, cnt, idv, SNAME, mark=new):
            out.append(ln)
        out.append("")
        if k < len(steps) - 1:
            out.append("  ★ = 这一步新建的结点；没有★的是复用的老结点。")
            out.append("")
    out.append("  记住两件事：")
    out.append("    1. 每次插入只是顺着已有的路往下接一段，能复用就复用（这就是「共享前缀」）；")
    out.append("    2. 牌子挂在不同的深度上——深度 1 挂 a、深度 2 挂 ab、深度 3 挂 abc。")
    out.append("       所以「走得更深」就等于「前缀更长」。")
    return out


# ================================================================ 图 2
def fig2():
    """ch 表里的一个数字 = 树上的一条边"""
    out = hdr("图 2  ch[v][x] 里的一个数字，就是树上的一条边") + [""]
    out.append("  ① ch 表（只列 a b c 三列；0 = 没有这个儿子）：")
    out.append("")
    out += ch_table()
    out.append("")
    out.append("  ② 这张表唯一决定的那棵树：")
    out.append("")
    out += tree_lines()
    out.append("")
    out.append("  ③ 一一对上（左边是表里的格子，右边是树上的边）：")
    out.append("")
    for v in range(len(CH)):
        for j, ltr in enumerate(LETTERS):
            u = CH[v][j]
            if u:
                out.append("     ch[%d]['%s'] = %d   %s  站在 %d 号位置走一步 %s，就来到 %d 号位置"
                           % (v, ltr, u, "⟶", v, ltr, u))
    out.append("")
    out.append("  读法：左边表里每一个非零格子，就是右边树上一条实实在在的边。")
    out.append("        格子里的数字 = 边的终点；格子的行号 = 边的起点；")
    out.append("        格子的列号 = 边上写的字符。反过来也成立。")
    out.append("        树变了，数组就变；数组动了，树就动。它们是同一个东西的两种画法。")
    return out


# ================================================================ 图 3
def fig3():
    """一块牌子拆成 id 和 cnt"""
    out = hdr("图 3  结点上那块牌子的内容，分别是 id 和 cnt 里的一个数字") + [""]
    out.append("  ① 先把 v=2 上的这块牌子放大：")
    out.append("")
    out.append("       ┌────────────────────────────┐")
    out.append("       │   「ab」   id = 2   剩 1   │")
    out.append("       └────────────────────────────┘")
    out.append("")
    out.append("  ② 它整棵树里的位置（★ 就是 v=2）：")
    out.append("")
    out += tree_lines(mark=(2,))
    out.append("")
    out.append("  ③ 「id = 2」这个 2 是从 id[] 表里取来的（下标是结点编号 v）：")
    out.append("")
    out += render_array("id", IDV, idx_name="v", start=0)
    out.append("")
    out.append("     取法：站在 v=2 --> 读 id[2] --> 得到 2（编号 2 的串「ab」在这儿结束）")
    out.append("")
    out.append("  ④ 「剩 1」这个 1 是从 cnt[] 表里取来的（下标是字符串编号 i）：")
    out.append("")
    out += render_array("cnt", CNT0[1:], idx_name="i", start=1)
    out.append("")
    out.append("     取法：拿到编号 i=2 --> 读 cnt[2] --> 得到 1（「ab」还剩 1 个）")
    out.append("")
    out.append("  注意：id 的下标是结点编号 v，cnt 的下标是字符串编号 i ——")
    out.append("        两张表的下标不是一回事，这是本题最容易混的地方。")
    return out


# ================================================================ 图 4
def fig4():
    """查询 t = abc：三步走"""
    out = hdr('图 4  查询 t = "abc" 的三步，每步看一眼牌子') + [""]
    cnt = [0, 2, 1, 0]
    steps = [
        (1, "a", 1, "id[1] = 1，cnt[1] = 2 > 0", "合法！best 从 0 改成 1",
         "（候选：「a」）", [1]),
        (2, "b", 2, "id[2] = 2，cnt[2] = 1 > 0", "合法！best 从 1 改成 2",
         "（「ab」更长，直接覆盖）", [1, 2]),
        (3, "c", 3, "id[3] = 3，可是 cnt[3] = 0", "牌子在，货没了，跳过",
         "（走完，best 停在 2）", [1, 2, 3]),
    ]
    for n, c, v, cond, why, note, path in steps:
        out.append("  ── 第 %d 步：踩到 '%s' → 结点 v=%d ──" % (n, c, v))
        out.append("     %s" % cond)
        out.append("     %s  %s" % (why, note))
        out.append("")
        for ln in tree_lines(cnt=cnt, mark=(v,)):
            out.append(ln)
        out.append("")
    out.append("  沿 t 一个字一个字往下走，踩到的每个结点都恰好对应 t 的一个前缀；")
    out.append("  越走越深，最后一次覆盖就是最长的那一个。")
    out.append("")
    out.append("  走完之后 cnt[2] 从 1 减成 0：")
    out.append("")
    out += render_array("cnt", [2, 0, 0], idx_name="i", start=1)
    return out


# ================================================================ 图 5
def fig5():
    """两种「选不了它」的情况"""
    out = hdr("图 5  两种「选不了它」的情况") + [""]

    out.append('  ── ① t = "ax"：\'a\' 走得到，\'x\' 这条路不存在 ──')
    out.append("")
    out.append("     第 1 个字符 'a'：ch[0]['a'] = 1 → 走到 v=1，id[1]=1、cnt[1]=1>0 → best = 1")
    out.append("     第 2 个字符 'x'：ch[1]['x'] = 0，这条路不存在")
    out.append("                    → break（后面更长的前缀都要从这里过，所以更不可能存在）")
    out.append("     走完 → 答案 1（随后 cnt[1] 从 1 减成 0）")
    out.append("")
    for ln in tree_lines(cnt=[0, 1, 1, 0], mark=(1,)):
        out.append(ln)
    out.append("")

    out.append('  ── ② t = "a"：走到了 v=1，牌子也在，可是没货了 ──')
    out.append("")
    out.append("     第 1 个字符 'a'：ch[0]['a'] = 1 → 走到 v=1")
    out.append("                    id[1] = 1，可是 cnt[1] = 0 → 跳过（best 保持 0）")
    out.append("     走完 → 答案 0（不减任何库存）")
    out.append("")
    for ln in tree_lines(cnt=[0, 0, 1, 0], mark=(1,)):
        out.append(ln)
    out.append("")
    out.append("  两句话记住：")
    out.append("    · 牌子在 = 这个串「属于这棵树」（它确实是从某个 s_i 长出来的）")
    out.append("    · cnt = 0 = 它「没库存了」")
    out.append("    所以代码里那行判断是两个条件都要成立：if (id[v] && cnt[id[v]] > 0)")
    return out


FIGS = {"1": fig1, "2": fig2, "3": fig3, "4": fig4, "5": fig5}


def main(argv):
    which = argv[0] if argv else "all"
    for k in sorted(FIGS):
        if which in ("all", k):
            print("\n".join(FIGS[k]()))
            if which == "all":
                print()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
