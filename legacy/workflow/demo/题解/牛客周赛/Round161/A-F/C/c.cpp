#include <bits/stdc++.h>
using namespace std;

// 最低位 1 所在的位序（从 0 开始数）。题目规定 0 的最低位 1 在第 31 位
int lowbit_pos(unsigned int v) {
    if (v == 0) return 31;        // 0 没有 1，按题意记为 31
    return __builtin_ctz(v);      // 数末尾有几个 0，就是最低位 1 的位序
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;
    vector<unsigned int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    sort(a.begin(), a.end(), [](unsigned int p, unsigned int q) {
        int cp = __builtin_popcount(p);   // 规则一：1 的数量少的更小
        int cq = __builtin_popcount(q);
        if (cp != cq) return cp < cq;

        int lp = lowbit_pos(p);           // 规则二：最低位 1 更低的更小
        int lq = lowbit_pos(q);
        if (lp != lq) return lp < lq;

        return p < q;                     // 规则三：数值小的更小
    });

    cout << a[k - 1] << '\n';             // 第 k 个：下标是 k-1
    return 0;
}
