#include <bits/stdc++.h>
using namespace std;

// 暴力（不同范式）：枚举所有节点子集，检查「非空 + 连通 + 盖住所有坏边」，取最小大小
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    string s;
    cin >> s;

    vector<vector<int>> adj(n + 1);
    vector<pair<int, int>> edges;
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    vector<int> bad;                            // 坏边（两端异色）
    for (auto [u, v] : edges) if (s[u - 1] != s[v - 1]) bad.push_back(u * (n + 2) + v);

    int ans = n;
    for (int mask = 1; mask < (1 << n); ++mask) {
        vector<int> in(n + 1, 0);
        int cnt = 0, root = -1;
        for (int i = 1; i <= n; ++i) if (mask >> (i - 1) & 1) { in[i] = 1; ++cnt; root = i; }
        if (cnt >= ans) continue;

        // 连通性：从任一点出发只在集合内 BFS，看能否走遍
        vector<int> vis(n + 1, 0);
        queue<int> q;
        q.push(root); vis[root] = 1;
        int reach = 1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) if (in[v] && !vis[v]) { vis[v] = 1; ++reach; q.push(v); }
        }
        if (reach != cnt) continue;

        bool cover = true;
        for (int code : bad) {
            int u = code / (n + 2), v = code % (n + 2);
            if (!in[u] && !in[v]) { cover = false; break; }
        }
        if (cover) ans = cnt;
    }
    cout << ans << '\n';
    return 0;
}
