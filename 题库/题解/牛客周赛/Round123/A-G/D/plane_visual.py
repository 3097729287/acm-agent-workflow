# -*- coding: utf-8 -*-
"""D 题配图脚本：把一个「飞机」摆开看，再讲清楚「为什么数 (a,b,c) 就等于数飞机」。

实测没有 py 命令，双击 run.cmd 或手敲：
    python plane_visual.py

四部分：
  1. 飞机长什么样（三张 + 三张 + 两个对子）
  2. 数飞机 = 数合法三元组 (a, b ≤ c)
  3. 为什么同一个飞机不会有两种写法（代表元唯一）
  4. 官方样例 2 手算 + 对答案
"""
import os
import sys
from collections import Counter

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
from vizgrid import part, note, table, pad       # noqa: E402

TOTAL = 4


def plane_fig(tri1, tri2, p1, p2, head1="三张", head2="三张", head3="对子", head4="对子"):
    """把一个飞机画成四组牌。tri1/tri2 是三张的点数，p1/p2 是对子的点数。"""
    def cell(head, body, width):
        top = "┌" + "─" * (width - 2) + "┐"
        mid = "│" + pad(" " + body + " ", width - 2, "^") + "│"
        bot = "└" + "─" * (width - 2) + "┘"
        return [pad(head, width, "^"), top, mid, bot]

    groups = [
        (head1, ("%s %s %s" % (tri1, tri1, tri1))),
        (head2, ("%s %s %s" % (tri2, tri2, tri2))),
        (head3, ("%s %s" % (p1, p1))),
        (head4, ("%s %s" % (p2, p2))),
    ]
    blocks = [cell(h, b, 13) for h, b in groups]
    for line in range(4):
        print("      " + "  ".join(b[line] for b in blocks))
    print("      " + "  ".join(pad(t, 13, "^") for t in
                               ("a = %s" % tri1, "a+1 = %s" % tri2,
                                "b = %s" % p1, "c = %s" % p2)))


def solve_d(a):
    """D 题正解：Σ_a [ C(|T|,2) + |T4| ]。"""
    cnt = Counter(a)
    MAXA = max(a) + 2
    g2 = sum(1 for v, c in cnt.items() if c >= 2)
    g4 = sum(1 for v, c in cnt.items() if c >= 4)
    ans = 0
    detail = []
    for x in sorted(cnt):
        if cnt[x] < 3 or cnt[x + 1] < 3:
            continue
        T = g2 - 2 + (cnt[x] >= 5) + (cnt[x + 1] >= 5)
        T4 = g4 - (cnt[x] >= 4) - (cnt[x + 1] >= 4) + (cnt[x] >= 7) + (cnt[x + 1] >= 7)
        c2 = T * (T - 1) // 2
        detail.append((x, T, c2, T4))
        ans += c2 + T4
    return ans, detail


def brute_d(a):
    """暴力：枚举 10 张牌的所有可重集合，按定义检查是不是飞机。"""
    cnt = Counter(a)
    vals = sorted(cnt)
    chosen, ans = [0] * len(vals), 0

    def is_plane():
        cards = []
        for i, k in enumerate(chosen):
            cards += [vals[i]] * k
        if len(cards) != 10:
            return False
        for x in set(cards):
            if cards.count(x) >= 3 and cards.count(x + 1) >= 3:
                rest = list(cards)
                for _ in range(3):
                    rest.remove(x)
                    rest.remove(x + 1)
                rest.sort()
                if rest[0] == rest[1] and rest[2] == rest[3]:
                    return True
        return False

    def dfs(i, remain):
        nonlocal ans
        if remain == 0:
            ans += 1 if is_plane() else 0
            return
        if i == len(vals):
            return
        for k in range(0, min(cnt[vals[i]], remain) + 1):
            chosen[i] = k
            dfs(i + 1, remain - k)
        chosen[i] = 0

    if len(a) >= 10:
        dfs(0, 10)
    return ans


def main():
    # ---------------------------------------------------------- 1
    part(1, TOTAL, "飞机长什么样")
    note("""题面给的形状是 {a,a,a, a+1,a+1,a+1, b,b, c,c}：两个**连续**的三张，加两个对子。
对子的点数 b、c 没有限制——可以相等，也可以和三张的点数撞在一起。
下面这个是题面里的第一个例子 {1,1,1,2,2,2,3,3,4,4}：""")
    plane_fig(1, 2, 3, 4)
    note("""再看题面里「不是飞机」的那个 {1,1,1,3,3,3,2,2,4,4}：
两个三张的点数是 1 和 3，**不连续**，所以怎么摆都不行：""")
    plane_fig(1, 3, 2, 4)
    note("""而样例 1 的牌是四个 1、三个 2，写成飞机的样子是这样——两个对子都取 1
（b = c = 1 是允许的，这正是最容易漏掉的一种）：""")
    plane_fig(1, 2, 1, 1)

    # ---------------------------------------------------------- 2
    part(2, TOTAL, "数飞机 = 数合法三元组 (a, b ≤ c)")
    note("""一个飞机完全由三样东西决定：三张的起点 a、两个对子的点数 b 和 c。
为了让同一个飞机只数一次，约定 **b ≤ c**（b、c 交换不算新的飞机）。

对固定的 a，三张的部分要先吃掉 cnt[a] 和 cnt[a+1] 各 3 张，剩下的容量记作
cap[x] = cnt[x] - 3（x 是 a 或 a+1）、cap[x] = cnt[x]（其它数字）。于是：
  · b < c：cap[b] ≥ 2 且 cap[c] ≥ 2   →  可选的 b、c 都来自集合 T = {x : cap[x] ≥ 2}
  · b = c：cap[b] ≥ 4                  →  可选的 b 来自集合 T4 = {x : cap[x] ≥ 4}
所以这个 a 的贡献 = C(|T|, 2) + |T4|，答案就是所有合法 a 的贡献之和。""")
    note("""|T| 和 |T4| 不用每次重扫：全场先统计
  g2 = 够 2 张的数字种数，g4 = 够 4 张的数字种数，
再对 a、a+1 这两个特殊位置做加减即可（代码里就三行）。""")

    # ---------------------------------------------------------- 3
    part(3, TOTAL, "为什么同一个飞机不会有两种写法")
    note("""这是「不重不漏」的关键。假设同一个可重集合既能写成 (a, b, c)，又能写成 (a', b', c')：

  · 若 a' ≥ a+2：集合里要有 a、a+1、a'、a'+1 四种数字各至少 3 张 = 至少 12 张，
    可飞机一共只有 10 张 —— 不可能。
  · 若 a' = a+1：数字 a+1 要同时充当「a 的三张」和「a' 的三张」，
    至少 6 张，再加 a、a+2 各 3 张，又是至少 12 张 —— 不可能。

所以 a 是唯一的；a 定了以后，扣掉两个三张，剩下的四张就是两个对子，
b、c 也随之唯一。三种写法各对应一个不同的飞机，一个不多一个不少。""")
    table(["同一个集合能不能有两种写法", "要多少张牌", "结论"],
          [["a' ≥ a+2（两组三张隔开）", "≥ 3×4 = 12 张", "装不进 10 张，不可能"],
           ["a' = a+1（两组三张挨着）", "≥ 6 + 3 + 3 = 12 张", "装不进 10 张，不可能"]],
          aligns=["<", "<", "<"])

    # ---------------------------------------------------------- 4
    part(4, TOTAL, "官方样例 2 手算 + 对答案")
    a = [1, 1, 1, 3, 3, 4, 4, 5, 5, 2, 2, 2]
    note("样例 2 的 12 张牌：1×3、2×3、3×2、4×2、5×2。")
    note("能当三张起点的只有 a = 1（要 cnt[1] ≥ 3 且 cnt[2] ≥ 3，只有这一对满足）。")
    note("""扣掉 1、2 各 3 张后：cap[1] = 0、cap[2] = 0、cap[3] = cap[4] = cap[5] = 2，
所以 T = {3,4,5}、T4 = 空：""")
    cnt = Counter(a)
    rows = [[v, cnt[v], cnt[v] - 3 if v in (1, 2) else cnt[v]] for v in sorted(cnt)]
    table(["数字 v", "cnt[v]", "cap[v]（a = 1 时）"], rows, aligns=[">", ">", ">"])
    ans, detail = solve_d(a)
    table(["起点 a", "|T|", "C(|T|,2)", "|T4|"], [[x, T, c2, t4] for x, T, c2, t4 in detail],
          aligns=[">", ">", ">", ">"])
    note("总答案 = 3 + 0 = %d（C(3,2) = 3 就是 b<c 的那三种：(3,4) (3,5) (4,5)）"
         % ans)
    note("官方样例 2 输出 3  →  %s" % ("一致" if ans == 3 else "★不一致★"))
    note("样例 1 的 10 张牌：1×7、2×3 → 答案 %d，官方输出 1  →  %s"
         % (solve_d([1] * 7 + [2] * 3)[0],
            "一致" if solve_d([1] * 7 + [2] * 3)[0] == 1 else "★不一致★"))

    # 顺带和暴力互验一下
    import random
    rng, bad = random.Random(20261001), 0
    for _ in range(120):
        m = rng.randint(1, 12)
        arr = [rng.randint(1, 4) for _ in range(m)]
        if solve_d(arr)[0] != brute_d(arr):
            bad += 1
            print("      ★不一致★ %s" % arr)
    note("120 组随机小数据：公式与「枚举 10 张可重集合」的暴力 %s"
         % ("全部一致" if bad == 0 else "有 %d 组不一致" % bad))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
