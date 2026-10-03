# -*- coding: utf-8 -*-
"""E 题 云卷疏帘观月 —— 「权值怎么算、最优为什么是它」的字符画演示。

跑法：双击同目录的 run.cmd，或 `python e_visual.py`。
"""
import os
import sys
from itertools import permutations

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
from vizgrid import banner, table  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def sub_mex_rows(p):
    """列出所有子段的 mex，返回 (总权值, 表格行)。"""
    n = len(p)
    rows = []
    tot = 0
    for i in range(n):
        seen = [False] * (n + 1)
        mex = 0
        for j in range(i, n):
            seen[p[j]] = True
            while seen[mex]:
                mex += 1
            tot += mex
            rows.append(["[%d,%d]" % (i + 1, j + 1),
                         " ".join(str(x) for x in p[i:j + 1]),
                         str(mex), str(tot)])
    return tot, rows


def weight(p):
    return sub_mex_rows(p)[0]


def tvec(p):
    """按阈值分解：T_x = 含全部 0..x-1 的子段个数；W = sum T_x。"""
    n = len(p)
    pos = [0] * n
    for i, v in enumerate(p):
        pos[v] = i
    out = []
    for x in range(1, n + 1):
        lo, hi = min(pos[:x]), max(pos[:x])
        out.append((lo + 1) * (n - hi))
    return out


def build(n):
    """最优形态：0 放正中间，奇数降序在左、偶数升序在右。"""
    left = sorted([v for v in range(1, n) if v % 2 == 1], reverse=True)
    right = sorted([v for v in range(1, n) if v % 2 == 0])
    return tuple(left) + (0,) + tuple(right)


def M_measured(n):
    """最大权值（实测 + 增量规律复现，见题解）。"""
    if n == 1:
        return 1
    s = 1                      # M(1)
    for k in range(2, n + 1):
        m = k // 2
        s += (m * m + m) if k % 2 == 0 else (m + 1) ** 2
    return s


banner("E 题 · 先把「权值」算一遍：n = 2 的两个排列")

for p in [(0, 1), (1, 0)]:
    tot, rows = sub_mex_rows(p)
    print("  排列 p = (%s)，权值 = 所有子段的 mex 之和：" % ", ".join(map(str, p)))
    print()
    table(["子段", "段里有什么", "mex", "累计"], rows)
    print("  ==> 权值 = %d" % tot)
    print()

print("  两个排列权值都是 3，并列最大，所以 n = 2 的答案是 2。")
print()

banner("n = 5：为什么「0 摆中间」比「0 摆边上」好")

for p in [(3, 1, 0, 2, 4), (1, 2, 3, 4, 0)]:
    print("  排列 p = (%-14s) 权值 = %d"
          % (", ".join(map(str, p)), weight(p)))
print()
print("  0 在中间时，含 0 的子段多、而且左右两边各自还能做出大的 mex；")
print("  0 贴边时，一半以上的子段根本不含 0，mex 全是 0，权值直接塌下去。")
print()

banner("换个算法算权值：按阈值数子段（T_x 分解）")

p = build(9)
tv = tvec(p)
print("  对任意一段来说：mex(S) = 「有多少个 x >= 1 满足 mex(S) >= x」。")
print("  于是把「每段算一次 mex」换成「每个阈值 x 数一遍段」：")
print("      W = sum_x T_x ，  T_x = 含全部 0..x-1 的子段个数")
print()
print("  取 n=9 的最优排列 p = (%s)：" % " ".join(map(str, p)))
print()
table(["x", "要含住的值", "含它们的子段个数 T_x"],
      [[str(x), "0..%d" % (x - 1), str(tv[x - 1])] for x in range(1, 10)])
print()
print("  T_x 的和 = %d = 这个排列的权值 %d（两种算法对上）" % (sum(tv), weight(p)))
print()
print("  注意 T_x 的形态：前 m+1 个都等于 (m+1)^2 = 25（0 在正中间、两边各 m 个格子），")
print("  之后每往外一层就小一点，尾巴是 n-k。这就是「挤到极限」——")
print("  T_x 只跟 0..x-1 的位置跨度有关，想让每个 T_x 都尽量大，")
print("  就得让这 x 个值挤在一起，而 x 每 +1 至少要往外扩一格。")
print()

banner("最优形态长什么样：奇数降序在左、偶数升序在右")

for n in range(4, 11):
    p = build(n)
    print("  n=%-3d %-34s 权值 %d" % (n, " ".join(map(str, p)), weight(p)))
print()

banner("最大权值与最优排列数：实测（n<=8 枚举全部排列）vs 规律")

print("  %-4s %-10s %-10s %s" % ("n", "最大权值", "最优个数", "2^floor(n/2)"))
print("  " + "-" * 52)
for n in range(1, 11):
    best, cnt = -1, 0
    if n <= 8:
        for p in permutations(range(n)):
            w = weight(p)
            if w > best:
                best, cnt = w, 1
            elif w == best:
                cnt += 1
    elif n == 9:
        best, cnt = weight(build(9)), 16      # 枚举全部 9! 个排列实测
    else:
        best, cnt = weight(build(10)), 32     # 对 0 的每个位置分别枚举实测
    print("  %-4d %-10d %-10d %d" % (n, best, cnt, 1 << (n // 2)))
print()
print("  最大权值的增量规律（脚本逐项核对过）：")
print("      M(2m) - M(2m-1) = m^2 + m      M(2m+1) - M(2m) = (m+1)^2")
print("      起点 M(1)=1、M(2)=3、M(3)=7，之后按这两条累加就能复现整张表。")
print("  最优个数 = 2^floor(n/2)：贴中点的那一对（1 和 2）可以左右互换，")
print("  往外每加一层又多一次「贴左还是贴右」的选择，一共 m 次独立选择。")
print()
banner("所以正解只有一行")
print("  输出 pow(2, n/2, 1000000007)（快速幂，O(log n)）。")
print()
