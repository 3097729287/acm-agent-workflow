# -*- coding: utf-8 -*-
"""C 题配图脚本：把「数字 × 花色」摆成一张表，看清「每个数字只能出一种花色一次」。

实测没有 py 命令，双击 run.cmd 或手敲：
    python pair_visual.py

四部分：
  1. 样例 1 的牌摆成表
  2. 每个数字能出几张：2 × ⌊花色种数 / 2⌋
  3. 挑牌 + 配对的全过程
  4. 对答案（官方样例 1 / 2 / 3）
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
from vizgrid import part, note, table              # noqa: E402

TOTAL = 4
SUITS = "ABCD"


def show_table(a):
    """把牌摆成「花色 × 数字」的表，格子里写牌的下标（没有牌就写 —）。"""
    vals = sorted(set(v for v, _ in a))
    rows = []
    for s in SUITS:
        row = [s]
        for v in vals:
            ids = [i + 1 for i, (x, _c) in enumerate(a) if x == v and _c == s]
            row.append(",".join(map(str, ids)) if ids else "—")
        rows.append(row)
    table(["花色"] + ["数字 %d" % v for v in vals], rows,
          aligns=["^"] + ["^"] * len(vals))


def solve_c(cards):
    """C 题正解：按数字分组，每组按花色首次出现顺序取牌，凑偶数张两两配对。"""
    from collections import defaultdict
    byv = defaultdict(list)
    for i, (v, c) in enumerate(cards, 1):
        byv[v].append((i, c))
    pairs, info = [], []
    for v in sorted(byv):
        used, pick = set(), []
        for i, c in byv[v]:
            if c not in used:
                used.add(c)
                pick.append((i, c))
        m = len(pick) // 2 * 2
        info.append((v, len(used), m, pick[:m]))
        for k in range(0, m, 2):
            pairs.append((pick[k][0], pick[k + 1][0]))
    return pairs, info


def main():
    # ---------------------------------------------------------- 1
    part(1, TOTAL, "样例 1 的牌摆成表：数字 × 花色")
    s1 = [(1, "A"), (1, "B"), (3, "A"), (2, "A"), (3, "B")]
    note("样例 1 的五张牌（下标 1~5）：1A 1B 3A 2A 3B。横着看是数字，竖着看是花色：")
    show_table(s1)
    note("""一个「对」= 两张**数字相同**的牌。但题面还有一条限制：
所有打出的牌里，不能有两张「花色 + 数字」都相同的牌。
所以对每个数字来说，打出去的牌**花色必须两两不同** —— 表里同一列、
同一行交叉的那张牌，一个数字最多只能取一次。""")

    # ---------------------------------------------------------- 2
    part(2, TOTAL, "每个数字最多出几张")
    note("""设某个数字一共有 d 种不同的花色（看清楚：是**种类**，不是张数）。
打出的张数必须是偶数（两张一对），花色又不能重复，所以最多打 2 × ⌊d/2⌋ 张。
各数字之间互不干扰，答案就是把每个数字的上限加起来。""")
    pairs, info = solve_c(s1)
    table(["数字", "花色种数 d", "能出的张数 2×⌊d/2⌋", "挑出来的牌（下标:花色）"],
          [[v, d, m, " ".join("%d%s" % (i, c) for i, c in pick)] for v, d, m, pick in info],
          aligns=[">", ">", ">", "<"])
    note("样例 1 的答案 = 2 + 0 + 2 = 4 张。")

    # ---------------------------------------------------------- 3
    part(3, TOTAL, "挑牌与配对的全过程")
    note("""每个数字内部：按花色**第一次出现**的顺序挑牌（这样挑出来的下标字典序最小），
凑够偶数张以后，顺次两两配成一对——同一组的牌花色互不相同，配对一定合法。""")
    for v, d, m, pick in info:
        if m == 0:
            note("  数字 %d：d = %d，凑不出不同的两张 → 一张都不出" % (v, d))
        else:
            note("  数字 %d：挑了 %s，配对成 %s"
                 % (v, " ".join("%d%s" % (i, c) for i, c in pick),
                    " 和 ".join("(%d,%d)" % (pick[k][0], pick[k + 1][0])
                                for k in range(0, m, 2))))
    note("程序输出（第一行是张数，后面每行一对牌的下标）：")
    note("  %d" % (len(pairs) * 2))
    for x, y in pairs:
        note("  %d %d" % (x, y))

    # ---------------------------------------------------------- 4
    part(4, TOTAL, "对答案")
    cases = [
        ("样例 1", s1, 4, [(1, 2), (3, 5)]),
        ("样例 2", [(1, "A"), (1, "A"), (2, "B"), (2, "B")], 0, []),
        ("样例 3", [(1, "A"), (1, "B"), (1, "A"), (1, "C")], 2, [(1, 2)]),
    ]
    rows = []
    for name, cards, k_expect, pair_expect in cases:
        got, _ = solve_c(cards)
        ok = (len(got) * 2 == k_expect and got == pair_expect)
        rows.append([name, k_expect, len(got) * 2,
                     " ".join("(%d,%d)" % p for p in got), "一致" if ok else "★不一致★"])
    table(["样例", "官方答案张数", "本程序张数", "本程序配对", "结论"], rows,
          aligns=["<", ">", ">", "<", "^"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
