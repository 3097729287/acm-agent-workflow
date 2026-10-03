#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    long long d, r;      // 距离、风险，都要 long long：路径最长 2e5 条边 × 1e9
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<Edge>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        long long d, r;
        cin >> u >> v >> d >> r;
        adj[u].push_back({v, d, r});
    }

    if (n == 1) {                    // 起点就是终点
        cout << "0 0\n";
        return 0;
    }

    const long long INF = (1LL << 62);
    vector<long long> dist(n + 1, INF), risk(n + 1, INF);

    // 按距离排序的小根堆；距离相同时靠下面的松弛把风险压到最小
    priority_queue<pair<long long, int>,
                   vector<pair<long long, int>>,
                   greater<pair<long long, int>>> pq;

    dist[1] = 0;
    risk[1] = 0;
    pq.push({0, 1});

    while (!pq.empty()) {
        auto [du, u] = pq.top();
        pq.pop();
        if (du != dist[u]) continue;          // 这是过时的一份，丢掉

        for (const Edge &e : adj[u]) {
            long long nd = dist[u] + e.d;
            long long nr = risk[u] + e.r;
            // 距离更小 → 换；距离一样但风险更小 → 也换
            if (nd < dist[e.to] || (nd == dist[e.to] && nr < risk[e.to])) {
                dist[e.to] = nd;
                risk[e.to] = nr;
                pq.push({nd, e.to});
            }
        }
    }

    if (dist[n] == INF) cout << "-1 -1\n";
    else cout << dist[n] << ' ' << risk[n] << '\n';
    return 0;
}
