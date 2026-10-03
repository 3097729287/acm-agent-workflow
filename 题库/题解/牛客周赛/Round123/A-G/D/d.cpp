// 牛客周赛 Round 123 D. 小红打牌
// 题意：手上有 n 张牌（牌面数字 a_i）。一个「飞机」是 10 张牌，重排后能写成
//       {a,a,a,a+1,a+1,a+1,b,b,c,c} 的形状（两个连续的三张 + 两个对子，
//       对子的点数 b、c 随便，可以相等，也可以和三张的点数重合）。
//       问能选出多少种**不同的**飞机（两个飞机相同 ⟺ 十张牌的可重集合完全一样）。
//
// 关键 1：飞机由 (a, b, c) 决定，且**这三个数是唯一的**——
//         假设同一个可重集合还能写成 (a', b', c') 且 a' ≠ a：
//         a' ≥ a+2 时集合里至少有 4 种不同的点数各 ≥3 张，共 ≥12 张 > 10 张，不可能；
//         a' = a+1 时点数 a+1 需要 ≥6 张，加上 a、a+2 各 3 张也是 ≥12 张，不可能。
//         所以数飞机 = 数合法三元组 (a, b ≤ c)。
// 关键 2：对固定的 a，三张的部分吃掉 cnt[a] 和 cnt[a+1] 各 3 张，
//         剩下的容量 cap[x] = cnt[x] - 3*[x==a] - 3*[x==a+1]。
//         两个对子要求：b < c 时 cap[b], cap[c] ≥ 2；b == c 时 cap[b] ≥ 4。
//         于是令 T = {x : cap[x] ≥ 2}、T4 = {x : cap[x] ≥ 4}，
//         这一档的贡献就是 C(|T|, 2) + |T4|。
// 关键 3：|T| 和 |T4| 可以用全场统计量 O(1) 算出来（见代码），不必每个 a 重扫。
#include <bits/stdc++.h>
using namespace std;

const int MAXA = 200005;                 // a_i ≤ 2*10^5
const long long MOD = 998244353;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> cnt(MAXA + 2, 0);
    for (int i = 0; i < n; i++) {
        int v;
        cin >> v;
        cnt[v]++;
    }

    // 全场统计：有多少种点数够 2 张、够 4 张
    long long g2 = 0, g4 = 0;
    for (int v = 1; v <= MAXA; v++) {
        if (cnt[v] >= 2) g2++;
        if (cnt[v] >= 4) g4++;
    }

    long long ans = 0;
    for (int a = 1; a + 1 <= MAXA; a++) {
        if (cnt[a] < 3 || cnt[a + 1] < 3) continue;   // 两个三张凑不出来

        // |T| = g2 - 2 + [cnt[a]≥5] + [cnt[a+1]≥5]
        // （a 与 a+1 本来都算进了 g2，扣掉；如果它们还剩 ≥2 张，再加回来）
        long long T = g2 - 2 + (cnt[a] >= 5) + (cnt[a + 1] >= 5);
        // |T4| = g4 - [cnt[a]≥4] - [cnt[a+1]≥4] + [cnt[a]≥7] + [cnt[a+1]≥7]
        long long T4 = g4 - (cnt[a] >= 4) - (cnt[a + 1] >= 4)
                          + (cnt[a] >= 7) + (cnt[a + 1] >= 7);

        long long pairs2 = T >= 2 ? T * (T - 1) / 2 : 0;   // 两个不同的点数做对子
        ans = (ans + pairs2 % MOD + T4 % MOD) % MOD;       // 同一个点数做两个对子
    }

    cout << ans % MOD << "\n";
    return 0;
}
