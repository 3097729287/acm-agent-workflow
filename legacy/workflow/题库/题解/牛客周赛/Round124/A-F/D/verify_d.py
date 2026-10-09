# -*- coding: utf-8 -*-
"""D 题验证：答案 = ceil(叶子数/2)。

公式本身已在 _work\\brute_D.py 里用「n<=7 的全部标号树 + 枚举加边多重集」暴力验证过
（0 处不一致），这里跑样例、边界与极限。
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

EDGES = [
    # 手推：n=2 一条边，两个叶子 -> ceil(2/2)=1
    ("n=2 单边", "2\n1 2\n", "1\n"),
    # 手推：n=3 链 1-2-3，两个叶子 -> 1
    ("n=3 链", "3\n1 2\n2 3\n", "1\n"),
    # 手推：n=4 星形 1 连 2/3/4，三个叶子 -> ceil(3/2)=2
    ("n=4 星形", "4\n1 2\n1 3\n1 4\n", "2\n"),
    # 手推：n=4 链 1-2-3-4，两个叶子 -> 1
    ("n=4 长链", "4\n1 2\n2 3\n3 4\n", "1\n"),
    # 手推：n=6 双星（两个中心各带两叶），4 个叶子 -> 2
    ("n=6 两个中心", "6\n1 2\n1 3\n1 4\n2 5\n2 6\n", "2\n"),
]

LIMITS = [
    ("极限 n=2e5 链", lambda: "200000\n" +
     "".join("%d %d\n" % (i, i + 1) for i in range(1, 200000))),
    ("极限 n=2e5 菊花", lambda: "200000\n" +
     "".join("1 %d\n" % i for i in range(2, 200001))),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "d.cpp"), edges=EDGES, limits=LIMITS)
