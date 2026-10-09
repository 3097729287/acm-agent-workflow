// 牛客周赛 Round 140 G - 小红的生成树构造
// 结论：可行 <=> 「只由 A/B 点组成的每个连通块里 A、B 都有」且「只由 C/D 点组成的每个连通块里 C、D 都有」。
// 构造：组内边（A-B 之间 / C-D 之间）用并查集取生成森林，缩点后在「跨组边」上 BFS 取生成树。
#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> f;
    explicit DSU(int n) : f(n + 1) { iota(f.begin(), f.end(), 0); }
    int find(int x) {
        while (f[x] != x) {
            f[x] = f[f[x]];
            x = f[x];
        }
        return x;
    }
    void unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a != b) f[a] = b;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    string s;
    cin >> s;                                   // s[v-1] 是 v 号点的标记

    vector<int> eu(m), ev(m);
    for (int i = 0; i < m; i++) cin >> eu[i] >> ev[i];

    // 第 0 组 = A/B，第 1 组 = C/D
    auto grp = [&](int v) { return (s[v - 1] == 'A' || s[v - 1] == 'B') ? 0 : 1; };
    // 每组里的「前一半字母」：A/B 组的 A，C/D 组的 C
    auto first = [&](int v) { return (s[v - 1] == 'A' || s[v - 1] == 'C') ? 1 : 2; };

    DSU d(n);
    vector<pair<int, int>> ans;

    // ① 组内边：取生成森林
    for (int i = 0; i < m; i++) {
        if (grp(eu[i]) == grp(ev[i]) && d.find(eu[i]) != d.find(ev[i])) {
            d.unite(eu[i], ev[i]);
            ans.push_back({eu[i], ev[i]});
        }
    }

    // ② 每个组内连通块必须同时含「前一半」和「后一半」字母
    vector<int> mask(n + 1, 0);
    for (int v = 1; v <= n; v++) mask[d.find(v)] |= first(v);
    for (int v = 1; v <= n; v++) {
        if (mask[d.find(v)] != 3) {             // 只有 A 没 B（或只有 C 没 D）
            cout << "No\n";
            return 0;
        }
    }

    // ③ 缩点：并查集分量 -> 新点，跨组边建图
    vector<int> id(n + 1, -1);
    int cnt = 0;
    for (int v = 1; v <= n; v++) {
        int r = d.find(v);
        if (id[r] == -1) id[r] = cnt++;
    }
    vector<vector<pair<int, int>>> cadj(cnt);
    for (int i = 0; i < m; i++) {
        if (grp(eu[i]) != grp(ev[i])) {
            int a = id[d.find(eu[i])], b = id[d.find(ev[i])];
            cadj[a].push_back({b, i});
            cadj[b].push_back({a, i});
        }
    }
    vector<char> vis(cnt, 0);
    vector<int> q;
    q.push_back(id[d.find(1)]);
    vis[q[0]] = 1;
    for (size_t h = 0; h < q.size(); h++) {     // BFS 取缩点图的生成树
        int u = q[h];
        for (auto &pr : cadj[u]) {
            int v = pr.first, ei = pr.second;
            if (!vis[v]) {
                vis[v] = 1;
                q.push_back(v);
                ans.push_back({eu[ei], ev[ei]});
            }
        }
    }

    cout << "Yes\n";
    for (auto &e : ans) cout << e.first << " " << e.second << "\n";
    return 0;
}
