#include <bits/stdc++.h>
using namespace std;

// 暴力：比较函数用手写位循环（不用 __builtin_popcount / ctz），排序用选择排序。
// 与正解（内建位运算 + std::sort）是不同的实现范式，用于对拍
int pc(unsigned int v) {                 // 一位一位数 1 的个数
    int c = 0;
    while (v) { c += (v & 1); v >>= 1; }
    return c;
}
int lp(unsigned int v) {                 // 从低位往高位找第一个 1
    if (v == 0) return 31;               // 题目规定 0 记为第 31 位
    int p = 0;
    while (((v >> p) & 1) == 0) p++;
    return p;
}
bool less_than(unsigned int p, unsigned int q) {
    int cp = pc(p), cq = pc(q);
    if (cp != cq) return cp < cq;
    int lp1 = lp(p), lq1 = lp(q);
    if (lp1 != lq1) return lp1 < lq1;
    return p < q;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;
    vector<unsigned int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    for (int i = 0; i < n; i++) {        // 选择排序：每轮把最小的换到 i
        int best = i;
        for (int j = i + 1; j < n; j++)
            if (less_than(a[j], a[best])) best = j;
        swap(a[i], a[best]);
    }

    cout << a[k - 1] << '\n';
    return 0;
}
