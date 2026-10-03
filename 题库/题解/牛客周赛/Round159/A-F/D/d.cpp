// D-小月的校验码：把 01 串当位掩码，枚举「翻转一位」查表
// 题意：n 个互不相同的长 b 的 01 串，统计恰好一位不同的无序对总数，以及每一位上的对数。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, b;
    cin >> n >> b;

    // has[v] = 编号为 v 的串是否在集合里。b <= 20 → 最多 2^20 ≈ 1.05×10^6 个状态
    vector<char> has(size_t(1) << b, 0);
    vector<int> code(n);                       // 输入串转成的整数（第 1 个字符是最高位）
    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        int v = 0;
        for (char c : s) v = v * 2 + (c - '0');
        code[i] = v;
        has[v] = 1;
    }

    // diff[i]：第 i 个字符位（1-based，从左往右数）产生差异的对数，
    // 每个无序对会被两个端点各数一次，所以最后统一除以 2
    vector<long long> diff(b + 1, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < b; j++) {
            int y = code[i] ^ (1 << j);        // 把第 i 个串的第 j 个二进制位翻过来
            if (has[y]) {
                // 二进制第 j 位（0-based，从低位起）对应字符串第 (b-j) 个字符
                diff[b - j]++;
            }
        }
    }

    long long total = 0;
    for (int i = 1; i <= b; i++) total += diff[i];
    total /= 2;                                // 每对恰好被数了两次

    cout << total << "\n";
    for (int i = 1; i <= b; i++) {
        cout << diff[i] / 2 << " \n"[i == b];
    }

    return 0;
}
