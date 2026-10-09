# -*- coding: utf-8 -*-
"""把「小月的对局」的博弈树完整打印出来（只在 n <= 3、牌少的时候看得清）

用法：
    python 打印博弈树.py            # 用内置的两个例子
    python 打印博弈树.py 2 4 6 3    # 自定义：第 1 个数是 n，接着 n 个 Alice 的牌，再 n 个 Bob 的牌
"""
import sys
from math import gcd
from functools import lru_cache

def solve(a, b):
    n = len(a)
    mem = {}

    def win(ma, mb):
        """Alice 是否必胜（和 C++ 版完全同一套逻辑）"""
        if ma == 0:
            return False
        if (ma, mb) in mem:
            return mem[(ma, mb)]
        res = False
        for i in range(n):
            if not (ma >> i) & 1:
                continue
            blocked_all = True
            for j in range(n):
                if not (mb >> j) & 1:
                    continue
                if gcd(a[i], b[j]) > 1:
                    continue
                if win(ma ^ (1 << i), mb ^ (1 << j)):
                    continue
                blocked_all = False
                break
            if blocked_all:
                res = True
                break
        mem[(ma, mb)] = res
        return res

    print(f"局面：Alice {a}  vs  Bob {b}")
    print(f"结论：{'Alice 必胜' if win((1 << n) - 1, (1 << n) - 1) else 'Bob 必胜'}")
    print()
    print("博弈树（缩进表示深度；【】里是这一步的结果）：")

    def show(ma, mb, depth, label):
        pad = "    " * depth
        if ma == 0:
            print(f"{pad}{label} -> Alice 没牌了，Bob 胜")
            return
        verdict = "必胜" if win(ma, mb) else "必败"
        print(f"{pad}{label} [这个局面 Alice {verdict}]")
        for i in range(n):
            if not (ma >> i) & 1:
                continue
            pad2 = "    " * (depth + 1)
            print(f"{pad2}Alice 出 {a[i]}：")
            any_escape = False
            for j in range(n):
                if not (mb >> j) & 1:
                    continue
                pad3 = "    " * (depth + 2)
                if gcd(a[i], b[j]) > 1:
                    print(f"{pad3}Bob 出 {b[j]} -> gcd({a[i]},{b[j]})={gcd(a[i],b[j])}>1，Alice 立刻获胜 ✗")
                    continue
                if win(ma ^ (1 << i), mb ^ (1 << j)):
                    print(f"{pad3}Bob 出 {b[j]} -> gcd=1 安全，但之后 Alice 仍必胜 ✗")
                else:
                    print(f"{pad3}Bob 出 {b[j]} -> gcd=1 安全，之后 Alice 必败 ✓ Bob 会选这个")
                    show(ma ^ (1 << i), mb ^ (1 << j), depth + 3, "继续：")
                    any_escape = True
                    break          # Bob 找到一个能逃的就够了，和代码里的 break 对应
            if not any_escape:
                print(f"{pad2}=> Bob 无路可逃，Alice 出 {a[i]} 就能赢")

    show((1 << n) - 1, (1 << n) - 1, 0, "根局面：")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        v = list(map(int, sys.argv[1:]))
        n = v[0]
        solve(v[1:1 + n], v[1 + n:1 + 2 * n])
    else:
        solve([2, 4], [6, 3])      # Alice 必胜的小例子
        print("=" * 60)
        solve([2, 3], [4, 9])      # Alice 必败的小例子
