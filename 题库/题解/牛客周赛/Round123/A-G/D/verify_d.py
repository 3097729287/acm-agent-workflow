# -*- coding: utf-8 -*-
"""D 题验证：官方样例 + 边界 + 与「枚举 10 张可重集合」暴力对拍。"""
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
    """小数据：牌数 ≤ 13、点数种数 ≤ 4，暴力才跑得动。"""
    n = rng.randint(1, 13)
    V = rng.randint(1, 4)
    return "%d\n%s\n" % (n, " ".join(str(rng.randint(1, V)) for _ in range(n)))


EDGES = [
    ("n=1 最小规模", "1\n1\n", "0\n"),
    ("只有 9 张，凑不出 10 张", "9\n1 1 1 2 2 2 3 3 3\n", "0\n"),
    ("刚好一副飞机", "10\n1 1 1 2 2 2 3 3 4 4\n", "1\n"),
    ("只有一种数字", "10\n3 3 3 3 3 3 3 3 3 3\n", "0\n"),
    # 1、2 各 5 张：{1,1,1,2,2,2} + 两个对子只能都取 1 或都取 2 或各取一个 → 恰好 1 种
    ("两个数字各 5 张", "10\n1 1 1 1 1 2 2 2 2 2\n", "1\n"),
    # 1、2 各 3 张（凑三张），5 有 4 张（只能当两个对子）→ 1 种
    ("三张 + 四张同点对子", "10\n1 1 1 2 2 2 5 5 5 5\n", "1\n"),
    ("样例 2 的牌", "12\n1 1 1 3 3 4 4 5 5 2 2 2\n", "3\n"),
]

# 极限：4 万个数字各 5 张（每个合法的 a 都能配出大量对子，答案要取模）
LIMITS = [
    ("极限：4 万种数字各 5 张", lambda: "200000\n" +
     " ".join(str(i // 5 + 1) for i in range(200000)) + "\n"),
    ("极限：2e5 张全同数字", lambda: "200000\n" + "1 " * 200000 + "\n"),
]

if __name__ == "__main__":
    main(solution="d.cpp", brute="d_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500)
