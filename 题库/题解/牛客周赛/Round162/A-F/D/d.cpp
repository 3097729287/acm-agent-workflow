#include <bits/stdc++.h>
using namespace std;

// 一次复制：s -> s + c + reverse(s)
// 关键观察：新串的首字符 = s 的首字符，尾字符 = reverse(s) 的尾 = s 的首字符
//   => 首字符永远是 c0，尾字符也永远是 c0
// 相邻相同对数：s 内部 f(s) + reverse(s) 内部 f(s) + 两处接缝（last(s) 与 c、c 与 last(s)）
//   => f(new) = 2*f(s) + 2*[c == c0]
// 第 i 轮的贡献会被后面 (n-i) 轮翻倍：系数 2^(n-i+1)
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    char c0;
    cin >> n >> c0;

    long long f = 0;
    for (int i = 1; i <= n; ++i) {
        char c;
        cin >> c;
        if (c == c0) f += 1LL << (n - i + 1);   // n<=60，最大 2^61-2，long long 装得下
    }
    cout << f << '\n';
    return 0;
}
