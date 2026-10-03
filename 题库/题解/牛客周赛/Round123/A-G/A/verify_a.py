# -*- coding: utf-8 -*-
"""A 题验证（签到题：只跑官方样例 + 边界，不做对拍）。"""
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

EDGES = [
    ("同点数 A > B", "1 A\n1 B\n", "Yes\n"),
    ("同点数 B < A", "1 B\n1 A\n", "No\n"),
    ("同点数 D < C", "5 D\n5 C\n", "No\n"),
    ("同点数 A > D", "100 A\n100 D\n", "Yes\n"),
    ("点数大者胜（花色更小）", "1 D\n2 A\n", "No\n"),
    ("点数大者胜（花色更大）", "100 D\n99 A\n", "Yes\n"),
    ("最小牌 1A vs 1D", "1 A\n1 D\n", "Yes\n"),
]

LIMITS = [
    ("极限：点数取上下界", lambda: "100 A\n1 D\n"),
]

if __name__ == "__main__":
    main(solution="a.cpp", edges=EDGES, limits=LIMITS)
