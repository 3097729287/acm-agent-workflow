// E - 暴力（不同范式）：预先枚举全部 2^k 个门牌号 c_x，每次查询线性扫描
// 正解用 Gray 码递归区间计数（数位 DP 式）；这里用全枚举 + 线性统计，作为对拍基准。
#include <iostream>
#include <vector>

using namespace std;
using ll = long long;

ll gray(ll t) { return t ^ (t >> 1); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int k, q;
    if (!(cin >> k >> q)) return 0;
    int N = 1 << k;
    vector<ll> cs(N);
    for (int x = 1; x <= N; ++x) {
        ll cnt = x - 1;
        ll mid = gray(cnt);
        ll c = 0;                       // 把 mid 写成 k 位再整体翻转
        for (int i = 0; i < k; ++i)
            if ((mid >> i) & 1) c |= (1LL << (k - 1 - i));
        cs[x - 1] = c;
    }

    while (q--) {
        ll l, r, h, z;
        cin >> l >> r >> h >> z;
        ll mod = (1LL << h);
        ll cnt = 0;
        for (ll x = l; x <= r; ++x)
            if (cs[(ll)x - 1] % mod == z) cnt++;
        cout << cnt << "\n";
    }
    return 0;
}
