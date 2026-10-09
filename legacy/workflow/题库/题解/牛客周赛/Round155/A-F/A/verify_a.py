# -*- coding: utf-8 -*-
"""A - 小月的奇偶灯控：清样 + 官方样例 + 边界(全部输入组合) + 极限计时。
填法照 verify.py 文档：EDGES / LIMITS。A 是三整数输入，无对拍暴力。"""
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

# 边界用例：三个开关全组合的期望输出（手算）
EDGES = [
    ("全 1 -> ON", "1 1 1\n", "ON\n"),
    ("全 0 -> OFF", "0 0 0\n", "OFF\n"),
    ("混合(奇) -> OFF", "1 0 1\n", "OFF\n"),
]

LIMITS = [
    ("极限 三数", lambda: "1 0 1\n"),
]

if __name__ == "__main__":
    main(solution="a.cpp", edges=EDGES, limits=LIMITS, workdir=HERE)
