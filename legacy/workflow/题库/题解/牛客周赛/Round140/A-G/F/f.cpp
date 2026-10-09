// 牛客周赛 Round 140 F - 小红的三角形构造
// 思路：x 当直角边。
//   x 为奇数 (x>=3)：x² = ((x²+1)/2)² - ((x²-1)/2)²，取 (x, (x²-1)/2, (x²+1)/2)
//   x 为偶数 (x>=4)：x² = ((x/2)²+1)² - ((x/2)²-1)²，取 (x, (x/2)²-1, (x/2)²+1)
// x = 1、2 无解（枚举 (c-b)(c+b)=x² 的因子对可证），其余都有解。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        long long x;
        cin >> x;
        if (x <= 2) {
            cout << "No\n";
            continue;
        }
        long long a = x, b, c;
        if (x & 1LL) {
            long long h = (x * x - 1) / 2;   // x² ≤ 10^18，long long 装得下
            b = h;
            c = h + 1;
        } else {
            long long h = x / 2;
            h = h * h;
            b = h - 1;
            c = h + 1;
        }
        cout << "Yes\n" << a << " " << b << " " << c << "\n";
    }
    return 0;
}
