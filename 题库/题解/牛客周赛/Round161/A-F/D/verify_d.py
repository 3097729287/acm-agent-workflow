import os, random, sys
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
    n = rng.randint(1, 6)
    m = rng.randint(1, 6)
    rows = []
    for _ in range(n):
        rows.append("".join(rng.choice("01") for _ in range(m)))
    return "%d %d\n%s" % (n, m, "\n".join(rows))


EDGES = [
    ("1x1 全是 0",           "1 1\n0",              "0 0 0"),
    ("1x1 全是 1",           "1 1\n1",              "0 1 1"),
    ("2x2 全 1",             "2 2\n11\n11",         "0 4 4"),
    ("2x2 对角：四连通 2 块", "2 2\n10\n01",         "1 1 2"),
    ("3x3 全 0",             "3 3\n000\n000\n000",  "0 0 0"),
    ("十字：四连通 1 块",     "3 3\n010\n111\n010",  "0 5 5"),
]

_r = random.Random(20261001)
LIMITS = [
    ("极限 200x200 全 1",
     lambda: "200 200\n" + "\n".join("1" * 200 for _ in range(200))),
    ("极限 200x200 棋盘（块最多）",
     lambda: "200 200\n" + "\n".join(
         "".join("1" if (i + j) % 2 == 0 else "0" for j in range(200))
         for i in range(200))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "d.cpp"),
         brute=os.path.join(HERE, "d_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=300)
