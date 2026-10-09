# -*- coding: utf-8 -*-
"""E 题验证：正解 = 2^floor(n/2) 的快速幂；暴力枚举全部排列（n<=9 才跑得动）。

暴力除了数个数，还会把「它自己算出来的最大权值」打到 stderr，
和正解注释里的闭式逐项对比（数对了但权值公式错了，同样是错的）。
"""
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
from verify import main  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# 实测真值（枚举全部排列 : n=1..9；对 0 的每个位置分别枚举 : n=10..11）
CNT = {1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 16, 9: 16, 10: 32, 11: 32, 12: 64}


def gen(rng):
    """n 必须 <= 9，暴力才跑得动（9! = 362880）。"""
    return "%d\n" % rng.randint(1, 9)


EDGES = [("n=%d 实测 %d 个" % (n, CNT[n]), "%d\n" % n, "%d\n" % CNT[n])
         for n in sorted(CNT)]

LIMITS = [
    ("极限 n=1e9", lambda: "1000000000\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "e.cpp"),
         brute=os.path.join(HERE, "e_brute.cpp"), gen=gen,
         edges=EDGES, limits=LIMITS, rounds=200)
