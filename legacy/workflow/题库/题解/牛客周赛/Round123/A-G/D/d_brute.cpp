// D 题暴力（跟正解**不同实现范式**）：正解是 O(值域) 的计数公式，
// 这里直接**枚举所有 10 张牌的可重集合**，再拿题面定义去检查它是不是飞机。
// 只在小数据上用（指数级）。
#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> vals;                 // 出现过的点数（升序）
vector<int> cap;                  // 每个点数最多能取几张
vector<int> chosen;               // 当前可重集合里，各点数取了几张
long long ans = 0;

// 按题面定义判断：这 10 张牌（展开成 cards）是不是飞机
bool isPlane() {
    vector<int> cards;
    for (size_t i = 0; i < chosen.size(); i++)
        for (int k = 0; k < chosen[i]; k++) cards.push_back(vals[i]);
    if ((int)cards.size() != 10) return false;

    for (int x : cards) {                     // 枚举「两个连续三张」的起点 x
        int c1 = 0, c2 = 0;
        for (int v : cards) {
            if (v == x) c1++;
            if (v == x + 1) c2++;
        }
        if (c1 < 3 || c2 < 3) continue;

        // 扣掉 x 三张、x+1 三张，剩下的 4 张必须能分成两个对子
        vector<int> rest;
        int u1 = 3, u2 = 3;
        for (int v : cards) {
            if (v == x && u1 > 0) { u1--; continue; }
            if (v == x + 1 && u2 > 0) { u2--; continue; }
            rest.push_back(v);
        }
        sort(rest.begin(), rest.end());
        if ((int)rest.size() == 4 && rest[0] == rest[1] && rest[2] == rest[3])
            return true;                      // {p,p,q,q} 或 {p,p,p,p}
    }
    return false;
}

void dfs(int idx, int remain) {
    if (remain == 0) {
        if (isPlane()) ans++;
        return;
    }
    if (idx == (int)vals.size()) return;
    for (int k = 0; k <= min(cap[idx], remain); k++) {
        chosen[idx] = k;
        dfs(idx + 1, remain - k);
    }
    chosen[idx] = 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    if (n < 10) { cout << 0 << "\n"; return 0; }   // 凑不出 10 张

    sort(a.begin(), a.end());
    for (int v : a) {
        if (vals.empty() || vals.back() != v) { vals.push_back(v); cap.push_back(1); }
        else cap.back()++;
    }
    chosen.assign(vals.size(), 0);
    dfs(0, 10);

    cout << ans << "\n";
    return 0;
}
