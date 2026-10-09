// F - 小红的网格路径 II
// 题意：n×m 网格，从 (1,1) 到 (n,m)，每步上/下/右，不重复经过格子，k 个禁格（每列至多一个），
//       求方案数 mod 1e9+7。n,m 到 1e9，k 到 1e5。
// 结论：因为不能向左、不能重复经过格子，每一列里走过的格子必然是一段连续的行区间。
//       整条路径由"切换行号"唯一决定：
//         令 a_0 = 1（起点行），a_m = n（终点行），a_j = 从第 j 列横移到第 j+1 列时的行号；
//         第 j 列走过的行区间就是 [min(a_{j-1},a_j), max(a_{j-1},a_j)]，它不能含禁格。
//       所以只需统计满足这些限制的序列 a_1..a_{m-1} 的个数。
// 压缩：a 的取值 1..n 太大，但"限制"只出现在有禁格的列，且每个限制形如
//       "a_{j-1} 与 a_j 同侧于 x_j"。无限制的列会把分布"抹平"成常数分布，
//       限制列则把分布变成以 x_j 为界的两段常数。所以分布只需存 (常数) 或 (阈值,左值,右值)。
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1000000007LL;

ll pw(ll b, ll e) {
    b %= MOD;
    ll r = 1;
    while (e) {
        if (e & 1) r = r * b % MOD;
        b = b * b % MOD;
        e >>= 1;
    }
    return r;
}

int main() {
    ll n, m;
    int k;
    scanf("%lld %lld %d", &n, &m, &k);
    vector<pair<ll, ll>> obs(k);                 // (列 y, 行 x)
    for (int i = 0; i < k; i++) scanf("%lld %lld", &obs[i].second, &obs[i].first);
    sort(obs.begin(), obs.end());                // 按列排序（保证同一列至多一个）

    // 分布 f：mode 0 = 只有 a=1 处为 1（起点固定）；1 = 处处为常数 C；2 = 阈值 t 的两段 (L,R)
    int mode = 0;
    ll C = 0, t = 0, L = 0, R = 0;
    auto norm = [](ll v) { v %= MOD; if (v < 0) v += MOD; return v; };
    auto getSum = [&]() -> ll {                  // Σ_v f(v)
        if (mode == 0) return 1 % MOD;
        if (mode == 1) return C * (n % MOD) % MOD;
        return (L * ((t - 1) % MOD) + R * ((n - t) % MOD)) % MOD;
    };
    auto split = [&](ll x, ll &Slo, ll &Shi) {    // 求 Σ_{v<x} f(v) 与 Σ_{v>x} f(v)
        if (mode == 0) {
            Slo = (1 < x);
            Shi = (1 > x);
        } else if (mode == 1) {
            Slo = C * ((x - 1) % MOD) % MOD;
            Shi = C * ((n - x) % MOD) % MOD;
        } else {
            if (x <= t) Slo = L * ((x - 1) % MOD) % MOD;
            else        Slo = (L * ((t - 1) % MOD) + R * ((x - 1 - t) % MOD)) % MOD;
            if (x >= t) Shi = R * ((n - x) % MOD) % MOD;
            else        Shi = (L * ((t - 1 - x) % MOD) + R * ((n - t) % MOD)) % MOD;
        }
        Slo = norm(Slo); Shi = norm(Shi);
    };

    ll prevY = 0, ans = -1;
    for (int i = 0; i < k; i++) {
        ll y = obs[i].first, x = obs[i].second;
        ll d = y - 1 - prevY;                    // 这之间自由变量 a_{prevY+1}..a_{y-1} 的个数
        if (d >= 1) {                            // 至少一个自由变量 -> 分布被抹平
            C = getSum() * pw(n, d - 1) % MOD;
            mode = 1;
        }
        ll Slo, Shi;
        split(x, Slo, Shi);
        if (y == m) { ans = Shi; break; }         // 最后一个变量 a_m = n 固定，必须 > x
        t = x; L = Slo; R = Shi; mode = 2;        // a_y 的分布
        prevY = y;
    }
    if (ans < 0) {
        ll d = m - 1 - prevY;                     // 末尾自由变量 a_{prevY+1}..a_{m-1}
        ans = getSum() * pw(n, d) % MOD;
    }
    printf("%lld\n", norm(ans));
    return 0;
}
