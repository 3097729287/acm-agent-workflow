// 牛客周赛 Round 123 A. 小红玩牌
// 题意：比两张牌的大小。先比点数，点数大的牌大；点数相同比花色，A > B > C > D。
// 输出 Yes 表示第一张比第二张大，否则 No。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n1, n2;          // 两张牌的点数
    char c1, c2;         // 两张牌的花色
    cin >> n1 >> c1;     // 第一张牌
    cin >> n2 >> c2;     // 第二张牌

    bool firstBigger;
    if (n1 != n2) {
        firstBigger = (n1 > n2);   // 点数不同：直接比点数
    } else {
        // 点数相同：花色 A>B>C>D。字符的 ASCII 恰好是 'A'<'B'<'C'<'D'，
        // 而我们需要的是"A 最大"，所以**字符更小的反而更大**，用 < 比较。
        firstBigger = (c1 < c2);
    }

    cout << (firstBigger ? "Yes" : "No") << "\n";
    return 0;
}
