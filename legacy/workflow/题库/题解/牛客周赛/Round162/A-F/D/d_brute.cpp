#include <bits/stdc++.h>
using namespace std;

// 暴力（不同范式）：真把字符串拼出来再数相邻相同对
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    char c0;
    cin >> n >> c0;

    string cur(1, c0);
    for (int i = 1; i <= n; ++i) {
        char c;
        cin >> c;
        string rev = cur;
        reverse(rev.begin(), rev.end());
        cur = cur + c + rev;
    }

    int ans = 0;
    for (int i = 0; i + 1 < (int)cur.size(); ++i)
        if (cur[i] == cur[i + 1]) ++ans;
    cout << ans << '\n';
    return 0;
}
