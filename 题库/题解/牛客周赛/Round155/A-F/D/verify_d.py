# -*- coding: utf-8 -*-
"""D - 小月的电台：清样 + 官方样例 + 边界 + 随机对拍(d_brute.cpp 不同范式) + 极限计时。
填法照 verify.py 文档：gen / EDGES / LIMITS，brute 指向上面那份不同范式的暴力。"""
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


def gen(rng, nmax=12, mmax=6):
    """随机小输入：n 台电台 + 各自长度 m 的 01 串。"""
    n = rng.randint(1, nmax)
    m = rng.randint(1, mmax)
    ss = ["".join(rng.choice("01") for _ in range(m)) for _ in range(n)]
    return "%d %d\n%s\n" % (n, m, "\n".join(ss))


# 边界用例：期望值手算推出（mask 计数法与本文件暴力两条路都校过）
EDGES = [
    ("n=1 没有电台对", "1 1\n0\n", "0\n"),
    ("两台同掩码 11 -> 1 对", "2 2\n11\n11\n", "1\n"),
    ("三台全 0 -> 0 对", "3 2\n00\n00\n00\n", "0\n"),
]


def _limit_input():
    """极限计时用例：n=2e5, m=11 随机串（喂给正解，不喂暴力）。"""
    rng = random.Random(7)
    n, m = 200000, 11
    ss = ["".join(rng.choice("01") for _ in range(m)) for _ in range(n)]
    return "%d %d\n%s\n" % (n, m, "\n".join(ss))


LIMITS = [
    ("极限 n=2e5 m=11", _limit_input),
]


if __name__ == "__main__":
    main(solution="d.cpp", brute="d_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=800, seed=155, workdir=HERE)
