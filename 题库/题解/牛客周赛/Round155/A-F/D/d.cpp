// D - 小月的电台
// 题意：n 台电台，每台一个长度 m(≤11) 的 01 串表示支持的频道。
//       两台电台至少共同支持一个频道即可通信，求可通信的电台对数。
// 思路：反向计数。总对数 C(n,2) 减去「不相交对」——即两台电台支持集按位与为 0 的对数。
//       把每台的串压成 m 位掩码；统计每个掩码出现次数 cnt[mask]。
//       不相交对 = Σ_{a<b, a&b==0} cnt[a]*cnt[b]。
//       复杂度 O(2^m * 2^m) ≤ 2048^2 ≈ 4.2e6。
#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    int MAXM = 1 << m;
    vector<long long> cnt(MAXM, 0);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        int mask = 0;
        for (int j = 0; j < m; ++j)
            if (s[j] == '1') mask |= (1 << j);
        cnt[mask]++;
    }

    long long total = (long long)n * (n - 1) / 2;
    long long disjoint = 0;
    for (int a = 0; a < MAXM; ++a) {
        if (!cnt[a]) continue;
        // 同一 mask 的站内配对：只有全 0 掩码自身相与为 0，才是互不相交对
        if ((a & a) == 0)
            disjoint += (long long)cnt[a] * (cnt[a] - 1) / 2;
        for (int b = a + 1; b < MAXM; ++b) {
            if (!cnt[b]) continue;
            if ((a & b) == 0)
                disjoint += cnt[a] * cnt[b];
        }
    }

    cout << total - disjoint << "\n";
    return 0;
}
