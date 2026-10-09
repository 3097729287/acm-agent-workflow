// A - 小月的奇偶灯控
// 题意：三个开关 x1,x2,x3 ∈ {0,1}，开启数为奇数 → 指示灯 ON，否则 OFF。
// 思路：只关心 1 的个数，模 2 即可。
#include <iostream>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int x1, x2, x3;
    if (!(cin >> x1 >> x2 >> x3)) return 0;

    int on = x1 + x2 + x3;          // 开启的开关数量
    cout << (on % 2 == 1 ? "ON" : "OFF") << "\n";
    return 0;
}
