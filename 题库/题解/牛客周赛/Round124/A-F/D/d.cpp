#include <bits/stdc++.h>
using namespace std;

// D 题 云栖山涧听松
// 题意：给一棵 n 个点的树，最少加多少条无向边（可重边、可自环），
//       使得加完边后「随便删掉哪一条边，图仍然连通」。
//
// 「删任意一条边仍连通」⟺ 图里没有桥（每条边都在某个环上）。
// 树有 n-1 条边、全是桥，加一条边 (u,v) 会让树上 u→v 的整条路径上的边都进环。
//
// 结论：答案 = ceil(叶子数 / 2)。
// 下界：叶子点度数为 1，它唯一那条边是桥；要让这条边不再是桥，就必须给这个叶子
//       添一条边（只有叶子自己新增的边才能救它）。一条新增边 (u,v) 最多救两个叶子
//       （u、v 各一个，除非 u=v 那种自环），所以至少要 ceil(叶子数/2) 条。
// 上界：把叶子按 DFS 序排成一圈，第 i 个叶子连第 i + ceil(leaf/2) 个叶子，
//       这样每个叶子都被救到，且每条树边都会落在某个环上 —— 恰好 ceil(leaf/2) 条。
//
// 验证：n ≤ 7 的全部标号树（Pruefer 枚举）用暴力「枚举加边多重集 + 每次删边重算连通性」
//       对拍过，0 处不一致（见 _work 里的 brute_D.py）。

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> deg(n + 1, 0);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        ++deg[u];
        ++deg[v];
    }
    int leaf = 0;
    for (int i = 1; i <= n; ++i)
        if (deg[i] == 1) ++leaf;                        // 度数 1 = 叶子
    cout << (leaf + 1) / 2 << "\n";                     // ceil(leaf / 2)
    return 0;
}
