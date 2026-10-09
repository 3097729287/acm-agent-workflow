# -*- coding: utf-8 -*-
"""对 unpair_ticks.keep() 的回归自测：真代码必须保留灰底，数学记号必须去掉灰底。"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unpair_ticks import keep

# 必须【保留】灰底（真代码：标识符 / 函数 / 路径 / 仓库名 / 关键词）
KEEP = [
    "flow_reps", "water_glow", "bloom_str", "flow_env_amt", "flow_dark", "flow_lift",
    "flow_soft", "flow_sharp", "flow_fil_k", "flow_beta", "flow_tex", "flow_freq",
    "caustic_hi", "caustic_lo", "glint_str", "glint_thr", "scroll_cycles",
    "grabCut", "findContours(RETR_EXTERNAL)", "DistanceTransform",
    "DepthFlow", "Texture-Distortion", "particular-drift", "someorg/some-repo",
    "_work/", "render.py", "check.py", "geom.npz", "说明.md",
    "vignette", "contrast", "warm",
    "INT_MAX", "LLONG_MAX", "__int128", "lower_bound", "unordered_map", "dfs", "cout",
    "dp[i][j]", "a[i]", "v.size()", "cv2.remap", "np.clip", "int", "bool", "vector",
    "MOD = 998244353", "https://ac.nowcoder.com/acm/contest/126120",
    # 2026-10-01 晚补：斜杠命令与带前导 / 的路径（火山引擎接入手册逼出来的）
    "claude", "/status", "/model", "/api/plan", "/api/plan/v3", "/api/coding",
    "/usr/bin/python3",
]

# 必须【去掉】灰底（数学记号：变量 / 旧式下标 / 区间 / 公式）
DROP = [
    "x_i", "n_max", "a_i", "a_j", "b_k", "dp_i", "s_j", "t_k", "cnt_i",
    "n", "x", "s", "d", "p", "k", "i", "j", "O(n)", "O(nlog n)",
    "n <= 10^5", "10^18", "2<=n<=2e5", "a <= b", "x + y",
    "[1, n]", "[l, r]", "[1, n], [1, m]", "sum_{i=1}^{n}", "P(A|B)", "X ~ N(0,1)",
    "x = 帧号 / (时长×帧率)", "lum > 125", "f(x)", "log2 n", "n^2", "a<b",
    "/x",   # 单字母斜杠：更像除法记号，斜杠命令规则故意不放过（2026-10-01 边界样本）
]


def main():
    bad = []
    for s in KEEP:
        if not keep(s):
            bad.append(("该保留却去掉", s))
    for s in DROP:
        if keep(s):
            bad.append(("该去掉却保留", s))
    for kind, s in bad:
        print("!! %s: %s" % (kind, s))
    print()
    if bad:
        print("回归自测: 有 %d 处不符   (保留 %d / 去掉 %d 条样本)"
              % (len(bad), len(KEEP), len(DROP)))
        sys.exit(1)
    print("回归自测: 全部通过 ✓   (保留 %d / 去掉 %d 条样本)" % (len(KEEP), len(DROP)))


if __name__ == "__main__":
    main()
