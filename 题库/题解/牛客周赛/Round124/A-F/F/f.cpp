#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
typedef __int128 lll;

// F 题 竹摇清风拂面
// 题意：n 个字符按顺时针放在圆周上（下标 0..n-1），第 i 个字符 s[i]、权值 a[i]。
//       选若干对 (i,j)，i != j、s[i] == s[j]，每个点恰好被连一次（完美匹配），
//       代价 a[i]*a[j]。在所有「线段互不相交」的匹配里求最小总代价；不存在输出 -1。
//
// 关键 1（存在性）：圆周上两两不相交的完美匹配 ⟺ 这个字符串可以反复删掉
//   「相邻且相同」的字符变成空串（栈消除）。把某条线段的一侧切开摊平，它就是一对
//   配对的括号：里面必须自成一组能配完的点，外面同理；两端相邻时正是"删掉相邻相同"。
//
// 关键 2（圆上做区间 DP）：把 s 复制成 2n 长，做一遍区间 DP，只取 n 个长度为 n 的窗口
//   的最小值。为什么可以这样：
//     · 圆上任取一个不相交匹配，把圆周在某条弧上剪开摊平，它就是直线上的一个不相交匹配；
//       摊平后落在窗口 [k, k+n-1] 里的部分，用下面的 dp 一定能表示出来（线段只在窗口内配对）。
//     · 窗口外那一头（双倍串里下标 >= k+n）不用另外算：它对应的正是圆上"跨过切口"的线段，
//       由转移 ② 覆盖。
//   （之前写成"对 n 个切口各做一遍完整 DP"，n=500 全同字母时最坏 33.9 秒；
//     改成一次双倍串 DP、只取 n 个窗口后为 O(n^3)，见题解实测记录。）
//
// dp[l][r]（双倍串下标）= 把 l..r 这段点两两配完、线段互不相交的最小代价：
//     ① l 与窗口内的 j 配对（l < j <= r, s[l] == s[j]）：
//          a[l]*a[j] + dp[l+1][j-1] + dp[j+1][r]
//     ② l 与"跨出去"的 j 配对（j > r, s[l] == s[j]）：a[l]*a[j] + dp[l+1][r]
//   区间长度只能是偶数；空区间代价 0。
//
// 复杂度：O(n^3)，n <= 500 且单文件 n 之和 <= 500。

const lll INF = (lll)1 << 120;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;
        vector<ll> a(n);
        for (int i = 0; i < n; ++i) cin >> a[i];

        if (n % 2 == 1) {                 // 奇数个点不可能两两配对
            cout << -1 << "\n";
            continue;
        }

        // ---- 存在性：栈消除 ----
        string stk;
        for (char ch : s) {
            if (!stk.empty() && stk.back() == ch) stk.pop_back();
            else stk.push_back(ch);
        }
        if (!stk.empty()) {               // 消不掉 -> 不存在不相交完美匹配
            cout << -1 << "\n";
            continue;
        }

        // ---- 双倍串 + 区间 DP ----
        int N = 2 * n;
        string t = s + s;
        vector<ll> b(N);
        for (int i = 0; i < N; ++i) b[i] = a[i % n];

        // dp 尺寸取 N + 2：下标会用到 l+1、j+1，最远 N
        vector<vector<lll>> dp(N + 2, vector<lll>(N + 2, INF));

        for (int len = 2; len <= n; len += 2) {
            for (int l = 0; l + len - 1 < N; ++l) {
                int r = l + len - 1;
                lll res = INF;
                // ① l 与窗口内的 j 配对
                for (int j = l + 1; j <= r; j += 2) {
                    if (t[l] != t[j]) continue;
                    lll inner = (j - 1 >= l + 1) ? dp[l + 1][j - 1] : 0;
                    lll outer = (r >= j + 1) ? dp[j + 1][r] : 0;
                    if (inner >= INF || outer >= INF) continue;
                    lll cand = (lll)b[l] * b[j] + inner + outer;
                    if (cand < res) res = cand;
                }
                // ② l 与"跨出去"的 j 配对：把窗口内剩下的 l+1..r 自己配完
                for (int j = r + 1; j < N; ++j) {
                    if (t[l] != t[j]) continue;
                    lll rest = (r >= l + 1) ? dp[l + 1][r] : 0;
                    if (rest >= INF) continue;
                    lll cand = (lll)b[l] * b[j] + rest;
                    if (cand < res) res = cand;
                    break;                // 只需要最近的那个同字母点
                }
                dp[l][r] = res;
            }
        }

        // ---- 取 n 个长度为 n 的窗口 ----
        lll best = INF;
        for (int k = 0; k + n - 1 < N; ++k)
            if (dp[k][k + n - 1] < best) best = dp[k][k + n - 1];

        if (best >= INF) cout << -1 << "\n";
        else cout << (ll)best << "\n";
    }
    return 0;
}
