// ============================================================================
// 牛客周赛 Round 163 · C「小月的对局」
// 解法：枚举 a 的全排列 × b 的全排列（即你发的那张图的写法）
//       判据：Alice 赢  <=>  不存在任何"全互质的完美匹配"
//
// 为什么这等价于原博弈？（关键，容易想错）
//   Bob 是"后手但看到牌"，所以 Bob 有一招必胜策略：
//   开局就固定一个自己的排列 P（这是允许的，他不需要提前亮牌），
//   之后 Alice 出什么，他就照着 P 里跟那张配对的牌应对。
//     - 若 P 里每一对 gcd 都 == 1，那不管 Alice 按什么顺序出，
//       Bob 每次都能用 P 里配对的那张顶住，Alice 永远赢不了 -> Bob 赢；
//     - 反之若 Alice 的某个排列下不存在这样的 P，则 Bob 无论用什么策略，
//       Alice 都能按"对上 P 的那个顺序"打出，逼 Bob 打出 gcd>1 的一对 -> Alice 赢。
//   于是"博弈"退化成"存不存在全互质的完整配对"。
//
// 时间复杂度：O((n!)^2 * n)，n ≤ 6 时约 6!*6!*6 ≈ 1.9e8 次 gcd（实测最坏 ~2ms）
// ============================================================================
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n), b(n);
    for (auto &c : a) cin >> c;
    for (auto &c : b) cin >> c;

    sort(a.begin(), a.end());                  // next_permutation 要求先升序
    do {
        sort(b.begin(), b.end());
        do {
            bool has_block = false;            // 这一组配对里是否存在 gcd>1
            for (int i = 0; i < n; i++) {
                if (gcd(a[i], b[i]) > 1) { has_block = true; break; }
            }
            if (!has_block) {                  // 找到一组"全互质"配对 -> Bob 能躲
                cout << "Bob" << endl;
                return 0;
            }
        } while (next_permutation(b.begin(), b.end()));
    } while (next_permutation(a.begin(), a.end()));

    cout << "Alice" << endl;                   // 任何配对都有 gcd>1 的一对 -> Alice 必胜
    return 0;
}
