import os, sys
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
    return "%d %d %d" % (rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))


EDGES = [
    ("全灭",         "0 0 0", "0"),
    ("全亮",         "1 1 1", "3"),
    ("只亮第 1 盏（0 分）", "1 0 0", "0"),
    ("只亮第 2 盏（1 分）", "0 1 0", "1"),
    ("只亮第 3 盏（2 分）", "0 0 1", "2"),
]

LIMITS = [("极限（输入只有 8 种，跑全亮）", lambda: "1 1 1")]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "a.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS)
