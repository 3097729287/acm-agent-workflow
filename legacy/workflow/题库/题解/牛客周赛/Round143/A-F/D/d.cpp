// D - 小红的最佳区间
// 题意：n 个闭区间 [l_i,r_i]，另选长度恰为 k 的闭区间 [L,L+k]（L 任意整数），
//       求最多能有多少个给定区间与它相交（端点重合算相交）。
// 转化：区间 i 与 [L,L+k] 相交 <=> 存在公共点
//         <=> l_i <= L+k 且 L <= r_i
//         <=> L >= l_i - k 且 L <= r_i
//         <=> L ∈ [l_i-k, r_i]
//       于是问题变成：找一个整数 L 被最多的区间 [l_i-k, r_i] 覆盖 —— 经典扫描线/差分。
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    int n;
    ll k;
    scanf("%d %lld", &n, &k);
    vector<pair<ll,int>> ev;
    ev.reserve(2 * n);
    for (int i = 0; i < n; i++) {
        ll l, r;
        scanf("%lld %lld", &l, &r);
        ev.push_back({l - k, +1});     // L 从 l-k 起被这个区间覆盖
        ev.push_back({r + 1, -1});     // L 到 r+1 起不再被覆盖
    }
    sort(ev.begin(), ev.end());

    ll cur = 0, ans = 0;
    for (size_t i = 0; i < ev.size(); ) {
        ll pos = ev[i].first;
        while (i < ev.size() && ev[i].first == pos) cur += ev[i].second, i++; // 同坐标事件一起算
        ans = max(ans, cur);           // 此刻 cur 就是 L=pos 处的覆盖数
    }
    printf("%lld\n", ans);
    return 0;
}
