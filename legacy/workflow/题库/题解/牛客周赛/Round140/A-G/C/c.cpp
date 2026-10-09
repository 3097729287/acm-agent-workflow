// 牛客周赛 Round 140 C - 小红的矩阵计数
// 思路：每个 L 块 ↔ (某个 2×2 方阵, 缺的那一格)，共 4 种。
//       枚举每个 2×2 窗口的 4 个三元组，判断三个字符是否互不相同。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<string> g(n);
    for (auto &row : g) cin >> row;

    long long ans = 0;
    for (int i = 0; i + 1 < n; i++) {
        for (int j = 0; j + 1 < m; j++) {
            char a = g[i][j], b = g[i][j + 1];
            char c = g[i + 1][j], d = g[i + 1][j + 1];
            char tri[4][3] = {{a, b, c}, {a, b, d}, {a, c, d}, {b, c, d}};
            for (int k = 0; k < 4; k++) {
                char x = tri[k][0], y = tri[k][1], z = tri[k][2];
                if (x != y && y != z && x != z) ans++;   // 恰好 0、1、2 各一个
            }
        }
    }
    cout << ans << "\n";
    return 0;
}
