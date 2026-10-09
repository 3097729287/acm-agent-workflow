#include <bits/stdc++.h>
using namespace std;

// 转化：剩余每个连通块同色 <=> 剩余图里没有一条「两端异色」的边（坏边）
//   => 要删的连通点集 D 必须盖住每条坏边（每条坏边至少一个端点在 D 里）
// 树形 DP：以 1 为根，D 是一棵连通子树，设它的最浅点是 top
//   badCnt[u] = subtree(u) 内部的坏边条数（不含 u 与父亲那条边）
//   F[u] = 以 u 为顶、盖住 subtree(u) 内所有坏边所需的最少点数
//        = 1 + sum_{v 是 u 的儿子} (badCnt[v] > 0 ? F[v] : 0)
//        （u 自己在 D 里，所以 (u,v) 这条边无论好坏都被盖住；
//          v 的子树里若根本没有坏边，就不必再往下选，选了反而更贵）
//   top 合法 <=> 不在 subtree(top) 里的坏边最多只有 (parent(top), top) 这一条
// 答案 = 合法 top 中最小的 F[top]
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    string s;
    cin >> s;                                   // s[i-1] 是 i 号点的颜色

    vector<vector<int>> adj(n + 1);
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // 迭代 DFS 定父子（递归在 2e5 的链上会爆栈）
    vector<int> parent(n + 1, 0), order;
    order.reserve(n);
    parent[1] = -1;
    order.push_back(1);
    for (int idx = 0; idx < (int)order.size(); ++idx) {
        int u = order[idx];
        for (int v : adj[u])
            if (v != parent[u]) { parent[v] = u; order.push_back(v); }
    }

    vector<long long> F(n + 1, 1);
    vector<int> badCnt(n + 1, 0);
    for (int idx = n - 1; idx >= 0; --idx) {    // 逆序 = 自底向上
        int u = order[idx];
        long long f = 1;
        for (int v : adj[u]) {
            if (parent[v] != u) continue;
            if (badCnt[v] > 0) f += F[v];
            badCnt[u] += badCnt[v];
            if (s[u - 1] != s[v - 1]) ++badCnt[u];
        }
        F[u] = f;
    }

    int total = badCnt[1];                      // 全树的坏边条数
    long long ans = n;
    for (int top = 1; top <= n; ++top) {
        int out = total - badCnt[top];          // 不在 subtree(top) 里的坏边条数
        bool ok;
        if (out == 0) ok = true;
        else if (out == 1 && parent[top] != -1 && s[parent[top] - 1] != s[top - 1])
            ok = true;                          // 唯一的例外是 (parent(top), top)，被 top 自己盖住
        else ok = false;
        if (ok) ans = min(ans, F[top]);
    }
    cout << ans << '\n';
    return 0;
}
