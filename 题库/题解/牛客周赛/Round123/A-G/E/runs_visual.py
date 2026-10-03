# -*- coding: utf-8 -*-
"""E / F 题配图脚本：顺子、连续段、以及两个算法过程。

实测没有 py 命令，双击 run.cmd 或手敲：
    python runs_visual.py

五部分：
  1. 「顺子」到底是什么（画在数轴上）
  2. 最少出牌次数 = 连续段的个数（E 题：数字互不相同）
  3. 有重复数字怎么办（F 题：cnt 差分公式，配柱状图）
  4. E 题：前缀一个个来，段数怎么变（官方样例 5 3 1 2 4）
  5. F 题：前缀一个个来，公式的哪两项在变（官方样例 1 3 1 2 3 2）
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
from vizgrid import Grid, part, note, table          # noqa: E402

TOTAL = 5


# ----------------------------------------------------------------- 画图小工具
def axis(values, marks=(), hi=None, xs=4):
    """数轴：刻度上放数字，marks 里的数字下面画粗线（表示它们在同一个顺子里）。"""
    hi = hi if hi is not None else max(values) + 1
    g = Grid(0, hi, 0, 2, xs=xs, ys=2)
    for v in range(0, hi + 1):
        g.put(v, 1, "·")
    for v in values:
        g.put(v, 2, str(v))
    for a, b in marks:
        g.seg(a, 1, b, 1, "━")
    return g


def bars(cnt, xs=4):
    """柱状图：横轴是牌面数字，柱子高度是该数字的张数 cnt[v]。"""
    hi = max(cnt.values()) + 1
    g = Grid(0, max(cnt) + 1, 0, hi, xs=xs, ys=2)
    for v in range(0, max(cnt) + 1):
        g.put(v, 0, str(v) if v < 10 else "#")
    for v, c in cnt.items():
        for y in range(1, c + 1):
            g.put(v, y, "┃")
    return g


def draw(g):
    print(g.text(indent="      "))


# ----------------------------------------------------------------- 两个算法
def solve_e(a):
    """E 题正解：在线维护连续段数。"""
    has = set()
    out, segs = [], 0
    for v in a:
        segs += 1
        if v - 1 in has:
            segs -= 1
        if v + 1 in has:
            segs -= 1
        has.add(v)
        out.append(segs)
    return out


def solve_f(a):
    """F 题正解：Σ max(0, cnt[v] - cnt[v-1])，每步只更新 v、v+1 两项。"""
    from collections import defaultdict
    cnt = defaultdict(int)
    term = lambda v: max(0, cnt[v] - cnt[v - 1])       # noqa: E731
    total, out = 0, []
    for v in a:
        before = term(v) + term(v + 1)
        cnt[v] += 1
        total += term(v) + term(v + 1) - before
        out.append(total)
    return out


# ----------------------------------------------------------------- 主流程
def main():
    # ---------------------------------------------------------- 1
    part(1, TOTAL, "「顺子」是什么")
    note("""题面说：k 张牌是一个顺子 ⟺ 从小到大排序后每相邻两张都差 1。
换句话说，顺子就是**数轴上挨在一起的一段**，中间不许有空。
拿题面自己的例子 a = {4,3,6,7,5} 看，排好序是 3,4,5,6,7：""")
    draw(axis([3, 4, 5, 6, 7], marks=[(3, 7)]))
    note("""这一整段连着，所以 5 张牌**一次**就能出完。
再看 {3,5}：中间缺了 4，粗线连不起来，只能算两张单牌（两张单牌各自也是顺子）。""")
    draw(axis([3, 5], hi=6))

    # ---------------------------------------------------------- 2
    part(2, TOTAL, "最少出牌次数 = 连续段的个数（E 题）")
    note("""E 题保证牌面数字**互不相同**，于是问题变成：
把这一堆数字画在数轴上，它裂成了几段？每段出一次，段数就是答案。
段与段之间至少空一个数字，永远没法并成一次出完，所以段数就是最少次数。""")
    note("例：手上有 {1,2,3, 5, 8,9,10}，数轴上是这样三段：")
    draw(axis([1, 2, 3, 5, 8, 9, 10], marks=[(1, 3), (5, 5), (8, 10)], hi=11))
    note("→ 最少 3 次。注意中间那张 5 自己就是一段（单独一张牌也是顺子）。")

    # ---------------------------------------------------------- 3
    part(3, TOTAL, "有重复数字怎么办（F 题）")
    note("""F 题不保证互不相同，一段里同一个数字只能放一张牌，
所以「有几段」这个说法不够用了。换成数**每张牌属于哪个顺子**：
设 cnt[v] = 数字 v 有几张。数字 v 的这些牌里，最多有 cnt[v-1] 张能接在
某个「已经走到 v-1 的顺子」后面（一个顺子最多经过 v-1 一次），
所以至少要有 cnt[v] - cnt[v-1] 个顺子**从 v 开始**。把所有「开头」加起来：

    最少顺子数 = Σ_v max(0, cnt[v] - cnt[v-1])      （规定 cnt[0] = 0）

每个顺子恰好有一个开头，所以这个和正好是顺子个数。""")
    cnt = {1: 2, 2: 1, 3: 2, 4: 1}
    note("例：cnt[1]=2, cnt[2]=1, cnt[3]=2, cnt[4]=1，柱子画出来是这样：")
    draw(bars(cnt))
    note("把它代进公式：")
    rows = []
    prev = 0
    for v in sorted(cnt):
        rows.append([v, cnt[v], prev, max(0, cnt[v] - prev)])
        prev = cnt[v]
    table(["数字 v", "cnt[v]", "cnt[v-1]", "max(0, 差)"], rows,
          aligns=[">", ">", ">", ">"])
    note("四项相加 = 2 + 0 + 1 + 0 = 3，所以最少出 3 次：")
    note("  {1,2,3,4} + {1,3} + {3}   —— 三个顺子，正好把 6 张牌出完。")

    # ---------------------------------------------------------- 4
    part(4, TOTAL, "E 题：前缀一个个来，段数怎么变")
    a = [5, 3, 1, 2, 4]
    note("官方样例 a = 5 3 1 2 4。每读一张牌：先 +1（自己算一段），"
         "左右邻牌已经在集合里就各 -1（并进那一段）。")
    has, segs, rows = set(), 0, []
    for v in a:
        segs += 1
        left = (v - 1) in has
        right = (v + 1) in has
        if left:
            segs -= 1
        if right:
            segs -= 1
        has.add(v)
        rows.append([v, "有" if left else "无", "有" if right else "无", segs])
    table(["新牌 v", "v-1 在集合里", "v+1 在集合里", "段数"], rows,
          aligns=[">", "^", "^", ">"])
    got = solve_e(a)
    note("答案：%s" % " ".join(map(str, got)))
    note("官方样例输出：1 2 3 2 1  →  %s"
         % ("一致" if got == [1, 2, 3, 2, 1] else "★不一致★"))

    # ---------------------------------------------------------- 5
    part(5, TOTAL, "F 题：公式里到底哪两项在变")
    b = [1, 3, 1, 2, 3, 2]
    note("官方样例 a = 1 3 1 2 3 2。cnt[v] 一变，只有 term(v) 和 term(v+1) "
         "这两项会动，所以每步 O(1) 就能更新总和。")
    from collections import defaultdict
    cnt2, term = defaultdict(int), None
    term = lambda v: max(0, cnt2[v] - cnt2[v - 1])     # noqa: E731
    total, rows = 0, []
    for v in b:
        before = term(v) + term(v + 1)
        cnt2[v] += 1
        after = term(v) + term(v + 1)
        total += after - before
        rows.append([v, before, after, after - before, total])
    table(["新牌 v", "改前 term(v)+term(v+1)", "改后", "增量", "总和"],
          rows, aligns=[">", ">", ">", ">", ">"])
    got = solve_f(b)
    note("答案：%s" % " ".join(map(str, got)))
    note("官方样例输出：1 2 3 2 3 2  →  %s"
         % ("一致" if got == [1, 2, 3, 2, 3, 2] else "★不一致★"))
    note("""注意第 4 步（读到第 4 张牌 2）总和反而变小了：因为 2 一来，
数字 3 的牌就能接上，原来的两个顺子并成了一个——这正是「段数合并」。""")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
