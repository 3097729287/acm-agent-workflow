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
    n = rng.randint(0, 10)
    c0 = rng.choice("ab")
    line = "%d %c\n" % (n, c0)
    if n > 0:
        line += " ".join(rng.choice("ab") for _ in range(n)) + "\n"
    return line


EDGES = [
    ("n=0", "0 z\n", "0\n"),
    ("n=1 c1==c0 -> aaa", "1 a\na\n", "2\n"),
    ("n=1 c1!=c0 -> aba", "1 a\nb\n", "0\n"),
    ("n=2 a,a,b -> aaabaaa", "2 a\na b\n", "4\n"),
    ("官方样例1", "3 a\na b a\n", "10\n"),
    ("n=60 全等于 c0 -> 2^61-2", "60 a\n" + "a " * 59 + "a\n", "2305843009213693950\n"),
]

LIMITS = [
    ("极限 n=60 交替", lambda: "60 a\n" + " ".join("ab"[i % 2] for i in range(60)) + "\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "d.cpp"), brute=os.path.join(HERE, "d_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=500)
