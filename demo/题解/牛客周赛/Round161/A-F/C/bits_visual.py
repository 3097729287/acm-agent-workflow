# -*- coding: utf-8 -*-
"""C 题配图：popcount（1 的个数）和「最低位 1 在第几位」到底怎么数。

双击同目录的 run.cmd 就能看，或者在终端里跑：python bits_visual.py
"""
import os
import sys

def _tools_dir():
    """工具目录：AGENT_CP_TOOLS 环境变量优先；否则向上找含 tools/toolutil.py 的目录。"""
    p = os.environ.get("AGENT_CP_TOOLS")
    if p:
        return p
    p = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(p, "tools", "toolutil.py")):
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit("没找到仓库 tools/：把 AGENT_CP_TOOLS 环境变量指向它的绝对路径")
        p = q
    return os.path.join(p, "tools")


sys.path.insert(0, _tools_dir())
from vizgrid import banner, table, note

W = 8          # 只画低 8 位，够看清楚


def bits(v, w=W):
    """把 v 写成二进制字符串，高位在前。"""
    return "".join(str((v >> (w - 1 - i)) & 1) for i in range(w))


def pc(v):
    c = 0
    while v:
        c += v & 1
        v >>= 1
    return c


def lp(v):
    if v == 0:
        return 31                      # 题目规定：0 的最低位 1 记在第 31 位
    p = 0
    while ((v >> p) & 1) == 0:
        p += 1
    return p


def show(values, k, title):
    banner(title)
    rows = []
    for v in values:
        b = bits(v)
        rows.append((v, b, pc(v), lp(v)))
    table(["数值", "二进制（低 %d 位）" % W, "1 的个数", "最低位 1 在第几位"], rows)

    order = sorted(values, key=lambda v: (pc(v), lp(v), v))
    print()
    print("按题目三条规则排好序后：")
    table(["第几个", "数值", "1 的个数", "最低位 1 的位序"],
          [(i + 1, v, pc(v), lp(v)) for i, v in enumerate(order)])
    print()
    note("要的是第 %d 个 = %d" % (k, order[k - 1]))


def main():
    banner("第 1 部分 · 两个数怎么比：先看 1 的个数，再看最低位 1")
    show([8, 3, 4, 7, 0], 3, "样例 1：n=5，k=3")
    show([6, 5, 10, 0], 2, "样例 2：n=4，k=2")

    banner("第 2 部分 · 为什么 0 要特殊记成第 31 位")
    print("0 的二进制里一个 1 都没有，没法说「最低位的 1 在哪」。")
    print("题目把它记成 31 —— 比任何真实的最低位（最多第 30 位）都大，")
    print("意思是「0 在这一条比较里排最后」。")
    print()
    table(["数值", "1 的个数", "最低位 1 的位序", "说明"],
          [(0, 0, 31, "1 的个数最少，第一条就赢了"),
           (1, 1, 0, "1 的个数 1 个，比 0 多"),
           (2, 1, 1, "和 1 的个数相同，但最低位 1 更靠后，排在 1 后面")])
    print()
    note("所以 0 一定是全场最小的那个（除非还有别的 0，那时按数值比，全都一样）。")

    banner("第 3 部分 · 三条规则的优先级，用一组数看清楚")
    show([12, 10, 6, 3, 5, 0], 4, "第 4 个是谁？")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
