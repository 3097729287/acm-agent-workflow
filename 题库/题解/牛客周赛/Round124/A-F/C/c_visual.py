# -*- coding: utf-8 -*-
"""C 题 夜揽星河入梦 —— 连续段合并的字符画演示。

跑法：双击同目录的 run.cmd，或 `python c_visual.py`。
图中每一行都是脚本实跑输出，可以直接贴进题解。
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
from vizgrid import banner, table  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def board(tag, pieces, m, extra=None, lo=1, hi=9):
    """画 [lo, hi] 这一段棋盘：有棋子就标 ●，空格标 ·，新落的子标 ◎。"""
    cells = []
    for x in range(lo, hi + 1):
        if extra is not None and x == extra:
            cells.append("◎")
        elif x in pieces:
            cells.append("●")
        else:
            cells.append("·")
    line = " ".join(cells)
    ruler = " ".join(str(x % 10) for x in range(lo, hi + 1))
    print("  %s（m = %d）" % (tag, m))
    print("    坐标 " + ruler)
    print("    棋盘 " + line)
    print()


def longest(pieces):
    """排序后数最长连续段，并返回这一段本身。"""
    a = sorted(pieces)
    best, cur = 1, 1
    end = 0
    for i in range(1, len(a)):
        if a[i] == a[i - 1] + 1:
            cur += 1
        else:
            cur = 1
        if cur > best:
            best, end = cur, i
    return best, a[end - best + 1:end + 1]


banner("C 题 · 什么算「m 子连珠」：m 个坐标排序后是公差 1 的等差数列")

print("  题面里「等差数列」只要求公差 d 存在，并不要求 d = 1。")
print("  但 m 个棋子的坐标互不相同、又都是整数，排序后相邻两项之差 >= 1；")
print("  要让这 m 个差全都相等，那个差只能恰好是 1 —— 也就是这 m 个格子必须连着。")
print()
print("  ==> m 子连珠 <=> 存在长度 m 的一段连续整数格子，里面全是棋子。")
print()

banner("一张棋盘看明白：棋子越「挤」，越容易凑出 m 子连珠")

board("初始局面（样例 1）", {1, 2, 5}, 3)
board("同一堆棋子，换个摆法", {1, 3, 5}, 3)

print("  左边最长连续段 2（1,2），右边最长连续段只有 1。")
print("  同样 3 个棋子，摆得挤的那一堆更容易连成一片。")
print()

banner("加一个子最多能把最长连续段撑多长")

board("落子前：最长连续段 = 2", {1, 2, 5}, 3, lo=1, hi=6)
board("在 3 落子：最长连续段 = 3 -> YES", {1, 2, 5}, 3, extra=3, lo=1, hi=6)
board("在 4 落子：最长连续段 = 3 -> YES", {1, 2, 5}, 3, extra=4, lo=1, hi=6)
board("在 6 落子：左边没接上，最长连续段还是 2", {1, 2, 5}, 3, extra=6, lo=1, hi=6)

print("  一个空位只有两端都挨着已有连续段时，才把两段「焊」起来。")
print("  所以新棋子最多让最长连续段从 L 变成 L + 1（贴在段的两头之一）。")
print("  于是判据只有一条：L + 1 >= m ?")
print()

banner("几个手算例子（对着正解跑过）")

rows = [
    ["(1,2,5)  m=3", "2", "3", "YES", "在 3 落子，1 2 3 连成 3 个"],
    ["(1,2,5)  m=4", "2", "3", "NO", "最多 3 个，凑不出 4"],
    ["(1,2,3)  m=10", "3", "4", "NO", "全场只有 4 个棋子，10 连不可能"],
    ["(1,3,5)  m=2", "1", "2", "YES", "贴着一个子放，2 连立刻成立"],
    ["(1,3,5)  m=3", "1", "2", "NO", "放哪儿都是两段 1，凑不出 3"],
]
table(["棋子坐标 / m", "最长连续段 L", "L+1", "答案", "为什么"], rows)

print()
print("  注意最后一行：L + 1 >= m 用的是「最长」那一段。")
print("  哪怕棋盘上别处有 3 个棋子，只要它们不连续，L 依然只有 1。")
print()
banner("所以整题的代码只有三步")
print("  1) 读进来排序；2) 扫一遍数最长连续段 L；3) 输出 (L + 1 >= m ? YES : NO)。")
print("  复杂度：每组 O(n log n)（排序），n 之和 <= 2e5。")
print()
