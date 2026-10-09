"""Parse and curate archive lessons without changing the archive or its code.

The catalog remains the source of problem-level tags. Explicitly taught named
concepts may refine a lesson's own tags; all discrepancies are retained in audit.
"""
import hashlib
import re
import concept_basics
from knowledge import canonical_tag, category_path, dictionary, normalize_tags
import toolutil

VERSION='lectures-v1.0'


def fenced_mask(lines):
    """CommonMark fence length/type semantics, including four-tick and tilde blocks."""
    mask=[];opened=None
    for line in lines:
        if opened:
            mask.append(True)
            if re.match(r'^ {0,3}'+re.escape(opened[0])+r'{'+str(opened[1])+r',}[ \t]*\r?\n?$',line):opened=None
            continue
        match=re.match(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)',line)
        if match and not (match[1][0]=='`' and '`' in match[2]):
            opened=(match[1][0],len(match[1]));mask.append(True)
        else:mask.append(False)
    return mask


def plain_text(value):
    value=re.sub(r'!\[([^]]*)\]\([^)]*\)',r'\1',str(value))
    value=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',value)
    substitutions={'oplus':'⊕','iff':'⇔','Rightarrow':'⇒','ge':'≥','le':'≤','times':'×','cdot':'·','in':'∈','mid':'∣','sum':'Σ','gcd':'gcd','min':'min','max':'max','sqrt':'√'}
    value=re.sub(r'\\([A-Za-z]+)',lambda m:substitutions.get(m[1],m[1]),value)
    value=re.sub(r'[`*#$]', '',value)
    return re.sub(r'\s+',' ',value).strip()


def code_hashes(markdown):
    lines=markdown.splitlines(keepends=True);mask=fenced_mask(lines);result=[];buf=[]
    for line,inside in zip(lines,mask):
        if inside:buf.append(line)
        elif buf:result.append(hashlib.sha256(''.join(buf).encode()).hexdigest());buf=[]
    if buf:result.append(hashlib.sha256(''.join(buf).encode()).hexdigest())
    return result


def parse_document(original):
    """One source read; ignore catalog rows and headings inside code fences."""
    lines=original.splitlines(keepends=True);mask=fenced_mask(lines)
    headings=[];letter=None;problem_title=''
    for i,line in enumerate(lines):
        if mask[i]:continue
        match=re.match(r'^ {0,3}(#{1,6})[ \t]+(.+?)\s*(?:[ \t]+#+)?\s*$',line)
        if not match:continue
        level=len(match[1]);title=match[2].strip()
        problem=re.match(r'([A-Z]\d?)\s*[.、．)]\s*(.*)',title) if level==2 else None
        if problem:letter,problem_title=problem.groups()
        if level==2 and not problem:letter=None
        headings.append({'start':i,'level':level,'title':title,'problem':letter,'problemTitle':problem_title})
    for index,heading in enumerate(headings):
        stop=next((h['start'] for h in headings[index+1:] if h['level']<=heading['level']),len(lines))
        heading.update(stop=stop,markdown=''.join(lines[heading['start']:stop]),body=''.join(lines[heading['start']+1:stop]).strip())
    catalog={}
    section=next((h for h in headings if h['level']==2 and h['title']=='目录'),None)
    if section:
        for i in range(section['start']+1,section['stop']):
            if mask[i]:continue
            cells=toolutil.split_cells(lines[i])
            if cells and len(cells)==4 and re.fullmatch(r'[A-Z][0-9]?',cells[0]):
                catalog[cells[0]]=(toolutil.strip_title_prefix(cells[1]),cells[2],cells[3])
    problems={h['problem']:h['markdown'] for h in headings if h['level']==2 and h['problem']}
    return {'lines':lines,'mask':mask,'headings':headings,'catalog':catalog,'problems':problems}


def quality(body,title=''):
    text=re.sub(r'```.*?```|~~~.*?~~~','',body,flags=re.S)
    fields={
        'definition':bool(re.search(r'是什么|什么叫|定义|是指|叫做|称为|表示',text)),
        'purpose':bool(re.search(r'有什么用|作用|用途|用来|用于|可以.{0,12}(?:求|判|算|维护)|目标',text)),
        'example':bool(re.search(r'手算|例子|样例|例如|比如|最小的|举例',text) and re.search(r'\d|`[^`]+`',text)),
        'application':bool(re.search(r'在这题|本题|这里|下面的思路|本节',text)),
        'justification':bool(re.search(r'为什么|理由|证明|必要|充分|归纳|因此|矛盾|不会.*漏|恰好',text)),
    }
    fields['canonicalTitle']=bool(title and canonical_tag(title)==title)
    return {'checks':fields,'missing':[k for k,v in fields.items() if not v],
            'foundationComplete':all(fields[k] for k in ('definition','purpose','example','application','justification'))}


# Fixed, searchable subtopic vocabulary. Overrides reflect the actual named source
# material, not a prediction of the judge's intended algorithm.
_OVERRIDES_TEXT='''
ABC 470::C|位运算|最低有效位与相邻整数异或
ABC 470::D|模拟|逆排列与位置映射
ABC 470::E|期望与概率|条件状态与期望递推
ABC 470::F|并查集|交换可达性与排列奇偶
ABC 472::D|BFS|多源最短距离
ABC 472::E|二分图判定|二染色与奇环
ABC 472::F|计算几何|多边形重心与面积矩
ABC 472::G|最小割|闭合子图与容量建模
ABC 473::D|线性 DP|计数状态与方案枚举
ABC 473::F|前缀和|字符串前缀平衡与可达性
ABC 473::G|斯特林数|第一类斯特林数与分治卷积
ABC 475::E|字典树|前缀类与候选集合
ABC 475::F|结论与计数|唯一代表元与紧矩形
ABC 476::D|排序|资源分配与前缀累计
ABC 476::F|计算几何|距离变换与坐标旋转
ABC 477::D|模拟|逆序处理与最后修改
ABC 477::E|最短路|轮图的路径分类
ABC 477::G|莫队|欧拉序与树上路径查询
ABC 478::E|差分约束|不等式建图与拓扑依赖
ABC 478::F|组合计数|发现树与排列计数
ARC 223::A|贪心|超递增序列与唯一表示
ARC 223::B|取模与同余|互补余数与交换可达性
ARC 223::C|置换环|范德蒙德乘积与排列奇偶
ARC 224::B|整数平方根|平方边界与精确计算
ARC 224::C|DFS|DFS 树与非树边
ARC 225::E|树状数组|逆序对与动态频数
ARC 226::A|二分图判定|冲突建图与二染色
ARC 226::B|二分答案|容量判定与层次分解
ARC 227::A|贪心|相邻交换距离与中位数
ARC 228::B|贪心|凸代价与边际选择
ARC 229::A|势能分析|单调度量与操作上界
ARC 229::B|位运算|右移与逐位贡献
ARC 229::C|贪心|向下取整与奇偶代价
ARC 229::D|博弈论|回合合并与可达状态
ARC 229::E|图论|可达闭包与状态扩展
ARC 230::A|组合计数|边贡献与路径计数
ARC 231::A|线性 DP|平方距离分解与状态合并
ARC 231::B|构造|高位分组与异或构造
Div.2 1112::D|组合计数|排列记录与自由位置
Div.2 1112::E|线段树|段边界事件与动态计数
Div.2 1112::F|位运算|异或矩阵与二阶差分
Div.2 1113::A|博弈论|字典序与最优回应
Div.2 1113::B|贪心|分组合并与区间覆盖
Div.2 1113::C|线性 DP|操作压缩与连续块状态
Div.2 1113::E|结论与计数|连续块结构与候选计数
Div.2 1113::F|构造|增量分解与可行边界
Div.2 1115::B|连续段|交替子序列与段压缩
Div.2 1115::C|树状数组|前缀频数与第 k 项查询
Div.2 1115::D|差分|相邻交换与差分更新
Div.2 1115::E|数位 DP|逐位比较与上界状态
Div.2 1115::F|虚树|关键点与路径压缩
Div.2 1116::B|结论与计数|奇偶位置与独立子链
Div.2 1116::C|博弈论|弱优势策略
Div.2 1116::D|组合计数|隔板法与非负整数解
Div.2 1116::E|交互题|通信编码与信息恢复
Div.2 1116::F|二分答案|时间阈值与幂次增长
Div.2 1117::E|倍增|块压缩与迭代跳跃
Div.2 1117::F1|矩阵运算|min-plus 半环与区间复合
Div.2 1118::B1|枚举|答案枚举与后缀统计
Div.2 1118::B2|前缀和|长度分块与贡献累计
Div.2 1118::C|交互题|最远点询问与记录法
Div.2 1118::D|结论与计数|幂塔比较与序列顺序
Div.2 1118::E|素数|素数幂与区间条件
Div.2 1118::F|差分|凸函数与差分多重集
Div.2 1120::C2|线性 DP|区间命中与位置状态
Div.2 1120::D|树状数组|逆序插入与动态块统计
Div.2 1120::E|图论|函数图与基环结构
Div.2 1120::F|贪心|动态边权与一次性路径
Div.2 1121::B|贪心|带权差分与贡献分解
Div.2 1121::D|构造|前缀余数与区间整除
Div.2 1121::F|容斥|错排数与固定点限制
Div.2 1123::E|线段树|相邻变化与区间统计
Div.2 1123::F2|位运算|两两异或与第 k 小值
Div.2 1123::G|线性 DP|子集汇总与逐位合并
Div.2 1124::B|递推|函数迭代与循环检测
Div.2 1124::E|笛卡尔树|数组堆序与区间结构
Div.3 1076::B|贪心|后缀最值与可行选择
Div.3 1076::D|排序|离散候选与阈值查询
Div.3 1076::E|线性 DP|整除关系与乘积状态
Div.3 1076::F|线性 DP|区间覆盖与移动代价
Div.3 1076::G|图论|极大匹配与独立集
Div.3 1076::H|拓扑排序|删除顺序与边定向
Div.3 1080::E|树形 DP|子树遍历与操作计数
Div.3 1080::F|计算几何|二次曲线与交点条件
Div.3 1080::G|模拟|子树过程与遍历复用
Div.3 1080::H|构造|整点三角形与面积条件
Div.3 1084::D|结论与计数|循环移位与段边界
Div.3 1084::E|博弈论|素因子划分与最优策略
Div.3 1084::F|排序|阈值前缀与最大和
Div.3 1084::G|期望与概率|期望线性性与对称多项式
Div.3 1084::H|取模与同余|同余方程与递归分解
Div.3 1096::B|结论与计数|括号前缀平衡
Div.3 1096::C|构造|整除条件与因子分配
Div.3 1096::D|Manacher|回文半径与线性判定
Div.3 1096::E|单调栈|左侧最近更小元素
Div.3 1096::F|树状数组|单点修改与前缀和
Div.3 1096::G|前缀和|交错和与不变量
Div.3 1096::H|树形 DP|配对路径与边贡献
Div.3 1103::D|博弈论|必胜状态与必败状态
Div.3 1103::E|单调队列|滑动窗口与最值维护
Div.3 1103::F1|素数|最小公倍数与指数分解
Div.3 1103::F2|容斥|有上界的定和计数
Div.3 1103::G|位运算|异或与加法的取等条件
Div.3 1107::E|组合计数|树上中位点与路径分解
Div.3 1107::G|取模与同余|操作不变量与同余类
Div.3 1109::C|取模与同余|最大公约数与可达位置
Div.3 1109::D|前缀和|前缀取反与符号分段
Div.3 1109::F|连续段|子树顺序与循环移位
Div.3 1109::G|线性 DP|双变量约束分解
Div.3 1114::C1|结论与计数|奇偶类与交换可达性
Div.3 1114::C2|贪心|相邻交换与顺序配对
Div.3 1114::G|贪心|树上链合并
Div.3 1119::E|构造|距离限制与禁用区间
Div.3 1119::F|模拟|二进制数组与逆序对
Div.3 1119::G|二分查找|删除缺口与阈值传递
Div.3 1119::H|图论|二选一约束与点覆盖
Div.3 1122::F|构造|逆向需求与递归依赖
Div.3 1122::G|树形 DP|同余状态与等差可达集
Div.3 1122::H|线性 DP|前后缀最值与状态优化
Div.3 1125::E|结论与计数|割边界与路径穿越
Div.3 1125::F|素数|平方自由核与乘积维护
Div.3 1125::G|生成树|Kruskal 前缀与离散凸性
Div.4 1003::D|贪心|元素贡献与权重排序
Div.4 1003::E|前缀和|正负映射与前缀极差
Div.4 1003::F|虚树|多数条件与路径权值
Div.4 1003::G|素数|半素数与最小公倍数
Div.4 1003::H|组合计数|子序列段数与位置贡献
Div.4 1017::E|位运算|异或和的逐位贡献
Div.4 1017::F|构造|编号取模与网格染色
Div.4 1017::G|模拟|翻转标记与带权总和
Div.4 1050::D|贪心|奇偶配对与最小损失
Div.4 1050::F|贪心|拼接比较与字典序
Div.4 1050::G|素数|公约数提升与指数条件
Div.4 1062::D|枚举|互质条件与有限候选
Div.4 1062::E|二分答案|区间并集与可行性
Div.4 1062::F|LCA|最近公共祖先与路径查询
Div.4 1062::G|线性 DP|带权最长不下降子序列
Div.4 1074::C|连续段|MEX 与整体平移
Div.4 1074::D|模拟|版本标记与批量重置
Div.4 1074::E|双指针|共同位移与阈值统计
Div.4 1074::F|位运算|满二叉树与祖先分组
Div.4 1074::G|枚举|单元素变化与 MEX
Div.4 1090::D|构造|互素因子与公约数序列
Div.4 1090::G|组合计数|逐位选择与乘法原理
Div.4 952::D|模拟|曼哈顿等距线与菱形
Div.4 952::E|枚举|约数配对与体积条件
Div.4 952::H2|差分|二维区间修改与四角更新
Div.4 964::D|双指针|子序列匹配与最早位置
Div.4 964::E|前缀和|除法层数与区间统计
Div.4 964::G1|交互题|询问协议与缓冲刷新
Div.4 964::G2|交互题|三段询问与信息划分
Div.4 971::C|结论与计数|向上取整与步数奇偶
Div.4 971::D|枚举|两行点集与直角分类
Div.4 971::F|前缀和|循环数组与双倍展开
Div.4 971::G1|莫队|区间排序与增量频数
Div.4 971::G2|扫描线|离线事件与区间维护
Div.4 971::G3|组合计数|元素贡献与不重不漏
Div.4 993::B|模拟|镜像映射与字符串转换
Div.4 993::D|构造|众数条件与序列生成
Div.4 993::E|枚举|不等式变换与候选区间
Div.4 993::F|枚举|约数枚举与因子配对
Div.4 993::G1|树形 DP|内向基环树与反向子树
Div.4 993::G2|树形 DP|函数图与逐层传递
Div.4 993::H|前缀和|二维贡献与带权求和
入门赛 43::H|DFS|回溯选择与状态恢复
入门赛 46::I|哈希|字符串指纹与冲突处理
入门赛 49::C|枚举|进制拆位与数位检查
入门赛 49::D|线性 DP|状态、转移与顺序
入门赛 49::E|枚举|区间并集与端点分类
入门赛 49::F|DFS|邻接表与树的遍历
入门赛 50::F|背包 DP|0/1 背包与完全背包
入门赛 51::D|前缀和|枚举总成本与调和级数
入门赛 51::E|素数|不同素因子与前缀统计
入门赛 51::F|线性 DP|状态设计与模计数
入门赛 52::C|计算几何|圆的坐标判定与网格覆盖
入门赛 52::D|素数|素性测试与平方根试除
入门赛 52::F|BFS|树边划分与搬运次数
基础赛 31::B|模拟|指令索引与周期
基础赛 31::C|线性 DP|斜率区间与状态划分
基础赛 31::D|线段树|布尔矩阵与连通性复合
基础赛 32::C|贪心|可撤销选择与反悔策略
基础赛 32::D|线性 DP|区间嵌套与弧线结构
基础赛 32::E|组合计数|分数规划与方案分类
基础赛 33::B|位运算|按位与与位删除
基础赛 33::C|DFS|前序遍历与子树顺序
基础赛 33::D|取模与同余|低位稳定性与周期
基础赛 33::E|排序|二进制分组与字典树结构
基础赛 34::C|取模与同余|进制表示与数位和
基础赛 34::D|贪心|预算约束与顺序选择
基础赛 35::B|组合计数|回文拼接与日期分类
基础赛 35::C|前缀和|多维累计与维度压缩
基础赛 35::D|线性 DP|操作序列计数与栈状态
基础赛 36::C|计算几何|点线对偶与共线条件
基础赛 36::D|线性 DP|线性状态与前驱选择
基础赛 37::B|前缀和|等差插值与区间累计
基础赛 37::C|并查集|离线激活与组件合并
基础赛 37::D|线性 DP|按边数分层的路径状态
基础赛 38::B|递推|删除重编号与位置映射
基础赛 38::C|结论与计数|MEX 限制与区间结构
基础赛 38::D|图论|定长走法与状态扩展
基础赛 39::B|贪心|强制选择与顺序决策
基础赛 39::C|线性 DP|可达金额与集合转移
基础赛 39::D|字典树|异或最大值与按位选择
基础赛 40::B|线性 DP|固定步长与链式状态
基础赛 40::C|位运算|最低有效位与进位变化
基础赛 40::D|线性 DP|带符号二进制表示
月赛 293::C|构造|局部翻转与可达图案
月赛 293::D|线性 DP|计数状态与矩阵复合
月赛 295::B|字典树|二次幂对齐与区间分块
月赛 297::B|图论|函数图与回文路径
月赛 298::D|线性 DP|逆操作与固定区段
月赛 301::C|构造|点对贡献与系数分配
月赛 302::B|图论|图的直径与最大距离
月赛 302::C|生成树|位掩码分层与 Kruskal
月赛 303::B|构造|同余分类与双射
月赛 303::C|Z 函数|最长公共前缀与字符串匹配
月赛 310::C|根号分治|取值分类与计数合并
周赛 123::C|构造|上界证明与达到上界
周赛 123::D|组合计数|可重对象与唯一代表元
周赛 123::E|连续段|数轴连续区域与最少分段
周赛 123::G|双指针|同向窗口与单调扫描
周赛 124::C|连续段|连续格子与区间模型
周赛 124::D|图论|桥、叶子配对与连通增强
周赛 124::E|结论与计数|阈值分解与最优排列
周赛 124::F|区间 DP|圆周配对与区间分割
周赛 141::B|位运算|异或性质与构造
周赛 141::C|双指针|合并匹配与顺序配对
周赛 141::D|枚举|指数上界与有限值域
周赛 142::C|贪心|最早选择与交换论证
周赛 142::D|差分|二元选择与循环相邻约束
周赛 142::E|结论与计数|高度分层与贡献累计
周赛 142::F|DFS|子树块与随机前序
周赛 144::B|构造|不可行条件与边界反证
周赛 144::D|组合计数|低位同余与异或整除
周赛 144::E|递推|水位增长与分层累计
周赛 144::F|树形 DP|奇偶状态与局部翻转
周赛 145::E|生成树|组件连接与并查集
周赛 146::C|计算几何|等腰条件与顶点分类
周赛 146::D|线性 DP|整除规则与数位状态
周赛 146::E|博弈论|对称策略与最优应对
周赛 146::F|枚举|顺子配对与候选化简
周赛 147::D|素数|最小素因子筛
周赛 147::E|结论与计数|插入位置与连续窗口
周赛 147::F|构造|硬币表示与方案生成
周赛 148::C|结论与计数|区间结构与阈值水位
周赛 148::D|位运算|最高不同位与瓶颈路径
周赛 148::E|差分|相邻翻转与边变量
周赛 148::F|组合计数|方向分类与节点分组
周赛 149::E|线性 DP|列状态与网格填法
周赛 150::D|计算几何|轴平行线段与相交判定
周赛 150::E|位运算|连续整数异或与周期
周赛 150::F|线性 DP|字符串拼接与模转移
周赛 151::D|前缀和|二维前缀累计
周赛 151::E|计算几何|力矩平衡与重心
周赛 151::F|组合计数|倍数分类与整除计数
周赛 152::E|线性 DP|区段压缩与有限状态
周赛 152::F|期望与概率|随机排列与期望拆分
周赛 153::F|构造|交替序列与相邻兼容
周赛 153::G|构造|连通块上界与网格方案
周赛 154::D|差分|区间翻转与端点更新
周赛 154::E|双指针|中位数条件与频数阈值
周赛 154::F|线性 DP|操作次数与位置状态
周赛 155::D|位运算|集合掩码与不相交计数
周赛 155::E|位运算|Gray 码与位翻转
周赛 155::F|构造|二进制小数与周期分数
周赛 156::D|状压 DP|列掩码与相邻兼容
周赛 156::E|树的直径|最远点与最长路径
周赛 156::F|组合计数|交替运行段与递推计数
周赛 157::F|线段树|区间统计与懒标记
周赛 158::F|快速幂|矩阵复合与幂次计算
周赛 161::C|位运算|置位计数与最低有效位
周赛 161::D|连通块计数|四连通、八连通与区域遍历
周赛 161::E|最短路|Dijkstra 的非负边权松弛
周赛 161::F|折半枚举|半集枚举与异或配对
周赛 162::E|稀疏表|区间最值与单调边界
周赛 162::F|树形 DP|点覆盖与连通子树状态
周赛 163::E|计算几何|叉积与有向面积
周赛 163::F|字典树|前缀路径与数组实现
周赛 164::C|素数|最大平方因子与公约数上界
周赛 164::D|前缀和|区间累计与固定一维
周赛 164::F|组合计数|删树顺序与子树交错
周赛 164::G|树形 DP|换根与双向信息
小白月赛 128::E|构造|网格覆盖与周期点阵
小白月赛 128::F|乘法逆元|模除法与可逆条件
小白月赛 129::D|置换环|余数状态与迭代周期
小白月赛 129::E|倍增|函数图与重复跳跃
小白月赛 129::F|摊还分析|有效变化与修改总成本
小白月赛 129::G|LCA|树上相遇与路径交汇
小白月赛 130::D|线性 DP|MEX 与缺失状态
小白月赛 130::E|Hall 定理|支配关系与匹配可达性
小白月赛 130::F|贪心|可行集合与字典序选择
小白月赛 131::D|模拟|复数表示与乘法运算
小白月赛 131::E|位运算|位掩码与子集枚举
小白月赛 131::F|结论与计数|等比结构与有限公比
小白月赛 132::E|单调栈|候选删除与最近极值
小白月赛 133::F|KMP|前缀函数与自动机转移
小白月赛 134::D|结论与计数|等价节点压缩
小白月赛 134::E|BFS|指定距离与可行边条件
小白月赛 134::F|差分|切比雪夫等距线与区间贡献
小白月赛 135::E|取模与同余|循环数位和与周期
小白月赛 135::F|树状数组|频数累计与动态查询
小白月赛 136::C|构造|曼哈顿距离与方向分类
小白月赛 136::E|BFS|附加状态与最短步数
小白月赛 136::F|可持久化线段树|路径复制与历史查询
小白月赛 137::E|位运算|异或不变量与可达性
挑战赛 83::B|栈|出栈序列与操作顺序
挑战赛 83::C|构造|括号分段与嵌套结构
挑战赛 83::D|取模与同余|整除分块与商的区间
挑战赛 84::B|贪心|固定和与乘积上界
挑战赛 84::C|位运算|逐位独立与交换距离
挑战赛 85::A|枚举|硬币面额与互素周期
挑战赛 85::B|结论与计数|绝对值迭代与三角数阈值
挑战赛 85::C|位运算|高位分组与异或边界
挑战赛 86::A|结论与计数|操作不变量与等价条件
挑战赛 86::B|位运算|杨辉三角奇偶与子掩码
挑战赛 86::C|递推|前缀公约数与状态复用
挑战赛 86::D|最短路|离散状态与循环距离
挑战赛 87::B|差分|二维修改与四角恢复
挑战赛 87::C|倍增|二进制步数与幂次递推
挑战赛 87::D|虚树|关键节点与 DFS 序
挑战赛 88::C|线性 DP|函数映射与自环条件
挑战赛 89::B|DFS|冲突图与有限候选搜索
挑战赛 89::D|位运算|张量幂与蝶形变换
挑战赛 90::A|鸽巢原理|前缀余数与重复类别
挑战赛 90::B|构造|非负增量与可行序列
挑战赛 91::A|贪心|奇偶界限与最小差值
挑战赛 91::B|递推|无穷级数与递推关系
挑战赛 91::C|DFS|无向 DFS 树与回边配对
挑战赛 91::D|线性 DP|凹性与决策单调
挑战赛 92::B|前缀和|定和区间与哈希频数
挑战赛 92::D|结论与计数|中心对称与有限中心
练习赛 148::C|置换环|置换分解与环内独立性
练习赛 148::F|莫比乌斯反演|约数关系与杜教筛
练习赛 149::C|BFS|状态建图与最少步数
练习赛 149::D|前缀和|变量替换与单侧阈值
练习赛 149::E|组合计数|相对次序与对称概率
练习赛 149::F|结论与计数|奇偶分类与方案数
练习赛 149::G|矩阵运算|矩阵秩与信息维度
练习赛 150::D|位运算|共同异或与状态关系
练习赛 150::F|位运算|按位与与候选压缩
练习赛 151::D|树形 DP|边定向与子树状态
练习赛 151::E|位运算|最高不同位与数值比较
练习赛 152::C|构造|单点删除与 MEX
练习赛 152::D|树形 DP|二元移动与子树背包
练习赛 152::E|树形 DP|子树频数与状态可达性
练习赛 152::F|组合计数|逆序对分布与五边形数
练习赛 152::G|后缀自动机|endpos 类与后缀链接
练习赛 153::C|线性 DP|最大子段和与结束位置状态
练习赛 153::D|前缀和|前缀异或与区间消去
练习赛 153::E|组合计数|二项式和与奇偶条件
练习赛 153::F|可撤销并查集|历史恢复与时间分治
练习赛 154::B|贪心|操作依赖与树形结构
练习赛 154::C|递推|数值拼接与长度幂
练习赛 154::D|线性 DP|最后操作与区间空隙
练习赛 154::E|置换环|轮换结构与组内统计
练习赛 154::F|树状数组|逆序对与最少相邻交换
练习赛 155::D|模拟|表达式求值与顺序状态
练习赛 156::B|博弈论|手牌不变量与终局条件
练习赛 156::C|树的直径|树的中心与距离上界
练习赛 156::E|贪心|重排不等式与系数配对
练习赛 156::F|二分答案|瓶颈条件与单调交界
练习赛 157::E|结论与计数|特殊区间与一一对应
练习赛 157::F|线段树|位置标记与区间结构
'''
OVERRIDES={}
for _line in _OVERRIDES_TEXT.splitlines():
    if _line.strip():
        _identity,_name,_topic=_line.split('|');OVERRIDES[_identity]=(_name,_topic)

_MULTIPLE = {
    'Div.4 1074::H':[('擂主','前缀和','前缀技能与累计值'),('这个位置','树状数组','前缀频数与可行位置')],
    'Div.4 952::G':[('D(kn)','组合计数','数位乘法与无进位条件'),('前导零','组合计数','前导零与定长串计数')],
    '挑战赛 84::D':[('逆元','乘法逆元','模分数与可逆条件'),('DAG','期望与概率','有向无环图上的期望状态')],
    '挑战赛 88::D':[('自动机','线性 DP','子序列自动机与状态矩阵'),('幂零','矩阵运算','幂零矩阵与复合闭式')],
    '挑战赛 90::D':[('立方','素数','立方自由核与完全幂'),('四边形','分治优化 DP','四边形不等式与决策单调')],
}


def choose_topic(identity,original_concept,source_tags):
    for needle,name,topic in _MULTIPLE.get(identity,[]):
        if needle in original_concept:return name,topic,'curated-source'
    if identity in OVERRIDES:return (*OVERRIDES[identity],'curated-source')
    # Only the heading describes which concept this section actually teaches;
    # another technique mentioned in the body can be a comparison or an oracle.
    names=[n for n in dictionary()['names'] if n in original_concept]
    if '期望' in original_concept or '概率' in original_concept:names.insert(0,'期望与概率')
    if '二染色' in original_concept or ('二分图' in original_concept and '匹配' not in original_concept):names.insert(0,'图论')
    if 'Trie' in original_concept:names.insert(0,'字典树')
    if 'Dijkstra' in original_concept:names.insert(0,'最短路')
    if re.search(r'状态压缩|状压',original_concept):names.insert(0,'状压 DP')
    if 'DP' in original_concept and not names:names.insert(0,'线性 DP')
    names=sorted(dict.fromkeys(names),key=lambda n:(-len(n),source_tags.index(n) if n in source_tags else 999))
    primary=(names or source_tags or ['结论与计数'])[0]
    topic=concept_basics.DEFAULT_TOPICS.get(primary,'定义与基础应用')
    return primary,topic,'explicit-heading' if names else 'catalog-foundation'


def _paragraphs(text):
    """Paragraph boundaries must not split a fenced diagram or display math."""
    lines=text.splitlines(keepends=True);mask=fenced_mask(lines)
    blocks=[];buffer=[];display=False
    for line,inside in zip(lines,mask):
        if not inside:
            if len(re.findall(r'(?<!\\)\$\$',line))%2:display=not display
            if not line.strip() and not display:
                if buffer:blocks.append(''.join(buffer).strip());buffer=[]
                continue
        buffer.append(line)
    if buffer:blocks.append(''.join(buffer).strip())
    return blocks


def _labelled(body,labels,limit=2000):
    """Keep whole paragraphs/equations; never truncate through a math delimiter."""
    lines=body.splitlines(keepends=True)
    searchable=''.join(''.join('\n' if c=='\n' else ' ' for c in line) if inside else line
                       for line,inside in zip(lines,fenced_mask(lines)))
    match=re.search(r'(?m)^(?:\*\*|#{4,6}\s*|\d+[.、]\s*)(?:'+labels+r')[^\n]*?(?:\*\*|[。:：])',searchable)
    if not match:return None
    start=match.end();next_label=re.search(r'(?m)^(?:\*\*[^*\n]+\*\*|#{3,6}\s)',searchable[start:])
    value=body[start:start+next_label.start()] if next_label else body[start:]
    # An introductory newline should not discard the first display equation.
    blocks=_paragraphs(value);out=[];length=0
    for block in blocks:
        if length>limit:break
        out.append(block);length+=len(block)
    return '\n\n'.join(out).strip() or None


def _example(body,fallback):
    labelled=_labelled(body,r'(?:能手算的|手算|有什么用[^\n]*手算|例子|最小例子)')
    if labelled:return labelled
    blocks=_paragraphs(body)
    for index,block in enumerate(blocks):
        if re.match(r'^(?:`{3,}|~{3,})',block):continue
        if re.search(r'手算|最小例子|例如|比如|举例',block) and re.search(r'\d|`[^`]+`',block):
            result=[block]
            # Include the immediate equation / list, without pulling a later section.
            for next_block in blocks[index+1:index+3]:
                if re.match(r'^\*\*|^#{3,6}\s',next_block):break
                result.append(next_block)
            return '\n\n'.join(result)
    return fallback


_SPECIAL = {
    'ABC 470::C': (
        r'最低有效位是正整数二进制表示中最靠右的 $1$。若它在第 $k$ 位（最低位编号为 $0$），则 $v\oplus(v-1)=2^{k+1}-1$。',
        r'减一会改变低位的整段结构；该恒等式把逐元素减一后的异或变化转成低位翻转的奇偶计数。',
        r'$v=12=1100_2$，最低有效位在第 $2$ 位。$v-1=11=1011_2$，所以 $12\oplus11=0111_2=7=2^3-1$。',
        r'正整数减一时，第 $k$ 位从 $1$ 变成 $0$，低 $k$ 位从 $0$ 变成 $1$，更高位不动；异或恰好得到低 $k+1$ 位全为 $1$。',
        r'要求 $v>0$；题中 $0$ 的饱和减一不使用该恒等式。$k$ 是位序，不是低位 $1$ 的数值。'),
    'ABC 472::E': (
        r'二分图可以把顶点分成两组，使每条边的端点处于不同组；二染色就是给这两组两种颜色。奇环是边数为奇数的环。',
        r'无向图可二染色当且仅当不含奇环。染色冲突可以同时给出不合法的证据。',
        r'三角形 $1-2-3-1$：黑、白、黑之后最后一条边连接两个黑点，产生冲突。四边形 $1-2-3-4-1$：黑、白、黑、白可以闭合。',
        r'成功染色时，沿环颜色交替，回到起点必须走偶数条边。反过来，按生成树深度奇偶染色；若某边同色，则它与树上偶数长度路径构成奇环。',
        r'二分图判定与最大匹配分别处理着色可行性与一对一分配。多个连通块都需检查；还原奇环时应先找到路径交汇点。'),
    'ABC 473::F': (
        r'将字符 `A` 记为 $+1$、`B` 记为 $-1$，前缀平衡值 $P_i$ 是前 $i$ 个字符的累计和。从空串插入 `A` 或 `AB` 可生成的串，其每个前缀的平衡值都不为负。',
        r'把指数级的插入历史判定压成前缀最小值条件，再用区间结构应对字符修改。',
        r'`AB` 的前缀值为 $1,0$，可生成；`BA` 的前缀值为 $-1,0$，第一项为负，不可生成；`AAB` 的前缀值为 $1,2,1$，可先插 `AB` 再插 `A`。',
        r'插入 `A` 或 `AB` 不会使已有的合法前缀变负。反向不断删除相邻 `AB`；若不存在 `AB`，串形如先若干 `B` 再若干 `A`，非负前缀迫使 `B` 为零，剩余 `A` 可逐个删除。',
        r'允许单独插入 `A`，所以总平衡值可以大于 $0$；只有总量非负不足够，必须检查所有前缀。'),
    'ABC 476::D': (
        r'将两种券拆成两项约束：总价值 $X+KY$，以及可使用的 $K$ 元券张数 $Y$。交易后的总价值减少商品标价，而找零改变两种券的比例。',
        r'证明购买集合可行性的条件，再对商品价格排序、累计资源需求并查询可购买数量。',
        r'$K=10,X=0,Y=1$。用一张 $10$ 元券买 $5$ 元商品后，得到五张 $1$ 元券，总价值从 $10$ 变为 $5$，但 $K$ 元券张数从 $1$ 变为 $0$。',
        r'若商品总价为 $P$、使用 $s$ 张 $K$ 元券，最终 $1$ 元券为 $X+Ks-P$。先处理净找零非负的交易，余额先增后减；结合 $s\le Y$ 和饮料必需券数下界 $L$，得到 $P\le X+KY$ 且 $L\le Y$。',
        r'只有总价值足够不保证可行；饮料需要的 $K$ 元券数量是独立约束。推导依赖题目允许的支付与找零规则。'),
}


def curate(entry,source_markdown,problem_markdown=''):
    original_concept=re.sub(r'^.*?从零讲\s*[:：]?\s*','',entry['title']).strip()
    identity=entry['sourceContest']+'::'+entry['sourceProblem']
    raw_tags=list(entry.get('tags',[]));tags=normalize_tags(raw_tags)['tags']
    primary,topic,selection=choose_topic(identity,original_concept,tags)
    if canonical_tag(primary)!=primary:raise ValueError('非标准讲义概念：'+primary)
    # This section is a positive explicit lesson, not an alternative mentioned in passing.
    tags=list(dict.fromkeys([primary]+tags))
    if primary=='Z 函数':tags=[t for t in tags if t!='KMP']
    if primary=='后缀自动机':tags=[t for t in tags if t!='字典树']
    if primary=='虚树':tags=[t for t in tags if t!='字典树']
    body='\n'.join(source_markdown.splitlines()[1:]).strip()
    baseline=_SPECIAL.get(identity) or concept_basics.BASICS[primary]
    before=quality(body,original_concept)
    definition=baseline[0] if identity in _SPECIAL else _labelled(body,r'是什么|什么叫|定义') or baseline[0]
    purpose=baseline[1] if identity in _SPECIAL else _labelled(body,r'有什么用|作用|用途') or baseline[1]
    example=baseline[2] if identity in _SPECIAL else _example(body,baseline[2])
    application=_labelled(body,r'在这题里怎么用|在本题[^\n]*|本题应用')
    if not application:
        parsed=parse_document(problem_markdown)
        idea=next((h for h in parsed['headings'] if h['level']==3 and re.search(r'思路',h['title'])),None)
        if idea:
            chunks=_paragraphs(idea['body']);kept=[];length=0
            for chunk in chunks:
                if length>1600 or re.match(r'^```|^~~~',chunk):break
                kept.append(chunk);length+=len(chunk)
            application='\n\n'.join(kept).strip()
    if not application:
        application=f"本节来自 {entry['sourceContest']} 的 {entry['sourceProblem']} 题《{entry.get('sourceTitle','')}》。原有推导在下方完整保留，可沿它的变量、判据和例子检查该技术如何应用。"
    reason=baseline[3]
    source_reason=_labelled(body,r'为什么(?:可行|正确|成立)?|证明|必要性|充分性')
    if source_reason and source_reason!=reason:reason+='\n\n'+source_reason
    concept=primary+'：'+topic
    markdown=f"# {concept}\n\n## 定义\n\n{definition}\n\n## 作用\n\n{purpose}\n\n## 手算例子\n\n{example}\n\n## 本题应用\n\n{application}\n\n## 为何可行\n\n{reason}\n\n## 易错点\n\n{baseline[4]}\n\n## 本题完整推导与原有例子\n\n{body}\n"
    # Every fenced source block occurs verbatim in the unabridged part.
    original_blocks=code_hashes(source_markdown)
    result=dict(entry,concept=concept,displayTitle=concept,knowledgeName=primary,
                topic=topic,category=category_path(primary),categories=list(dict.fromkeys(category_path(t) for t in tags)),
                tags=tags,originalTitle=entry['title'],originalConcept=original_concept,sourceTags=raw_tags,
                sourceMarkdown=source_markdown,sourceHash=hashlib.sha256(source_markdown.encode()).hexdigest(),
                sourceCodeHashes=original_blocks,curationVersion=VERSION,conceptSource=selection,
                quality={'original':before,'normalized':True,'supplemented':True,
                         'catalogClassificationChanged':primary not in raw_tags,
                         'sourceAlgorithmReverified':False},excerpt=plain_text(definition)[:180],markdown=markdown)
    return result
