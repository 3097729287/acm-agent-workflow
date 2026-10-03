#include <bits/stdc++.h>
using namespace std;

// 暴力（不同范式）：枚举每个 [l,r]，直接扫一遍求最大/最小，再跟左右两侧比
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    long long ans = 0;
    for (int l = 1; l <= n; ++l) {
        for (int r = l; r <= n; ++r) {
            int mx = a[l], mn = a[l];
            for (int i = l; i <= r; ++i) { mx = max(mx, a[i]); mn = min(mn, a[i]); }

            bool okLeft = true;                 // 左侧没有元素时视作成立
            for (int i = 1; i < l; ++i) if (a[i] >= mx) okLeft = false;
            bool okRight = true;                // 右侧没有元素时视作成立
            for (int i = r + 1; i <= n; ++i) if (a[i] <= mn) okRight = false;

            if (okLeft && okRight) ++ans;
        }
    }
    cout << ans << '\n';
    return 0;
}
