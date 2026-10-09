// E - 小月的折月门牌
// 题意：位置 x(1..2^k) 的门牌号 c_x 计算：
//   cnt = x-1;  mid = cnt ^ (cnt>>1);   // 这正是 Gray 码 G(cnt)
//   把 mid 写成 k 位二进制并翻转，得 c_x。
// 所以 c_x 的「低 h 位」= G(cnt) 的「高 h 位」翻转后的结果。
// 查询：区间 [l,r] 内满足 c_x mod 2^h == z 的 x 数。
//   c_x mod 2^h == z  ⟺  G(cnt) 的高 h 位翻转后 == z
//   ⟺  G(cnt) 的高 h 位 == reverse_h(z)  （记 w）
//   ⟺  G(cnt) ∈ [w*2^{k-h}, (w+1)*2^{k-h})。
// 令 t = cnt = x-1，问题变成：t∈[l-1, r) 且 G(t)∈[lo,hi) 的个数。
// G 是标准二进制反射 Gray 码，性质：G(t) 的 MSB == t 的 MSB。
//   t 下半（MSB=0）：G(t) 的 MSB=0 且 G(t)=G(t_low)，直接递归。
//   t 上半（MSB=1）：t=half+x, G(t)=half+G(u), u=(2^m-1)-x，
//       即上半的 G 仍在上半，u 也在上半；把 t 的上半区间按 u 映射后递归。
// 递归在 O(k) 节点内完成（区间计数，类似数位 DP）。
#include <iostream>

using namespace std;
using ll = long long;

ll countRange(ll tlo, ll thi, ll glo, ll ghi, int m) {
    if (tlo >= thi || glo >= ghi) return 0;
    ll full = 1LL << m;
    if (tlo == 0 && thi == full && glo == 0 && ghi == full) return full;
    if (m == 0) return 1;                       // 此时必为单点 [0,1)
    ll half = 1LL << (m - 1);
    ll res = 0;
    // 下半：t∈[tlo, min(thi,half))，G 的 MSB=0
    ll lo0 = tlo, hi0 = (thi < half ? thi : half);
    if (lo0 < hi0) {
        ll ga = (glo > 0 ? glo : 0), gb = (ghi < half ? ghi : half);
        if (ga < gb) res += countRange(lo0, hi0, ga, gb, m - 1);
    }
    // 上半：t∈[max(tlo,half), thi)，令 z = (2^m-1) - t，则 z∈[0,half)，
    //       且 G(t) 的低位 = G(z)，递归到 m-1 空间。
    ll lo1 = (tlo > half ? tlo : half), hi1 = thi;
    if (lo1 < hi1) {
        ll u_lo = (1LL << m) - hi1;             // z = (2^m-1) - t，t∈[lo1,hi1) -> z∈[2^m-hi1, 2^m-lo1)
        ll u_hi = (1LL << m) - lo1;
        ll ga = glo - half, gb = ghi - half;
        ll ga2 = (ga > 0 ? ga : 0), gb2 = (gb < half ? gb : half);
        if (ga2 < gb2) res += countRange(u_lo, u_hi, ga2, gb2, m - 1);
    }
    return res;
}

ll rev_bits(ll z, int h) {
    ll w = 0;
    for (int i = 0; i < h; ++i)
        if ((z >> i) & 1) w |= (1LL << (h - 1 - i));
    return w;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int k, q;
    if (!(cin >> k >> q)) return 0;
    while (q--) {
        ll l, r, h, z;
        cin >> l >> r >> h >> z;
        ll w = rev_bits(z, h);
        ll lo, hi;
        if (h == 0) { lo = 0; hi = 1LL << k; }
        else { lo = w << (k - h); hi = (w + 1) << (k - h); }
        ll tlo = l - 1, thi = r;
        cout << countRange(tlo, thi, lo, hi, k) << "\n";
    }
    return 0;
}
