# -*- coding: utf-8 -*-
r"""E - 小月的路线：官方样例 + 手算边界 + 随机对拍（e_brute.cpp Bellman-Ford）+ 极限计时。

    python verify_e.py

对拍基准是 `e_brute.cpp`（Bellman-Ford 反复松弛）：和主解「Dijkstra + 优先队列」
是两种不同范式，不算同源互拍。组数/种子写在文件末端 `main(...)` 的实参里
（第 6 步 `tools/md_full.py` 复验时会原样读到那里的 rounds / brute）。
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
    n = rng.randint(1, 8)
    m = rng.randint(0, 20) if n >= 2 else 0     # n=1 时没有合法边（u≠v），否则下面的 while 会死循环
    lines = ["%d %d" % (n, m)]
    for _ in range(m):
        u = rng.randint(1, n)
        v = rng.randint(1, n)
        while v == u:
            v = rng.randint(1, n)
        lines.append("%d %d %d %d" % (u, v, rng.randint(0, 5), rng.randint(0, 5)))
    return "\n".join(lines)


EDGES = [
    ("n=1：直接输出 0 0",      "1 0\n",                 "0 0"),
    ("n=2 且 m=0：不可达",     "2 0\n",                 "-1 -1"),
    ("有边但到不了 n",         "3 1\n1 2 1 1",          "-1 -1"),
    ("重边：距离同取风险小的",  "2 2\n1 2 3 9\n1 2 3 1",  "3 1"),
    ("零距离边优先",           "2 2\n1 2 0 5\n1 2 1 0",  "0 5"),
    ("绕路更近（样例 1）",      "3 3\n1 2 2 5\n2 3 2 1\n1 3 5 0", "4 6"),
    ("两条距离相同选风险小的",  "3 4\n1 3 4 9\n1 2 2 5\n2 3 2 1\n1 3 4 2", "4 2"),
]

_r = random.Random(20261001)
LIMITS = [
    ("极限 n=2e5 m=3e5 长链",
     lambda: "200000 299999\n" + "\n".join(
         "%d %d %d %d" % (i, i + 1, _r.randint(0, 1000000000),
                          _r.randint(0, 1000000000))
         for i in range(1, 200000))),
    ("极限 n=2e5 m=3e5 随机边",
     lambda: "200000 300000\n" + "\n".join(
         "%d %d %d %d" % (u, (u % 200000) + 1,
                          _r.randint(0, 1000000000), _r.randint(0, 1000000000))
         for u in (_r.randint(1, 200000) for _ in range(300000)))),
]

if __name__ == "__main__":
    main(solution="e.cpp", brute="e_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=400, seed=161, workdir=HERE)
