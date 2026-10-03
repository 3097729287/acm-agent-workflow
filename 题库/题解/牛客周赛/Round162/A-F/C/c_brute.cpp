#include <bits/stdc++.h>
using namespace std;

// 暴力（不同范式）：不推公式，对 10 个 x 各自老老实实把每一位转一遍再 Horner 取模
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    cin >> n >> m;
    string s;
    cin >> s;

    int ans = 0;
    for (int x = 0; x <= 9; ++x) {
        long long val = 0;
        for (int i = 0; i < n; ++i) {          // 从最高位往最低位做 Horner
            int d = (s[i] - '0' + x) % 10;
            val = (val * 10 + d) % m;
        }
        if (val == 0) ++ans;
    }
    cout << ans << '\n';
    return 0;
}
