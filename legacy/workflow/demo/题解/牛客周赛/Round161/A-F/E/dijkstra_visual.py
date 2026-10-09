# -*- coding: utf-8 -*-
"""E 题配图：Dijkstra 双关键字（先比距离，再比风险）一步一步怎么更新。

双击同目录的 run.cmd 就能看，或者在终端里跑：python dijkstra_visual.py
"""
import os
import sys

def _tools_dir():
    """工具目录：AGENT_CP_TOOLS 环境变量优先；否则向上找含 tools/toolutil.py 的目录。"""
    p = os.environ.get("AGENT_CP_TOOLS")
    if p:
        return p
    p = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(p, "tools", "toolutil.py")):
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit("没找到仓库 tools/：把 AGENT_CP_TOOLS 环境变量指向它的绝对路径")
        p = q
    return os.path.join(p, "tools")


sys.path.insert(0, _tools_dir())
from vizgrid import banner, table, note, render_array

INF = float('inf')


def fmt(v):
    return "∞" if v == INF else str(v)


def show_state(dist, risk, n):
    table(["结点"] + [str(i) for i in range(1, n + 1)],
          [["dist"] + [fmt(dist[i]) for i in range(1, n + 1)],
           ["risk"] + [fmt(risk[i]) for i in range(1, n + 1)]])


def run(n, edges, name):
    """在图上跑一遍双关键字 Dijkstra，把每一步打印出来。"""
    banner(name)
    adj = [[] for _ in range(n + 1)]
    for u, v, d, r in edges:
        adj[u].append((v, d, r))
    print("边（u -> v，距离 d，风险 r）：")
    table(["边", "距离 d", "风险 r"],
          [("%d → %d" % (u, v), d, r) for u, v, d, r in edges])
    print()

    dist = [INF] * (n + 1)
    risk = [INF] * (n + 1)
    dist[1] = 0
    risk[1] = 0
    done = set()
    step = 1

    print("出发前：只有 1 号结点是 (0, 0)，其余都还不知道怎么到")
    show_state(dist, risk, n)
    print()

    while True:
        # 找还没定下来、距离最小的结点；距离一样时取风险小的
        u, best = 0, (INF, INF)
        for x in range(1, n + 1):
            if x not in done and (dist[x], risk[x]) < best:
                u, best = x, (dist[x], risk[x])
        if u == 0 or dist[u] == INF:
            break

        done.add(u)
        print("第 %d 步：定下来的是 %d 号结点，目前（距离 %s，风险 %s）"
              % (step, u, fmt(dist[u]), fmt(risk[u])))
        step += 1

        if not adj[u]:
            print("  它没有出边，跳过。")
            print()
            continue

        for v, d, r in adj[u]:
            nd = dist[u] + d
            nr = risk[u] + r
            better = (nd < dist[v]) or (nd == dist[v] and nr < risk[v])
            if better:
                old = "（原来 %s, %s）" % (fmt(dist[v]), fmt(risk[v])) \
                    if dist[v] != INF else "（原来到不了）"
                print("  走 %d → %d：新方案（距离 %s，风险 %s）%s，比原来好，更新"
                      % (u, v, fmt(nd), fmt(nr), old))
                dist[v] = nd
                risk[v] = nr
            else:
                print("  走 %d → %d：新方案（距离 %s，风险 %s），不比现在的（%s, %s）好，丢掉"
                      % (u, v, fmt(nd), fmt(nr), fmt(dist[v]), fmt(risk[v])))
        show_state(dist, risk, n)
        print()

    if dist[n] == INF:
        print("终点 %d 号一直没被更新到 —— 走不到，输出 -1 -1。" % n)
    else:
        print("终点 %d 号：距离 %s，风险 %s" % (n, fmt(dist[n]), fmt(risk[n])))
    return dist[n], risk[n]


def main():
    banner("第 1 部分 · 样例 1：绕路更近，哪怕风险更高也要绕")
    run(3, [(1, 2, 2, 5), (2, 3, 2, 1), (1, 3, 5, 0)], "样例 1")
    note("注意 1 → 3 那条直连边：距离 5、风险 0，风险是全场最低，"
         "但距离 5 比绕路的 2 + 2 = 4 大，所以小月根本不选它 —— 先比距离，距离定了才比风险。")

    banner("第 2 部分 · 距离打平时，才轮到风险说话")
    run(3, [(1, 3, 4, 9), (1, 2, 2, 5), (2, 3, 2, 1), (1, 3, 4, 2)], "两条路距离都是 4")
    note("两条路距离都是 4：直接那条风险 9，绕路那条风险 6，还有一条直连风险 2。"
         "距离打平，就选风险最小的那条。")

    banner("第 3 部分 · 走不到终点时")
    run(3, [(1, 2, 1, 8), (2, 1, 1, 3)], "样例 2：1 和 2 互相绕圈")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
