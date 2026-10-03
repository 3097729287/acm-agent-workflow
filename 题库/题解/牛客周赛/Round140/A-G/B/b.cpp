// 牛客周赛 Round 140 B - 小红的牛魔
// 思路：删除 "niu" / "mo" 两个模式互不重叠（没有临界对），重写系统合流，
//       所以从左往右用栈「能消就消」，最后看栈是否为空。
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string s;
    cin >> n >> s;

    string st;                      // 栈：当前的不可约简形式
    st.reserve(n);
    for (char ch : s) {
        st.push_back(ch);
        int m = (int)st.size();
        if (m >= 3 && st[m - 3] == 'n' && st[m - 2] == 'i' && st[m - 1] == 'u') {
            st.resize(m - 3);       // 弹出 "niu"
        } else if (m >= 2 && st[m - 2] == 'm' && st[m - 1] == 'o') {
            st.resize(m - 2);       // 弹出 "mo"
        }
        // 弹出后剩下的还是「不可约」的：它是弹出前栈的前缀，而前缀不可能突然出现新模式
    }
    cout << (st.empty() ? "Yes" : "No") << "\n";
    return 0;
}
