#include <bits/stdc++.h>
using namespace std;

const int MOD = 1000000007;

// 枚举半边的所有子集，压成 (选了几个, 异或值) -> 方案数，按 key 排序好
vector<pair<unsigned long long, int>> build(const vector<int> &a, int st, int len) {
    vector<pair<int, int>> v;            // (选了几个, 异或值)，每个子集一项
    v.reserve(1u << len);
    v.push_back({0, 0});                 // 空集
    for (int i = 0; i < len; i++) {
        int sz = (int)v.size();
        for (int t = 0; t < sz; t++)     // 已有的每个子集都多一个"选 a[st+i]"的版本
            v.push_back({v[t].first + 1, v[t].second ^ a[st + i]});
    }

    vector<pair<unsigned long long, int>> c;
    c.reserve(v.size());
    for (auto &p : v) {
        unsigned long long key = ((unsigned long long)p.first << 32) | (unsigned int)p.second;
        c.push_back({key, 1});
    }
    sort(c.begin(), c.end());

    vector<pair<unsigned long long, int>> comp;   // 合并相同的 (个数, 异或值)
    for (auto &p : c) {
        if (!comp.empty() && comp.back().first == p.first)
            comp.back().second = (comp.back().second + p.second) % MOD;
        else
            comp.push_back(p);
    }
    return comp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k, x;
    cin >> n >> k >> x;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    int L = n / 2, R = n - L;            // 折半：前 L 个、后 R 个
    auto left  = build(a, 0, L);
    auto right = build(a, L, R);

    long long ans = 0;
    for (auto &p : left) {
        int c1 = (int)(p.first >> 32);                 // 左半选了几个
        int v1 = (int)(p.first & 0xffffffffu);         // 左半的异或值
        int c2 = k - c1;                               // 右半要选几个
        if (c2 < 0 || c2 > R) continue;
        unsigned long long key =
            ((unsigned long long)c2 << 32) | (unsigned int)(v1 ^ x);   // 右半该长什么样
        auto it = lower_bound(right.begin(), right.end(),
                              make_pair(key, 0));
        if (it != right.end() && it->first == key)
            ans = (ans + (long long)p.second * it->second) % MOD;
    }

    cout << ans << '\n';
    return 0;
}
