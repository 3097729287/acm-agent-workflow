# -*- coding: utf-8 -*-
"""
st_visual.py —— E 题「稀疏表（ST 表）」的可跑字符画
====================================================
双击同目录的 run.cmd 就能看。画三件事：

  1. 一个 8 个数的排列，它的稀疏表每一层长什么样
  2. 查 [2,7] 的最大值时，为什么拿「两块长 4 的区间」拼起来就够
  3. 稀疏表的内存/预处理量是多少（给个具体数字）

所有数字都是脚本自己算出来的，不是写死的。
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
from vizgrid import Grid, banner, note, pad, table

A = [0, 4, 2, 7, 1, 8, 3, 6, 5]      # 1-based，1..8 的一个排列
N = 8


def build(a, n):
    """搭稀疏表：st[k][i] = 从 i 开始、长 2^k 这一段的最大值"""
    st = [[0] * (n + 2) for _ in range(n.bit_length() + 1)]
    for i in range(1, n + 1):
        st[0][i] = a[i]
    for k in range(1, len(st)):
        for i in range(1, n - (1 << k) + 2):
            st[k][i] = max(st[k - 1][i], st[k - 1][i + (1 << (k - 1))])
    return st


def query(st, l, r):
    k = (r - l + 1).bit_length() - 1
    return max(st[k][l], st[k][r - (1 << k) + 1]), k


def index_row(n, xs=3):
    return "      " + "".join(pad(str(i), xs) for i in range(1, n + 1))


def value_row(a, n, xs=3):
    return "      " + "".join(pad(str(a[i]), xs) for i in range(1, n + 1))


def cover_rows(n, l, r):
    """把 [l,r] 的查询画成三行：目标区间 / 左半块 / 右半块"""
    k = (r - l + 1).bit_length() - 1
    half = 1 << k
    b1, e1 = l, l + half - 1
    b2, e2 = r - half + 1, r
    g = Grid(1, n, 0, 2, xs=3, ys=1)
    g.seg(l, 2, r, 2, "·")            # 想查的那一段
    g.seg(b1, 1, e1, 1, "━")          # 第一块：从 l 开始
    g.seg(b2, 0, e2, 0, "─")          # 第二块：到 r 结束
    g.put(b1, 1, "┌"); g.put(e1, 1, "┐")
    g.put(b2, 0, "└"); g.put(e2, 0, "┘")
    rows = g.text(indent="      ").split("\n")
    return rows, k, half, (b1, e1), (b2, e2)


banner("第 1 部分 · 稀疏表的每一层")

note("原始排列（下标从 1 开始）：")
print(index_row(N))
print(value_row(A, N))

st = build(A, N)
rows = []
for k in range(N.bit_length()):
    cells = [str(st[k][i]) for i in range(1, N - (1 << k) + 2)]
    rows.append(["k=%d" % k, "2^%d = %d" % (k, 1 << k), "  ".join(cells)])
table(["层 k", "段长", "这一层每个起点的最大值（起点 i = 1, 2, ...）"], rows)

note("读法：第 k 层的第 i 个数 = 从 i 开始、连续 2^k 个数的最大值。")
note("第 0 层就是原数组本身（每段长 1）；上一层由下一层「左右两半取 max」得到。")

banner("第 2 部分 · 查 [2,7]：两块拼起来正好盖住")

for (l, r) in [(2, 7), (3, 3), (1, 8)]:
    val, k = query(st, l, r)
    rows, k, half, (b1, e1), (b2, e2) = cover_rows(N, l, r)
    print()
    note("查 [%d,%d]：长度 %d，取 k = floor(log2(%d)) = %d，块长 2^%d = %d"
         % (l, r, r - l + 1, r - l + 1, k, k, half))
    print(index_row(N))
    print(value_row(A, N))
    print(rows[0] + "   <- 想查的 [%d,%d]" % (l, r))          # rows 自带缩进，别再加
    print(rows[1] + "   <- 第一块 [%d,%d]，值 %d" % (b1, e1, st[k][b1]))
    print(rows[2] + "   <- 第二块 [%d,%d]，值 %d" % (b2, e2, st[k][b2]))
    note("两块可以重叠（重叠不影响 max/min），但合起来必须盖住整段："
         "%d <= %d+1" % (b2, e1))
    note("答案 = max(%d, %d) = %d" % (st[k][b1], st[k][b2], val))

banner("第 3 部分 · 代价")

note("N = %d 时：层数 = floor(log2 %d) + 1 = %d，表格大小 = %d x %d = %d 个 int"
     % (N, N, N.bit_length(), N.bit_length(), N, N.bit_length() * N))
note("N = 200000 时：层数 = %d，表格 = %d 个 int = %.1f MB，每次查询 O(1)。"
     % (200000 .bit_length(), 200000 .bit_length() * 200000,
        200000 .bit_length() * 200000 * 4 / 1024 / 1024))
note("预处理 O(N log N)，查询 O(1) —— 本题要查 O(N log N) 次（每个左端点二分两次），"
     "用「每次扫一遍求最值」的 O(N) 查询会变成 O(N^2)，2e5 直接超时。")
