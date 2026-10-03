# -*- coding: utf-8 -*-
"""B 题验证：判三个点是否等边。边界里含「等边」「共线」「退化」三类。"""
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

EDGES = [
    # 手推：(0,0)(0,1)(1,0) 三边平方 1,2,1 -> 不等边 -> NO
    ("直角三角形 -> NO", "0 0 0 1 1 0\n", "NO\n"),
    # 手推：(0,0)(2,0)(1,1) 三边平方 4,2,2 -> 不等边 -> NO（等腰非等边）
    ("等腰非等边 -> NO", "0 0 2 0 1 1\n", "NO\n"),
    # 手推：等边三角形要无理数边长，整点做不到；这组是"几乎等边"的反例
    ("几乎等边 -> NO", "0 0 1000000 0 500000 866025\n", "NO\n"),
    # 手推：三点重合，三边平方都是 0。要不是正解里单独加了 ab > 0，这组会被误判成 YES ——
    # 三个圆完全重合并不相切（相切要求有且仅有一个公共点）。期望值按题意写 NO。
    ("三点重合 -> NO", "5 5 5 5 5 5\n", "NO\n"),
    # 共线等距：(0,0)(1,0)(2,0)：三边平方 1,1,4 -> 不等边 -> NO
    ("共线等距 -> NO", "0 0 1 0 2 0\n", "NO\n"),
]

LIMITS = [
    ("极限 坐标取到 1e6", lambda: "1000000 1000000 -1000000 -1000000 1000000 -1000000\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "b.cpp"), edges=EDGES, limits=LIMITS)
