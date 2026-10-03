#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<string> g;

// eight = false 走四连通，true 走八连通。
// 返回连通块个数，最大面积写进 smax
int count_blocks(bool eight, int &smax) {
    vector<vector<char>> vis(n, vector<char>(m, 0));
    int cnt = 0;
    smax = 0;

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (g[i][j] != '1' || vis[i][j]) continue;

            cnt++;                       // 发现一个新连通块
            int area = 0;
            queue<pair<int, int>> q;
            vis[i][j] = 1;
            q.push({i, j});

            while (!q.empty()) {
                auto [x, y] = q.front();
                q.pop();
                area++;

                for (int dx = -1; dx <= 1; dx++) {
                    for (int dy = -1; dy <= 1; dy++) {
                        if (dx == 0 && dy == 0) continue;              // 自己不算邻居
                        if (!eight && abs(dx) + abs(dy) != 1) continue; // 四连通只要上下左右
                        int nx = x + dx, ny = y + dy;
                        if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                        if (g[nx][ny] != '1' || vis[nx][ny]) continue;
                        vis[nx][ny] = 1;
                        q.push({nx, ny});
                    }
                }
            }
            smax = max(smax, area);
        }
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    g.resize(n);
    for (int i = 0; i < n; i++) cin >> g[i];

    int s4, s8;
    int c4 = count_blocks(false, s4);   // 四连通
    int c8 = count_blocks(true,  s8);   // 八连通

    cout << c4 - c8 << ' ' << s4 << ' ' << s8 << '\n';
    return 0;
}
