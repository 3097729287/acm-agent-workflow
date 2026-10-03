// 牛客周赛 Round 163 · C「小月的对局」—— DFS + 记忆化搜索（推荐提交版本）
//
// 思路：这就是一棵"博弈树"，我们用 DFS 把 Alice 的每一种出法、Bob 的每一种应对
//       全部试一遍。Alice 想找"存在一招能赢"，Bob 想找"存在一招能逃"。
//       同样的局面会被反复算到，所以加一张 memo 表把结果存下来（记忆化搜索）。
//
// 状态： (ma, mb) = Alice 手里剩的牌集合、Bob 手里剩的牌集合（用二进制位表示）
#include <bits/stdc++.h>
using namespace std;

int n;
int a[8], b[8];              // a = Alice 的牌, b = Bob 的牌

// memo[ma][mb]：-1 表示还没算过，0 表示这个局面 Alice 必败，1 表示 Alice 必胜
int memo[1 << 6][1 << 6];

// 判断：轮到 Alice 出牌、Alice 手里是集合 ma、Bob 手里是集合 mb 时，Alice 是否必胜
bool win(int ma, int mb) {
    if (ma == 0) return false;      // Alice 没牌可出了，牌打完还没赢 -> Bob 胜

    int &res = memo[ma][mb];        // 用引用，写 res 就等于写 memo[ma][mb]
    if (res != -1) return res;      // 算过了，直接返回（这就是"记忆化"）

    // 枚举 Alice 这一轮打出的牌 i
    for (int i = 0; i < n; ++i) {
        if (!(ma >> i & 1)) continue;          // 这张牌不在手里，跳过

        // 假设 Bob 怎么应对都挡不住，然后逐一验证
        bool aliceCanWinByThis = true;

        // Bob 看到 Alice 出的牌后，枚举自己打出的牌 j（他要挑一张最能保命的）
        for (int j = 0; j < n; ++j) {
            if (!(mb >> j & 1)) continue;              // 这张牌不在 Bob 手里
            if (__gcd(a[i], b[j]) > 1) continue;       // Bob 出这张就当场输，他不会选它

            // Bob 出 b[j] 能安全活过这一轮，那么看"去掉这两张牌之后"的局面
            if (win(ma ^ (1 << i), mb ^ (1 << j))) continue;  // 后续 Alice 还是必胜 -> 这张也救不了

            // 找到一张既能挡住、又能让 Alice 后面赢不了的牌 -> Bob 会用这张
            aliceCanWinByThis = false;
            break;
        }

        if (aliceCanWinByThis) return res = 1;   // 存在一招必胜 -> Alice 必胜
    }

    return res = 0;   // 所有出法都被 Bob 化解 -> Alice 必败
}

int main() {
    scanf("%d", &n);
    for (int i = 0; i < n; ++i) scanf("%d", &a[i]);
    for (int i = 0; i < n; ++i) scanf("%d", &b[i]);

    memset(memo, -1, sizeof(memo));      // -1 = 所有局面都还没算过
    int full = (1 << n) - 1;             // 一开始双方都是满手牌
    puts(win(full, full) ? "Alice" : "Bob");
    return 0;
}
