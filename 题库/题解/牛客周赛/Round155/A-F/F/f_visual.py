# -*- coding: utf-8 -*-
"""F 可视化：三份样例的构造过程（串接 S → 选 L → 输出 p,q,a）。"""
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

def construct(ss):
    S = "".join(ss)
    n = len(ss)
    allzero = all(c == '0' for c in S)
    allone = all(c == '1' for c in S)
    if allzero:
        return ("1", "10", [2] * n, "全 0 特判：p=1,q=10（展开 0.1000… 含任意长 0 串）")
    if allone:
        S = "0" + S
    C = len(S)
    L = 0 if S[0] == '0' else 1
    p_str = S.lstrip('0') or '0'
    q_str = "1" * C + "0" * L
    a = [L + S.find(s) + 1 for s in ss]
    return (p_str, q_str, a, "L=%d，p=S 去前导 0，q=C 个 1 后接 L 个 0" % L)

samples = [
    (["010", "101"], "样例 1"),
    (["111"], "样例 2"),
    (["00", "0000"], "样例 3"),
]

part(1, 1, "三份样例的构造结果")
rows = []
for ss, name in samples:
    p, q, a, why = construct(ss)
    rows.append([name, "".join(ss), "C=%d" % len("".join(ss)), p, q, " ".join(map(str, a))])
table(["样例", "串接 S", "长度", "p", "q", "a_i"], rows)
note("样例 1：S=010101（以 0 开头）→ L=0，p=10101，q=111111，010 在位置 1、101 在位置 2。")
note("样例 2：S=111 全 1 → 前缀补 0 得 0111 → L=0，p=111，q=1111，111 在位置 2。")
note("样例 3：S=00000000 全 0 → p=1,q=10，每个串在位置 2（0.1000… 的连续 0）。")
note("该展开值为 p/q，标准二进制展开正是 0.(L 个 0)(S)(S)…，必含每个 s_i。")
