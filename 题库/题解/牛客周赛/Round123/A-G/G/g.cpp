// 牛客周赛 Round 123 G. 小红出千
// 题意：n 张牌（数字 a_i ≤ 10^9，可能有重复）。每次「出千」可以把任意一张牌改成
//       任意正整数。要使这 n 张牌最终成为一个「顺子」（重排后 x, x+1, ..., x+n-1，
//       即 n 个互不相同的连续整数），求最少出千次数，并给出一种方案。
//
// 关键 1：最后是 n 个**互不相同**的连续整数，所以**原样保留**下来的牌必须
//         数字互不相同，而且都落在一个长度 n 的区间 [L, L+n-1] 里。
//         所以「保留几张」= 某个长度 n 的区间里，最多覆盖多少种**不同的**数字。
//         （同一个数字有 10 张也只能保 1 张，其余的全得改。）
// 关键 2：把出现过的数字排序去重成 D[0..m-1]，用**同向双指针**求
//         D[j] - D[i] ≤ n-1 的最宽窗口，窗口里的数字个数就是能保留的最大张数。
//         答案 k = n - 最多保留数。
// 关键 3：构造方案——区间取 L = max(1, D[j] - n + 1)，保留窗口里每个数字
//         **第一次出现**的那张牌，剩下的每张空闲牌依次填进 [L, L+n-1] 里
//         没被占用的数字（空闲牌数 = 空缺数，正好一一对应）。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<long long> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    // 按（数字，下标）排序，得到去重后的数字表 D 和每个数字第一次出现的下标
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 1);
    sort(ord.begin(), ord.end(), [&](int i, int j) {
        return a[i] != a[j] ? a[i] < a[j] : i < j;
    });

    vector<long long> D;                 // 出现过的数字（升序、去重）
    vector<int> firstIdx;                // 每个数字在输入里第一次出现的下标
    for (int k = 0; k < n; k++) {
        if (k == 0 || a[ord[k]] != a[ord[k - 1]]) {
            D.push_back(a[ord[k]]);
            firstIdx.push_back(ord[k]);
        }
    }
    int m = (int)D.size();

    // 同向双指针：窗口内数字的跨度不超过 n-1（这样它们才能塞进长度 n 的区间）
    int best = 0, bi = 0, bj = 0, i = 0;
    for (int j = 0; j < m; j++) {
        while (D[j] - D[i] > n - 1) i++;
        if (j - i + 1 > best) { best = j - i + 1; bi = i; bj = j; }
    }

    long long L = max(1LL, D[bj] - (long long)n + 1);   // 目标顺子的起点

    // 保留：窗口里每个数字取第一次出现的那张
    vector<char> keep(n + 1, 0);
    for (int k = bi; k <= bj; k++) keep[firstIdx[k]] = 1;

    // 要改的牌（按输入顺序）与要填的空缺（按数字升序）
    vector<int> freeCard;
    for (int x = 1; x <= n; x++) if (!keep[x]) freeCard.push_back(x);

    vector<long long> freeTarget;
    int p = bi;                                  // 窗口里被保留数字的下标
    for (long long t = L; t <= L + n - 1; t++) {
        if (p <= bj && D[p] == t) { p++; continue; }   // 这个数字已被保留的牌占用
        freeTarget.push_back(t);
    }

    cout << freeCard.size() << "\n";
    for (size_t k = 0; k < freeCard.size(); k++)
        cout << freeCard[k] << " " << freeTarget[k] << "\n";
    return 0;
}
