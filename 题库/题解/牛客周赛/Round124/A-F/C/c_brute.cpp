#include <bits/stdc++.h>
using namespace std;

// C 题暴力：直接按定义判「加一个棋子后能否出现 m 子连珠」。
// 实现范式与正解不同：正解是排序后数最长连续段，暴力是把棋盘摊开到足够大的区间上，
// 对每个可能的落点用滑动窗口数「这一段里已经有几个棋子」，再判有没有达到 m。
// 只在坐标范围很小（坐标 <= 40）时用，供对拍。

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    while (T--) {
        int n;
        long long m;
        cin >> n >> m;
        vector<long long> a(n);
        for (int i = 0; i < n; ++i) cin >> a[i];

        // 把所有棋子放进一个布尔数组：坐标 1..40
        const int MAXC = 40;
        vector<int> occ(MAXC + 2, 0);
        for (int i = 0; i < n; ++i) occ[(int)a[i]] = 1;

        bool ok = false;
        for (int put = 1; put <= MAXC && !ok; ++put) {   // 枚举新棋子落点
            if (occ[put]) continue;                      // 该格已有棋子
            occ[put] = 1;
            // 枚举这段 m 个连续格子的起点，看有没有一段被填满
            for (int x = 1; x + m - 1 <= MAXC; ++x) {
                bool full = true;
                for (long long t = 0; t < m; ++t)
                    if (!occ[x + (int)t]) { full = false; break; }
                if (full) { ok = true; break; }
            }
            occ[put] = 0;
        }
        cout << (ok ? "YES" : "NO") << "\n";
    }
    return 0;
}
