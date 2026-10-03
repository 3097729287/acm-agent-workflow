# -*- coding: utf-8 -*-
"""F 题验证：官方样例 + 边界 + 与「穷举划分」暴力对拍。"""
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


def gen(rng):
    """a_i ≤ n，允许重复；数据要小，穷举暴力才跑得动。"""
    n = rng.randint(1, 9)
    V = rng.randint(1, min(n, 5))
    return "%d\n%s\n" % (n, " ".join(str(rng.randint(1, V)) for _ in range(n)))


EDGES = [
    ("n=1 最小规模", "1\n1\n", "1\n"),
    ("三张同一个数字", "3\n2 2 2\n", "1 2 3\n"),
    # {1}→1；{1,1}→2；{1,1,2}→2；{1,1,2,2}→2
    ("两两成对", "4\n1 1 2 2\n", "1 2 2 2\n"),
    # 1 和 2 各三张 → 三个顺子 {1,2}
    ("1、2 各三张", "6\n1 2 1 2 1 2\n", "1 1 2 2 3 3\n"),
    # 1 有 2 张、3 有 2 张，都不连续 → 先各算各的，一共 4 个单张顺子
    ("两张 1、两张 3", "4\n1 3 1 3\n", "1 2 3 4\n"),
]

LIMITS = [
    ("极限：n=1e5 全同数字", lambda: "100000\n" + "1 " * 100000 + "\n"),
    ("极限：n=1e5 数字 1..n 各一次", lambda: "100000\n" +
     " ".join(str(i + 1) for i in range(100000)) + "\n"),
]

if __name__ == "__main__":
    main(solution="f.cpp", brute="f_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500)
