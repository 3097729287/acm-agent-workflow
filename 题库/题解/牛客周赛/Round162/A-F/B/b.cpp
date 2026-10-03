#include <bits/stdc++.h>
using namespace std;

// 抽掉第 x 行、第 y 列后，剩下的格子被切成若干块矩形：
//   行被切成两段（高 x-1 和 n-x），列被切成两段（宽 y-1 和 m-y）
//   非空行段 H 个、非空列段 W 个 -> 共 H*W 块，每块 h 行 w 列，周长 2(h+w)
// 总和 = 2 * ( W*(n-1) + H*(m-1) )   （所有行段高之和 = n-1，所有列段宽之和 = m-1）
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        long long n, m, x, y;
        cin >> n >> m >> x >> y;

        int H = (x - 1 > 0) + (n - x > 0);   // 非空行段个数
        int W = (y - 1 > 0) + (m - y > 0);   // 非空列段个数
        long long totH = n - 1;              // 行段高之和
        long long totW = m - 1;              // 列段宽之和

        cout << 2 * (W * totH + H * totW) << '\n';
    }
    return 0;
}
