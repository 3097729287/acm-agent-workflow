# -*- coding: utf-8 -*-
"""C 题五路交叉验证（在第 163 场「对拍.py」基础上，加入"排列枚举"这一版）：
     C_排列枚举         —— 双重 next_permutation 全排列枚举
     C_DFS记忆化        —— 状压 + 记忆化博弈搜索
     C_纯DFS_无记忆化   —— 同算法去掉记忆化
     匈牙利匹配          —— 主题解里的写法
     Python 独立复刻：博弈真值 / 匈牙利匹配
"""
import os, random, subprocess
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "_build")          # 编译产物：可随时删，重跑本脚本会重新生成

# 现场把四种写法编译出来（源文件都在本目录 / 上一级）——脚本自包含，不依赖预编译的 exe
SOURCES = {
    "排列枚举": "C_排列枚举.cpp",
    "DFS记忆化": "C_DFS记忆化.cpp",
    "纯DFS": "C_纯DFS_无记忆化.cpp",
    "匈牙利": os.path.join(HERE, "..", "c.cpp"),
}


def build():
    os.makedirs(BUILD, exist_ok=True)
    out = {}
    for name, src in SOURCES.items():
        src = os.path.join(HERE, src)
        exe = os.path.join(BUILD, name + ".exe")
        r = subprocess.run(["g++", "-O2", "-std=c++17", "-o", exe, src],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise SystemExit("编译失败：%s\n%s" % (src, r.stderr))
        out[name] = exe
    return out


EXES = build()


def run(path, inp):
    p = subprocess.run([path], input=inp.encode(), capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"{path} 退出码 {p.returncode}")
    return p.stdout.decode().strip()


def py_game(a, b):
    """博弈真值：显式模拟回合（Alice 出 / Bob 应）"""
    n = len(a)
    full = (1 << n) - 1
    memoA, memoB = {}, {}

    def alice_turn(Am, Bm):
        if Am == full: return False
        k = (Am, Bm)
        if k in memoA: return memoA[k]
        Aval = [i for i in range(n) if not (Am >> i) & 1]
        Bval = [j for j in range(n) if not (Bm >> j) & 1]
        for i in Aval:
            if all(gcd(a[i], b[j]) > 1 for j in Bval):
                memoA[k] = True; return True
            if bob_turn(Am | (1 << i), Bm, i):
                memoA[k] = True; return True
        memoA[k] = False
        return False

    def bob_turn(Am, Bm, ai):
        k = (Am, Bm, ai)
        if k in memoB: return memoB[k]
        Bval = [j for j in range(n) if not (Bm >> j) & 1]
        res = True
        for j in Bval:
            if gcd(a[ai], b[j]) > 1: continue          # 挡不住，Bob 不选
            if not alice_turn(Am, Bm | (1 << j)):
                res = False; break                     # Bob 找到活路
        memoB[k] = res
        return res

    return "Alice" if alice_turn(0, 0) else "Bob"


def py_match(a, b):
    """独立实现：匈牙利求全互质完美匹配"""
    n = len(a)
    mB = [-1] * n
    def dfs(u, vis):
        for v in range(n):
            if gcd(a[u], b[v]) != 1 or vis[v]: continue
            vis[v] = True
            if mB[v] == -1 or dfs(mB[v], vis):
                mB[v] = u; return True
        return False
    matched = sum(1 for i in range(n) if dfs(i, [False] * n))
    return "Bob" if matched == n else "Alice"


# ---------- 1. 官方样例 ----------
print("== 官方样例 ==")
samples = [("1\n2\n4\n", "Alice"), ("1\n2\n3\n", "Bob"), ("5\n3 8 5 2 4\n6 9 10 7 2\n", "Alice")]
ok = True
for inp, exp in samples:
    got = {name: run(exe, inp) for name, exe in EXES.items()}
    flag = all(v == exp for v in got.values())
    ok &= flag
    print(f"  {'OK ' if flag else 'FAIL'} 期望 {exp} | " +
          " | ".join(f"{k} {v}" for k, v in got.items()))

# ---------- 2. 随机对拍（重点压 n=6） ----------
print("== 随机对拍（含 Python 博弈真值 + 匈牙利匹配） ==")
rnd = random.Random(163163)
fails = 0
T = 300
for r in range(T):
    n = 6 if r % 3 != 2 else rnd.randint(1, 6)
    hi = rnd.choice([6, 12, 30])
    a = [rnd.randint(1, hi) for _ in range(n)]
    b = [rnd.randint(1, hi) for _ in range(n)]
    inp = f"{n}\n{' '.join(map(str, a))}\n{' '.join(map(str, b))}\n"
    res = {name: run(exe, inp) for name, exe in EXES.items()}
    res["py博弈"] = py_game(a, b)
    res["py匹配"] = py_match(a, b)
    if len(set(res.values())) != 1:
        fails += 1
        print(f"  FAIL n={n} a={a} b={b} -> {res}")
        if fails > 3: break
print(f"  {T} 组：{'全部一致（6 个实现互不相同的思路）' if fails == 0 else str(fails) + ' 组不一致'}")

# ---------- 3. 排列枚举版的最坏耗时 ----------
print("== 排列枚举版最坏耗时（n=6 全部排列都要跑满的情形） ==")
import time
cases = [([2,4,6,8,10,12], [3,9,27,5,15,21]),   # 只有 b=5 能配 a=6/12，凑不出全互质匹配 -> Alice，外层 720 个排列全跑满
         ([2,4,8,16,6,12], [3,9,27,5,15,21])]   # 同上
exe = EXES["排列枚举"]
for a, b in cases:
    inp = f"6\n{' '.join(map(str, a))}\n{' '.join(map(str, b))}\n"
    t0 = time.perf_counter()
    got, reps = None, 50
    for _ in range(reps):
        got = run(exe, inp)
    dt = (time.perf_counter() - t0) / reps
    print(f"  a={a} b={b} -> {got}，单组 {dt*1000:.2f} ms（每次都是完整的进程启动；纯计算约 5 ms）")

print()
print("结果：" + ("全部通过" if ok and fails == 0 else "有问题"))
