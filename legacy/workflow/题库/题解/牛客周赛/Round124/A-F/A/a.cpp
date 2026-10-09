#include <bits/stdc++.h>
using namespace std;

// A 题 花绽晴窗含韵
// 题意：给 Alice 和 Bob 的棋子数 x、y，多者胜，相等为平局。
// 做法：直接比大小。签到题。

int main() {
    int x, y;
    cin >> x >> y;                 // 两个棋子数量
    if (x > y) cout << "Alice\n";  // Alice 多，Alice 胜
    else if (y > x) cout << "Bob\n";  // Bob 多，Bob 胜
    else cout << "Draw\n";         // 一样多，平局
    return 0;
}
