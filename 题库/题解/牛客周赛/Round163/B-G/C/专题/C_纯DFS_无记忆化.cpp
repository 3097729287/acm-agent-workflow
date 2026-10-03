// 牛客周赛 Round 163 · C「小月的对局」—— 纯 DFS，不加记忆化（用来做对比实验）
//
// 逻辑和 C_DFS记忆化.cpp 一模一样，唯一的区别是：不查表、不存表。
// 它会重复计算大量相同的局面，所以我们会数一数"到底递归了多少次"，
// 把这个次数打到 stderr，方便和记忆化版本比较。
#include <bits/stdc++.h>
using namespace std;

int n;
int a[8], b[8];
long long calls = 0;        // 递归调用次数计数器

bool win(int ma, int mb) {
    ++calls;                            // 每进一次函数就 +1
    if (ma == 0) return false;

    for (int i = 0; i < n; ++i) {
        if (!(ma >> i & 1)) continue;

        bool aliceCanWinByThis = true;
        for (int j = 0; j < n; ++j) {
            if (!(mb >> j & 1)) continue;
            if (__gcd(a[i], b[j]) > 1) continue;
            if (win(ma ^ (1 << i), mb ^ (1 << j))) continue;
            aliceCanWinByThis = false;
            break;
        }
        if (aliceCanWinByThis) return true;
    }
    return false;
}

int main() {
    scanf("%d", &n);
    for (int i = 0; i < n; ++i) scanf("%d", &a[i]);
    for (int i = 0; i < n; ++i) scanf("%d", &b[i]);

    int full = (1 << n) - 1;
    bool ans = win(full, full);
    puts(ans ? "Alice" : "Bob");
    fprintf(stderr, "纯 DFS 递归调用次数 = %lld\n", calls);
    return 0;
}
