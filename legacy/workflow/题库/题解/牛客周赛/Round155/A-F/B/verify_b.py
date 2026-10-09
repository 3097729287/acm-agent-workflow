# -*- coding: utf-8 -*-
"""B - 小月的立方体：清样 + 官方样例 + 边界(a=1 全 0) + 极限计时(a=100 全 1)。
填法照 verify.py 文档：EDGES / LIMITS。"""
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

EDGES = [
    ("a=1 全 0 -> 0", "1\n0 0\n0 0\n0 0\n0 0\n", "0\n"),
]

def _limit_input():
    a = 100
    lines = [str(a)]
    for _ in range((a + 1) * (a + 1)):
        lines.append(" ".join(["1"] * (a + 1)))
    return "\n".join(lines) + "\n"

LIMITS = [
    ("极限 a=100 全 1", _limit_input),
]

if __name__ == "__main__":
    main(solution="b.cpp", edges=EDGES, limits=LIMITS, workdir=HERE)
