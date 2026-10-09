#include <bits/stdc++.h>
using namespace std;

// 暴力：递归洪水填充（正解是队列 BFS），方向用显式数组（正解用 dx/dy 双重循环）。
// 不同的实现范式，用于对拍。只在小网格上跑，递归不会爆栈
int n, m;
vector<string> g;
vector<vector<int>> vis;
int area;

int dx4[4] = {-1, 1, 0, 0};
int dy4[4] = {0, 0, -1, 1};
int dx8[8] = {-1, -1, -1, 0, 0, 1, 1, 1};
int dy8[8] = {-1, 0, 1, -1, 1, -1, 0, 1};

void flood(int x, int y, bool eight) {
    vis[x][y] = 1;
    area++;
    int cnt = eight ? 8 : 4;
    for (int t = 0; t < cnt; t++) {
        int nx = x + (eight ? dx8[t] : dx4[t]);
        int ny = y + (eight ? dy8[t] : dy4[t]);
        if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
        if (g[nx][ny] != '1' || vis[nx][ny]) continue;
        flood(nx, ny, eight);
    }
}

int count_blocks(bool eight, int &smax) {
    vis.assign(n, vector<int>(m, 0));
    int cnt = 0;
    smax = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            if (g[i][j] == '1' && !vis[i][j]) {
                cnt++;
                area = 0;
                flood(i, j, eight);
                smax = max(smax, area);
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
    int c4 = count_blocks(false, s4);
    int c8 = count_blocks(true, s8);
    cout << c4 - c8 << ' ' << s4 << ' ' << s8 << '\n';
    return 0;
}
