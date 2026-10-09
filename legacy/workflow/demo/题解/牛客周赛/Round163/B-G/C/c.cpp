// C - 小月的对局
// 结论：Bob 能活下来（Bob 胜）<=> 二分图“安全配对”存在完美匹配
//       Alice 牌 i 与 Bob 牌 j 能安全配对 <=> gcd(a_i, b_j) == 1
// 若不存在完美匹配，Alice 先打出缺口子集里的牌即可逼死 Bob
#include <bits/stdc++.h>
using namespace std;

int n;
int a[10], b[10];
int matchB[10];      // matchB[j] = 与 Bob 的牌 j 配对的 Alice 牌编号，-1 表示还没配对
bool vis[10];        // 本轮 DFS 中 Bob 的牌 j 是否已被访问过

// 匈牙利算法：尝试给 Alice 的牌 u 找一张能安全配对的 Bob 牌
bool dfs(int u) {
    for (int v = 0; v < n; ++v) {
        if (__gcd(a[u], b[v]) != 1) continue;   // gcd > 1 就不安全，Bob 不敢出这张
        if (vis[v]) continue;                   // 本轮已经试过 Bob 的这张牌
        vis[v] = true;
        // Bob 的牌 v 还空着，或者能给它原来的主人换一张别的牌
        if (matchB[v] == -1 || dfs(matchB[v])) {
            matchB[v] = u;
            return true;
        }
    }
    return false;   // 实在找不到，说明这张 Alice 牌没法被安全应对
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    for (int i = 0; i < n; ++i) cin >> a[i];
    for (int i = 0; i < n; ++i) cin >> b[i];

    fill(matchB, matchB + n, -1);
    int matched = 0;
    for (int i = 0; i < n; ++i) {
        fill(vis, vis + n, false);   // 每个左部点开始找增广路前都要清空标记
        if (dfs(i)) ++matched;
    }

    // 所有 Alice 的牌都能被互质的 Bob 牌一对一挡住 -> Bob 胜，否则 Alice 胜
    cout << (matched == n ? "Bob" : "Alice") << '\n';
    return 0;
}
