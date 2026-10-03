# -*- coding: utf-8 -*-
"""F 题 竹摇清风拂面 —— 圆周不交线配对的字符画演示（含「切口」那一张）。

跑法：双击同目录的 run.cmd，或 `python f_visual.py`。
"""
import math
import os
import sys
from itertools import combinations, permutations

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
from vizgrid import Grid, banner, table  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

R = 5.0


def point_pos(n, i):
    """第 i 个点放在圆周上，i 按顺时针排。"""
    ang = math.radians(90.0 - 360.0 * i / n)
    return (R * math.cos(ang), R * math.sin(ang))


def draw(n, s, pairs, title, cut=None, note=None):
    """画圆周 + 连线。pairs 是 [(i,j), ...]；cut=k 表示把第 k 条弧（k -> k+1）剪开。"""
    g = Grid(-6, 6, -6, 6, xs=2, ys=1)      # 画布边界贴着半径 5 的圆（Grid 按整数算尺寸）
    # 圆周（逐格步进的折线）
    prev = None
    for k in range(73):
        ang = math.radians(90.0 - 360.0 * k / 72)
        x, y = R * math.cos(ang), R * math.sin(ang)
        if prev is not None:
            g.seg(prev[0], prev[1], x, y, "·")
        prev = (x, y)
    # 连线
    for (i, j) in pairs:
        x1, y1 = point_pos(n, i)
        x2, y2 = point_pos(n, j)
        g.seg(x1, y1, x2, y2, "*")
    # 剪开的那条弧用 ':' 标出来
    if cut is not None:
        a, b = cut, (cut + 1) % n
        x1, y1 = point_pos(n, a)
        x2, y2 = point_pos(n, b)
        g.seg(x1, y1, x2, y2, ":")
    # 点本身
    for i in range(n):
        x, y = point_pos(n, i)
        g.put(x, y, s[i])
    print("  %s" % title)
    print(g.text(indent="    "))
    if note:
        print("    %s" % note)
    print()


def count_cross(n, pairs):
    """数交叉对数（圆周上的真交叉：四个端点交错）。"""

    def in_arc(a, b, x):
        return (a < x < b) if a < b else (x > a or x < b)

    cnt = 0
    for (i, j), (k, l) in combinations(pairs, 2):
        c1, c2 = in_arc(i, j, k), in_arc(i, j, l)
        c3, c4 = in_arc(k, l, i), in_arc(k, l, j)
        if c1 != c2 and c3 != c4:
            cnt += 1
    return cnt


def brute_min(n, s, a):
    """枚举全部完美匹配，取「只连同字母 + 互不相交」里的最小代价。"""
    best = None
    for perm in permutations(range(n)):
        if any(perm[perm[i]] != i for i in range(n)):
            continue
        pairs = sorted({(min(i, perm[i]), max(i, perm[i])) for i in range(n)})
        if len(pairs) * 2 != n:
            continue
        if any(s[i] != s[j] for i, j in pairs):
            continue
        if count_cross(n, pairs):
            continue
        cost = sum(a[i] * a[j] for i, j in pairs)
        if best is None or cost < best:
            best = cost
    return best


banner("F 题 · 圆周上的配对：线段不许相交")

print("  n 个字符按顺时针放在圆周上，每个点恰好连一条线段，")
print("  而且只能连同字母的点。问所有「线段互不相交」的连法里，代价最小是多少。")
print()

print("  官方的三个样例（n = 4）：")
print()
draw(4, "aabb", [(0, 1), (2, 3)], "① s = aabb：(0,1) + (2,3)，不相交",
     note="交叉 0 对，代价 = 1*2 + 3*4 = 14 -> 样例答案 14")
draw(4, "abab", [(0, 2), (1, 3)], "② s = abab：(0,2) + (1,3)，交叉",
     note="交叉 1 对 -> 不合法，样例答案 -1")
draw(4, "aaaa", [(0, 3), (1, 2)], "③ s = aaaa：(0,3) + (1,2)，嵌套不相交",
     note="代价 = 1*4 + 2*3 = 10 -> 比 (0,1)+(2,3) 的 14 更小，取 10")

banner("第一步：判「到底有没有解」—— 栈消除")

print("  把圆周从某处剪开摊成一排，一段不相交的连线就是一对括号：")
print("      (i,j) 里面必须是另一组完整的、能配完的点；(i,j) 外面同理；")
print("      两个端点相邻时，正好就是「删掉两个相邻且相同的字符」。")
print("  于是：存在不相交完美匹配 <=> 这个字符串能反复删掉「相邻且相同」的字符变空。")
print()
rows = []
for s in ["aabb", "abab", "aaaa", "abba", "aaabbb", "aabbaa", "abcabc"]:
    stk = []
    for ch in s:
        if stk and stk[-1] == ch:
            stk.pop()
        else:
            stk.append(ch)
    rows.append([s, ("".join(stk) if stk else "（空）"), "有解" if not stk else "无解"])
table(["字符串", "栈消完剩下", "不相交连法"], rows)
print()
print("  abab 消完剩 ab（无解），aabb 消完是空的（有解）。这一步 O(n)。")
print()

banner("第二步：切口 —— 圆上的最优解总能被某条「没有线跨过」的弧剪开")

print("  把圆周在弧 k -> k+1 处剪开摊平。如果没有任何一条线段「跨过」这条弧，")
print("  那么摊平之后所有线段都变成数轴上的普通区间，区间 DP 就能直接用了。")
print()
draw(4, "aaaa", [(0, 3), (1, 2)], "s = aaaa，连法 (0,3) + (1,2)：弧 0->1 被冒号标出",
     cut=0, note="看这条弧：没有任何线跨过它 -> 在 0 和 1 之间剪开摊平即可")
print("  这个例子说明为什么不能只试一个切口：不同的切口下，「跨过切口的线」不一样，")
print("  摊平后能表示的连法也不一样。稳妥做法是把字符串复制成两倍，")
print("  对 n 个切口各做一遍 DP，取最小值 —— n <= 500，全试也很快。")
print()

banner("第三步：区间 DP 的转移")

print("      dp[l][r] = 把这一段点两两配完、线段互不相交的最小代价")
print("      l 一定和某个 j 配对：")
print("        ① j 在段内：a[l]*a[j] + dp[l+1][j-1] + dp[j+1][r]")
print("        ② j 在段外（双倍串里 j > r）：a[l]*a[j] + dp[l+1][r]")
print("      奇长度 -> 无解；空区间 -> 0")
print()
a = [1, 2, 3, 4]
print("  拿 aaaa、a = [1,2,3,4] 实跑（正解输出）：")
print("      (0,1)+(2,3) -> 1*2 + 3*4 = 14")
print("      (0,3)+(1,2) -> 1*4 + 2*3 = 10   <- 最小")
print("      答案 10")
print()

banner("易错点：判交别用「数轴上的开区间」")

print("  圆周上 (i,j) 与 (k,l) 相交 <=> 四个端点按 i k j l 或 i l j k 交错。")
print("  本目录 f_brute.cpp 一开始把它写成数轴开区间判交 (i-k)*(i-l) < 0，")
print("  结果把「共享端点 / 相邻」的线段误判成交叉，对拍时两边才开始不一致。")
print("  正确写法在 f_brute.cpp 的 cross()：两个方向都交错才算相交。")
print()
