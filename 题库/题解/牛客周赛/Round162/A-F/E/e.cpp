#include <bits/stdc++.h>
using namespace std;

// 子数组 [l,r] 新鲜 <=> max(a[l..r]) > preMax[l]  且  min(a[l..r]) < sufMin[r]
//   其中 preMax[l] = max(a[1..l-1])（l=1 时为 0，空集条件恒真）
//        sufMin[r] = min(a[r+1..n])（r=n 时为 n+1，空集条件恒真）
// 两个条件都随 r 单调：max 只会变大、min 只会变小，而阈值一个固定一个单调
//   => 对每个 l，两个条件各自形如「r >= 某个阈值」，二分找阈值即可
// 区间 max / min 用稀疏表 O(1) 查询，总复杂度 O(n log n)
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<int> preMax(n + 2, 0), sufMin(n + 2, n + 1);
    for (int i = 2; i <= n; ++i) preMax[i] = max(preMax[i - 1], a[i - 1]);  // preMax[1] = 0
    for (int i = n - 1; i >= 1; --i) sufMin[i] = min(sufMin[i + 1], a[i + 1]);
    sufMin[n] = n + 1;

    int K = 32 - __builtin_clz(n);            // = floor(log2 n) + 1
    vector<vector<int>> stMax(K, vector<int>(n + 2)), stMin(K, vector<int>(n + 2));
    for (int i = 1; i <= n; ++i) stMax[0][i] = stMin[0][i] = a[i];
    for (int k = 1; k < K; ++k)
        for (int i = 1; i + (1 << k) - 1 <= n; ++i) {
            stMax[k][i] = max(stMax[k - 1][i], stMax[k - 1][i + (1 << (k - 1))]);
            stMin[k][i] = min(stMin[k - 1][i], stMin[k - 1][i + (1 << (k - 1))]);
        }
    auto qMax = [&](int l, int r) {
        int k = 31 - __builtin_clz(r - l + 1);
        return max(stMax[k][l], stMax[k][r - (1 << k) + 1]);
    };
    auto qMin = [&](int l, int r) {
        int k = 31 - __builtin_clz(r - l + 1);
        return min(stMin[k][l], stMin[k][r - (1 << k) + 1]);
    };

    long long ans = 0;
    for (int l = 1; l <= n; ++l) {
        // 条件一：max(a[l..r]) > preMax[l]
        int r1 = n + 1;
        if (qMax(l, n) > preMax[l]) {
            int lo = l, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) >> 1;
                if (qMax(l, mid) > preMax[l]) hi = mid; else lo = mid + 1;
            }
            r1 = lo;
        }
        // 条件二：min(a[l..r]) < sufMin[r]
        int r2 = n + 1;
        if (qMin(l, n) < sufMin[n]) {          // sufMin[n] = n+1，r=n 时必成立，所以一定存在
            int lo = l, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) >> 1;
                if (qMin(l, mid) < sufMin[mid]) hi = mid; else lo = mid + 1;
            }
            r2 = lo;
        }
        int start = max(r1, r2);
        if (start <= n) ans += n - start + 1;
    }
    cout << ans << '\n';
    return 0;
}
