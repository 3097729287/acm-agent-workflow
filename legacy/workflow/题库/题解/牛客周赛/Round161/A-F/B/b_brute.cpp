#include <bits/stdc++.h>
using namespace std;

// 暴力：对每个位置单独问一遍"我比左边所有数都大吗"，O(n^2)。
// 与正解（一次扫描 + 维护前缀最大值）是不同的实现范式，用于对拍
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<long long> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    vector<int> pos;                 // 所有记录点的下标
    for (int i = 0; i < n; i++) {
        bool ok = true;
        for (int j = 0; j < i; j++)
            if (a[j] >= a[i]) { ok = false; break; }   // 左侧有不小于它的，就不是记录点
        if (ok) pos.push_back(i);
    }

    int best = 0;
    for (int t = 1; t < (int)pos.size(); t++)
        best = max(best, pos[t] - pos[t - 1]);

    cout << pos.size() << ' ' << best << '\n';
    return 0;
}
