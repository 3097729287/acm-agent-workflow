// 牛客周赛 Round 123 C. 小红出对
// 题意：n 张牌，每张有「牌面数字 a_i」和「花色 c_i」。每次打出一个「对」＝两张数字相同的牌。
//       限制：所有打出的牌里，不能有两张「花色 + 数字」都相同的牌。
//       求最多能打出多少张，并给出一种方案。
//
// 关键：把牌按**数字**分组，一组的牌里，打出去的那些必须**花色两两不同**
//       （否则就出现两张花色数字都相同的牌）。
//       设某个数字一共有 d 种不同的花色，那这个数字最多打 2*floor(d/2) 张
//       （打出的张数必须是偶数，而且每种花色最多一次）。
//       各组互不影响，所以答案 = Σ 2*floor(d_v/2)。
//
//       构造：每组按「输入顺序里第一次出现某花色」取牌，凑成偶数张后
//       顺次两两配对——同一组的牌花色互不相同，配对自然合法。
#include <bits/stdc++.h>
using namespace std;

const int MAXA = 200005;                 // a_i ≤ 2*10^5

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    // ids[v]：牌面数字为 v 的牌的下标，按输入顺序存
    vector<vector<int>> ids(MAXA);
    vector<int> suit(n + 1);             // suit[i]：第 i 张牌的花色（0~3 表示 A~D）
    for (int i = 1; i <= n; i++) {
        int a;
        char c;
        cin >> a >> c;
        suit[i] = c - 'A';
        ids[a].push_back(i);
    }

    vector<pair<int, int>> pairs;        // 打出的每一对
    vector<char> used(4, 0);             // 本次分组里，哪些花色已经拿过牌
    vector<int> pick;                    // 本次分组里挑出来的牌（花色互不相同）

    for (int v = 1; v < MAXA; v++) {
        if (ids[v].empty()) continue;

        pick.clear();
        fill(used.begin(), used.end(), 0);   // 每个数字单独统计花色
        for (int id : ids[v]) {
            if (!used[suit[id]]) {           // 这种花色还没拿过 → 可以拿
                used[suit[id]] = 1;
                pick.push_back(id);
            }
        }
        int m = (int)pick.size() / 2 * 2;    // 只能取偶数张
        for (int k = 0; k + 1 < m; k += 2)
            pairs.push_back({pick[k], pick[k + 1]});
    }

    cout << pairs.size() * 2 << "\n";
    for (auto &p : pairs) cout << p.first << " " << p.second << "\n";
    return 0;
}
