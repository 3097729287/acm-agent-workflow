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
from verify import main

HERE = os.path.dirname(os.path.abspath(__file__))


def gen(rng):
    t = rng.randint(1, 4)
    lines = ["%d" % t]
    for _ in range(t):
        n = rng.randint(1, 8)
        m = rng.randint(1, 8)
        lines.append("%d %d %d %d" % (n, m, rng.randint(1, n), rng.randint(1, m)))
    return "\n".join(lines) + "\n"


EDGES = [
    ("n=1,m=1 只剩一格也被抽走", "1\n1 1 1 1\n", "0\n"),
    ("n=1 整行抽走", "1\n1 5 1 3\n", "0\n"),
    ("m=1 整列抽走", "1\n5 1 3 1\n", "0\n"),
    ("2x2 抽左上角", "1\n2 2 1 1\n", "4\n"),
    ("2x3 抽(1,2) 剩两个孤立格", "1\n2 3 1 2\n", "8\n"),
    ("3x3 抽正中（官方样例1）", "1\n3 3 2 2\n", "16\n"),
]

LIMITS = [
    ("极限 T=1000 组 14x14", lambda: "1000\n" + "14 14 7 7\n" * 1000),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "b.cpp"), brute=os.path.join(HERE, "b_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=400)
