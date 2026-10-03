// F-小月的路径码：dfs 序把子树变成区间 + 树状数组维护「区间加、单点查」
// 题意：根为 1 的树上每个点有 0/1 状态，C(u) = Σ F(s_v)·2^dep(v)（v 取 1→u 路径上的点）。
//       两种操作：翻转某点状态；查询某点的 C(u)（对 1e9+7 取模）。
#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

int n, q;
vector<vector<int>> adj;
string s;                    // s[u-1] 是节点 u 的当前状态字符
vector<int> par_, dep_, tin, tout;
vector<long long> pw;        // pw[d] = 2^d mod MOD
vector<long long> base_;     // base_[u]：还没发生任何翻转时，节点 u 的路径码
int timer_ = 0;

// 树状数组：支持「区间加」「单点查」
struct BIT {
    int n;
    vector<long long> t;
    BIT(int n) : n(n), t(n + 2, 0) {}
    void add(int i, long long v) {                 // 下标 i 处加 v
        for (; i <= n; i += i & (-i)) t[i] = (t[i] + v) % MOD;
    }
    void range_add(int l, int r, long long v) {    // [l, r] 整段加 v
        add(l, v);
        add(r + 1, (MOD - v) % MOD);               // 差分思想：r+1 处减回去
    }
    long long query(int i) {                       // 单点查 = 前缀和
        long long res = 0;
        for (; i > 0; i -= i & (-i)) res = (res + t[i]) % MOD;
        return res;
    }
};

// 迭代版 dfs：一次遍历同时求出 dep、dfs 序区间 [tin, tout] 和 base_ 路径码
void dfs_build() {
    vector<int> it(n + 1, 0);          // 每个点已经枚举到第几个邻居
    vector<int> st;
    st.reserve(n);
    par_[1] = 0;
    dep_[1] = 0;
    tin[1] = ++timer_;
    base_[1] = (s[0] - '0') * pw[0] % MOD;

    st.push_back(1);
    while (!st.empty()) {
        int u = st.back();
        if (it[u] < (int)adj[u].size()) {
            int v = adj[u][it[u]++];
            if (v == par_[u]) continue;              // 不走回头路
            par_[v] = u;
            dep_[v] = dep_[u] + 1;
            tin[v] = ++timer_;                       // 进入 v：分配 dfs 序位置
            base_[v] = (base_[u] + (s[v - 1] - '0') * pw[dep_[v]]) % MOD;
            st.push_back(v);
        } else {
            tout[u] = timer_;                        // 离开 u：子树区间右端点 = 当前已分配的最大位置
            st.pop_back();
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> q;
    cin >> s;
    adj.assign(n + 1, {});
    for (int i = 0; i < n - 1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    pw.assign(n + 1, 1);
    for (int i = 1; i <= n; i++) pw[i] = pw[i - 1] * 2 % MOD;

    par_.assign(n + 1, 0);
    dep_.assign(n + 1, 0);
    tin.assign(n + 1, 0);
    tout.assign(n + 1, 0);
    base_.assign(n + 1, 0);
    dfs_build();

    BIT bit(n);
    while (q--) {
        char op;
        int u;
        cin >> op >> u;

        if (op == 'F') {
            long long w = pw[dep_[u]];               // 翻转 u 的状态，会让整棵子树里的路径码都 ±2^dep(u)
            if (s[u - 1] == '0') {
                s[u - 1] = '1';
                bit.range_add(tin[u], tout[u], w);
            } else {
                s[u - 1] = '0';
                bit.range_add(tin[u], tout[u], (MOD - w) % MOD);
            }
        } else {
            // 当前路径码 = 初始路径码 + 所有覆盖到它的翻转带来的累积增量
            long long ans = (base_[u] + bit.query(tin[u])) % MOD;
            cout << ans << "\n";
        }
    }

    return 0;
}
