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
    n = rng.randint(1, 12)
    p = list(range(1, n + 1))
    rng.shuffle(p)
    return "%d\n%s\n" % (n, " ".join(map(str, p)))


EDGES = [
    ("n=1", "1\n1\n", "1\n"),
    ("n=2 递增 [1,2]", "2\n1 2\n", "3\n"),
    ("n=2 递减 [2,1]", "2\n2 1\n", "1\n"),
    ("官方样例1", "3\n2 1 3\n", "4\n"),
    ("官方样例2", "3\n3 2 1\n", "1\n"),
]

LIMITS = [
    ("极限 n=2e5 递增排列", lambda: "200000\n" + " ".join(map(str, range(1, 200001))) + "\n"),
    ("极限 n=2e5 递减排列", lambda: "200000\n" + " ".join(map(str, range(200000, 0, -1))) + "\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "e.cpp"), brute=os.path.join(HERE, "e_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=800)
