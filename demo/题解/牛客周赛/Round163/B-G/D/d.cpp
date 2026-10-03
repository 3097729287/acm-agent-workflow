// D - 小月的地砖
// 构造：想象一条总长为 S = sum(a_i) 的一维带子，把第 i 行要填的 a_i 个 1
//       依次摆在带子上（第 i 行占 [P_i, P_i + a_i)，P_i 是前 i-1 行的 1 的个数之和）。
//       带子上第 t 个位置映射到列 t mod m。
// 这样：每行的 1 在环上连续；每一列被用到的次数只差不超过 1。
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    scanf("%d %d", &n, &m);
    vector<int> a(n);
    for (int i = 0; i < n; ++i) {
        scanf("%d", &a[i]);
    }

    vector<string> g(n, string(m, '0'));
    long long ptr = 0;              // 当前这一行在“总带子”上的起点
    for (int i = 0; i < n; ++i) {
        for (int t = 0; t < a[i]; ++t) {
            int col = (int)((ptr + t) % m);   // 带子上的位置 -> 列号
            g[i][col] = '1';
        }
        ptr += a[i];                // 下一行的起点往后挪 a_i
    }

    for (int i = 0; i < n; ++i) puts(g[i].c_str());
    return 0;
}
