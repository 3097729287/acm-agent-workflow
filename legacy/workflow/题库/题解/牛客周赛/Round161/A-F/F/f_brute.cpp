#include <bits/stdc++.h>
using namespace std;

// 暴力：枚举每个筹码选 / 不选，统计"选了 k 个且异或和 = x"的方案数。只用于小 n 对拍
const int MOD = 1000000007;
int n, k, x;
vector<int> a;
long long ans = 0;

void dfs(int i, int cnt, int xr) {
    if (i == n) {
        if (cnt == k && xr == x) ans = (ans + 1) % MOD;
        return;
    }
    dfs(i + 1, cnt, xr);                 // 不选第 i 个
    dfs(i + 1, cnt + 1, xr ^ a[i]);      // 选第 i 个
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> k >> x;
    a.resize(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    dfs(0, 0, 0);
    cout << ans << '\n';
    return 0;
}
