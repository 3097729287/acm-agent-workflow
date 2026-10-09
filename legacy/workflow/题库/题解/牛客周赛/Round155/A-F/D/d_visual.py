# -*- coding: utf-8 -*-
"""D 可视化：位掩码 = 集合；a&b==0 = 互不相交。以样例 1 演示。"""
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

stations = ["1100", "0011", "0101", "1000", "0010"]
m = 4
def mask(s):
    v = 0
    for i, ch in enumerate(s):
        if ch == '1': v |= 1 << i
    return v

part(1, 1, "样例 1：5 台电台的串 → 位掩码（第 i 位 = 是否支持频道 i）")
rows = []
for s in stations:
    rows.append([s, "0x%X" % mask(s), mask(s)])
table(["电台串", "掩码(十六进制)", "掩码(十进制)"], rows)
note("两台电台能通信 ⟺ 掩码按位与 ≠ 0（至少有一个共同为 1 的位）。")
note("不通信 ⟺ 掩码按位与 == 0（两个集合不相交）。")
note("总对数 C(5,2)=10；下面列出所有「不相交」对，共 6 对，故答案 = 10-6 = 4。")

pairs = []
for i in range(len(stations)):
    for j in range(i + 1, len(stations)):
        if mask(stations[i]) & mask(stations[j]) == 0:
            pairs.append((stations[i], stations[j]))
rows2 = [[a, b, "0x%X & 0x%X = 0" % (mask(a), mask(b))] for a, b in pairs]
table(["电台 A", "电台 B", "判定"], rows2)
note("直接做法要对 C(n,2) 对两两判；正解改用「总数 − 不相交对」，")
note("不相交对用掩码计数表 cnt[mask] 一次算完，n 到 2e5 也不怕。")
