// 牛客周赛 Round 163 F - 小月的前缀
// 做法：把所有 s_i 插进一棵 Trie；查询时沿 t 往下走，边走边记"最深且还有货"的那种串。
#include <bits/stdc++.h>
using namespace std;

// 结点总数 = 所有 s_i 的长度之和 + 1（根）<= 5*10^5 + 1，所以开 500005 富余
const int MAXN = 500005;

int ch[MAXN][26];   // ch[v][x] = 结点 v 沿字符 x（0..25 对应 'a'..'z'）走到的儿子；0 表示没有这条路
int id[MAXN];       // id[v] = 在结点 v 结束的那种字符串的编号；0 表示没有串在这里结束
int cnt[MAXN];      // cnt[i] = 第 i 种字符串还剩几个（注意下标是"字符串编号"，不是结点编号）

int main() {
    ios::sync_with_stdio(false);   // 关掉 cin 与 scanf 的同步，读入快很多
    cin.tie(nullptr);              // 解绑 cout，避免每次 cin 都冲一次输出缓冲

    int n, q;
    cin >> n >> q;

    int tot = 0;                   // 已经开出多少个结点；根固定是 0 号，从 1 开始分配新结点
    string s;
    for (int i = 1; i <= n; ++i) {         // 字符串编号从 1 开始，0 号留给"没有"
        int c;
        cin >> s >> c;
        cnt[i] = c;                        // 先记下这种串的库存

        int v = 0;                         // v 是"我现在站在哪个结点"，从根出发
        for (char cc : s) {                // 一个字符一个字符往下走
            int x = cc - 'a';              // 把字符翻译成 0..25 的列号
            if (ch[v][x] == 0) {           // 这条边还不存在 → 新开一个结点
                ch[v][x] = ++tot;          // 新结点编号 = tot + 1；同时把这条边接上
            }
            v = ch[v][x];                  // 走到儿子去
        }
        id[v] = i;                         // 整串走完，停在 v：把编号牌挂在 v 上
    }

    string t;
    for (int qi = 0; qi < q; ++qi) {
        cin >> t;

        int v = 0;                         // 从根出发
        int best = 0;                      // 目前找到的最长合法前缀的编号；0 = 还没找到
        for (char cc : t) {
            int x = cc - 'a';
            if (ch[v][x] == 0) break;      // 这条路不存在 → 再走只会更长的前缀更不可能存在，直接停
            v = ch[v][x];                  // 走到下一个前缀对应的结点
            if (id[v] && cnt[id[v]] > 0) { // 这里挂着牌子，并且还有货
                best = id[v];              // 越走越深，所以后来者一定更长，直接覆盖即可
            }
        }

        cout << best << '\n';              // 输出答案
        if (best) --cnt[best];             // 用掉一个（best = 0 时什么都不减）
    }
    return 0;
}
