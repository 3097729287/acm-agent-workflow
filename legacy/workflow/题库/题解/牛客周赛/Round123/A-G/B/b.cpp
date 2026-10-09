// 牛客周赛 Round 123 B. 小红作弊
// 题意：两人共 52 张牌，牌面 1~13。要求「每个数字的牌恰好 4 张」（两人合计）。
//       小紫的牌合法（同一个数字不超过 4 张），小红可以改自己手上任意一张牌的数字，
//       问最少改几次。
//
// 关键：小紫不动，所以小红最终手牌是**唯一确定的**：
//       第 i 种数字最终必须持有 need[i] = 4 - y[i] 张。
//       小红现在有 x[i] 张，多了的（x[i] > need[i]）必须改掉；
//       少了的自然由别处多出来的补上（总数一定对得上：两边总和都是 52）。
//       所以答案 = Σ max(0, x[i] - need[i])。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int x[14], y[14];                       // 下标 1~13 对应牌面 1~13
    for (int i = 1; i <= 13; i++) cin >> x[i];   // 小红手上的张数
    for (int i = 1; i <= 13; i++) cin >> y[i];   // 小紫手上的张数

    long long ans = 0;
    for (int i = 1; i <= 13; i++) {
        int need = 4 - y[i];                // 小红最终必须持有几张 i
        if (x[i] > need) ans += x[i] - need; // 多出来的每一张都得改一次
    }

    cout << ans << "\n";
    return 0;
}
