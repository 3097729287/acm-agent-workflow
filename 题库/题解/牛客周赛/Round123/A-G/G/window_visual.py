# -*- coding: utf-8 -*-
"""G 题配图脚本：为什么答案是「n - 窗口里最多能覆盖多少种数字」，以及双指针怎么扫。

实测没有 py 命令，双击 run.cmd 或手敲：
    python window_visual.py

四部分：
  1. 最后要变成什么：长度 n 的窗口（画在数轴上）
  2. 同向双指针：窗口右端一步步往右挪
  3. 官方样例 1 的完整方案（保留哪张、改哪张、改成几）
  4. 对答案（并和「枚举起点 L」的暴力互验）
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
from vizgrid import Grid, part, note, table          # noqa: E402

TOTAL = 4


def window_fig(vals, L, n, hi=None, xs=4):
    """数轴图：刻度上写出现过的数字，最下面一条粗线是目标窗口 [L, L+n-1]。"""
    hi = hi if hi is not None else max(max(vals), L + n - 1) + 1
    g = Grid(0, hi, 0, 3, xs=xs, ys=2)
    for v in range(0, hi + 1):
        g.put(v, 1, "·")
    for v in vals:
        if v < 10:
            g.put(v, 2, str(v))
        else:
            g.put(v, 2, "#")
    g.seg(L, 0, L + n - 1, 0, "━")
    return g


def draw(g):
    print(g.text(indent="      "))


def solve_g(a):
    """G 题正解：排序去重 + 双指针；返回 (k, 方案, 调试信息)。"""
    n = len(a)
    D = sorted(set(a))
    first = {}
    for i, v in enumerate(a, 1):
        first.setdefault(v, i)

    best, bi, bj, i = 0, 0, 0, 0
    steps = []
    for j in range(len(D)):
        while D[j] - D[i] > n - 1:
            i += 1
        if j - i + 1 > best:
            best, bi, bj = j - i + 1, i, j
        steps.append((j, D[j], i, D[i:j + 1], j - i + 1, best))

    L = max(1, D[bj] - n + 1)
    keep = {first[v] for v in D[bi:bj + 1]}
    free_card = [x for x in range(1, n + 1) if x not in keep]
    occupied = set(D[bi:bj + 1])
    free_target = [t for t in range(L, L + n) if t not in occupied]
    plan = list(zip(free_card, free_target))
    return n - best, plan, dict(D=D, steps=steps, L=L, keep=keep, free_card=free_card,
                                free_target=free_target, best=best)


def brute_g(a):
    """暴力：枚举每一个起点 L，数窗口里覆盖了多少种不同的数字。"""
    n = len(a)
    D = sorted(set(a))
    mx = max(D)
    best = 0
    for L in range(1, mx + 1):
        best = max(best, sum(1 for v in D if L <= v <= L + n - 1))
    return n - best


def main():
    # ---------------------------------------------------------- 1
    part(1, TOTAL, "最后要变成什么")
    note("""「顺子」= 重排后是 x, x+1, ..., x+n-1，也就是**互不相同的连续 n 个整数**。
所以：原样保留的牌，数字必须两两不同，而且都要落进某个长度 n 的窗口 [L, L+n-1]。
窗口外的牌、以及窗口内重复的牌，全都必须改。""")
    note("例：n = 5，手上的牌是 1 2 3 4 6。窗口取 [1,5] 时：")
    draw(window_fig([1, 2, 3, 4, 6], 1, 5, hi=7))
    note("""刻度上的 1 2 3 4 落在粗线里 → 可以原样留着；6 在窗口外 → 必须改。
（窗口的起点 L 是可以自己定的，我们要挑一个「框住的数字种类最多」的窗口。）

    ★ 注意重复：如果同一个数字有 3 张，窗口里也只能留 1 张，另外 2 张照样得改，
      所以数的是「窗口里有多少种**不同**的数字」，不是有多少张牌。""")

    # ---------------------------------------------------------- 2
    part(2, TOTAL, "同向双指针：窗口右端一步步往右挪")
    note("""把出现过的数字排序去重成 D[0..m-1]。窗口左端 i 只会往右走，不会回头：
右端 j 往右挪一格时，如果 D[j] - D[i] 超过了 n-1（装不进窗口），就把 i 往右推，
直到重新装得下。i 一共只会走 m 步，所以整体 O(m)。""")
    demo = [1, 2, 3, 4, 6]
    n = 5
    D = sorted(set(demo))
    rows, i, best = [], 0, 0
    for j in range(len(D)):
        moved = []
        while D[j] - D[i] > n - 1:
            moved.append(D[i])
            i += 1
        best = max(best, j - i + 1)
        rows.append([j, D[j], i, ",".join(map(str, D[i:j + 1])), j - i + 1,
                     ("左端吐出 " + ",".join(map(str, moved))) if moved else "—", best])
    table(["j", "D[j]", "左端 i", "窗口里的数字", "个数", "本步动作", "最好成绩"],
          rows, aligns=[">", ">", ">", "<", ">", "<", ">"])
    note("""最后一行 j=4（数字 6）时，窗口被迫左移到只剩 6 自己，
但「最好成绩」早就记下了 4 —— 这就是**取历史最大**，不是看最后一个窗口。""")

    # ---------------------------------------------------------- 3
    part(3, TOTAL, "官方样例 1 的完整方案")
    a = [1, 2, 3, 4, 6]
    k, plan, info = solve_g(a)
    note("输入：n = 5，牌面 1 2 3 4 6（第 i 张牌的下标就是 i）")
    note("去重后的数字 D = %s" % info["D"])
    note("最好的窗口：包含 %d 种数字，起点 L = %d，也就是目标顺子 %s"
         % (info["best"], info["L"], list(range(info["L"], info["L"] + len(a)))))
    draw(window_fig(a, info["L"], len(a), hi=7))
    table(["第几张牌", "原来的数字", "怎么处理", "改成"],
          [[x, a[x - 1], "保留" if x in info["keep"] else "出千", "—" if x in info["keep"]
            else dict(plan)[x]] for x in range(1, len(a) + 1)],
          aligns=[">", ">", "^", ">"])
    note("最少出千次数 k = n - 最多保留张数 = %d - %d = %d" % (len(a), info["best"], k))
    note("程序输出：")
    note("  %d" % k)
    for x, t in plan:
        note("  %d %d" % (x, t))
    note("官方样例 1 输出是「1 / 5 5」→ %s"
         % ("一致" if (k, plan) == (1, [(5, 5)]) else "★不一致★"))

    # ---------------------------------------------------------- 4
    part(4, TOTAL, "对答案：和「枚举起点 L」的暴力互验")
    bad = 0
    import random
    rng = random.Random(20261001)
    for it in range(300):
        m = rng.randint(1, 7)
        arr = [rng.randint(1, 12) for _ in range(m)]
        k1 = solve_g(arr)[0]
        k2 = brute_g(arr)
        if k1 != k2:
            bad += 1
            print("      ★不一致★ %s：双指针 %d，暴力 %d" % (arr, k1, k2))
    note("300 组随机小数据：双指针与暴力枚举 %s" % ("全部一致" if bad == 0 else "有 %d 组不一致" % bad))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
