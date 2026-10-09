// C - 小月的对局 · 写法 A：全排列枚举
// 判据：Alice 胜 ⟺ 不存在一组“每一对都互质（gcd==1）”的完整配对
// 依据：Bob 可以开局固定一个排列当“应对表”，照单对接，Alice 就永远赢不了。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n), b(n);
    for (auto &c : a) cin >> c;
    for (auto &c : b) cin >> c;

    sort(a.begin(), a.end());          // next_permutation 要求先升序
    do {
        sort(b.begin(), b.end());      // 每轮外层都要把 b 复位，才能重新枚举它的全排列
        do {
            bool has_block = false;    // 这组配对里有没有 gcd>1 的一对
            for (int i = 0; i < n; i++) {
                if (gcd(a[i], b[i]) > 1) { has_block = true; break; }
            }
            if (!has_block) {          // 找到一组“全互质”的配对 → Bob 照单对接就能赢
                cout << "Bob" << '\n';
                return 0;              // 找到一组就够，直接结束
            }
        } while (next_permutation(b.begin(), b.end()));
    } while (next_permutation(a.begin(), a.end()));

    cout << "Alice" << '\n';           // 所有配对都有 gcd>1 的一对 → Alice 必胜
    return 0;
}
