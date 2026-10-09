// C - 小红的因子幂和
// 题意：x,y <= 1e9+7，v=x*y，求 sum_{d|v} d^d mod 1e9+7。
// 做法：v 最大约 1e18，不能直接试除到 sqrt(v)（要 1e9 次）。
//       但可以分别分解 x 和 y（各自 <= 1e9+7，试除到 31623 即可），
//       再合并质因子指数，然后 DFS 枚举出 v 的全部因子 d，
//       对每个 d 用快速幂算 d^d（指数就是 d 本身，d 在 long long 内）。
//       v<=1e18 时因子个数最多约 1e5，每次快速幂 60 次乘法，完全够。
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1000000007LL;

ll pw(ll b, ll e) {                    // 快速幂
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
    ll x, y;
    scanf("%lld %lld", &x, &y);

    // 分别分解 x、y，合并质因子指数
    map<ll, int> fac;
    for (ll t : {x, y}) {
        ll v = t;
        for (ll d = 2; d * d <= v; d++) {
            while (v % d == 0) { fac[d]++; v /= d; }
        }
        if (v > 1) fac[v]++;           // 剩下的大质数（含 t 本身是质数、或 t=1e9+7 的情形）
    }

    // 枚举 v 的所有正因子
    vector<ll> divs{1};
    for (auto &kv : fac) {
        ll p = kv.first;
        int e = kv.second;
        vector<ll> add;
        ll pk = 1;
        for (int i = 0; i < e; i++) {
            pk *= p;                   // pk = p^(i+1)，不会超过 v <= 1e18
            for (ll d : divs) add.push_back(d * pk);
        }
        divs.insert(divs.end(), add.begin(), add.end());
    }

    ll ans = 0;
    for (ll d : divs) ans = (ans + pw(d, d)) % MOD;
    printf("%lld\n", ans);
    return 0;
}
