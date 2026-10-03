#include <bits/stdc++.h>
using namespace std;

// 按 x 次 = 每一位 d 变成 (d+x) mod 10
// 记 P_i = 10^(n-i) mod m（第 i 位的权值），则
//   数值(x) = sum_i ((d_i + x) mod 10) * P_i
//           = V0 + x*S - 10 * T(x)
// 其中 V0 = sum d_i P_i，S = sum P_i，
//       T(x) = sum_{d_i >= 10-x} P_i   （只有 d_i + x >= 10 的位才要减 10）
// T(x) 用「按数字分桶的前缀和」O(1) 拿到，于是 10 个 x 各判一次即可。
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    cin >> n >> m;
    string s;
    cin >> s;

    vector<long long> bucket(10, 0);   // bucket[d] = 数字 d 那些位的权值和
    long long V0 = 0, S = 0;
    long long p = 1;                   // 个位的权值是 10^0 = 1
    for (int i = n - 1; i >= 0; --i) { // s 的最后一位是个位，从右往左扫
        int d = s[i] - '0';
        V0 = (V0 + d * p) % m;
        S = (S + p) % m;
        bucket[d] = (bucket[d] + p) % m;
        p = p * 10 % m;
    }

    vector<long long> suf(11, 0);      // suf[d] = sum_{e >= d} bucket[e]
    for (int d = 9; d >= 0; --d) suf[d] = (suf[d + 1] + bucket[d]) % m;

    int ans = 0;
    for (int x = 0; x <= 9; ++x) {
        long long T = (x == 0 ? 0 : suf[10 - x]);   // x=0 时没有任何位会进位
        long long val = (V0 + x * S % m - 10 * T % m + m) % m;
        if (val == 0) ++ans;
    }
    cout << ans << '\n';
    return 0;
}
