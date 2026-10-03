#include <bits/stdc++.h>
using namespace std;

// 暴力：Bellman-Ford，把所有边松弛 n-1 轮（正解是 Dijkstra + 优先队列）。
// 不同的实现范式，用于对拍。只在小图上跑
struct Edge { int u, v; long long d, r; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<Edge> es;
    for (int i = 0; i < m; i++) {
        int u, v;
        long long d, r;
        cin >> u >> v >> d >> r;
        es.push_back({u, v, d, r});
    }

    if (n == 1) { cout << "0 0\n"; return 0; }

    const long long INF = (1LL << 62);
    vector<long long> dist(n + 1, INF), risk(n + 1, INF);
    dist[1] = 0;
    risk[1] = 0;

    for (int round = 1; round <= n - 1; round++) {
        bool changed = false;
        for (const Edge &e : es) {
            if (dist[e.u] == INF) continue;
            long long nd = dist[e.u] + e.d;
            long long nr = risk[e.u] + e.r;
            if (nd < dist[e.v] || (nd == dist[e.v] && nr < risk[e.v])) {
                dist[e.v] = nd;
                risk[e.v] = nr;
                changed = true;
            }
        }
        if (!changed) break;
    }

    if (dist[n] == INF) cout << "-1 -1\n";
    else cout << dist[n] << ' ' << risk[n] << '\n';
    return 0;
}
