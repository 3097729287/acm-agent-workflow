// G - 小月的环
// 每个置换环（组）只关心它的最小值 mn 和最大值 mx：
//   w_i  = 满足 mn <= i < mx 的组数        （i 在 [mn, mx-1] 里都“穿过”这一组）
//   s(l,r) = 满足 l <= mn 且 mx <= r 的组数
// 令 L = l-1，条件变成：w_L + w_R = k 且 #{组 : mn > L, mx <= R} >= t
// 固定 R 时，把 mx <= R 的组按 mn 从大到小排，第 t 大的 mn 记作 m_t，
// 则 #{mn > L} >= t  <=>  L <= m_t - 1，也就是 L 的合法上界。
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k, t;
    scanf("%d %d %d", &n, &k, &t);
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) scanf("%d", &p[i]);

    vector<int> diff(n + 2, 0);              // 差分数组，用来求 w
    vector<vector<int>> byMax(n + 1);        // byMax[R] = 所有 mx == R 的组的 mn
    vector<char> vis(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        if (vis[i]) continue;
        int cur = i, mn = i, mx = i;         // 顺着传送门走完整个环
        while (!vis[cur]) {
            vis[cur] = 1;
            mn = min(mn, cur);
            mx = max(mx, cur);
            cur = p[cur];
        }
        diff[mn] += 1;                       // 这组让 w[mn..mx-1] 各 +1
        diff[mx] -= 1;
        byMax[mx].push_back(mn);             // 当 R 增长到 mx 时，这组开始计入 s
    }

    vector<int> w(n + 1, 0);
    int run = 0;
    for (int i = 0; i <= n; ++i) {           // w[0] = 0（mn >= 1，没有组能穿过 0）
        run += diff[i];
        w[i] = run;
    }

    // pos[v] = 所有满足 w[L] == v 的 L，数组天然有序，方便二分
    vector<vector<int>> pos(n + 1);
    for (int L = 0; L <= n; ++L) pos[w[L]].push_back(L);

    // 树状数组：统计“已完成”的组的 mn 分布，支持查询第 k 小
    vector<int> bit(n + 1, 0);
    auto add = [&](int i) { for (; i <= n; i += i & -i) ++bit[i]; };
    auto kth = [&](int kk) {                 // 返回第 kk 小的 mn（kk 从 1 开始）
        int mask = 1;
        while ((mask << 1) <= n) mask <<= 1;
        int idx = 0;
        for (int d = mask; d; d >>= 1) {
            int nxt = idx + d;
            if (nxt <= n && bit[nxt] < kk) { idx = nxt; kk -= bit[nxt]; }
        }
        return idx + 1;
    };

    long long ans = 0;
    int finished = 0;                        // 目前 mx <= R 的组数
    for (int R = 1; R <= n; ++R) {
        for (int mn : byMax[R]) { add(mn); ++finished; }

        int P;                               // L 的上界：L <= R-1 且 L <= m_t - 1
        if (t == 0) {
            P = R - 1;                       // s >= 0 恒成立，只剩 L <= R-1
        } else if (finished >= t) {
            int mt = kth(finished - t + 1);  // 第 t 大的 mn = 第 (finished-t+1) 小的 mn
            P = min(R - 1, mt - 1);
        } else {
            P = -1;                          // 连 t 组都凑不齐
        }
        if (P < 0) continue;

        int need = k - w[R];                 // 需要 w[L] 等于它
        if (need < 0 || need > n) continue;
        const vector<int>& v = pos[need];
        ans += upper_bound(v.begin(), v.end(), P) - v.begin();   // 数出 L <= P 的个数
    }

    printf("%lld\n", ans);
    return 0;
}
