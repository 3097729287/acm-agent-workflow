# -*- coding: utf-8 -*-
r"""B - 小月的十六进制：官方样例 + 手算边界 + 随机对拍（b_brute.cpp 不同范式）+ 极限计时。

    python verify_b.py

对拍基准是 `b_brute.cpp`：把十六进制串整串展开成二进制字符串再数末尾零——
和主解「逐位扫描 + ctz」是两种不同范式，不算同源互拍。
组数/种子就写在文件末端 `main(...)` 的实参里（第 6 步 `tools/md_full.py`
复验时会原样读到这里的 rounds / brute）。
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


def gen(rng):
    """随机一组输入：长度 1~16 的十六进制串（含大小写），k 取各种量级。"""
    n = rng.randint(1, 16)
    s = "".join(rng.choice("0123456789abcdefABCDEF") for _ in range(n))
    k = rng.choice([0, 1, 2, 3, 4, 5, 8, 12, 16, 20, 30, 40, 64, 100000])
    return "%s %d\n" % (s, k)


# 边界用例：期望值手算推出（0x1A0=416=2^5×13 之类都写在各条名字里）
EDGES = [
    ("x 全零串, k 超大方（0 能被任何 2^k 整除）", "00 100000\n", "YES\n"),
    ("x=1, k=0（2^0 = 1 整除一切）", "1 0\n", "YES\n"),
    ("x=1, k=1（奇数）", "1 1\n", "NO\n"),
    ("x=F0=240=16×15, k=4", "F0 4\n", "YES\n"),
    ("x=F0=240, k=5（240÷32=7.5）", "F0 5\n", "NO\n"),
    ("x=aB0 大小写混排, k=4（0xAB0 末尾恰好 4 个零位）", "aB0 4\n", "YES\n"),
    ("x=A0=160=32×5, k=5", "A0 5\n", "YES\n"),
    ("前导零 0001, k=1（值是奇数）", "0001 1\n", "NO\n"),
    ("x=1000, k=12（0x1000=2^12）", "1000 12\n", "YES\n"),
]

_rng = random.Random(163)
LIMITS = [
    ("极限：|x|=8×10^5 全零串, k=10^5",
     lambda: "0" * 800000 + " 100000\n"),
    ("极限：|x|=8×10^5 随机十六进制, k=10^5",
     lambda: "".join(_rng.choice("0123456789abcdef") for _ in range(800000)) + " 100000\n"),
]


if __name__ == "__main__":
    main(solution="b.cpp", brute="b_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500, seed=163, workdir=HERE)
