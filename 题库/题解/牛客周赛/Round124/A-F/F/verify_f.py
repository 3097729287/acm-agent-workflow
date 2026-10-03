# -*- coding: utf-8 -*-
"""F 题验证：圆上不交线配对的最小代价。

暴力 f_brute.cpp 是「枚举全部完美匹配 + 两两判线段相交」，正解是「栈判存在 + 圆上区间 DP」，
两种完全不同的实现范式。
"""
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
    T = rng.randint(1, 2)
    lines = [str(T)]
    for _ in range(T):
        n = rng.randrange(2, 13, 2)             # 偶数，暴力才对得动
        k = rng.randint(1, 3)                   # 字母表大小：1~3 种字母
        s = "".join(rng.choice("abc"[:k]) for _ in range(n))
        a = [rng.randint(1, 20) for _ in range(n)]
        lines.append(str(n))
        lines.append(s)
        lines.append(" ".join(str(x) for x in a))
    return "\n".join(lines) + "\n"


EDGES = [
    # 手推：两个同字母点，唯一连线不相交 -> 1*1 = 1
    ("n=2 最小规模", "1\n2\naa\n1 1\n", "1\n"),
    # 手推：n=1 奇数个点，配不了 -> -1
    ("n=1 无解", "1\n1\na\n5\n", "-1\n"),
    # 手推：n=3 奇数 -> -1
    ("n=3 奇数", "1\n3\naab\n1 2 3\n", "-1\n"),
    # 手推：aabb 只有 (0,1)(2,3) 一种配法，代价 1*2+3*4 = 14（官方样例 1）
    # 而 aaabbb 呢？先看 "abb a" 不行 —— 用栈判：(a,a) 消掉剩 abbb -> (b,b) -> (a,b) 剩 ab 非空
    # 所以 aaabbb 无解，期望 -1
    ("aaabbb 无解", "1\n6\naaabbb\n1 1 1 1 1 1\n", "-1\n"),
    # 手推：abab 只有 (0,2)(1,3)，两条线段交叉 -> -1（官方样例 2）
    # 手推：aaaa 可配 (0,3)(1,2) 代价 4+6=10，或 (0,1)(2,3) 代价 2+12=14，取 10（官方样例 3）
    # 手推：abba，只有 (0,3)(1,2)：代价 2*3 + 5*7 = 41
    ("abba 嵌套", "1\n4\nabba\n2 5 7 3\n", "41\n"),
    # 手推：ababab 三个 a 三个 b 都是奇数个 -> 栈消不掉 -> -1
    ("ababab 无解", "1\n6\nababab\n3 1 4 1 5 9\n", "-1\n"),
]

LIMITS = [
    ("极限 n=500 全同字母", lambda: "1\n500\n" + "a" * 500 + "\n" +
     " ".join(str(1000000 - i) for i in range(500)) + "\n"),
    ("极限 n=500 两字母交替", lambda: "1\n500\n" + "ab" * 250 + "\n" +
     " ".join("1000000" for _ in range(500)) + "\n"),
]

if __name__ == "__main__":
    main(solution=os.path.join(HERE, "f.cpp"),
         brute=os.path.join(HERE, "f_brute.cpp"), gen=gen,
         edges=EDGES, limits=LIMITS, rounds=300)
