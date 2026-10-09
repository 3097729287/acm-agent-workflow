// E-小月的前缀集合：给每个 01 串前缀编一个「不会撞车」的整数编号，用数组记出现次数
// 题意：初始为空的 01 串可重集合，支持插入/删除，每次操作后输出「所有串的不同非空前缀」个数。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // 编号规则：先写上 1，再依次接上前缀的每个字符。
    //   前缀 "0"   -> 10        = 2
    //   前缀 "01"  -> 101       = 5
    //   前缀 "101" -> 1101      = 13
    // 长度为 L 的前缀编号落在 [2^L, 2^(L+1)) 里，不同长度天然分居不同区间，绝不会撞车。
    // L <= 20，所以编号最大 2^21 - 1。
    const int MAXCODE = 1 << 21;
    vector<int> occ(MAXCODE, 0);   // occ[c] = 集合中有多少个串以编号 c 对应的串为前缀

    int q;
    cin >> q;

    long long distinct = 0;        // 当前「出现次数 >= 1」的编号个数 = 不同前缀个数
    while (q--) {
        char op;
        string s;
        cin >> op >> s;

        int delta = (op == '+') ? 1 : -1;   // 插入 +1，删除 -1
        int code = 1;                       // 起始标记位：保证每种长度独立成区间
        for (char c : s) {
            code = code * 2 + (c - '0');    // 每读一个字符，编号左移一位再接上这一位
            occ[code] += delta;
            if (occ[code] == 1 && delta == 1) distinct++;   // 这个前缀第一次出现
            if (occ[code] == 0 && delta == -1) distinct--;  // 这个前缀彻底消失
        }

        cout << distinct << "\n";
    }

    return 0;
}
