# -*- coding: utf-8 -*-
"""B 可视化：a=1 时 2×2×2 立方体的 8 个格点分别在哪条体对角线上。"""
import os, sys
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
from vizgrid import table, part, note

def on_diag(x, y, z, a):
    res = []
    if x == y == z: res.append("1")
    if x == y and z == a - x: res.append("2")
    if x == z and y == a - x: res.append("3")
    if y == z and x == a - y: res.append("4")
    return ",".join(res) if res else "-"

a = 1
part(1, 1, "a=1：8 个格点各自落在哪些体对角线（计数 = 落在几条上）")
rows = []
S = 0
for z in range(a + 1):
    for y in range(a + 1):
        for x in range(a + 1):
            d = on_diag(x, y, z, a)
            cnt = 0 if d == "-" else len(d.split(","))
            S += cnt
            rows.append(["(%d,%d,%d)" % (x, y, z), d, cnt])
table(["格点 (x,y,z)", "所在对角线", "计数"], rows)
note("四条体对角线：1=(0,0,0)-(1,1,1)；2=(0,0,1)-(1,1,0)；3=(0,1,0)-(1,0,1)；4=(1,0,0)-(0,1,1)。")
note("若每个 v=1，则总和 = 各点计数之和 = %d（正好 8 个点，每个落在 1 条对角线上）。" % S)
note("真实题目里把 1 换成该格点的 v 值、a 换成实际边长，对每条对角线求和即可。")
