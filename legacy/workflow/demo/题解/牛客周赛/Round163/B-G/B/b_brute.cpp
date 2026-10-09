// Round 163 B 对拍基准：另一种范式 —— 先把整个十六进制串展开成二进制字符串，
// 再数末尾零。和主解（从后往前逐位扫 + __builtin_ctz）思路不同，能互相揭错。
// 只用于随机对拍（长度小）；极限计时只跑主解。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string x;
    long long k;
    if (!(cin >> x >> k)) return 0;
    string bin;
    bin.reserve(x.size() * 4);
    for (char ch : x) {
        int v = (ch >= '0' && ch <= '9') ? ch - '0'
              : (ch >= 'a' && ch <= 'f') ? ch - 'a' + 10
              : ch - 'A' + 10;
        for (int b = 3; b >= 0; --b) bin.push_back(char('0' + ((v >> b) & 1)));
    }
    bool all_zero = true;
    for (char c : bin) if (c != '0') { all_zero = false; break; }
    long long z = 0;
    for (long long i = (long long)bin.size() - 1; i >= 0 && bin[i] == '0'; --i) ++z;
    cout << ((all_zero || z >= k) ? "YES" : "NO") << "\n";
    return 0;
}
