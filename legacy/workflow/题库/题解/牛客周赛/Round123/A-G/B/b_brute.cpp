// B 题暴力（跟正解**不同实现范式**）：正解是一次算完的公式，
// 这里用「能改就改」的模拟——不停地找一张多余的牌，挪到一个缺牌的数字上，
// 挪一次记一次，直到每个数字都不多不少。用来对拍验证公式。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int x[14], y[14];
    for (int i = 1; i <= 13; i++) cin >> x[i];
    for (int i = 1; i <= 13; i++) cin >> y[i];

    int need[14];
    for (int i = 1; i <= 13; i++) need[i] = 4 - y[i];

    long long ops = 0;
    while (true) {
        int from = -1, to = -1;
        for (int i = 1; i <= 13; i++) if (x[i] > need[i]) { from = i; break; }
        if (from < 0) break;                     // 没有多余的牌，收工
        for (int j = 1; j <= 13; j++) if (x[j] < need[j]) { to = j; break; }
        x[from]--;                               // 把 from 的一张牌改成 to
        x[to]++;
        ops++;
    }

    cout << ops << "\n";
    return 0;
}
