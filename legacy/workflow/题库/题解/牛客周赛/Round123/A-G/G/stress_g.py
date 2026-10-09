# -*- coding: utf-8 -*-
"""G 题随机对拍（Special Judge 版）。

G 题的答案不唯一，不能直接比字符串，所以这里做两件事：
  1. 跑 g.cpp，把它的输出**逐条当方案验证**：下标合法且不重复、新数字在 [1,2e9]、
     改完之后 n 张牌的数字**互不相同且连续**（也就是一个顺子）；
  2. 跑 g_brute.cpp（枚举起点 L 的暴力）拿最优次数，和方案里的 k 比。
两边任何一边出问题都会当场报出来。

用法：python stress_g.py [组数]
"""
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "g.exe")
GB = os.path.join(HERE, "g_brute.exe")


def run(exe, inp):
    r = subprocess.run([exe], input=inp.encode(), capture_output=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("%s 退出码 %d：%s" % (exe, r.returncode,
                                              r.stderr.decode("utf-8", "replace")[:300]))
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def check(n, a, out):
    """返回方案里的 k；方案不合法就抛异常。"""
    lines = out.strip().split("\n") if out.strip() else []
    k = int(lines[0])
    assert len(lines) - 1 == k, "第一行说改 %d 张，实际给了 %d 行" % (k, len(lines) - 1)
    assert 0 <= k <= n, "k = %d 越界" % k

    changed = {}
    for ln in lines[1:]:
        i, x = map(int, ln.split())
        assert 1 <= i <= n, "下标 %d 越界" % i
        assert i not in changed, "下标 %d 改了两次" % i
        assert 1 <= x <= 2 * 10 ** 9, "新数字 %d 越界" % x
        changed[i] = x

    final = [changed.get(i, a[i - 1]) for i in range(1, n + 1)]
    final.sort()
    assert final[0] >= 1, "顺子起点 %d < 1" % final[0]
    for t in range(1, n):
        assert final[t] == final[t - 1] + 1, \
            "改完之后不是顺子：%s" % final[:20]
    return k


def gen(rng):
    n = rng.randint(1, 7)
    V = rng.randint(1, 12)
    return n, [rng.randint(1, V) for _ in range(n)]


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    rng = random.Random(20261001)
    bad = 0
    for it in range(rounds):
        n, a = gen(rng)
        inp = "%d\n%s\n" % (n, " ".join(map(str, a)))
        got = run(G, inp)
        try:
            k = check(n, a, got)
        except AssertionError as e:
            bad += 1
            print("★第 %d 组方案不合法★ 输入=%r" % (it + 1, inp))
            print("   原因：%s" % e)
            print("   输出：%r" % got[:300])
            if bad >= 3:
                break
            continue
        kbest = int(run(GB, inp).strip().split("\n")[0])
        if k != kbest:
            bad += 1
            print("★第 %d 组不是最优★ 输入=%r" % (it + 1, inp))
            print("   g.cpp 改了 %d 张，暴力最优 %d 张" % (k, kbest))
            if bad >= 3:
                break
    print("实际跑了 %d 组（设计 %d 组），不一致 %d 组。" % (rounds if bad < 3 else it + 1, rounds, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
