// 牛客周赛 Round 140 A - 小红的区间计数
// 思路：区间长度 r-l+1，最多减 3（a,b,c 中落在区间内且互不相同的数）
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long a, b, c, l, r;
    cin >> a >> b >> c >> l >> r;

    long long ans = r - l + 1;      // 区间里的整数总个数
    long long v[3] = {a, b, c};
    for (int i = 0; i < 3; i++) {
        if (v[i] < l || v[i] > r) continue;   // 不在区间里，不影响答案
        bool dup = false;                     // 与前一个重复的话只减一次
        for (int j = 0; j < i; j++)
            if (v[j] == v[i]) dup = true;
        if (!dup) ans--;
    }
    cout << ans << "\n";
    return 0;
}
