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
SMALL = [0, 1, 2, 3, 4, 7, 8, 10, 12, 15, 16, 31]


def gen(rng):
    n = rng.randint(1, 10)
    k = rng.randint(1, n)
    a = [rng.choice(SMALL) for _ in range(n)]
    return "%d %d\n%s" % (n, k, " ".join(map(str, a)))


EDGES = [
    ("n=1 k=1",              "1 1\n0",          "0"),
    ("全是 0",               "3 2\n0 0 0",      "0"),
    ("k=n 取最后一个",        "3 3\n8 4 3",      "3"),
    ("0 排在最前（1 的个数 0）", "2 1\n1 0",       "0"),
    ("同个数同低位比数值",     "2 2\n3 5",        "5"),
    ("全是相同元素",          "3 1\n7 7 7",      "7"),
    ("个数相同时比最低位 1",   "2 1\n2 1",        "1"),
]

_r = random.Random(20261001)
LIMITS = [
    ("极限 n=2e5 随机数",
     lambda: "200000 100000\n" + " ".join(
         str(_r.randint(0, (1 << 31) - 1)) for _ in range(200000))),
    ("极限 n=2e5 全是 0",
     lambda: "200000 1\n" + " ".join("0" for _ in range(200000))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "c.cpp"),
         brute=os.path.join(HERE, "c_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=500)
