// A - 小红的区间构造
// 题意：给定 x，输出一对整数 l<=r，使 [l,r] 中恰好有 x 个不同的正整数。
// 直接取 [1,x]：区间内正整数正好是 1,2,...,x，共 x 个。
// x 最大 1e18，在 [-1e18,1e18] 范围内，合法。
#include <bits/stdc++.h>
using namespace std;

int main() {
    long long x;
    scanf("%lld", &x);
    printf("1 %lld\n", x);
    return 0;
}
