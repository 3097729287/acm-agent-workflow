#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// F 题暴力：枚举圆上所有完美匹配（递归配对第一个未配的点），
// 只保留「只连同字母」且「线段两两不相交」的，取最小代价。
// 实现范式与正解不同：正解是区间 DP，暴力是枚举 + 两两判交（几何判定）。
// n <= 12 时可用（完美匹配数 = (n-1)!! = 10395）。

int n;
string s;
vector<ll> a;
vector<int> mate;
vector<char> used;
ll best;
bool found;

// 圆周上两条线段 (i,j) 与 (k,l) 相交：四个端点必须按 i k j l 或 i l j k 交错。
// 用"跨越判定"：从 i 出发按圆周方向走到 j，看 k、l 是不是恰好一个在弧内、一个不在。
// 注意不能写成数轴上的开区间判交 —— 那样 (0,1) 与 (2,3) 这种相邻不交的会被误判成交，
// 而圆周上本来就不相交的线段也有可能在数轴上"看起来交叉"。
static bool cross(int i, int j, int k, int l) {
    auto inArc = [&](int s, int e, int x) {      // x 是否在 s 顺时针到 e 的弧内（不含端点）
        if (s < e) return x > s && x < e;
        return x > s || x < e;
    };
    bool c1 = inArc(i, j, k), c2 = inArc(i, j, l);
    bool c3 = inArc(k, l, i), c4 = inArc(k, l, j);
    return c1 != c2 && c3 != c4;                 // 双向都交错才算真相交
}

static bool allNonCrossing() {
    vector<pair<int, int>> seg;
    for (int i = 0; i < n; ++i) if (mate[i] > i) seg.push_back({i, mate[i]});
    for (size_t x = 0; x < seg.size(); ++x)
        for (size_t y = x + 1; y < seg.size(); ++y)
            if (cross(seg[x].first, seg[x].second, seg[y].first, seg[y].second))
                return false;
    return true;
}

void dfs() {
    int i = -1;
    for (int t = 0; t < n; ++t) if (!used[t]) { i = t; break; }
    if (i < 0) {
        if (!allNonCrossing()) return;
        ll cost = 0;
        for (int t = 0; t < n; ++t) if (mate[t] > t) cost += a[t] * a[mate[t]];
        if (!found || cost < best) { best = cost; found = true; }
        return;
    }
    used[i] = 1;
    for (int j = i + 1; j < n; ++j) {
        if (used[j] || s[i] != s[j]) continue;
        used[j] = 1;
        mate[i] = j; mate[j] = i;
        dfs();
        used[j] = 0;
        mate[i] = mate[j] = -1;
    }
    used[i] = 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    while (T--) {
        cin >> n >> s;
        a.assign(n, 0);
        for (int i = 0; i < n; ++i) cin >> a[i];
        mate.assign(n, -1);
        used.assign(n, 0);
        found = false;
        best = 0;
        dfs();
        if (!found) cout << -1 << "\n";
        else cout << best << "\n";
    }
    return 0;
}
