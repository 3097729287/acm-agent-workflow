// 牛客周赛 Round 140 D - 小红的排序（easy）
// 思路：交换操作是「位置 i 与位置 i+x / i+y」的对换，能生成每个连通分量内的任意置换。
//       并查集维护位置图；可排序 <=> 每个值 v 的当前位置 p[v] 与 v 同属一个分量。
#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> f;
    explicit DSU(int n) : f(n + 1) {
        iota(f.begin(), f.end(), 0);
    }
    int find(int x) {                 // 迭代 + 路径减半，别写递归
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
            if (d.find(v) != d.find(p[v])) {   // 值 v 最终要落在位置 v 上
                ok = false;
                break;
            }
        }
        cout << (ok ? "Yes" : "No") << "\n";
    }
    return 0;
}
