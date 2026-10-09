# -*- coding: utf-8 -*-
r"""verify_<字母>.py 模板 —— 复制到题目录改成自己的用例。

用法（复制到 `RoundN\<区间>\<字母>\verify_<字母>.py` 后）：

    python verify_<字母>.py

四个要点（`tools\verify.py` 的接口约定）：

1. **别用 argparse、别调 sys.exit**：第 6 步 `tools\md_full.py` 会把这个文件
   按 `__name__ == "__main__"` 整个 exec 一遍、接住最下面那行 `main(...)` 的实参
   来复用你的用例——用了 argparse 会去读 `md_full` 自己的命令行参数，当场报错。
2. **用例写在文件最下面那行 `main(...)` 的实参里**（rounds / seed / brute 都在这），
   不要写成别的常量再 getattr 读——读不到时会静默变成「跳过对拍」，看着像这题本来就不对拍。
3. **对拍基准要换范式**：`brute` 用和正解不同的写法（暴力 / DFS / 直接模拟），
   同一种写法互拍等于没拍。
4. **期望值手算**：EDGES 每条的期望输出要能手算推出，名字里写上为什么。
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
    """随机生成一组输入：覆盖小规模 + 各种边界形状。"""
    n = rng.randint(1, 10)
    return "%d\n" % n  # TODO: 换成这题的输入格式


# 边界用例：(名字写清为什么) 三元组
EDGES = [
    ("n=1 最小规模", "1\n", "1\n"),          # TODO: 换成手算过的期望输出
    ("n=10 上界", "10\n", "55\n"),
]

# 极限用例：贴最坏数据，测耗时（串要能复现：用固定 seed 的随机或常量）
_rng = random.Random(1)
LIMITS = [
    ("极限：n=2×10^5", lambda: "200000\n"),
]


if __name__ == "__main__":
    main(solution="x.cpp", brute="x_brute.cpp", gen=gen,
         edges=EDGES, limits=LIMITS, rounds=500, seed=1, workdir=HERE)
