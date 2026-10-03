#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<long long> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    // a[0] 一定是记录点，先把它记上
    long long mx = a[0];          // 目前见过的最大值
    int cnt = 1;                  // 记录点个数
    int last = 0;                 // 上一个记录点的下标
    int best = 0;                 // 相邻记录点下标之差的最大值

    for (int i = 1; i < n; i++) {
        if (a[i] > mx) {          // 严格大于左侧所有元素
            cnt++;
            best = max(best, i - last);
            last = i;
            mx = a[i];
        }
    }

    cout << cnt << ' ' << best << '\n';
    return 0;
}
