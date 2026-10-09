# -*- coding: utf-8 -*-
"""B 题验证：官方样例 + 边界 + 与「模拟挪牌」暴力对拍。"""
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
    """小紫每种数字不超过 4 张、两人合计 52 张。"""
    y = [rng.randint(0, 4) for _ in range(13)]
    x = [0] * 13
    for _ in range(52 - sum(y)):        # 剩下的牌全在小红手里
        x[rng.randrange(13)] += 1
    return " ".join(map(str, x)) + "\n" + " ".join(map(str, y)) + "\n"


EDGES = [
    # 样例 1：两人已经合法
    ("两人已经合法", "0 0 0 0 0 0 0 0 0 0 0 0 1\n"
                     "4 4 4 4 4 4 4 4 4 4 4 4 3\n", "0\n"),
    # 小紫每种 4 张、小红 0 张：已经满足「每种恰好 4 张」
    ("小紫每种 4 张、小红空手", "0 0 0 0 0 0 0 0 0 0 0 0 0\n"
                                "4 4 4 4 4 4 4 4 4 4 4 4 4\n", "0\n"),
    # 52 张全在「1」上：最终每种要 4 张，1 只要留 4 张 → 改 48 张
    ("52 张全在一种数字上", "52 0 0 0 0 0 0 0 0 0 0 0 0\n"
                            "0 0 0 0 0 0 0 0 0 0 0 0 0\n", "48\n"),
    # 小红 1 张「1」，小紫 3 张「1」+ 其余每种 4 张：正好差 1 张，不用改
    ("只差最后一张", "1 0 0 0 0 0 0 0 0 0 0 0 0\n"
                     "3 4 4 4 4 4 4 4 4 4 4 4 4\n", "0\n"),
    # 四种数字各 5 张、其余 8 种各 4 张、一种 0 张：多出的 4 张全得改
    ("四种数字各多一张", "5 5 5 5 4 4 4 4 4 4 4 4 0\n"
                         "0 0 0 0 0 0 0 0 0 0 0 0 0\n", "4\n"),
]

LIMITS = [("极限：52 张全在一种数字上", lambda: "52 " + "0 " * 12 + "\n" + "0 " * 13 + "\n")]

if __name__ == "__main__":
    main(solution="b.cpp", brute="b_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500)
