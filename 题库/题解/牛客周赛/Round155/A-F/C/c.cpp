// C - 小月的密码锁
// 题意：长度为 n 的密码，每位是 A~E 按 A→B→C→D→E→A 循环。
//       选一个分界 c（前 c 位用偏移 p，后 n-c 位用偏移 q，p,q∈[0,4]），
//       每位沿循环方向移动对应偏移。求与目标 t 最少不同的位数。
// 思路：枚举 c(0..n)、p(0..4)、q(0..4)，对每位用对应偏移算移动后的字符，
//       与 t 比较统计不同数，取最小。
//       复杂度 O(n * (n+1) * 5 * 5) ≤ 1e3*1e3*25 = 2.5e7，C++ 轻松过。
#include <iostream>
#include <string>
#include <algorithm>

using namespace std;

int shift(int ch, int p) {           // 字符 ch('A'..'E') 循环移动 p 次
    return (ch - 'A' + p) % 5;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    string s, t;
    cin >> s >> t;

    int best = n;
    for (int c = 0; c <= n; ++c) {
        for (int p = 0; p < 5; ++p) {
            for (int q = 0; q < 5; ++q) {
                int diff = 0;
                for (int i = 0; i < n; ++i) {
                    int d = (i < c) ? p : q;
                    int ns = shift(s[i], d);
                    if (ns != (t[i] - 'A')) ++diff;
                }
                if (diff < best) best = diff;
            }
        }
    }

    cout << best << "\n";
    return 0;
}
