# -*- coding: utf-8 -*-
"""E 题验证：官方样例 + 边界 + 与「每步重排序重扫」暴力对拍。"""
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
    """题目保证数字互不相同，且 a_i ≤ n → 生成 1..n 的一个随机排列。"""
    n = rng.randint(1, 8)
    p = list(range(1, n + 1))
    rng.shuffle(p)
    return "%d\n%s\n" % (n, " ".join(map(str, p)))


EDGES = [
    ("n=1 最小规模", "1\n1\n", "1\n"),
    ("已经是连续的一段", "3\n1 2 3\n", "1 1 1\n"),
    # 倒着读进来也一样：3 先来、接着 2 和 3 相邻 → 第二张就并成一段
    ("完全逆序", "3\n3 2 1\n", "1 1 1\n"),
    # {1}→1；{1,3}→2；{1,3,5}→3；{1,2,3,5}→2；全部→1
    ("奇数先来、偶数后补", "5\n1 3 5 2 4\n", "1 2 3 2 1\n"),
    # {2}→1；{2,4}→2；{2,3,4}→1；全部→1
    ("中间空一格", "4\n2 4 3 1\n", "1 2 1 1\n"),
    # {1}→1；{1,5}→2；{1,2,5}→2；{1,2,4,5}→2；全部→1
    ("先各成一段再合并", "5\n1 5 2 4 3\n", "1 2 2 2 1\n"),
]

LIMITS = [
    ("极限：n=1e5 顺序排列", lambda: "100000\n" +
     " ".join(str(i + 1) for i in range(100000)) + "\n"),
    ("极限：n=1e5 倒序排列", lambda: "100000\n" +
     " ".join(str(100000 - i) for i in range(100000)) + "\n"),
]

if __name__ == "__main__":
    main(solution="e.cpp", brute="e_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500)
