"""Explicit local test profiles; original statements reviewed, no archive scripts run.

Oracles below enumerate choices/pairs/sets/cells instead of invoking reference C++.
AC means this deterministic local suite passed, never the original OJ's verdict.
Profile IDs are fixed to the reviewed problem semantics, not matched by tags/titles.
"""
import itertools
import math
import random
from fractions import Fraction
from functools import lru_cache

PROFILES = {
    'ABC 478::D': '逐集合模拟；重复、相交、分离区间；最大 N/Q',
    'ABC 478::E': '小图枚举所有赋值；独立不等式判定器；严格环与最大链',
    'Div.4 1003::C1': '枚举每个元素是否变换；边界及最大数组',
    'Div.4 1003::C2': '枚举每个元素的所有选项；边界及最大数组',
    'Div.4 1003::D': '枚举数组排列与逐项累计分数；64 位最大输入',
    'Div.4 993::E': '枚举区间所有数对并检查整数比；最大范围与幂边界',
    'Div.4 1003::G': '枚举所有 i≤j 数对并试除 LCM；半素数与最大数组',
    'Div.4 993::H': '逐格展开子矩阵并加权；矩形方向、64 位及最大矩阵',
    '入门赛 49::D': '完整 n=1–60；按不相邻二步位置组合计数',
    '入门赛 50::F': '枚举有限物品子集和唯一无限种类；最大容量与 64 位',
    '基础赛 37::B': '精确分数重建最终位置；固定点分段与大规模',
    '入门赛 46::H': '逐查询 BFS；未知人名、自反关系与 500 人链',
    '周赛 164::C': '输入双因子分解求最大公约数；非唯一构造审核判定器',
    '周赛 164::D': '客户子集穷举；库存、预算、篮子与 64 位',
    '周赛 164::F': '叶删除序列穷举；星形排列计数与长路径边界',
}

def _case(name, text, expected):
    return {'name': name, 'input': text, 'output': str(expected)}

def _batch(cases):
    return str(len(cases))+'\n'+''.join(text.rstrip()+'\n' for text,_ in cases), '\n'.join(str(answer) for _,answer in cases)+'\n'

def _semi(value):
    factors=0;d=2
    while d*d<=value:
        while value%d==0: factors+=1;value//=d
        d+=1
    return factors+int(value>1)==2

def inequality_checker(inp, got, expected):
    values=list(map(int,inp.split()));n,q=values[:2]
    parts=got.split()
    if not parts or parts[0] not in ('Yes','No'):return False
    possible=expected.split()[0]=='Yes'
    if parts[0]=='No':return not possible and len(parts)==1
    if not possible or len(parts)!=n+1:return False
    try:a=list(map(int,parts[1:]))
    except ValueError:return False
    if not all(1<=v<=n for v in a):return False
    return all(a[u-1]+t<=a[v-1] for t,u,v in zip(values[2::3],values[3::3],values[4::3]))

def _max_gcd(x,y):
    factors={}
    for value in (x,y):
        p=2
        while p*p<=value:
            while value%p==0:factors[p]=factors.get(p,0)+1;value//=p
            p+=1 if p==2 else 2
        if value>1:factors[value]=factors.get(value,0)+1
    return math.prod(p**(count//2) for p,count in factors.items())

def gcd_checker(inp,got,expected):
    values=list(map(int,inp.split()))
    try:answers=list(map(int,got.split()))
    except ValueError:return False
    if len(answers)!=values[0]*2:return False
    return all(1<=a<=10**18 and 1<=b<=10**18 and a*b==x*y and math.gcd(a,b)==_max_gcd(x,y)
               for (x,y),(a,b) in zip(zip(values[1::2],values[2::2]),zip(answers[::2],answers[1::2])))

def build(identity):
    if identity not in PROFILES:return [],None
    rng=random.Random(20261008);cases=[];checker=None
    if identity=='入门赛 49::D':
        for n in range(1,61):
            answer=sum(math.comb(n-2*k+1,k) for k in range((n+1)//3+1))
            cases.append(_case('完整输入域 n='+str(n),str(n),answer))
    elif identity=='入门赛 50::F':
        tests=[]
        for _ in range(90):
            n=rng.randint(1,8);m=rng.randint(1,25);items=[(rng.randint(1,m),rng.randint(1,30),rng.choice((-1,1))) for _ in range(n)]
            singles=[item for item in items if item[2]==1];infinite=[item for item in items if item[2]==-1];best=0
            for mask in range(1<<len(singles)):
                w=sum(item[0] for i,item in enumerate(singles) if mask>>i&1);v=sum(item[1] for i,item in enumerate(singles) if mask>>i&1)
                if w>m:continue
                best=max(best,v,*[v+(m-w)//iw*iv for iw,iv,_ in infinite])
            tests.append((f'{n} {m}\n'+''.join(f'{w} {v} {c}\n' for w,v,c in items),best))
        text,expect=_batch(tests);cases.append(_case('有限子集及唯一无限种类 90 组',text,expect))
        for c in (-1,1):cases.append(_case('最大容量价值',f'1\n5000 5000\n'+f'1 1000000000 {c}\n'*5000,5000*10**9))
    elif identity=='基础赛 37::B':
        for index in range(40):
            n=rng.randint(2,22);d=[rng.randint(1,30) for _ in range(n-1)];flags=[0]+[rng.randrange(2) for _ in range(n-2)]+[0]
            positions=[0]
            for distance in d:positions.append(positions[-1]+distance)
            fixed=[i for i in range(n) if not flags[i]];answer=0
            for left,right in zip(fixed,fixed[1:]):
                for i in range(left+1,right):
                    final=Fraction(positions[left]*(right-i)+positions[right]*(i-left),right-left)
                    answer+=final!=positions[i]
            cases.append(_case('精确分数 '+str(index),str(n)+'\n'+' '.join(map(str,d))+'\n'+' '.join(map(str,flags)),answer))
        n=100000;cases.append(_case('等距大规模无需移动',str(n)+'\n'+'1 '*(n-1)+'\n0 '+'1 '*(n-2)+'0',0))
    elif identity=='入门赛 46::H':
        def name(i):return 'P'+chr(97+i//26)+chr(97+i%26)
        for index in range(25):
            n=rng.randint(2,18);names=[name(i) for i in range(n)];ops=[rng.choice(('=>','<=','<=>')) for _ in range(n-1)];edges=[set() for _ in range(n)]
            for i,op in enumerate(ops):
                if op in ('=>','<=>'):edges[i].add(i+1)
                if op in ('<=','<=>'):edges[i+1].add(i)
            questions=[];answers=[]
            for _ in range(70):
                u=rng.randint(0,n);v=rng.randint(0,n);questions.append((name(u),name(v)))
                seen={u};pending=[u]
                while pending:
                    cur=pending.pop()
                    for nxt in edges[cur] if cur<n else ():
                        if nxt not in seen:seen.add(nxt);pending.append(nxt)
                answers.append('Yes' if v in seen else 'No')
            text=names[0]+''.join(op+names[i+1] for i,op in enumerate(ops))+'\n70\n'+''.join(f'{u} {v}\n' for u,v in questions)
            cases.append(_case('逐查询 BFS '+str(index),text,'\n'.join(answers)))
        chain='=>'.join(name(i) for i in range(500))
        cases.append(_case('500 人单向链',chain+'\n1000\n'+f'{name(0)} {name(499)}\n{name(499)} {name(0)}\n'*500,'Yes\nNo\n'*500))
    elif identity=='周赛 164::C':
        checker=gcd_checker
        pairs=[(rng.randint(1,1000),rng.randint(1,1000)) for _ in range(160)]+[(1,1),(1,10**9),(10**9,10**9),(999999937,999999937),(999999937,999999929),(2,8),(6,10)]
        for start in range(0,len(pairs),80):
            group=pairs[start:start+80];outputs=[]
            for x,y in group:
                g=_max_gcd(x,y);outputs.append(f'{g} {x*y//g}')
            cases.append(_case('因子分解构造 '+str(start),str(len(group))+'\n'+''.join(f'{x} {y}\n' for x,y in group),'\n'.join(outputs)))
    elif identity=='周赛 164::D':
        for index in range(45):
            n=rng.randint(1,10);x=rng.randint(1,8);y=rng.randint(1,9);k=rng.randint(1,4);s=rng.randint(1,150);stock=rng.randint(1,35);b=[rng.randrange(2) for _ in range(n)];a=[k*x+b[i]*y+rng.randint(1,70) for i in range(n)];best=0
            for mask in range(1<<n):
                chosen=[i for i in range(n) if mask>>i&1]
                if len(chosen)*k<=stock and len(chosen)*k*x+sum(b[i] for i in chosen)*y<=s:best=max(best,sum(a[i] for i in chosen))
            cases.append(_case('客户子集 '+str(index),f'{x} {y} {s} {stock} {k}\n{n}\n'+' '.join(map(str,a))+'\n'+' '.join(map(str,b)),best))
        n=200000
        cases.append(_case('64 位收入',f'1 1 1000000000 1000000000 1\n{n}\n'+'1000000000 '*n+'\n'+'0 '*n,n*10**9))
        cases.append(_case('篮子预算极限',f'1 1 200000 1000000000 1\n{n}\n'+'1000000000 '*n+'\n'+'1 '*n,100000*10**9))
    elif identity=='周赛 164::F':
        for index in range(35):
            n=rng.randint(2,8);edges=[(i,rng.randrange(i)) for i in range(1,n)];which=rng.randrange(n-1);target=sum(1<<v for v in edges[which]);neighbors=[0]*n
            for u,v in edges:neighbors[u]|=1<<v;neighbors[v]|=1<<u
            @lru_cache(None)
            def count(mask):
                if mask.bit_count()==2:return 2 if mask==target else 0
                return sum(count(mask^(1<<u)) for u in range(n) if mask>>u&1 and (neighbors[u]&mask).bit_count()==1)
            expected=count((1<<n)-1)
            cases.append(_case('叶删除序列 '+str(index),f'{n} 1\n'+''.join(f'{u+1} {v+1}\n' for u,v in edges)+str(which+1),expected))
        n=200000;factorial=1
        for i in range(1,n-1):factorial=factorial*i%998244353
        cases.append(_case('最大星形叶排列',f'{n} 1\n'+''.join(f'1 {i}\n' for i in range(2,n+1))+'1',2*factorial%998244353))
        cases.append(_case('最长路径末端边',f'{n} 1\n'+''.join(f'{i} {i+1}\n' for i in range(1,n))+'1',2))
    elif identity=='ABC 478::D':
        for index in range(32):
            n=rng.randint(1,12);q=rng.randint(1,30);ops=[];sets=[set() for _ in range(n)]
            for _ in range(q):
                left=rng.randrange(n);right=rng.randrange(left,n);x=rng.randint(1,q)
                ops.append((left+1,right+1,x))
                for i in range(left,right+1):sets[i].add(x)
            cases.append(_case('集合穷举 '+str(index),f'{n} {q}\n'+''.join(f'{l} {r} {x}\n' for l,r,x in ops),' '.join(str(len(s)) for s in sets)))
        n=200000
        cases.append(_case('最大区间重复同值',f'{n} {n}\n'+f'1 {n} 1\n'*n,'1 '*n))
        cases.append(_case('最大区间不同值',f'{n} {n}\n'+''.join(f'1 {n} {x}\n' for x in range(1,n+1)),f'{n} '*n))
    elif identity=='ABC 478::E':
        checker=inequality_checker
        for index in range(45):
            n=rng.randint(1,4);q=rng.randint(1,10);ops=[(rng.randrange(2),rng.randint(1,n),rng.randint(1,n)) for _ in range(q)]
            feasible=any(all(a[u-1]+t<=a[v-1] for t,u,v in ops) for a in itertools.product(range(1,n+1),repeat=n))
            cases.append(_case('赋值穷举 '+str(index),f'{n} {q}\n'+''.join(f'{t} {u} {v}\n' for t,u,v in ops),'Yes' if feasible else 'No'))
        n=200000
        cases.append(_case('最大严格链',f'{n} {n-1}\n'+''.join(f'1 {i} {i+1}\n' for i in range(1,n)),'Yes'))
        cases.append(_case('最大非严格环',f'{n} {n}\n'+''.join(f'0 {i} {i+1}\n' for i in range(1,n))+f'0 {n} 1\n','Yes'))
        cases.append(_case('最大混合矛盾环',f'{n} {n}\n'+''.join(f'0 {i} {i+1}\n' for i in range(1,n))+f'1 {n} 1\n','No'))
    elif identity.endswith('::C1') or identity.endswith('::C2'):
        tests=[];m=1 if identity.endswith('::C1') else 3
        for _ in range(120):
            n=rng.randint(1,7);a=[rng.randint(1,20) for _ in range(n)];b=[rng.randint(1,25) for _ in range(m)]
            choices=[[value]+[v-value for v in b] for value in a]
            yes=any(all(arr[i]<=arr[i+1] for i in range(n-1)) for arr in itertools.product(*choices))
            tests.append((f'{n} {m}\n'+ ' '.join(map(str,a))+'\n'+' '.join(map(str,b)), 'YES' if yes else 'NO'))
        text,expect=_batch(tests);cases.append(_case('所有选项枚举 120 组',text,expect))
        for a,b,answer in [('1 '*200000,'1000000000','YES'),('3 1 3 1','1','NO')]:
            n=len(a.split());cases.append(_case('规模与不可达边界',f'1\n{n} 1\n{a}\n{b}\n',answer))
    elif identity=='Div.4 1003::D':
        tests=[]
        for _ in range(60):
            n=rng.randint(1,6);m=rng.randint(1,4);arrays=[[rng.randint(1,20) for _ in range(m)] for _ in range(n)]
            best=0
            for order in itertools.permutations(arrays):
                prefix=score=0
                for a in order:
                    for x in a:prefix+=x;score+=prefix
                best=max(best,score)
            tests.append((f'{n} {m}\n'+''.join(' '.join(map(str,a))+'\n' for a in arrays),best))
        text,expect=_batch(tests);cases.append(_case('所有数组排列枚举 60 组',text,expect))
        n=200000;cases.append(_case('最大 64 位分数',f'1\n{n} 1\n'+'1000000\n'*n,1000000*n*(n+1)//2))
    elif identity=='Div.4 993::E':
        tests=[]
        for _ in range(180):
            k=rng.randint(2,12);l1=rng.randint(1,30);r1=rng.randint(l1,45);l2=rng.randint(1,30);r2=rng.randint(l2,60)
            answer=0
            for x in range(l1,r1+1):
                for y in range(l2,r2+1):
                    if y%x:continue
                    ratio=y//x
                    while ratio>1 and ratio%k==0:ratio//=k
                    answer+=ratio==1
            tests.append((f'{k} {l1} {r1} {l2} {r2}',answer))
        # Broad intervals have exact closed-form counts for each disjoint power ratio.
        total=0;power=1
        while power<=10**9:total+=10**9//power;power*=2
        tests.extend([('2 1 1000000000 1 1000000000',total),('1000000000 1 5 6 1000000000',1),('2 1000000000 1000000000 1 999999999',0)])
        text,expect=_batch(tests);cases.append(_case('数对穷举及最大范围',text,expect))
    elif identity=='Div.4 1003::G':
        tests=[]
        for _ in range(180):
            n=rng.randint(2,14);a=[rng.randint(2,n) for _ in range(n)]
            answer=sum(_semi(math.lcm(a[i],a[j])) for i in range(n) for j in range(i,n))
            tests.append((str(n)+'\n'+' '.join(map(str,a)),answer))
        text,expect=_batch(tests);cases.append(_case('LCM 试除枚举 180 组',text,expect))
        n=200000
        cases.append(_case('最大素数重复',f'1\n{n}\n'+'2 '*n,0))
        cases.append(_case('最大平方半素数重复',f'1\n{n}\n'+'4 '*n,n*(n+1)//2))
        half=n//2;cases.append(_case('最大互异素数组合',f'1\n{n}\n'+'2 '*half+'3 '*half,half*half))
    elif identity=='Div.4 993::H':
        tests=[]
        for _ in range(35):
            n=rng.randint(1,8);q=40;matrix=[[rng.randint(1,1000000) for _ in range(n)] for _ in range(n)];queries=[];answers=[]
            for _ in range(q):
                x1=rng.randrange(n);x2=rng.randrange(x1,n);y1=rng.randrange(n);y2=rng.randrange(y1,n)
                flat=[matrix[x][y] for x in range(x1,x2+1) for y in range(y1,y2+1)]
                answers.append(sum((i+1)*v for i,v in enumerate(flat)));queries.append((x1+1,y1+1,x2+1,y2+1))
            tests.append((f'{n} {q}\n'+''.join(' '.join(map(str,a))+'\n' for a in matrix)+''.join(' '.join(map(str,a))+'\n' for a in queries),' '.join(map(str,answers))))
        text,expect=_batch(tests);cases.append(_case('逐格展开 1400 个矩形',text,expect))
        n=2000;q=12000;length=n*n
        cases.append(_case('最大矩阵与 64 位权重',f'1\n{n} {q}\n'+('1000000 '*n+'\n')*n+f'1 1 {n} {n}\n'*q,(str(1000000*length*(length+1)//2)+' ')*q))
    return cases,checker
