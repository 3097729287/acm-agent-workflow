# -*- coding: utf-8 -*-
"""例子分析器：把一个局面的所有关键信息算出来，供教学使用
   - 谁赢（博弈搜索）
   - 互质关系表（Bob 能安全接住哪张）
   - Alice 每一种首发牌的效果
   - Bob 赢：给出一组完美配对作为"作战手册"
   - Alice 赢：给出一个 Hall 缺口（哪几张牌挤在一张上）
"""
from math import gcd
from itertools import combinations

def analyze(A, B, verbose=True):
    n = len(A)
    memo = {}
    def win(ma, mb):
        if ma == 0: return False
        if (ma, mb) in memo: return memo[(ma, mb)]
        res = False
        for i in range(n):
            if not (ma >> i) & 1: continue
            blocked = True
            for j in range(n):
                if not (mb >> j) & 1: continue
                if gcd(A[i], B[j]) > 1: continue
                if win(ma ^ (1 << i), mb ^ (1 << j)): continue
                blocked = False; break
            if blocked:
                res = True; break
        memo[(ma, mb)] = res
        return res

    full = (1 << n) - 1
    winner = "Alice" if win(full, full) else "Bob"

    # 互质关系
    safe = [[j for j in range(n) if gcd(A[i], B[j]) == 1] for i in range(n)]

    # Alice 每一种首发牌：这招能不能直接锁定胜利
    first = []
    for i in range(n):
        blocked = True
        for j in range(n):
            if gcd(A[i], B[j]) > 1: continue
            if win(full ^ (1 << i), full ^ (1 << j)): continue
            blocked = False; break
        first.append(blocked)     # True = 出这张就能赢

    # 完美匹配（Bob 的作战手册）
    def find_matching():
        mB = [-1] * n
        def dfs(u, vis):
            for v in safe[u]:
                if vis[v]: continue
                vis[v] = True
                if mB[v] == -1 or dfs(mB[v], vis):
                    mB[v] = u; return True
            return False
        cnt = 0
        for i in range(n):
            if dfs(i, [False] * n): cnt += 1
        return cnt, mB

    cnt, mB = find_matching()

    # 最小 Hall 缺口：找 |N(S)| < |S| 的最小子集
    hall = None
    if cnt < n:
        for size in range(1, n + 1):
            found = None
            for S in combinations(range(n), size):
                N = set()
                for i in S: N.update(safe[i])
                if len(N) < size:
                    found = (S, sorted(N)); break
            if found:
                hall = found; break

    if verbose:
        print(f"局面：Alice {A}  vs  Bob {B}")
        print(f"结论：{'Alice 必胜' if winner == 'Alice' else 'Bob 必胜'}")
        print("互质关系（Bob 能安全接住的牌）：")
        for i in range(n):
            names = [B[j] for j in safe[i]] or ["（一张都没有！）"]
            print(f"   Alice 的 {A[i]:>3}  <-  {names}")
        print("Alice 的首发效果：")
        for i in range(n):
            print(f"   出 {A[i]:>3} -> {'✅ 这一招直接锁定胜局' if first[i] else '❌ Bob 有办法化解'}")
        if cnt == n:
            pairs = sorted((A[mB[j]], B[j]) for j in range(n))
            print(f"Bob 的作战手册（完美配对）：{pairs}")
        else:
            S, N = hall
            print(f"Hall 缺口：Alice 的 {[A[i] for i in S]} 只能挤在 Bob 的 {[B[j] for j in N] or '空集（没有一张接得住）'} 上，"
                  f"{len(S)} 张抢 {len(N)} 个位置")
        print(f"Alice 有 {sum(first)} 种能赢的首发牌（若为 Bob 必胜则全为 0）")
        print()
    return winner, first, safe, (cnt, mB), hall


if __name__ == "__main__":
    cases = [
        ([4, 6, 7], [2, 3, 5]),
    ]
    for A, B in cases:
        analyze(A, B)
