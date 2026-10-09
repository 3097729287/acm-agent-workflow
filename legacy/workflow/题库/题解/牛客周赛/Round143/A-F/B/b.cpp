// B - 小红的冷门副本
// 题意：编号 1..m 的副本，n 个人各选了一个，选择人数 c_j <= x 的叫冷门副本，
//       求冷门副本数量（没人选的副本 c_j=0 也算）。
// 关键：只有"出现过的编号"才可能不是冷门，出现过的编号最多 n 个（n<=2e5），
//       所以用排序统计出现次数即可，不需要开 m 大小的数组（m 能到 1e9）。
// 答案 = m - (出现次数 > x 的编号个数)。
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    long long m, x;
    scanf("%d %lld %lld", &n, &m, &x);
    vector<long long> a(n);
    for (int i = 0; i < n; i++) scanf("%lld", &a[i]);
    sort(a.begin(), a.end());

    long long ans = m;                 // 先假定 m 个副本全是冷门
    for (int i = 0; i < n; ) {
        int j = i;
        while (j < n && a[j] == a[i]) j++;
        long long c = j - i;           // 编号 a[i] 被选择了 c 次
        if (c > x) ans--;              // 人数超过 x，不是冷门副本
        i = j;
    }
    printf("%lld\n", ans);
    return 0;
}
