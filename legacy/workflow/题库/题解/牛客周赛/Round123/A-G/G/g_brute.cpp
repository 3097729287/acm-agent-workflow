// G 题暴力（跟正解**不同实现范式**）：正解用双指针扫窗口，
// 这里**枚举每一个可能的起点 L**（1 ~ 最大数字），数区间 [L, L+n-1] 里覆盖了多少种
// 不同的数字，取最大，答案 = n - 最大保留数。只输出最少的出千次数（方案由检查器验）。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<long long> a(n + 1);
    long long mx = 1;
    for (int i = 1; i <= n; i++) { cin >> a[i]; mx = max(mx, a[i]); }

    vector<long long> d(a.begin() + 1, a.end());
    sort(d.begin(), d.end());
    d.erase(unique(d.begin(), d.end()), d.end());

    long long bestKeep = 0;
    for (long long L = 1; L <= mx; L++) {
        long long hi = L + n - 1, keep = 0;
        for (long long v : d) if (L <= v && v <= hi) keep++;
        bestKeep = max(bestKeep, keep);
    }

    cout << n - bestKeep << "\n";
    return 0;
}
