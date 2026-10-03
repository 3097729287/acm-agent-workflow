// 牛客周赛 Round 140 E - 小红的排序（hard）
// 思路：与 easy 完全同一套做法——交换能力等价于「位置图每个连通分量内可任意重排」，
//       并查集维护位置图，判每个值 v 的当前位置 p[v] 是否与 v 同分量。
//       差别只在约束（本题 x,y < n，可换的对更少），算法不变，O(n α(n))。
#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> f;
    explicit DSU(int n) : f(n + 1) {
        iota(f.begin(), f.end(), 0);
    }
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

    int T;
    cin >> T;
    while (T--) {
        int n, x, y;
        cin >> n >> x >> y;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; i++) cin >> p[i];

        DSU d(n);
        for (int i = 1; i + x <= n; i++) d.unite(i, i + x);
        for (int i = 1; i + y <= n; i++) d.unite(i, i + y);

        bool ok = true;
        for (int v = 1; v <= n; v++) {
            if (d.find(v) != d.find(p[v])) {
                ok = false;
                break;
            }
        }
        cout << (ok ? "Yes" : "No") << "\n";
    }
    return 0;
}
