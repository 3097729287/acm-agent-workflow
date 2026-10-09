// A-小月的模块：二选一多路器
// 题意：给定选择信号 s 与两路数据 a、b，s=0 输出 a，s=1 输出 b。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int s, a, b;
    cin >> s >> a >> b;

    // s 只有两种取值：0 走第一路，1 走第二路
    if (s == 0) cout << a << "\n";   // 选择信号为 0：输出第一路数据
    else        cout << b << "\n";   // 选择信号为 1：输出第二路数据

    return 0;
}
