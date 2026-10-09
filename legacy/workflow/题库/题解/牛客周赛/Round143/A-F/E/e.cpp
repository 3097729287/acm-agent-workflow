// E - 小红的好矩阵
// 题意：2×n 的 01 矩阵，要求每个 0 的四连通块大小恰为 3，每个 1 的四连通块大小也恰为 3。
//       每次可以改一个字符，求最少修改次数，做不到输出 -1。
// 结构结论（已用 n<=12 的全枚举 + 独立 DFS 枚举器验证）：
//   合法矩阵 ⟺ 每 3 列切成一段，每段是 6 种"段模式"之一，且相邻段的接口逐行异色。
//   - 总格数 2n 必须能被 3 整除，所以 n 不是 3 的倍数时直接 -1；
//   - 每段 6 格正好是两个 3 格块，6 种模式由 2×3 段内穷举得到；
//   - 相邻段若某一行同色，两块会粘成 4 格以上的块，所以接口必须逐行异色。
// 于是变成一条链上的 DP：dp[段][模式] = 最小修改数。
#include <bits/stdc++.h>
using namespace std;
const int INF = 1e9;

// 6 种段模式（上排 3 格、下排 3 格）
const char* SU[6] = {"110", "100", "011", "001", "111", "000"};
const char* SD[6] = {"100", "110", "001", "011", "000", "111"};
// 每种模式的左列颜色、右列颜色（上,下）
const int LC[6][2] = {{1,1},{1,1},{0,0},{0,0},{1,0},{0,1}};
const int RC[6][2] = {{0,0},{0,0},{1,1},{1,1},{1,0},{0,1}};

int main() {
    int n;
    cin >> n;   // 注意：这里不能写 scanf——后面接 cin，实测（UCRT64 g++ 16.2.0）混用会读空
    string s0, s1;
    cin >> s0 >> s1;

    if (n % 3 != 0) { puts("-1"); return 0; }   // 2n 不是 3 的倍数，无法分块

    int t = n / 3;
    vector<array<int, 6>> dp(t, array<int, 6>());
    for (int m = 0; m < 6; m++) {               // 第 0 段
        int c = 0;
        for (int j = 0; j < 3; j++) {
            c += (s0[j] != SU[m][j]);
            c += (s1[j] != SD[m][j]);
        }
        dp[0][m] = c;
    }
    for (int seg = 1; seg < t; seg++) {         // 第 seg 段
        for (int m = 0; m < 6; m++) {
            int best = INF;
            for (int p = 0; p < 6; p++)         // 前一段 p 能接 m：接口逐行异色
                if (RC[p][0] != LC[m][0] && RC[p][1] != LC[m][1])
                    best = min(best, dp[seg - 1][p]);
            int c = 0;
            for (int j = 0; j < 3; j++) {
                c += (s0[3 * seg + j] != SU[m][j]);
                c += (s1[3 * seg + j] != SD[m][j]);
            }
            dp[seg][m] = best + c;
        }
    }
    int ans = INF;
    for (int m = 0; m < 6; m++) ans = min(ans, dp[t - 1][m]);
    printf("%d\n", ans);
    return 0;
}
