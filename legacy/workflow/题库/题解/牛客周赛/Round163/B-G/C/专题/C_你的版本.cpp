#include<bits/stdc++.h>
using namespace std;
#define int long long
#define rep(x,y,z) for(int x=y;x<=z;x++)
#define all(x) (x).begin(),(x).end()
#define endl '\n'
using PII=pair<int,int>;
#define pb push_back
#define eb emplace_back
int dx[]={0,1,0,-1,1,-1,1,-1};
int dy[]={1,0,-1,0,1,-1,-1,1};
const int MOD=1e9+7;
const int N=2e5+5;
int dp[1<<7][1<<7]={0};
void solve()
{
    int n;
    cin>>n;
    vector<int>a(n+1,0);
    vector<int>b(n+1,0);
    for(int i=1;i<=n;i++)
    cin>>a[i];
    for(int i=1;i<=n;i++)
    cin>>b[i];
    memset(dp,-1,sizeof(dp));
    function<bool(int,int)>dfs;
    //ALice能不能赢
    dfs=[&](int mask1,int mask2)->bool
    {
        if(mask1==0&&mask2==0)
        return false;
        if(dp[mask1][mask2]!=-1)
        return dp[mask1][mask2];

        //枚举Alice拿
        for(int p=0;p<n;p++)
        {
            if(mask1&(1<<p))
            {
                bool f=true;
                //Bob拿这个
                for(int pp=0;pp<n;pp++)
                {
                    if(mask2&(1<<pp))
                    {
                        //Bob和Alice选的数
                        int c=a[p+1];
                        int d=b[pp+1];
                        if(__gcd(c,d)>1)
                        {
                           continue;
                        }
                        bool kk=dfs(mask1^(1<<p),mask2^(1<<pp));
                        if(!kk)
                        {
                            f=false;
                            break;
                        }
                    }
                }
                if(f)
                return dp[mask1][mask2]=1;
            }
        }
        return dp[mask1][mask2]=0;
    };
    int ff=dfs((1<<n)-1,(1<<n)-1);
    cout<<(ff==1?"Alice":"Bob")<<endl;
}
signed main()
{
    solve();
    return 0;
}
