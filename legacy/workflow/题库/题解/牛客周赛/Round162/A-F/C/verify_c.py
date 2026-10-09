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
    n = rng.randint(1, 8)
    m = rng.choice([1, 2, 3, 7, 9, 11, 13, 37, 100, 999999937])
    s = "".join(rng.choice("0123456789") for _ in range(n))
    return "%d %d\n%s\n" % (n, m, s)


EDGES = [
    ("n=1,m=1 任何 x 都行", "1 1\n0\n", "10\n"),
    ("n=1,m=7,s=0 -> x=0 或 7", "1 7\n0\n", "2\n"),
    ("n=1,m=10,s=5 -> 只有 x=5", "1 10\n5\n", "1\n"),
    ("n=3,m=2,s=000 -> 111x 为偶即 x 偶", "3 2\n000\n", "5\n"),
    ("官方样例1", "2 7\n19\n", "1\n"),
    ("官方样例2", "2 11\n99\n", "10\n"),
]

LIMITS = [
    ("极限 n=2e5, m=1e9",
     lambda: "200000 1000000000\n" + "".join(random.choice("0123456789")
                                             for _ in range(200000)) + "\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "c.cpp"), brute=os.path.join(HERE, "c_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=600)
