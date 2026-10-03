# -*- coding: utf-8 -*-
"""C 题验证：最长连续段 + 1 >= m。针对 m 远大于 n 的情况另设边界。"""
import os
import random
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


def gen(rng):
    """坐标范围压在 1..40，配合 c_brute.cpp 的暴力（它只摊开到 40）。"""
    T = rng.randint(1, 3)
    lines = [str(T)]
    for _ in range(T):
        n = rng.randint(1, 8)
        m = rng.randint(2, 10)
        coords = rng.sample(range(1, 41), n)
        lines.append("%d %d" % (n, m))
        lines.append(" ".join(str(x) for x in coords))
    return "\n".join(lines) + "\n"


EDGES = [
    # 手推：n=1,m=2，一个棋子，再放一个就能 2 连 -> YES
    ("n=1,m=2 最小规模", "1\n1 2\n5\n", "YES\n"),
    # 手推：n=1,m=1e9 永远凑不齐 -> NO
    ("m 远大于 n", "1\n3 1000000000\n1 5 9\n", "NO\n"),
    # 手推：已是 1 2 3 4，再放一个可成 5 连 -> YES
    ("已有 4 连，m=5", "1\n4 5\n1 3 4 2\n", "YES\n"),
    # 手推：1 3 5，最长连续段 1，1+1 = 2 < 3 -> NO
    ("全间隔 m=3", "1\n3 3\n1 3 5\n", "NO\n"),
    # 手推：坐标贴着上界 1e9，999999999、1000000000 已经 2 连，m=3 -> YES
    ("贴上界坐标", "1\n2 3\n999999999 1000000000\n", "YES\n"),
    # 手推：单个点、m=2 -> YES（放旁边一个）
    ("单点 m=2", "1\n1 2\n1000000000\n", "YES\n"),
]

LIMITS = [
    ("极限 n=2e5 一整段连续", lambda: "1\n200000 200000\n" +
     " ".join(str(i) for i in range(1, 200001)) + "\n"),
    ("极限 n=2e5 坐标打散", lambda: "1\n200000 2\n" +
     " ".join(str(1000000000 - 3 * i) for i in range(200000)) + "\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "c.cpp"),
         brute=os.path.join(HERE, "c_brute.cpp"), gen=gen,
         edges=EDGES, limits=LIMITS, rounds=400)
