# -*- coding: utf-8 -*-
"""E - 小月的折月门牌：清样 + 官方样例 + 边界 + 随机对拍(e_brute.cpp 不同范式) + 极限计时。
填法照 verify.py 文档：gen / EDGES / LIMITS，brute 指向上面那份全枚举暴力。"""
import os, sys, random

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
from verify import main

HERE = os.path.dirname(os.path.abspath(__file__))


def gen(rng, kmax=10, qmax=8):
    """随机小 k 的查询集合（k<=10 时暴力可全枚举）。"""
    k = rng.randint(1, kmax)
    q = rng.randint(1, qmax)
    N = 1 << k
    queries = []
    for _ in range(q):
        l = rng.randint(1, N)
        r = rng.randint(1, N)
        if l > r:
            l, r = r, l
        h = rng.randint(0, k)
        zmax = (1 << h)
        z = rng.randint(0, zmax - 1) if zmax > 1 else 0
        queries.append((l, r, h, z))
    return "%d %d\n" % (k, q) + "\n".join("%d %d %d %d" % qy for qy in queries) + "\n"


# 边界用例：k=1 时门牌号 c_x ∈ {0,1}；整区间 h=0（模 1 恒为 0）应数出全部 x
EDGES = [
    ("k=1 整区间 h=0", "1 1\n1 2 0 0\n", "2\n"),
]


def _limit_input():
    """极限计时用例：k=60, q=2e5 随机查询（喂给正解，不喂暴力）。"""
    rng = random.Random(9)
    k, q = 60, 200000
    N = 1 << k
    qs = []
    for _ in range(q):
        l = rng.randint(1, N)
        r = rng.randint(1, N)
        if l > r:
            l, r = r, l
        h = rng.randint(0, k)
        z = rng.randint(0, (1 << h) - 1) if h else 0
        qs.append((l, r, h, z))
    return "%d %d\n" % (k, q) + "\n".join("%d %d %d %d" % qy for qy in qs) + "\n"


LIMITS = [
    ("极限 k=60 q=2e5", _limit_input),
]


if __name__ == "__main__":
    main(solution="e.cpp", brute="e_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=400, seed=155, workdir=HERE)
