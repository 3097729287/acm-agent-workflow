// B - 小月的立方体
// 题意：边长为 a 的格点立方体，坐标 (x,y,z)∈[0,a]^3。
//       求四条体对角线（含重复计入）上所有格点的 v 之和。
// 四条体对角线（相对顶点对）：
//   (0,0,0)-(a,a,a)        : x==y==z
//   (0,0,a)-(a,a,0)        : x==y 且 z==a-x
//   (0,a,0)-(a,0,a)        : x==z 且 y==a-x
//   (0,a,a)-(a,0,0)        : y==z 且 x==a-y
// 输入：a，之后 (a+1)^2 行，每 a+1 行为一组按 z 分层（k 从 0..a），
//       第 k 组第 i 行第 j 个 = v_{j-1, i-1, k-1}。
#include <iostream>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int a;
    if (!(cin >> a)) return 0;
    int S = a + 1;
    // v[z][y][x]
    vector<vector<vector<long long>>> v(
        S, vector<vector<long long>>(S, vector<long long>(S, 0)));

    for (int z = 0; z < S; ++z)
        for (int y = 0; y < S; ++y)
            for (int x = 0; x < S; ++x)
                cin >> v[z][y][x];

    long long ans = 0;
    for (int z = 0; z < S; ++z)
        for (int y = 0; y < S; ++y)
            for (int x = 0; x < S; ++x) {
                int cnt = 0;
                if (x == y && y == z)          cnt++;   // 对角线 1
                if (x == y && z == a - x)      cnt++;   // 对角线 2
                if (x == z && y == a - x)      cnt++;   // 对角线 3
                if (y == z && x == a - y)      cnt++;   // 对角线 4
                ans += (long long)cnt * v[z][y][x];
            }

    cout << ans << "\n";
    return 0;
}
