# -*- coding: utf-8 -*-
"""E 可视化：k=4 时 c_x 如何由 x 变出，以及查询的「高位翻转」归约。"""
import os, sys
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
from vizgrid import table, part, note

def gray(t): return t ^ (t >> 1)
def rev_bits(z, h):
    w = 0
    for i in range(h):
        if (z >> i) & 1: w |= 1 << (h - 1 - i)
    return w

k = 4
part(1, 2, "k=4：c_x 的生成过程（x 从 1 到 16）")
rows = []
for x in range(1, 1 << k):
    t = x - 1
    mid = gray(t)
    s = format(mid, "0%db" % k)
    cs = s[::-1]
    rows.append([x, t, s, cs, int(cs, 2)])
table(["x", "t=x-1", "G(t) 二进制", "翻转后二进制", "c_x"], rows)
note("注意 c_x 序列：0,8,12,4,6,14,10,2,3,11,15,7,5,13,9,1，正好就是样例给出的那串。")

part(2, 2, "查询归约：c_x mod 2^h == z  ⟺  G(t) 的高 h 位翻转后 == z")
note("翻转是「按位镜像」，所以等价于：G(t) 的高 h 位 == reverse_h(z)。")
note("例：查询 [3,14], h=2, z=2 → reverse_h(2,2)=1 → 要 G(t)∈[4,8)。")
rows2 = []
for x in range(3, 15):
    t = x - 1
    g = gray(t)
    rng = 4 <= g < 8
    rows2.append([x, t, format(g, "04b"), "是" if rng else "否"])
table(["x", "t", "G(t)", "落入 [4,8)?"], rows2)
note("共 4 个「是」→ 答案 4，与样例输出一致。于是问题变成：")
note("t∈[l-1,r) 且 G(t)∈[lo,hi) 的计数，用 Gray 码的递归结构 O(k) 算一档。")
