#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// E 题暴力：枚举 0..n-1 的全部排列，逐个算子段 mex 之和，取最大并数个数。
// 实现范式与正解不同：正解只算一个 2 的幂，暴力真的把每个排列的每个子段 mex 都算一遍。
// 另外顺手验一件事：正解注释里写的最大权值公式 M(n) = 2^n - 3m^2 - 6m - 4 (m = n/2)
// 是不是等于暴力算出来的最大值 —— 数对了但权值公式错了同样是错的。
// n <= 9 时可用（9! = 362880）。

int n;
vector<int> p;
vector<char> used;
ll bestW, bestCnt;

ll weightOf() {
    ll tot = 0;
    for (int i = 0; i < n; ++i) {
        vector<char> seen(n + 1, 0);
        int mex = 0;
        for (int j = i; j < n; ++j) {
            seen[p[j]] = 1;
            while (mex <= n && seen[mex]) ++mex;
            tot += mex;
        }
    }
    return tot;
}

void dfs(int dep) {
    if (dep == n) {
        ll w = weightOf();
        if (w > bestW) { bestW = w; bestCnt = 1; }
        else if (w == bestW) ++bestCnt;
        return;
    }
    for (int v = 0; v < n; ++v) {
        if (used[v]) continue;
        used[v] = 1;
        p[dep] = v;
        dfs(dep + 1);
        used[v] = 0;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n;
    if (n == 1) { cout << 1 << "\n"; return 0; }
    p.assign(n, 0);
    used.assign(n, 0);
    bestW = -1;
    bestCnt = 0;
    dfs(0);

    // 顺带自检：把暴力的最大权值打到 stderr，供人核对公式
    // （数对了、权值公式写错，同样是错的，所以两个都打出来）
    ll m = n / 2;
    ll pred = (4 * m * m * m - m) / 3 + 2 * m * m + 3 * m + 1;
    fprintf(stderr, "DIAG n=%d 最大权值=%lld 公式=%lld %s 最优个数=%lld\n",
            n, bestW, pred, bestW == pred ? "一致" : "★不一致★", bestCnt);

    cout << bestCnt % 1000000007LL << "\n";
    return 0;
}
