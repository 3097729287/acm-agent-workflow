# -*- coding: utf-8 -*-
"""A 题验证：只有比大小，跑样例 + 边界即可（无对拍对象，也没必要）。"""
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

HERE = os.path.dirname(os.path.abspath(__file__))   # 用脚本自身目录拼绝对路径，
                                                    # 不靠 cwd（verify.py 拿到的
                                                    # workdir 是 cwd，不是脚本目录）

EDGES = [
    # 手推：1 1 -> 平局；100 100 -> 平局；1 100 -> Bob 多；100 1 -> Alice 多
    ("x=y=1 平局", "1 1\n", "Draw\n"),
    ("x=y=100 平局", "100 100\n", "Draw\n"),
    ("最小值 x=1,y=100", "1 100\n", "Bob\n"),
    ("最大值 x=100,y=1", "100 1\n", "Alice\n"),
]

LIMITS = [
    ("极限 单组最大值", lambda: "100 100\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "a.cpp"), edges=EDGES, limits=LIMITS)
