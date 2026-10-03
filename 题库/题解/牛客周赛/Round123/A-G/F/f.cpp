// 牛客周赛 Round 123 F. 小红出牌（hard）
// 题意：跟 E 题一样，只是**不再保证牌面数字互不相同**。
//       对每个前缀 a[1..x]，求把这些牌全部出成顺子所需的最少次数。
//
// 关键：设 cnt[v] = 前缀里数字 v 的张数（cnt[0] = 0）。则
//       最少顺子数 = Σ_v max(0, cnt[v] - cnt[v-1])。
//       为什么：数字 v 的 cnt[v] 张牌，每张都待在某个顺子里；一个顺子最多
//       只经过 v-1 一次，所以最多有 cnt[v-1] 个顺子能「从 v-1 延伸过来」，
//       剩下 cnt[v] - cnt[v-1] 个顺子必须在 v 这里**开头**。把这些开头数加起来
//       就是顺子总数（每个顺子恰有一个最小数字）。反过来按「尽量接上左边」
//       贪心配对就能达到这个下界，所以它正好是最小值。
//
//       实现：每读入一张 v，只有 v 和 v+1 两项的值会变，O(1) 局部更新即可。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<long long> cnt(n + 2, 0);   // a_i ≤ n，多开两格给 v+1 用

    auto term = [&](int v) {           // 第 v 项：max(0, cnt[v] - cnt[v-1])
        return max(0LL, cnt[v] - cnt[v - 1]);
    };

    long long total = 0;               // Σ term(v)
    for (int i = 1; i <= n; i++) {
        int v;
        cin >> v;

        long long before = term(v) + term(v + 1);   // 会受影响的两项：v 和 v+1
        cnt[v]++;                                    // 新牌进桶
        long long after = term(v) + term(v + 1);
        total += after - before;

        cout << total << (i == n ? '\n' : ' ');
    }
    return 0;
}
