// C-小月的灯带：前缀和 + 二分定位
// 题意：灯带被切成 m 段，第 i 段有 a_i 盏灯、段内状态全同、相邻段状态相反；给定第 1 段状态 b。
//       每次询问第 p 盏灯：输出它的状态、它在第几段、它是该段第几盏。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m, q, b;
    cin >> m >> q >> b;

    // pre[i] = 前 i 段一共有多少盏灯（第 i 段占据区间 (pre[i-1], pre[i]]）
    // a_i 最大 10^18、总和不超过 10^18，long long（上限约 9.2×10^18）装得下
    vector<long long> pre(m + 1, 0);
    for (int i = 1; i <= m; i++) {
        long long a;
        cin >> a;
        pre[i] = pre[i - 1] + a;
    }

    while (q--) {
        long long p;
        cin >> p;

        // 第一段满足 pre[i] >= p 的 i 就是 p 所在段：单调，直接二分
        int seg = int(lower_bound(pre.begin() + 1, pre.end(), p) - pre.begin());
        // 段内编号 = p 减去前面所有段的灯数
        long long pos = p - pre[seg - 1];
        // 状态：第 1 段是 b，每往后一段翻转一次 → 与 (seg-1) 的奇偶性异或
        int state = b ^ ((seg - 1) & 1);

        cout << state << ' ' << seg << ' ' << pos << "\n";
    }

    return 0;
}
