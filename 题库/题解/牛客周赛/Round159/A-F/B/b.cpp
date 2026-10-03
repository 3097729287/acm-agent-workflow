// B-小月的信号：统计二进制中 1 的个数、最低位 1、最高位 1
// 题意：把 x 看作二进制位图，输出「激活通道数」「最小编号」「最大编号」；x=0 时后两项为 -1。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    cin >> x;

    // x = 0：一位都没有激活，两个编号项按题意输出 -1
    if (x == 0) {
        cout << "0 -1 -1\n";
        return 0;
    }

    int cnt = __builtin_popcountll(x);          // 二进制里 1 的个数 = 激活通道总数
    int lo  = __builtin_ctzll(x);               // 末尾 0 的个数 = 最低位 1 的下标
    int hi  = 63 - __builtin_clzll(x);          // 最高位 1 的下标（x != 0，clz 有定义）
    cout << cnt << ' ' << lo << ' ' << hi << "\n";

    return 0;
}
