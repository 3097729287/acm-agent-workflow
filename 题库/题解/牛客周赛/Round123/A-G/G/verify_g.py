# -*- coding: utf-8 -*-
"""G 题验证：官方样例 + 边界 + 极限计时。

注意：G 题是 Special Judge（方案不唯一），**不能拿暴力直接比输出**，
所以这里不给 --brute；随机对拍由同目录的 stress_g.py 负责——
它用 Python 检查器逐条验证方案合法性，并和 g_brute.cpp 的最优值比对。
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
from verify import main


def gen(rng):
    """小数据：n 小、值域小，方便 stress_g.py 里的暴力枚举。"""
    n = rng.randint(1, 7)
    V = rng.randint(1, 12)
    return "%d\n%s\n" % (n, " ".join(str(rng.randint(1, V)) for _ in range(n)))


EDGES = [
    # n=1：本来就满足「单独一张也是顺子」→ 0 次
    ("n=1 单张已是顺子", "1\n7\n", "0\n"),
    # 三张同数：保留一张 5，目标区间 [3,5]，把第 2、3 张改成 3、4
    ("三张同一个数字", "3\n5 5 5\n", "2\n2 3\n3 4\n"),
    ("已经连续", "3\n10 11 12\n", "0\n"),
    # 两张同数：目标区间 [3,4]，保留第 1 张，把第 2 张改成 3
    ("两张同一个数字", "2\n4 4\n", "1\n2 3\n"),
    # 1 和 10：只能保留 1 张，另一张填进 [1,2] 的空位 2
    ("两个数字差很远", "2\n1 10\n", "1\n2 2\n"),
]

LIMITS = [
    ("极限：n=2e5 全同数字", lambda: "200000\n" + "1000000000 " * 200000 + "\n"),
    ("极限：n=2e5 恰好是连续一段", lambda: "200000\n" +
     " ".join(str(i + 1) for i in range(200000)) + "\n"),
]

if __name__ == "__main__":
    main(solution="g.cpp", gen=gen, edges=EDGES, limits=LIMITS)
