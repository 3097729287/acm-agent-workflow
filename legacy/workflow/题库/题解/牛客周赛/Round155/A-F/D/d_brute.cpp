// D - 暴力（不同范式）：直接枚举所有电台对，逐位判断是否共享频道
// 正解用「按位与为 0」的掩码反向计数；这里用最朴素的两两比较，作为对拍基准。
#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(n);
    for (int i = 0; i < n; ++i) cin >> s[i];

    long long ans = 0;
    for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j) {
            bool share = false;
            for (int k = 0; k < m; ++k)
                if (s[i][k] == '1' && s[j][k] == '1') { share = true; break; }
            if (share) ans++;
        }
    cout << ans << "\n";
    return 0;
}
