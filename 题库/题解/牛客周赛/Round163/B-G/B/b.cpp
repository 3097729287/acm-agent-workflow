// B - 小月的十六进制
// 判断十六进制串 x 表示的数能否被 2^k 整除
// 做法：一个数能被 2^k 整除 <=> 它的二进制末尾至少有 k 个 0
// 十六进制每一位恰好是 4 个二进制位，所以可以从末位往前数 0
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string x;          // 十六进制字符串
    int k;             // 2 的指数
    cin >> x >> k;

    long long zeros = 0;   // 已经数出来的“二进制末尾 0”的个数
    bool allZero = true;   // x 表示的数是不是 0

    // 从字符串最后一位（最低的十六进制位）往前扫
    for (int i = (int)x.size() - 1; i >= 0; --i) {
        int d;                                   // 这一位对应的数值 0~15
        if (isdigit((unsigned char)x[i])) d = x[i] - '0';
        else                              d = tolower(x[i]) - 'a' + 10;

        if (d == 0) {
            zeros += 4;          // 这一位是 0，它贡献 4 个二进制 0，继续往前看
        } else {
            allZero = false;     // 遇到第一个非 0 位，数到这里就够了
            zeros += __builtin_ctz(d);   // d 自己的二进制末尾 0 的个数（d>0 才有定义）
            break;
        }
    }

    // 整个数是 0 时，0 = 0 * 2^k，任何 k 都整除
    if (allZero || zeros >= k) cout << "YES\n";
    else                       cout << "NO\n";
    return 0;
}
