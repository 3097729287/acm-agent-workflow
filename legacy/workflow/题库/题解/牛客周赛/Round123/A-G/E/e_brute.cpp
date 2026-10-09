// E 题暴力（跟正解**不同实现范式**）：正解是在线维护段数，
// 这里每读一张牌就把前缀**从头排序重扫一遍**，直接数连续段。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1), vals;
    for (int i = 1; i <= n; i++) cin >> a[i];

    for (int i = 1; i <= n; i++) {
        vals.push_back(a[i]);
        sort(vals.begin(), vals.end());

        int segs = 0;
        for (size_t k = 0; k < vals.size(); k++)
            if (k == 0 || vals[k] != vals[k - 1] + 1) segs++;

        cout << segs << (i == n ? '\n' : ' ');
    }
    return 0;
}
