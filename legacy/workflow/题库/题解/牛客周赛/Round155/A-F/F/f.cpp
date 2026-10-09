// F - 小月的二进制分数
// 题意：给定 n 个非空 01 串，构造二进制正整数 p,q(0<p<q, 1≤|p|<|q|≤1000)，
//       使每个 s_i 都是分数 p/q 的标准二进制小数展开 d1d2… 的连续子串；
//       输出 p,q 的二进制串，以及每个 s_i 在展开中的起始位置 a_i(1-based)。
// 构造思路：
//   1) 把全部 s_i 串接成 S（每个 s_i 都作为 S 的连续子串出现）。记 C=|S|≤1000。
//   2) 取无限序列 0.(L 个 0)(S)(S)(S)… ，其值为 S/(2^L·(2^C-1))。
//      该值的标准二进制展开正是 0.(L 个 0 之后 S 循环)，必然包含每个 s_i。
//   3) 令 p = S 作为 C 位二进制的值（输出时去掉前导 0），
//      q = (2^C - 1)·2^L 的二进制 = C 个 '1' 后接 L 个 '0'。
//      p<q 显然；|p|<|q| 通过选 L 保证（S 以 '1' 开头则 L=1，否则 L=0）。
//   4) a_i = L + (s_i 在 S 中的 1-based 位置)。
//   特例：S 全 0 → 输出 p="1", q="10"（展开 0.1000… 含任意长 0 串），a_i=2。
//   特例：S 全 1 → 前缀补一个 '0' 得到 S="0"+ones，既仍含原串又避免 p==q。
// 复杂度 O(Σ|s_i|)，只做字符串拼接与二进制输出。
#include <iostream>
#include <string>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<string> ss(n);
    for (int i = 0; i < n; ++i) cin >> ss[i];

    string S;
    for (int i = 0; i < n; ++i) S += ss[i];

    // 全 0 特判
    bool allzero = true;
    for (char c : S) if (c != '0') { allzero = false; break; }
    if (allzero) {
        cout << "1\n10\n";
        for (int i = 0; i < n; ++i) cout << (i ? " " : "") << "2";
        cout << "\n";
        return 0;
    }

    // 全 1 特判：前缀补 0
    bool allone = true;
    for (char c : S) if (c != '1') { allone = false; break; }
    if (allone) S = "0" + S;

    int C = (int)S.size();
    int L = (S[0] == '1') ? 1 : 0;

    // p：S 去前导 0
    string p_str = S;
    size_t f = p_str.find_first_not_of('0');
    if (f == string::npos) p_str = "0";
    else p_str = p_str.substr(f);

    // q：C 个 '1' 后接 L 个 '0'
    string q_str = string(C, '1') + string(L, '0');

    cout << p_str << "\n" << q_str << "\n";

    for (int i = 0; i < n; ++i) {
        size_t pos = S.find(ss[i]);           // 0-based
        long long a = (long long)L + (pos + 1);
        cout << (i ? " " : "") << a;
    }
    cout << "\n";
    return 0;
}
