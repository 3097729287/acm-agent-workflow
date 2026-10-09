# -*- coding: utf-8 -*-
"""D 题配图：四连通 / 八连通的连通块长什么样。

双击同目录的 run.cmd 就能看，或者在终端里跑：python grid_visual.py
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
from vizgrid import Grid, banner, table, note

MARKS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def label(grid, eight):
    """给每个 1 标上它属于第几块，返回 (标记图, 每块的面积表)。"""
    n, m = len(grid), len(grid[0])
    lab = [[0] * m for _ in range(n)]
    cnt = 0
    areas = []
    for i in range(n):
        for j in range(m):
            if grid[i][j] != '1' or lab[i][j]:
                continue
            cnt += 1
            area = 0
            stack = [(i, j)]
            lab[i][j] = cnt
            while stack:
                x, y = stack.pop()
                area += 1
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        if not eight and abs(dx) + abs(dy) != 1:
                            continue          # 四连通只认上下左右
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < n and 0 <= ny < m \
                                and grid[nx][ny] == '1' and not lab[nx][ny]:
                            lab[nx][ny] = cnt
                            stack.append((nx, ny))
            areas.append((cnt, area))
    return lab, areas


def draw(grid, lab=None, xs=3, ys=1):
    """把网格画成字符画。lab 为空就画原图（█ 是 1、· 是 0）。"""
    n, m = len(grid), len(grid[0])
    g = Grid(0, m - 1, -(n - 1), 0, xs=xs, ys=ys)
    for i in range(n):
        for j in range(m):
            if grid[i][j] == '0':
                g.put(j, -i, '·')
            elif lab is None:
                g.put(j, -i, '█')
            else:
                k = lab[i][j]
                g.put(j, -i, MARKS[k - 1] if k <= len(MARKS) else '?')
    return g.text(indent="      ")


def neighbor_demo(eight):
    """中心格的邻居示意图：▣ 是自己，◆ 是算相邻的格子。"""
    g = Grid(0, 2, -2, 0, xs=3, ys=1)
    for i in range(3):
        for j in range(3):
            if i == 1 and j == 1:
                ch = '▣'                      # 自己
            elif eight:
                ch = '◆'                      # 八连通：周围 8 格全算
            else:
                ch = '◆' if abs(i - 1) + abs(j - 1) == 1 else '·'
            g.put(j, -i, ch)
    return g.text(indent="      ")


def show_case(name, grid):
    banner("样例：%s" % name)
    print("原图（█ = 1，· = 0）：")
    print(draw(grid))

    lab4, a4 = label(grid, False)
    lab8, a8 = label(grid, True)
    print()
    print("四连通分块（同一个数字 = 同一块）：")
    print(draw(grid, lab4))
    print()
    print("八连通分块：")
    print(draw(grid, lab8))

    rows = []
    for k in range(1, max(len(a4), len(a8)) + 1):
        s4 = next((a for c, a in a4 if c == k), 0)
        s8 = next((a for c, a in a8 if c == k), 0)
        rows.append((k, s4, s8))
    print()
    table(["块号", "四连通面积", "八连通面积"], rows)
    print()
    note("四连通：块数 %d，最大面积 %d" % (len(a4), max((a for _, a in a4), default=0)))
    note("八连通：块数 %d，最大面积 %d" % (len(a8), max((a for _, a in a8), default=0)))
    note("答案 c4 - c8 = %d，s4 = %d，s8 = %d"
         % (len(a4) - len(a8),
            max((a for _, a in a4), default=0),
            max((a for _, a in a8), default=0)))


def main():
    banner("第 1 部分 · 什么叫「相邻」—— 中心格周围哪几格算邻居")
    print("四连通（只认上下左右，要拐直角走两步才算）：")
    print(neighbor_demo(False))
    print()
    print("八连通（周围 8 格全算，斜着一步就到）：")
    print(neighbor_demo(True))

    show_case("样例 1（3x3 对角线）", ["100", "010", "001"])
    show_case("样例 2（3x4 斜带）", ["1100", "0110", "0011"])

    banner("第 3 部分 · 为什么斜着放的两个 1 会在八连通里合并")
    g = ["10", "01"]
    print("这张 2x2 里，两个 1 是对角关系：")
    print(draw(g))
    print()
    print("四连通：两块，各 1 个格子")
    print(draw(g, label(g, False)[0]))
    print()
    print("八连通：一块，2 个格子")
    print(draw(g, label(g, True)[0]))
    print()
    note("对角两个 1 在四连通下要走两步（右 + 下），不相邻；"
         "在八连通下一步斜着就到，于是合并 —— 这就是 c4 - c8 的来源。")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
