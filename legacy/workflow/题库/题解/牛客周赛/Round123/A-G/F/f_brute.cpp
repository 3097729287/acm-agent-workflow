// F 题暴力（跟正解**不同实现范式**）：正解用 Σ max(0, cnt[v]-cnt[v-1]) 这个公式，
// 这里**穷举所有划分方式**求真正的最小顺子数（带记忆化，只在小数据上用）。
// 做法：每次取当前最小的非空数字 v，枚举「包含 v 的那个顺子」有多长
//       （必须是 v, v+1, ... 连续且都有牌），扣掉再递归，取最小。
#include <bits/stdc++.h>
using namespace std;

int V;                                  // 最大点数
map<vector<int>, int> memo;

int dfs(vector<int> c) {                // c[v] = 数字 v 还剩几张
    auto it = memo.find(c);
    if (it != memo.end()) return it->second;

    int v = -1;
    for (int i = 1; i <= V; i++) if (c[i] > 0) { v = i; break; }
    if (v < 0) return memo[c] = 0;      // 出完了

    int best = INT_MAX;
    for (int len = 1; v + len - 1 <= V; len++) {
        if (c[v + len - 1] == 0) break;          // 顺子必须连续
        for (int t = 0; t < len; t++) c[v + t]--;
        best = min(best, 1 + dfs(c));
        for (int t = 0; t < len; t++) c[v + t]++;
    }
    return memo[c] = best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    V = 1;
    for (int i = 1; i <= n; i++) { cin >> a[i]; V = max(V, a[i]); }

    vector<int> c(V + 2, 0);
    for (int i = 1; i <= n; i++) {
        c[a[i]]++;
        cout << dfs(c) << (i == n ? '\n' : ' ');
    }
    return 0;
}
