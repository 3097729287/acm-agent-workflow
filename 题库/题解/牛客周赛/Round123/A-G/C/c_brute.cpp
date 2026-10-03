// C 题暴力（跟正解**不同实现范式**）：正解是「每个数字里按花色首次出现的顺序取牌」，
// 这里把每个数字下的牌**所有偶数张、花色互不相同的子集都枚举一遍**，
// 取张数最多的；张数相同取下标字典序最小的那组（正解取法恰好就是它）。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    map<int, vector<pair<int, int>>> byVal;   // 数字 -> [(下标, 花色)]
    for (int i = 1; i <= n; i++) {
        int a;
        char c;
        cin >> a >> c;
        byVal[a].push_back({i, c - 'A'});
    }

    vector<pair<int, int>> pairs;
    for (auto &kv : byVal) {                  // map 天然按数字升序
        vector<pair<int, int>> &cards = kv.second;
        int k = cards.size();
        vector<int> best;                     // 最优子集的下标（升序）
        for (int mask = 0; mask < (1 << k); mask++) {
            int sz = __builtin_popcount(mask);
            if (sz != 2 && sz != 4) continue;          // 打出的牌数必须成对
            int su = 0;
            bool ok = true;
            vector<int> ids;
            for (int b = 0; b < k; b++) if (mask >> b & 1) {
                if (su >> cards[b].second & 1) { ok = false; break; }  // 花色重复
                su |= 1 << cards[b].second;
                ids.push_back(cards[b].first);
            }
            if (!ok) continue;
            sort(ids.begin(), ids.end());
            if (ids.size() > best.size() || (ids.size() == best.size() && ids < best))
                best = ids;
        }
        for (size_t p = 0; p + 1 < best.size(); p += 2)
            pairs.push_back({best[p], best[p + 1]});
    }

    cout << pairs.size() * 2 << "\n";
    for (auto &p : pairs) cout << p.first << " " << p.second << "\n";
    return 0;
}
