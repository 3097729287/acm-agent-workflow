#include <bits/stdc++.h>
using namespace std;

// 第 i 盏灯（i = 1,2,3）的状态是 a[i-1]，亮着就得 i-1 分
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int a0, a1, a2;
    cin >> a0 >> a1 >> a2;

    int ans = a0 * 0 + a1 * 1 + a2 * 2;   // 三盏灯的得分分别是 0、1、2
    cout << ans << '\n';
    return 0;
}
