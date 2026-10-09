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
    return "%d\n" % rng.randint(1, 100)


EDGES = [
    ("n=1 最小规模", "1\n", "2\n"),
    ("n=2", "2\n", "3\n"),
    ("n=100 最大规模", "100\n", "101\n"),
]

LIMITS = [
    ("极限 n=100", lambda: "100\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "a.cpp"), gen=gen,
         edges=EDGES, limits=LIMITS, rounds=0)
