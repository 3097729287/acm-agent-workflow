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
    n = rng.randint(1, 12)
    a = [rng.randint(-5, 5) for _ in range(n)]
    return "%d\n%s" % (n, " ".join(map(str, a)))


EDGES = [
    ("n=1",                  "1\n5\n",            "1 0"),
    ("全同元素",             "4\n3 3 3 3",        "1 0"),
    ("严格递增（全是记录点）", "5\n1 2 3 4 5",      "5 1"),
    ("严格递减（只有第一个）", "4\n5 4 3 2",        "1 0"),
    ("全 0",                 "3\n0 0 0",          "1 0"),
    ("含负数：2 个记录点",    "3\n-5 -3 -4",       "2 1"),
    ("记录点间隔 3",         "5\n1 9 9 9 10",     "3 3"),
]

LIMITS = [
    ("极限 n=2e5 严格递增",
     lambda: "200000\n" + " ".join(str(i) for i in range(1, 200001))),
    ("极限 n=2e5 严格递减",
     lambda: "200000\n" + " ".join(str(200000 - i) for i in range(200000))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "b.cpp"),
         brute=os.path.join(HERE, "b_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=500)
