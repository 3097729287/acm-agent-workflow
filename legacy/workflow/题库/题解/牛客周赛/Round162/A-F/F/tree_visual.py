# -*- coding: utf-8 -*-
"""
tree_visual.py —— F 题「坏边覆盖 + 树形 DP」的可跑字符画
==========================================================
双击同目录的 run.cmd 就能看。对两棵树各演示四件事：

  1. 把原树画出来，边上标「坏」（两端异色）/「同」（两端同色）
  2. 自底向上算出每个点的 badCnt（子树内的坏边数）与 F（以它为顶要删几个点）
  3. 逐行检查「哪个点能当最浅点 top」
  4. 从最优 top 回溯出到底删哪几个点

所有数字都是脚本自己算出来的，不是写死的。
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
from vizgrid import banner, note, show_tree, table

TREES = [
    ("官方样例 1：一条链 RBRBR", 5, "RBRBR",
     [(1, 2), (2, 3), (3, 4), (4, 5)]),
    ("一棵分叉的树（1 是根，2、3 是它的两个孩子）", 6, "RBBRRR",
     [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6)]),
]


def build(n, col, edges):
    """定父子（迭代 BFS），返回 parent、order、adj"""
    adj = [[] for _ in range(n + 1)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [0] * (n + 1)
    parent[1] = -1
    order = [1]
    for u in order:
        for v in adj[u]:
            if v != parent[u]:
                parent[v] = u
                order.append(v)
    return parent, order, adj


def solve(n, col, edges):
    parent, order, adj = build(n, col, edges)
    bad_cnt = [0] * (n + 1)
    f = [1] * (n + 1)
    for u in reversed(order):                      # 自底向上
        val = 1
        for v in adj[u]:
            if parent[v] != u:
                continue
            if bad_cnt[v] > 0:
                val += f[v]
            bad_cnt[u] += bad_cnt[v]
            if col[u - 1] != col[v - 1]:
                bad_cnt[u] += 1
        f[u] = val
    total = bad_cnt[1]
    return parent, order, adj, bad_cnt, f, total


def pick(n, col, adj, parent, bad_cnt, top):
    """从 top 回溯出要删的点集：儿子的子树里没有坏边就不往下走"""
    chosen = [top]
    stack = [top]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if parent[v] == u and bad_cnt[v] > 0:
                chosen.append(v)
                stack.append(v)
    return sorted(chosen)


for title, n, col, edges in TREES:
    parent, order, adj, bad_cnt, f, total = solve(n, col, edges)
    banner(title)

    note("原树（边上写「坏」= 两端异色，必须被盖住；写「同」= 两端同色，不用管）：")
    show_tree(children_of=lambda u: [("坏" if col[u - 1] != col[v - 1] else "同", v)
                                     for v in sorted(adj[u]) if parent[v] == u],
              label_of=lambda u: "v=%d %s   badCnt=%d   F=%d" % (u, col[u - 1],
                                                                  bad_cnt[u], f[u]),
              root=1, root_label="根 v=1 %s" % col[0])

    print()
    note("自底向上的计算顺序（先算儿子，再算父亲）：")
    rows = []
    for u in reversed(order):
        kids = [v for v in sorted(adj[u]) if parent[v] == u]
        pick_txt = "、".join("v=%d(F=%d)" % (v, f[v]) for v in kids if bad_cnt[v] > 0) or "（不选）"
        rows.append(["v=%d" % u, col[u - 1], "、".join("v=%d" % v for v in kids) or "无",
                     str(bad_cnt[u]), pick_txt, str(f[u])])
    table(["算到", "颜色", "它的孩子", "badCnt", "要往下选谁", "F"], rows)

    note("全树坏边总数 = badCnt[根] = %d" % total)
    print()
    note("逐个点检查「能不能当最浅点 top」：")
    rows = []
    best = None
    for top in range(1, n + 1):
        out = total - bad_cnt[top]
        if out == 0:
            why = "所有坏边都在它的子树里"
            ok = "可以"
        elif out == 1 and parent[top] != -1 and col[parent[top] - 1] != col[top - 1]:
            why = "只有 (父,它) 这一条在外面，它自己在 D 里，盖得住"
            ok = "可以"
        else:
            why = "外面还剩 %d 条坏边盖不住" % out
            ok = "不行"
        rows.append(["top=%d" % top, col[top - 1], str(bad_cnt[top]), str(out), ok, why])
        if ok == "可以" and (best is None or f[top] < f[best]):
            best = top
    table(["top", "颜色", "badCnt", "子树外坏边", "合法性", "理由"], rows)

    print()
    note("答案 = 可以当 top 的点里最小的 F = F[%d] = %d" % (best, f[best]))
    note("具体删哪些点：%s" % "、".join("v=%d" % v
                                       for v in pick(n, col, adj, parent, bad_cnt, best)))
