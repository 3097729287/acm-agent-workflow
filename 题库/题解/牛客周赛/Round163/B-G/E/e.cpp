// E - 小月的门
// 两条线段“真正相交”（交点严格落在两条线段内部）才叫穿过。
// 用叉积判断：闸门线段 P1P2 与物品线段 AC
//   d1 = cross(P1,P2,A)，d2 = cross(P1,P2,C)  -> A、C 在闸门直线异侧
//   d3 = cross(A,C,P1)，d4 = cross(A,C,P2)    -> P1、P2 在物品直线异侧
// 两个条件同时成立才是“内部相交”（等号表示端点在对方直线上，不算穿过）。
// 方向：d1 > 0 说明起点在闸门直线左侧（库内）-> 出库，答案 -1；否则 +1。
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

// 求 (O->A) 与 (O->B) 的叉积：>0 表示 B 在向量 OA 的左侧
ll cross(ll ox, ll oy, ll ax, ll ay, ll bx, ll by) {
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox);
}

int main() {
    int n;
    scanf("%d", &n);
    ll u1, v1, u2, v2;
    scanf("%lld %lld %lld %lld", &u1, &v1, &u2, &v2);

    ll ans = 0;
    for (int i = 0; i < n; ++i) {
        ll a, b, c, d;
        scanf("%lld %lld %lld %lld", &a, &b, &c, &d);

        ll d1 = cross(u1, v1, u2, v2, a, b);   // 起点相对闸门直线的位置
        ll d2 = cross(u1, v1, u2, v2, c, d);   // 终点相对闸门直线的位置
        ll d3 = cross(a, b, c, d, u1, v1);     // 闸门起点相对物品直线的位置
        ll d4 = cross(a, b, c, d, u2, v2);     // 闸门终点相对物品直线的位置

        // 严格异侧（不写成 d1*d2<0 是为了避免两个大数相乘溢出）
        bool sideAC = (d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0);
        bool sideP  = (d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0);
        if (!sideAC || !sideP) continue;       // 没穿过（含端点相交、共线重合等）

        if (d1 > 0) --ans;   // 起点在库内 -> 从库内穿到库外，库内 -1
        else        ++ans;   // 起点在库外 -> 穿进库内，库内 +1
    }
    printf("%lld\n", ans);
    return 0;
}
