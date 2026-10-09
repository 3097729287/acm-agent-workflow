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
    n = rng.randint(1, 18)
    k = rng.randint(0, n)
    if rng.random() < 0.5:                       # 小值域：容易命中非零答案
        x = rng.randint(0, 15)
        a = [rng.randint(0, 15) for _ in range(n)]
    else:                                        # 全值域
        x = rng.randint(0, (1 << 30) - 1)
        a = [rng.randint(0, (1 << 30) - 1) for _ in range(n)]
    return "%d %d %d\n%s" % (n, k, x, " ".join(map(str, a)))


EDGES = [
    ("k=0 且 x=0：只有空集",   "3 0 0\n1 2 3",   "1"),
    ("k=0 且 x!=0：无解",     "3 0 1\n1 2 3",   "0"),
    ("k=n 全选恰好等于 x",     "3 3 0\n1 2 3",   "1"),
    ("单个筹码命中",           "1 1 5\n5",       "1"),
    ("单个筹码不命中",         "1 1 5\n4",       "0"),
    ("重复数字算不同方案",     "2 2 0\n7 7",     "1"),
    ("两个筹码凑不出",         "3 2 7\n1 2 3",   "0"),
]

_r = random.Random(20261001)
LIMITS = [
    ("极限 n=40 k=20 随机数",
     lambda: "40 20 %d\n" % _r.randint(0, (1 << 30) - 1) + " ".join(
         str(_r.randint(0, (1 << 30) - 1)) for _ in range(40))),
    ("极限 n=40 全是 0，k=13",
     lambda: "40 13 0\n" + " ".join("0" for _ in range(40))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "f.cpp"),
         brute=os.path.join(HERE, "f_brute.cpp"),
         gen=gen, edges=EDGES, limits=LIMITS, rounds=300)
