# -*- coding: utf-8 -*-
"""
E - 小月的门 · 叉积（cross product）到底是什么
================================================

    python cross_visual.py

分三部分：
  1. 三个点算一次叉积 —— 它怎么算、结果的正负号是什么意思
  2. 让 B 点绕着 O→A 转一圈 —— 看符号什么时候正、什么时候负、什么时候是 0
  3. 回到这道题 —— 闸门线段 + 物品线段，把"真穿过"的四个叉积逐个算出来

纯 Python 标准库，不用装任何东西。
"""


def cross(ox, oy, ax, ay, bx, by):
    """向量 OA 与 OB 的叉积。> 0 表示 B 在 O→A 的左侧，< 0 右侧，= 0 共线。"""
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


class Grid:
    """字符画平面。x 每 1 单位占 xs 列，y 每 1 单位占 ys 行。

    终端里的字符是"高瘦"的（约 2:1），所以 ys 取 xs 的一半，画出来才不扁。
    """

    def __init__(self, xmin, xmax, ymin, ymax, xs=4, ys=2):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.xs, self.ys = xs, ys
        self.w = (xmax - xmin) * xs + 1
        self.h = (ymax - ymin) * ys + 1
        self.g = [[" "] * self.w for _ in range(self.h)]

    def rc(self, x, y):
        return (int(round((self.ymax - y) * self.ys)),
                int(round((x - self.xmin) * self.xs)))

    def put(self, x, y, ch):
        r, c = self.rc(x, y)
        if 0 <= r < self.h and 0 <= c < self.w:
            self.g[r][c] = ch

    def seg(self, x1, y1, x2, y2, ch):
        """逐格步进画线：每步只走一格（行或列），这样同一行不会堆出两个字符。"""
        r1, c1 = self.rc(x1, y1)
        r2, c2 = self.rc(x2, y2)
        steps = max(abs(r2 - r1), abs(c2 - c1), 1)
        for k in range(steps + 1):
            t = k / steps
            r = int(round(r1 + (r2 - r1) * t))
            c = int(round(c1 + (c2 - c1) * t))
            if 0 <= r < self.h and 0 <= c < self.w:
                self.g[r][c] = ch

    def axes(self):
        for x in range(self.xmin, self.xmax + 1):
            self.put(x, 0, "·")
        for y in range(self.ymin, self.ymax + 1):
            self.put(0, y, "·")
        self.put(0, 0, "+")
        self.put(self.xmax, 0, ">")

    def show(self, pad="      "):
        out = []
        for row in self.g:
            out.append(pad + "".join(row).rstrip())
        while out and not out[-1].strip():
            out.pop()
        print("\n".join(out))


def banner(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ---------------------------------------------------------------- 第一部分
def part1():
    banner("第一部分：三个点算一次叉积")
    O, A, B = (0, 0), (4, 0), (1, 3)

    print()
    print("先把公式钉死（O 是出发点，A、B 是另外两个点）：")
    print()
    print("    cross(O,A,B) = (A.x-O.x)*(B.y-O.y) - (A.y-O.y)*(B.x-O.x)")
    print()
    print("它的几何意思是：把 O→A 和 O→B 当成两条边，它们张成的平行四边形的")
    print("【有向面积】。面积本来总是正的，加上\"有向\"两个字，就是给它配一个符号：")
    print()
    print("    B 在 O→A 的左侧  ->  面积取正  ->  cross > 0")
    print("    B 在 O→A 的右侧  ->  面积取负  ->  cross < 0")
    print("    O、A、B 三点共线  ->  平行四边形被压扁成 0  ->  cross = 0")
    print()
    print("-" * 70)
    print()
    print("拿三个具体点代进去算：")
    print()
    print("    O = (0,0)      A = (4,0)      B = (1,3)")
    print()
    print("    A.x - O.x = 4 - 0 = 4        B.y - O.y = 3 - 0 = 3")
    print("    A.y - O.y = 0 - 0 = 0        B.x - O.x = 1 - 0 = 1")
    print()
    print("    cross = 4 × 3  -  0 × 1")
    v = cross(*O, *A, *B)
    print("          = 12     -  0        = %d" % v)
    print()
    print("得到 %d > 0  ->  B 在 O→A 的【左侧】。" % v)
    print()
    print("单位说明：O→A 长度是 4，B 离直线 OA 的高度是 3，")
    print("所以平行四边形的底乘高 = 4 × 3 = 12 —— 和叉积的绝对值一模一样，")
    print("这就是\"叉积 = 有向面积\"的字面意思。")

    print()
    print("画出来看：")
    print()
    g = Grid(-1, 5, -1, 3)
    g.axes()
    g.seg(0, 0, 4, 0, "━")          # O→A 这条边（也是 x 轴正方向）
    g.seg(0, 0, 1, 3, "/")          # O→B
    for (px, py), name in [((0, 0), "O"), ((4, 0), "A")]:
        g.put(px, py, name)
    g.put(1, 3, "B")
    g.show()
    print()
    print("      B 在 O→A 上方（左侧）—— 所以 cross = +12。")


# ---------------------------------------------------------------- 第二部分
def part2():
    banner("第二部分：让 B 绕着 O→A 转一圈，看符号怎么变")
    O, A = (0, 0), (4, 0)
    print()
    print("固定 O = (0,0)、A = (4,0)，把 B 放在周围 8 个位置上：")
    print()
    print("      %-10s %-14s %8s %6s   %s" % ("B 在哪", "B 的坐标", "叉积", "符号", "结论"))
    print("      " + "-" * 58)

    spots = [("正右边", (4, 0)), ("右上方", (3, 3)), ("正上方", (0, 4)), ("左上方", (-3, 3)),
             ("正左边", (-4, 0)), ("左下方", (-3, -3)), ("正下方", (0, -4)), ("右下方", (3, -3))]
    for name, B in spots:
        v = cross(*O, *A, *B)
        if v > 0:
            sign, concl = "+", "左侧"
        elif v < 0:
            sign, concl = "-", "右侧"
        else:
            sign, concl = "0", "在直线上（共线）"
        print("      %-10s %-14s %8d %6s   %s" % (name, str(B), v, sign, concl))

    print()
    print("规律一眼就看出来了：")
    print("      · x 轴【上方】的点，叉积全为正（左侧）")
    print("      · x 轴【下方】的点，叉积全为负（右侧）")
    print("      · 正好落在 x 轴上的点，叉积是 0")
    print()
    print("这不是巧合 —— 因为叉积的符号就是\"B 在直线 OA 的哪一边\"，")
    print("直线 OA 就是 x 轴，所以把平面切成了上下两半。")
    print()
    print("把这块矩形里的每个整点都算一遍，画出来：")
    print()
    g = Grid(-4, 5, -4, 4, xs=2, ys=1)
    for px in range(-4, 5):
        for py in range(-4, 5):
            if py == 0:                     # y = 0 那一行留给 OA 本身
                continue
            v = cross(0, 0, 4, 0, px, py)
            g.put(px, py, "+" if v > 0 else ("-" if v < 0 else "0"))
    g.seg(-4, 0, 0, 0, "·")                 # OA 所在直线的左半边（不是线段本身）
    g.seg(0, 0, 5, 0, "━")                  # 线段 O→A 及其右侧延长
    g.put(0, 0, "O")
    g.put(4, 0, "A")
    g.put(5, 0, ">")
    g.show()
    print()
    print("      + = 叉积为正（在 OA 左侧）      - = 叉积为负（在 OA 右侧）")
    print("      · = OA 所在直线的延长部分        ━ = 线段 O→A")
    print("      格点上一个反例都没有：上半平面清一色 +，下半平面清一色 -。")


# ---------------------------------------------------------------- 第三部分
def part3():
    banner("第三部分：回到这道题 —— 闸门与\"真穿过\"的判定")
    P1, P2 = (0, 0), (4, 0)
    print()
    print("题目里有一条有向闸门线段 P1 → P2，它的【左侧是库内】，右侧是库外。")
    print("本题样例 1 的闸门就是 P1 = (0,0) → P2 = (4,0)，左侧正好是 y > 0 那块。")
    print()
    print("现在有一个物品从 A = (1,-1) 直线走到 C = (1,1)，问：它穿过闸门了吗？")
    print()
    print("-" * 70)
    print()
    print("要判断\"真穿过\"（交点严格在两条线段【内部】），要算四个叉积：")
    print()

    A, C = (1, -1), (1, 1)
    d1 = cross(*P1, *P2, *A)
    d2 = cross(*P1, *P2, *C)
    d3 = cross(*A, *C, *P1)
    d4 = cross(*A, *C, *P2)

    def show_cross(name, O, X, Y_, v):
        print("    %s = cross((%d,%d), (%d,%d), (%d,%d))" % (name, O[0], O[1], X[0], X[1], Y_[0], Y_[1]))
        print("    %s   = (%d-%d)*(%d-%d) - (%d-%d)*(%d-%d) = %d"
              % (" " * len(name), X[0], O[0], Y_[1], O[1], X[1], O[1], Y_[0], O[0], v))

    print("  ① 物品的两个端点，在闸门直线的哪一侧？")
    show_cross("d1", P1, P2, A, d1)
    print("       d1 = %d < 0  ->  起点 A 在闸门直线的【右侧 = 库外】" % d1)
    print()
    show_cross("d2", P1, P2, C, d2)
    print("       d2 = %d > 0  ->  终点 C 在闸门直线的【左侧 = 库内】" % d2)
    print()
    print("       d1 和 d2 一负一正，【严格异号】 -> 物品线段跨过了闸门所在的那条直线")
    print()
    print("  ② 闸门的两个端点，在物品直线的哪一侧？")
    show_cross("d3", A, C, P1, d3)
    show_cross("d4", A, C, P2, d4)
    print("       d3 = %d、d4 = %d，也是一正一负，【严格异号】" % (d3, d4))
    print()
    print("       -> 闸门线段也跨过了物品所在的那条直线")
    print()
    print("-" * 70)
    print()
    print("    两条【同时】成立，说明交点被夹在两条线段的内部 —— 真穿过。")
    print("    再看方向：起点 A 在库外（d1 < 0）-> 从外穿到内 -> 库内 +1")
    print()
    print("-" * 70)
    print()
    print("为什么两个叉积都要算？只算①不行吗？")
    print("    只算①，只能保证两条【直线】相交，交点可能跑到闸门线段外面去。")
    print("    例：物品 (5,-1) → (5,1)，交点是 (5,0)，它在闸门直线上（d1、d2 也异号），")
    print("    但闸门只从 x=0 画到 x=4，交点 x=5 在线段【外面】—— 不算穿过。")
    print("    ② 就是为了把这种\"交在延长线上\"的情况挡掉。")
    print()
    print("-" * 70)
    print()
    print("画出来：")
    print()
    g = Grid(-1, 6, -2, 2)
    g.axes()
    g.seg(0, 0, 4, 0, "━")                  # 闸门
    g.seg(1, -1, 1, 1, "┃")                 # 物品
    g.seg(5, -1, 5, 1, "┆")                 # 反例：交点在闸门外面
    g.put(0, 0, "P1")
    g.put(4, 0, "P2")
    g.put(1, 1, "C")
    g.put(1, -1, "A")
    g.show()
    print()
    print("      ━ = 闸门 P1→P2      ┃ = 物品（真穿过，交点在闸门内部）")
    print("      右边那条虚线（x = 5）= 上面说的反例，它的交点在闸门【外面】，不算穿过")
    print("      闸门左侧（y > 0）是库内，右侧（y < 0）是库外。")
    print("      物品从下往上走：库外 -> 库内，所以库内 +1。")

    # ---- 对答案：样例 1 全部五条 ----
    print()
    print("-" * 70)
    print()
    print("把样例 1 的五条物品全算一遍，和样例答案对一下：")
    print()
    cases = [((1, -1), (1, 1)), ((3, 1), (3, -1)), ((5, -1), (5, 1)),
             ((2, 0), (2, 1)), ((2, -1), (2, 2))]
    total = 0
    print("      %-4s %-18s %6s %6s %6s %6s  %s" % ("#", "物品线段", "d1", "d2", "d3", "d4", "贡献"))
    print("      " + "-" * 62)
    for i, (A_, C_) in enumerate(cases, 1):
        e1 = cross(*P1, *P2, *A_)
        e2 = cross(*P1, *P2, *C_)
        e3 = cross(*A_, *C_, *P1)
        e4 = cross(*A_, *C_, *P2)
        s1 = (e1 > 0 and e2 < 0) or (e1 < 0 and e2 > 0)
        s2 = (e3 > 0 and e4 < 0) or (e3 < 0 and e4 > 0)
        if s1 and s2:
            add = -1 if e1 > 0 else 1
        else:
            add = 0
        total += add
        print("      %-4d %-18s %6d %6d %6d %6d  %+d"
              % (i, str(A_) + "→" + str(C_), e1, e2, e3, e4, add))
    print()
    print("      合计 = %+d" % total)
    print("      样例答案 = 1")
    print("      %s" % ("一致 ✔" if total == 1 else "★不一致，脚本或理解有问题★"))


if __name__ == "__main__":
    print()
    print("欢迎。这个脚本讲一件事：叉积。")
    print("它是这道题唯一的\"新概念\"，也是唯一需要动脑的地方，其余都是套公式。")
    part1()
    part2()
    part3()
    print()
    print("=" * 70)
    print("完。想自己试的话，改 part1() 里 O、A、B 的坐标再跑一遍，看叉积怎么变。")
    print("=" * 70)
    print()
