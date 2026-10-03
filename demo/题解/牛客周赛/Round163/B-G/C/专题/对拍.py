# -*- coding: utf-8 -*-
"""C 题三种解法交叉验证：DFS记忆化 vs 纯DFS vs 匈牙利匹配
   同时统计纯 DFS 的递归调用次数，用来做"记忆化到底省了多少"的对比实验。"""
import os, random, subprocess, sys
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "_build")          # 编译产物：可随时删，重跑本脚本会重新生成

# 现场把四种写法编译出来（源文件都在本目录 / 上一级）——脚本自包含，不依赖预编译的 exe
SOURCES = {
    "记忆化": "C_DFS记忆化.cpp",
    "纯DFS": "C_纯DFS_无记忆化.cpp",
    "匈牙利": os.path.join(HERE, "..", "c.cpp"),
    "你的": "C_你的版本.cpp",
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
    return p.stdout.decode().strip(), p.stderr.decode(errors="replace")

def py_dfs(a, b):
    """Python 逐行复刻 C_DFS记忆化.cpp 的同一算法，用于跨语言对拍"""
    n = len(a)
    memo = {}
    def win(ma, mb):
        if ma == 0: return False
        key = (ma, mb)
        if key in memo: return memo[key]
        res = False
        for i in range(n):
            if not (ma >> i) & 1: continue
            all_blocked = True
            for j in range(n):
                if not (mb >> j) & 1: continue
                if gcd(a[i], b[j]) > 1: continue
                if win(ma ^ (1 << i), mb ^ (1 << j)): continue
                all_blocked = False; break
            if all_blocked:
                res = True; break
        memo[key] = res
        return res
    return "Alice" if win((1 << n) - 1, (1 << n) - 1) else "Bob"

def py_match(a, b):
    """独立实现：匈牙利求最大匹配（验证二分图结论）"""
    n = len(a)
    mB = [-1] * n
    def dfs(u, vis):
        for v in range(n):
            if gcd(a[u], b[v]) != 1 or vis[v]: continue
            vis[v] = True
            if mB[v] == -1 or dfs(mB[v], vis):
                mB[v] = u; return True
        return False
    matched = 0
    for i in range(n):
        if dfs(i, [False] * n): matched += 1
    return "Bob" if matched == n else "Alice"

# ---------- 1. 官方样例 ----------
print("== 官方样例 ==")
samples = [("1\n2\n4\n", "Alice"), ("1\n2\n3\n", "Bob"), ("5\n3 8 5 2 4\n6 9 10 7 2\n", "Alice")]
ok = True
for inp, exp in samples:
    got, _ = run(EXES["记忆化"], inp)
    got2, _ = run(EXES["纯DFS"], inp)
    got3, _ = run(EXES["匈牙利"], inp)
    got4, _ = run(EXES["你的"], inp)
    flag = (got == exp and got2 == exp and got3 == exp and got4 == exp)
    ok &= flag
    print(f"  {'OK ' if flag else 'FAIL'} 期望 {exp} | 记忆化 {got} | 纯DFS {got2} | 匈牙利 {got3} | 你的 {got4}")

# ---------- 2. 随机对拍（重点压 n=6） ----------
print("== 随机对拍：DFS记忆化 vs 纯DFS vs 匈牙利 vs Python 复刻 ==")
rnd = random.Random(163163)
fails = 0
for r in range(600):
    n = 6 if r % 3 != 2 else rnd.randint(1, 6)      # 2/3 的用例压到 n=6
    hi = rnd.choice([6, 12, 30])                    # 小值域 -> 大量 gcd>1，更容易踩到边界
    a = [rnd.randint(1, hi) for _ in range(n)]
    b = [rnd.randint(1, hi) for _ in range(n)]
    inp = f"{n}\n{' '.join(map(str,a))}\n{' '.join(map(str,b))}\n"
    r1, _ = run(EXES["记忆化"], inp)
    r2, _ = run(EXES["纯DFS"], inp)
    r3, _ = run(EXES["匈牙利"], inp)
    r4 = py_dfs(a, b)
    r5 = py_match(a, b)
    r6, _ = run(EXES["你的"], inp)
    if not (r1 == r2 == r3 == r4 == r5 == r6):
        fails += 1
        print(f"  FAIL n={n} a={a} b={b} -> 记忆化{r1} 纯DFS{r2} 匈牙利{r3} py_DFS{r4} py_匹配{r5} 你的{r6}")
        if fails > 3: break
print(f"  600 组：{'全部一致 ✅' if fails == 0 else str(fails) + ' 组不一致 ❌'}")

# ---------- 3. 记忆化省了多少：递归调用次数对比 ----------
print("== 纯 DFS 递归调用次数（同一局面） ==")
for name, a, b in [("n=6 全是互质关系（分支最多）", [2,4,6,8,10,12], [3,5,7,9,11,13]),
                   ("n=6 随机", [6,10,14,15,21,22], [2,3,5,7,11,13]),
                   ("n=6 全同", [2]*6, [2]*6)]:
    inp = f"6\n{' '.join(map(str,a))}\n{' '.join(map(str,b))}\n"
    r_memo, _ = run(EXES["记忆化"], inp)
    r_pure, err = run(EXES["纯DFS"], inp)
    calls = err.strip().split("=")[-1].strip()
    print(f"  {name}: 结果={r_memo} | 纯DFS 调用 {calls} 次 | 记忆化最多只有 2^6*2^6=4096 个状态")

print()
print("结果：" + ("全部通过 ✅" if ok and fails == 0 else "有问题 ❌"))
