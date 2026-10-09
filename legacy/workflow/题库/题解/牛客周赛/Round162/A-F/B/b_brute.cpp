#include <bits/stdc++.h>
using namespace std;

// 暴力（不同范式）：真把网格画出来，逐格数「这一格有几条边露在外面」再加起来
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n, m, x, y;
        cin >> n >> m >> x >> y;
        vector<vector<int>> g(n + 1, vector<int>(m + 1, 1));
        for (int j = 1; j <= m; ++j) g[x][j] = 0;
        for (int i = 1; i <= n; ++i) g[i][y] = 0;

        long long ans = 0;
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= m; ++j) {
                if (!g[i][j]) continue;
                int exposed = 4;
                if (i > 1 && g[i - 1][j]) --exposed;
                if (i < n && g[i + 1][j]) --exposed;
                if (j > 1 && g[i][j - 1]) --exposed;
                if (j < m && g[i][j + 1]) --exposed;
                ans += exposed;
            }
        cout << ans << '\n';
    }
    return 0;
}
