# -*- coding: utf-8 -*-
"""
F - 小月的前缀：一条命令复跑全部验证
====================================

    python verify_all.py

做四件事：
  1. 编译 f.cpp（-O2 -std=c++17 -Wall -Wextra）
  2. 跑官方两个样例，和题面里的答案常量表比对
  3. 随机小数据 + Python 暴力对拍（暴力写法与正解完全不同：直接扫所有串）
  4. 极限数据计时

样例常量表来自题面原文（https://ac.nowcoder.com/acm/contest/140737/F），不是凭记忆敲的。
"""

import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "f.exe")
SRC = os.path.join(HERE, "f.cpp")

# ---------------------------------------------------------------- 样例常量表
SAMPLES = [
    (
        "样例 1",
        "3 5\n"
        "a 2\n"
        "ab 1\n"
        "abc 0\n"
        "abc\n"
        "abc\n"
        "ax\n"
        "a\n"
        "b\n",
        "2\n1\n1\n0\n0\n",
    ),
    (
        "样例 2",
        "1 2\n"
        "abc 1\n"
        "ab\n"
        "abc\n",
        "0\n1\n",
    ),
]


def compile_it():
    print("[1/4] 编译 f.cpp ...")
    cmd = ["g++", "-O2", "-std=c++17", "-Wall", "-Wextra", "-o", EXE, SRC]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("  编译失败：")
        print(r.stderr)
        sys.exit(1)
    warn = (r.stderr or "").strip()
    print("  编译通过。" + ("警告输出：\n" + warn if warn else "（无警告）"))


def run_exe(inp, timeout=20):
    r = subprocess.run([EXE], input=inp.encode(), capture_output=True, timeout=timeout)
    return r.stdout.decode().replace("\r\n", "\n")


def check_samples():
    print("[2/4] 官方样例 ...")
    ok = True
    for name, inp, expect in SAMPLES:
        got = run_exe(inp)
        same = got.strip() == expect.strip()
        ok = ok and same
        print("  %s：%s" % (name, "通过" if same else "★不通过★"))
        if not same:
            print("    输入： %r" % inp)
            print("    期望： %r" % expect)
            print("    实际： %r" % got)
    return ok


# ---------------------------------------------------------------- 暴力基准
def brute(setup, queries):
    """
    最直白的写法，和正解完全不同的实现范式：
    每次操作都把所有 s_i 拿出来挨个判"是不是 t 的前缀"，挑最长的。
    """
    cnt = [c for _, c in setup]
    ss = [s for s, _ in setup]
    out = []
    for t in queries:
        best = -1
        for i, s in enumerate(ss):
            if cnt[i] > 0 and t.startswith(s):
                if best == -1 or len(s) > len(ss[best]):
                    best = i
        if best == -1:
            out.append(0)
        else:
            out.append(best + 1)
            cnt[best] -= 1
    return out


def gen(rng, maxn=7, maxq=7, alpha="abc", maxlen=4):
    n = rng.randint(1, maxn)
    seen = set()
    setup = []
    tries = 0
    while len(setup) < n and tries < 200:
        tries += 1
        L = rng.randint(1, maxlen)
        s = "".join(rng.choice(alpha) for _ in range(L))
        if s in seen:
            continue
        seen.add(s)
        setup.append((s, rng.randint(0, 3)))
    n = len(setup)
    q = rng.randint(1, maxq)
    queries = ["".join(rng.choice(alpha) for _ in range(rng.randint(1, maxlen + 1)))
               for _ in range(q)]
    lines = ["%d %d" % (n, q)]
    for s, c in setup:
        lines.append("%s %d" % (s, c))
    lines.extend(queries)
    return "\n".join(lines) + "\n", setup, queries


def cross_check(rounds=1000, seed=163):
    print("[3/4] 随机对拍（Python 暴力 vs C++ 正解）...")
    rng = random.Random(seed)
    bad = 0
    for it in range(rounds):
        inp, setup, queries = gen(rng)
        expect = brute(setup, queries)
        got = run_exe(inp)
        got_list = [int(x) for x in got.split()]
        if got_list != expect:
            bad += 1
            print("  ★第 %d 组不一致★" % (it + 1))
            print("    输入：\n%s" % inp)
            print("    正解：%r" % got_list)
            print("    暴力：%r" % expect)
            if bad >= 3:
                break
        if (it + 1) % 200 == 0:
            print("    已跑 %d 组 ..." % (it + 1))
            sys.stdout.flush()
    print("  共 %d 组，不一致 %d 组。" % (rounds, bad))
    return bad == 0


def build_max_case_a():
    """
    极限 A：把总长顶到 5*10^5 上限。
    先塞满所有短的串（1 位 26 个、2 位 676 个、3 位 17576 个），再用 4 位串补满预算。
    这样 n 尽量大、串尽量短，正是"结点多、每次走几步"的形状。
    """
    AL = "abcdefghijklmnopqrstuvwxyz"
    setup = []
    for L in (1, 2, 3):
        for k in range(26 ** L):
            s = ""
            x = k
            for _ in range(L):
                s += AL[x % 26]
                x //= 26
            setup.append(s)
    used = sum(len(s) for s in setup)          # 26*1 + 676*2 + 17576*3 = 54106
    budget_s = 250000
    rng = random.Random(163163)
    seen = set(setup)
    while used + 4 <= budget_s and len(setup) < 200000:
        s = "".join(rng.choice(AL) for _ in range(4))
        if s in seen:
            continue
        seen.add(s)
        setup.append(s)
        used += 4
    body = ["%d %d" % (len(setup), 200000)]
    body += ["%s %d" % (s, rng.randint(0, 10 ** 9)) for s in setup]
    qtotal = 0
    qs = []
    while qtotal + 1 <= 500000 - used and len(qs) < 200000:
        s = rng.choice(AL)
        qs.append(s)
        qtotal += 1
    body[0] = "%d %d" % (len(setup), len(qs))
    body += qs
    return ("极限A 多串浅树 n=%d q=%d 总长=%d" % (len(setup), len(qs), used + qtotal),
            "\n".join(body) + "\n")


def build_max_case_b():
    """极限 B：一条 25 万字符的深链，专考"插入与查询都是逐字符迭代、不递归不爆栈"。"""
    deep = "a" * 250000
    qs = ["aa"] * 99998                      # 199996 个字符
    qs += ["a" * 25000, "a" * 24996]         # 再补 49996 个字符
    body = ["1 %d" % len(qs), "%s %d" % (deep, 10 ** 9)] + qs
    total = len(deep) + sum(len(x) for x in qs)
    return ("极限B 深链 单串长=%d q=%d 总长=%d" % (len(deep), len(qs), total),
            "\n".join(body) + "\n")


def stress():
    print("[4/4] 极限数据计时 ...")
    sys.stdout.flush()
    cases = [build_max_case_a(), build_max_case_b()]

    ok = True
    for name, inp in cases:
        t0 = time.time()
        r = subprocess.run([EXE], input=inp.encode(), capture_output=True, timeout=120)
        dt = time.time() - t0
        nout = len(r.stdout.split())
        print("  %s" % name)
        print("    -> 用时 %.3f s，输出 %d 行" % (dt, nout))
        if r.returncode != 0:
            print("    ★退出码 %d，stderr: %s" % (r.returncode, r.stderr[:500]))
            ok = False
        sys.stdout.flush()
    return ok


if __name__ == "__main__":
    compile_it()
    a = check_samples()
    b = cross_check()
    c = stress()
    print("\n===== 汇总 =====")
    print("  样例      : %s" % ("通过" if a else "失败"))
    print("  随机对拍  : %s" % ("通过" if b else "失败"))
    print("  极限计时  : %s" % ("完成" if c else "失败"))
