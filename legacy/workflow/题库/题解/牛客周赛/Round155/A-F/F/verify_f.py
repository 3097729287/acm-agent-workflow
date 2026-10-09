# -*- coding: utf-8 -*-
"""F - 小月的二进制分数：编译 + 官方样例(3) + 随机构造校验(模拟展开验证答案) + 极限计时。

注意：本文件不猜答案，而是把程序输出的 (p,q,a) 当作候选答案，
直接用 Python 大整数模拟 p/q 的标准二进制展开，核对：
  - 每位 s_i 确实出现在第 a_i 位；
  - a_i>=1 且 a_i+|s_i|-1 <= 2000；p<q、|p|<|q|<=1000、无前导 0。
只要全部满足，说明程序给出的就是一个合法答案（判题接受任意合法解）。
"""
import os, subprocess, sys, time, random

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "f.exe")
SRC = os.path.join(HERE, "f.cpp")

SAMPLES = [
    ("F 样例 1", "2\n010\n101", "10101\n111111\n1 2"),
    ("F 样例 2", "1\n111", "111\n1111\n2"),
    ("F 样例 3", "2\n00\n0000", "1\n10\n2 2"),
]

def compile_it():
    print("[1/4] 编译 f.cpp ...")
    r = subprocess.run(["g++", "-O2", "-std=c++17", "-Wall", "-Wextra", "-o", EXE, SRC],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("  编译失败：\n" + r.stderr); sys.exit(1)
    print("  编译通过。" + (("警告：\n"+r.stderr.strip()) if r.stderr.strip() else "（无警告）"))

def run_exe(inp, timeout=30):
    r = subprocess.run([EXE], input=inp.encode(), capture_output=True, timeout=timeout)
    return r.stdout.decode().replace("\r\n", "\n").strip()

def check_samples():
    print("[2/4] 官方样例 ...")
    ok = True
    for name, inp, expect in SAMPLES:
        got = run_exe(inp)
        same = got == expect
        ok = ok and same
        print("  %s：%s" % (name, "通过(与样例一致)" if same else "★不通过★"))
        if not same:
            print("    输入：%r 期望：%r 实际：%r" % (inp, expect, got))
    return ok

def validate(pbin, qbin, ss, a_list):
    """模拟 p/q 展开，核对每个 s_i 在 a_i 处。返回 (bool, msg)。"""
    if pbin[0] == '0' or qbin[0] == '0':
        return False, "前导零"
    p = int(pbin, 2); q = int(qbin, 2)
    if not (0 < p < q):
        return False, "p<q 不满足"
    if not (1 <= len(pbin) < len(qbin) <= 1000):
        return False, "|p|<|q|<=1000 不满足"
    need = 0
    for i, s in enumerate(ss):
        a = a_list[i]
        if a < 1 or a + len(s) - 1 > 2000:
            return False, "位置越界"
        need = max(need, a + len(s) - 1)
    # 模拟展开 need 位
    bits = []
    r = p
    for _ in range(need):
        t = 2 * r
        if t >= q:
            bits.append('1'); r = t - q
        else:
            bits.append('0'); r = t
    for i, s in enumerate(ss):
        a = a_list[i]
        seg = "".join(bits[a - 1 : a - 1 + len(s)])
        if seg != s:
            return False, "串 %r 在第 %d 位不是 %r(实际 %r)" % (s, a, s, seg)
    return True, "ok"

def gen(rng, nmax=8, lmax=8):
    n = rng.randint(1, nmax)
    ss = []
    total = 0
    while len(ss) < n and total < 1000:
        L = rng.randint(1, lmax)
        if total + L > 1000:
            L = 1000 - total
        if L <= 0:
            break
        s = "".join(rng.choice("01") for _ in range(L))
        ss.append(s); total += L
    inp = "%d\n%s\n" % (len(ss), "\n".join(ss))
    return inp, ss

def cross_check(rounds=400, seed=155):
    print("[3/4] 随机构造校验（模拟展开验证程序给出的答案）...")
    rng = random.Random(seed)
    bad = 0
    for it in range(rounds):
        inp, ss = gen(rng)
        out = run_exe(inp).split("\n")
        pbin, qbin = out[0], out[1]
        a_list = list(map(int, out[2].split()))
        ok, msg = validate(pbin, qbin, ss, a_list)
        if not ok:
            bad += 1
            print("  ★第 %d 组答案非法★ (%s)" % (it + 1, msg))
            print("    输入：%r" % inp)
            print("    输出：%r" % out)
            if bad >= 3: break
        if (it + 1) % 100 == 0:
            print("    已跑 %d 组 ..." % (it + 1)); sys.stdout.flush()
    print("  共 %d 组，非法 %d 组。" % (rounds, bad))
    return bad == 0

def stress():
    print("[4/4] 极限计时 ...")
    # 构造一个总长度接近上限的用例
    rng = random.Random(3)
    n = 200
    ss = []
    total = 0
    while total < 1000:
        L = rng.randint(1, 10)
        if total + L > 1000:
            L = 1000 - total
        if L <= 0:
            break
        s = "".join(rng.choice("01") for _ in range(L))
        ss.append(s); total += L
    inp = "%d\n%s\n" % (len(ss), "\n".join(ss))
    t0 = time.time()
    r = subprocess.run([EXE], input=inp.encode(), capture_output=True, timeout=60)
    dt = time.time() - t0
    out = r.stdout.decode().replace("\r\n", "\n").strip().split("\n")
    ok = len(out) == 3
    if ok:
        ok2, _ = validate(out[0], out[1], ss, list(map(int, out[2].split())))
        ok = ok2
    print("  总长=%d 串数=%d -> %.3f s，答案%s" % (total, len(ss), dt, "合法" if ok else "★非法★"))
    return ok

if __name__ == "__main__":
    compile_it()
    a = check_samples()
    b = cross_check()
    c = stress()
    print("\n===== 汇总 =====")
    print("  样例       : %s" % ("通过" if a else "失败"))
    print("  随机构造校验 : %s" % ("通过" if b else "失败"))
    print("  极限计时   : %s" % ("完成" if c else "失败"))
