#include <bits/stdc++.h>
using namespace std;

// n 段纸带，每段两端各一张贴纸 -> 共 2n 张
// 首尾相接有 n-1 个连接处，每个连接处两张贴纸重叠、只看得见一张 -> 少 n-1 张
// 答案 = 2n - (n-1) = n+1
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    cout << n + 1 << '\n';
    return 0;
}
