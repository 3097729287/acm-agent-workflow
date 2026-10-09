# -*- coding: utf-8 -*-
"""F 题配图：折半枚举（meet-in-the-middle）到底省在哪、怎么配对。

双击同目录的 run.cmd 就能看，或者在终端里跑：python mitm_visual.py
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
from vizgrid import banner, table, note


def subsets(a):
    """枚举这一半的所有子集，返回 [(选了几个, 异或值, 具体选了哪些下标)]。"""
    out = [([], 0)]
    for i, v in enumerate(a):
        out += [(s + [i], x ^ v) for s, x in out]
    return [(len(s), x, s) for s, x in out]


def name(sel):
    return "{" + ",".join("a%d" % (i + 1) for i in sel) + "}" if sel else "空集"


def pair_up(a, k, x, title):
    banner(title)
    n = len(a)
    half = n // 2
    left, right = a[:half], a[half:]
    print("筹码：%s，要选 %d 个，目标异或值 x = %d"
          % (" ".join("a%d=%d" % (i + 1, v) for i, v in enumerate(a)), k, x))
    print("折半：左半 = %s，右半 = %s"
          % (", ".join("a%d" % (i + 1) for i in range(half)) or "无",
             ", ".join("a%d" % (i + half + 1) for i in range(len(right))) or "无"))
    print()

    L = subsets(left)
    R = subsets(right)
    print("左半的 %d 个子集：" % len(L))
    table(["左半选了", "异或值", "个数"],
          [(name(s), v, c) for c, v, s in sorted(L, key=lambda t: (t[0], t[1]))])
    print()
    print("右半的 %d 个子集：" % len(R))
    table(["右半选了", "异或值", "个数"],
          [(name([i + half for i in s]), v, c)
           for c, v, s in sorted(R, key=lambda t: (t[0], t[1]))])
    print()

    rows = []
    ans = 0
    for c1, v1, s1 in L:
        c2 = k - c1
        need = v1 ^ x                      # 右半必须凑出这个异或值
        hit = sum(1 for c, v, _ in R if c == c2 and v == need)
        if hit:
            ans += hit
        rows.append((name(s1), c1, v1, c2, need, hit))
    table(["左半方案", "已选", "左异或", "右还差", "右要凑出", "配上几个"], rows)
    print()
    note("数一数最后一列：一共 %d 种配法，就是答案。" % ans)
    return ans


def main():
    banner("第 1 部分 · 为什么不能直接枚举：2^n 有多大")
    table(["n", "子集数 2^n", "能不能枚举"],
          [(n, 2 ** n, "可以" if 2 ** n <= 10 ** 7 else "不行，会超时")
           for n in (20, 26, 30, 40)])
    note("n = 40 时 2^40 ≈ 1.1 万亿，一台机器跑不完；"
         "拆成两半后每半只有 2^20 ≈ 105 万，两边各枚举一遍再配对就够快了。")

    pair_up([1, 2, 3, 0], 2, 3, "第 2 部分 · 样例 1 走一遍：n=4，k=2，x=3")
    pair_up([1, 2, 3, 4, 5], 3, 0, "第 3 部分 · 样例 2 走一遍：n=5，k=3，x=0")

    banner("第 4 部分 · 配对的依据：v1 xor v2 = x 等价于 v2 = v1 xor x")
    note("异或有个性质：两边同时再异或一个 v1，等式还成立。"
         "所以知道左半凑出 v1，右半该凑什么可以直接算出来，不用去试。")
    table(["v1", "x", "右半该凑 v1 xor x"],
          [(3, 3, 3 ^ 3), (1, 3, 1 ^ 3), (0, 3, 0 ^ 3), (7, 3, 7 ^ 3),
           (5, 3, 5 ^ 3)])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
