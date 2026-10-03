# -*- coding: utf-8 -*-
"""C 题验证：官方样例（构造方案与样例输出逐字一致）+ 边界 + 与枚举子集暴力对拍。"""
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
    """小数据：牌数少、数字值域小，这样暴力才有意义。"""
    n = rng.randint(1, 10)
    V = rng.randint(1, 4)
    lines = [str(n)]
    for _ in range(n):
        lines.append("%d %s" % (rng.randint(1, V), rng.choice("ABCD")))
    return "\n".join(lines) + "\n"


EDGES = [
    ("n=1 单张出不了对", "1\n1 A\n", "0\n"),
    ("只有一对", "2\n1 A\n1 B\n", "2\n1 2\n"),
    ("四张全同花色", "4\n2 A\n2 A\n2 A\n2 A\n", "0\n"),
    ("四花色齐全", "4\n5 A\n5 B\n5 C\n5 D\n", "4\n1 2\n3 4\n"),
    ("三个花色只出一对", "3\n7 A\n7 B\n7 A\n", "2\n1 2\n"),
    ("两个数字各三花色", "6\n1 A\n1 B\n1 C\n2 A\n2 B\n2 C\n", "4\n1 2\n4 5\n"),
]

# 极限 1：n=2e5 全是一个数字、四花色循环 → 正好打出 4 张
LIMITS = [
    ("极限：2e5 张全同数字四花色", lambda: "200000\n" +
     "\n".join("1 %s" % "ABCD"[i % 4] for i in range(200000)) + "\n"),
    ("极限：2e5 张、2e5 个数字各四花色", lambda: "200000\n" +
     "\n".join("%d %s" % (i // 4 + 1, "ABCD"[i % 4]) for i in range(200000)) + "\n"),
]

if __name__ == "__main__":
    main(solution="c.cpp", brute="c_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500)
