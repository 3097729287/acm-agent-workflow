import os
import random
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
    """随机一棵 n<=10 的树 + 随机染色（暴力枚举 2^n 个子集，n 必须小）"""
    n = rng.randint(1, 10)
    perm = list(range(1, n + 1))
    rng.shuffle(perm)                       # 随机 Prufer 式挂法：每个点挂到一个更早的点上
    edges = []
    for i in range(1, n):
        j = perm[rng.randint(0, i - 1)]
        edges.append((perm[i], j))
    col = "".join(rng.choice("RB") for _ in range(n))
    return "%d\n%s\n%s\n" % (n, col, "".join("%d %d\n" % e for e in edges))


EDGES = [
    ("n=1 单点", "1\nR\n", "1\n"),
    ("n=2 同色 -> 删 1 个即可", "2\nRR\n1 2\n", "1\n"),
    ("n=2 异色 -> 删任一端", "2\nRB\n1 2\n", "1\n"),
    ("官方样例1 链 RBRBR", "5\nRBRBR\n1 2\n2 3\n3 4\n4 5\n", "3\n"),
    ("官方样例2 全红星", "3\nRRR\n1 2\n1 3\n", "1\n"),
    ("官方样例3 链 RRRBBB", "6\nRRRBBB\n1 2\n2 3\n3 4\n4 5\n5 6\n", "1\n"),
]

LIMITS = [
    ("极限 n=2e5 链、颜色交替", lambda: "200000\n" + "RB" * 100000 + "\n"
        + "".join("%d %d\n" % (i, i + 1) for i in range(1, 200000))),
    ("极限 n=2e5 链、全同色", lambda: "200000\n" + "R" * 200000 + "\n"
        + "".join("%d %d\n" % (i, i + 1) for i in range(1, 200000))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "f.cpp"), brute=os.path.join(HERE, "f_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=400)
