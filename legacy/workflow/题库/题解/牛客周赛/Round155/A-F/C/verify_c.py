# -*- coding: utf-8 -*-
"""C - 小月的密码锁：清样 + 官方样例 + 边界(n=1) + 极限计时(n=1000 随机)。
填法照 verify.py 文档：EDGES / LIMITS。"""
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

EDGES = [
    ("n=1 A/B -> 0(整串用 q 偏移即可匹配)", "1\nA\nB\n", "0\n"),
]

def _limit_input():
    rng = random.Random(155)
    n = 1000
    s = "".join(rng.choice("ABCDE") for _ in range(n))
    t = "".join(rng.choice("ABCDE") for _ in range(n))
    return "%d\n%s\n%s\n" % (n, s, t)

LIMITS = [
    ("极限 n=1000 随机", _limit_input),
]

if __name__ == "__main__":
    main(solution="c.cpp", edges=EDGES, limits=LIMITS, workdir=HERE)
