"""Evidence-based canonical knowledge tags for archive and unsolved public rows.

This module does not fetch pages, write archive files, generate a solution, or
claim that a statement-derived tag is a verified algorithm. Call ``enrich_row``
when a public row is discovered and again when its original statement arrives.
"""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import urlsplit
import knowledge_dict as KD
import toolutil

VERSION = 'knowledge-v1.0'
def asset_path(name):
    from paths import resource
    return resource(name)

_DATA = asset_path('knowledge_catalog.json')
_EXTENSIONS = asset_path('knowledge_extensions.json')

# Official broad tags identify a subject, not a particular DP or string method.
BROAD = {
    'dp':'动态规划', 'dynamic programming':'动态规划', '动态规划（官方宽标签）':'动态规划',
    '动态规划':'动态规划', 'math':'数学', '数学':'数学', 'number theory':'数学 / 数论',
    '数论':'数学 / 数论', 'strings':'字符串', '字符串':'字符串', 'trees':'图论 / 树',
    '树':'图论 / 树', 'data structures':'数据结构', '数据结构':'数据结构',
}
OFFICIAL = {
    'binary search':'二分查找', 'brute force':'枚举', 'combinatorics':'组合计数',
    'constructive algorithms':'构造', 'dfs and similar':'DFS', 'dsu':'并查集',
    'geometry':'计算几何', 'graph matchings':'二分图匹配', 'graphs':'图论',
    'greedy':'贪心', 'hashing':'哈希', 'implementation':'模拟', 'shortest paths':'最短路',
    'sortings':'排序', 'two pointers':'双指针', 'bitmasks':'位运算', 'flows':'网络流', 'fft':'FFT',
}


@lru_cache(maxsize=1)
def dictionary():
    """Live authoritative dictionary, with the bundled exact snapshot as fallback."""
    result = dict(json.loads(_DATA.read_text(encoding='utf-8')), path='内置标准知识点词典')
    # The original dictionary used its first leaf as the DP bucket label.
    # Keep all canonical leaf names, but give the subject an actual category.
    dp=result['groups'].pop('线性 DP',None)
    if dp:result['groups']['动态规划']=dp
    if '计数' in result['groups']:
        mathematics=result['groups'].setdefault('数学',[])
        if '计数' not in mathematics:mathematics.append('计数')
    extension=json.loads(_EXTENSIONS.read_text(encoding='utf-8'))
    for entry in extension['concepts']:
        name=entry['name'];group=entry['category']
        if name not in result['names']:result['names'].append(name)
        for alias in entry.get('aliases',[]):result['aliases'][_key(alias)]=name
        children=result['groups'].setdefault(group,[])
        if name not in children:children.append(name)
    return result


def _key(value):
    return re.sub(r'\s+', '', str(value or '')).lower()


def canonical_tag(value):
    table = dictionary()
    lookup = {_key(n):n for n in table['names']}
    return lookup.get(_key(value)) or table['aliases'].get(_key(value))


def category_path(name):
    """Keep the dictionary's complete parent chain, including self-named buckets."""
    parents = {child:parent for parent,children in dictionary()['groups'].items()
               for child in children if parent != child}
    path = [name]; seen = {name}
    while path[0] in parents and parents[path[0]] not in seen:
        parent = parents[path[0]]; path.insert(0,parent); seen.add(parent)
    # Standard leaf is not a category in the UI; an ungrouped name is its own topic.
    return ' / '.join(path[:-1] or path)


def normalize_tags(values, *, official=False):
    tags=[]; categories=[]; unknown=[]
    if isinstance(values, str):values=KD.split_names(values)
    for value in values or []:
        if not isinstance(value, str):continue
        label=value.strip()
        if not label:continue
        broad=BROAD.get(label) or BROAD.get(label.lower())
        if official and label.lower() == 'dp':broad='动态规划'
        if broad:
            categories.append(broad);continue
        canonical=OFFICIAL.get(label.lower()) if official else None
        canonical=canonical or canonical_tag(label)
        if canonical:tags.append(canonical);categories.append(category_path(canonical))
        else:unknown.append(label)
    return {'tags':list(dict.fromkeys(tags)), 'categories':list(dict.fromkeys(categories)),
            'unknown':list(dict.fromkeys(unknown))}


@lru_cache(maxsize=1)
def _load_problem_knowledge(path,stamp,size):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8'))
        return value if value.get('version')==VERSION else {}
    except (OSError,ValueError):return {}


def _curated_problem(row):
    """Only exact archive identities or original URLs can share reviewed evidence."""
    path=asset_path('problem_knowledge.json')
    try:stat=path.stat()
    except OSError:return None
    data=_load_problem_knowledge(str(path),stat.st_mtime_ns,stat.st_size)
    identities=[str(row.get('id') or row.get('_id') or '')]
    contest=row.get('contest',row.get('场次',''));problem=row.get('problem',row.get('题号',''))
    if contest and problem:identities.append(str(contest)+'::'+str(problem))
    original=str(row.get('url') or row.get('_url') or '')
    if original:
        parsed=urlsplit(original)
        key=(parsed.hostname or '').lower()+parsed.path.rstrip('/')
        if key in data.get('urls',{}):identities.append(data['urls'][key])
    for identity in identities:
        identity=data.get('aliases',{}).get(identity,identity)
        if identity in data.get('problems',{}):return data['problems'][identity]
    return None


# Explicit named techniques are evidence; merely containing “array” is not DP.
_NAMED = (
    ('BFS',r'\bBFS\b|\bbreadth.first search\b|广度优先搜索'),
    ('DFS',r'\bDFS\b|\bdepth.first search\b|深度优先搜索'),
    ('并查集',r'\bdisjoint.set union\b|\bunion.find\b|并查集'),
    ('线段树',r'\bsegment tree\b|线段树'),
    ('树状数组',r'\bFenwick tree\b|树状数组'),
    ('前缀和',r'\bprefix sums?\b|前缀和|前缀异或'),
    ('差分约束',r'\bdifference constraints?\b|差分约束'),
    ('二分查找',r'\bbinary search\b|二分查找'),
    ('KMP',r'\bKMP\b|\bKnuth.Morris.Pratt\b'),
    ('NTT',r'\bNTT\b|\bnumber.theoretic transform\b'),
    ('FFT',r'\bFFT\b|\bfast Fourier transform\b|快速傅里叶变换'),
    ('Z 函数',r'\bZ.function\b|\bZ algorithm\b|Z 函数'),
    ('后缀自动机',r'\bsuffix automaton\b|后缀自动机'),
    ('Manacher',r'\bManacher\b|马拉车'),
    ('单调队列',r'\bmonotonic queue\b|单调队列'),
    ('可持久化线段树',r'\bpersistent segment tree\b|可持久化线段树'),
    ('可撤销并查集',r'\brollback (?:DSU|disjoint.set union)\b|可撤销并查集'),
    ('字典树',r'\btrie\b|字典树'),
    ('LCA',r'\bLCA\b|\blowest common ancestor\b|最近公共祖先'),
    ('拓扑排序',r'\btopological sort\b|拓扑排序'),
    ('乘法逆元',r'\bmodular (?:multiplicative )?inverse\b|乘法逆元'),
    ('素数',r'\bprime factor(?:ization|isation)s?\b|质因数分解|素因子分解|\bis prime\b|是否.*(?:素数|质数)'),
)


def analyze_problem(row=None, statement=None, official_tags=None, algorithm_evidence=None):
    """Return canonical tags plus bounded, reviewable provenance.

    A row marked local can trust its archive catalog; a missing public solution
    uses official tags, explicit technique names, or plainly stated graph models.
    Broad subject evidence remains a category awaiting a more specific technique.
    """
    row=row or {};remote=row.get('source')=='remote' or str(row.get('id','')).startswith('remote:') or row.get('_remote')
    existing=row.get('sourceTags',row.get('tags'))
    if existing is None:existing=KD.split_names(row.get('knowledge',row.get('知识点','')))
    original=list(existing) if isinstance(existing,(tuple,list)) else KD.split_names(str(existing or ''))
    inputs=official_tags if official_tags is not None else original
    if isinstance(inputs,str):inputs=KD.split_names(inputs)
    parsed=normalize_tags(inputs,official=bool(remote or official_tags is not None))
    evidence=[{'source':'official-tags' if remote or official_tags is not None else 'archive-catalog',
               'value':str(value),'tag':OFFICIAL.get(str(value).lower()) or canonical_tag(value)} for value in inputs or []]
    tags=list(parsed['tags']);categories=list(parsed['categories']);unknown=list(parsed['unknown'])
    curated=_curated_problem(row);removed=[]
    if curated:
        removed=normalize_tags(curated.get('removeTags',[]))['tags']
        additional=normalize_tags(curated.get('addTags',[]))['tags']
        tags=list(dict.fromkeys(additional+[t for t in tags if t not in removed]))
        retained=[i for i in inputs or [] if (OFFICIAL.get(str(i).lower()) or canonical_tag(i)) not in removed]
        categories=normalize_tags(retained,official=bool(remote or official_tags is not None))['categories']
        categories=list(dict.fromkeys(categories+[category_path(t) for t in additional]))
        for e in evidence:
            if e.get('tag') in removed:e['status']='superseded-by-source-lesson'
        for tag in additional:
            evidence.append({'source':'archive-lesson','tag':tag,'reference':curated['sourcePath'],
                'lessonIds':curated['lessonIds'],'sourceHashes':curated['sourceHashes'],
                'verified':False,'reason':'完整原题解明确讲授该技术；归档代码未重新验证'})
    text=str(statement or '')[:500_000]
    # Samples and code blocks cannot provide algorithmic proof.
    text=re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text)
    lower=text.lower()
    if text:
        for tag,pattern in _NAMED:
            match=re.search(pattern,text,re.I)
            if not match:continue
            # Names in an explanatory statement are classified, not a verified solution.
            tags.append(tag);categories.append(category_path(tag))
            evidence.append({'source':'statement-explicit','tag':tag,'excerpt':text[max(0,match.start()-50):match.end()+100].strip()})
        graph=re.search(r'(?:undirected|directed|unweighted|connected)\s+(?:graph|tree)|(?:有向|无向|无权|连通)图|(?:given|have)\s+(?:an?\s+)?tree\b|给定.{0,10}(?:一棵树|一张图)',text,re.I)
        if graph:
            tags.append('图论');categories.append('图论')
            evidence.append({'source':'statement-model','tag':'图论','excerpt':graph[0]})
        # Conditions, not the presence of the word “shortest”, establish BFS suitability.
        if graph and (re.search(r'unweighted graph|无权图',lower) or re.search(r'all (?:edges?|roads?).{0,30}(?:weight|length|cost).{0,8}(?:1|one|equal)',lower)) and re.search(r'shortest (?:path|distance)|minimum (?:number of )?(?:edges|steps)|最短路|最少步数',text,re.I):
            tags.extend(['BFS','最短路']);categories.append('搜索')
            evidence.append({'source':'statement-conditions','tag':'BFS','excerpt':'题面明确无权/等长边，并要求最少步数'})
        if re.search(r'\bgcd\b|\blcm\b|greatest common divisor|least common multiple|最大公约数|最小公倍数',text,re.I):
            categories.append('数学 / 数论')
        if re.search(r'\bprobability\b|\bexpected (?:value|number|cost)\b|概率|数学期望',text,re.I):
            tags.append('期望与概率');categories.append(category_path('期望与概率'))
            evidence.append({'source':'statement-model','tag':'期望与概率','excerpt':'题面明确概率或期望目标'})
    if isinstance(algorithm_evidence,dict) and algorithm_evidence.get('source') and algorithm_evidence.get('tags'):
        extra=normalize_tags(algorithm_evidence['tags']);tags+=extra['tags'];categories+=extra['categories'];unknown+=extra['unknown']
        for tag in extra['tags']:
            evidence.append({'source':'algorithm-explicit','tag':tag,'reference':str(algorithm_evidence['source'])[:500],
                             'verified':algorithm_evidence.get('verified') is True})
    tags=list(dict.fromkeys(t for t in tags if canonical_tag(t)==t));categories=list(dict.fromkeys(categories))
    official=any(e['source']=='official-tags' and e.get('tag') in tags for e in evidence)
    local=any(e['source']=='archive-catalog' and e.get('tag') in tags for e in evidence)
    confidence='high' if curated or official or local else 'medium' if tags else 'pending'
    source='archive-lesson' if curated else 'archive-catalog' if local else 'official-tags' if official else 'statement-analysis' if text else 'pending-evidence'
    digest=hashlib.sha256(json.dumps({'tags':inputs,'statement':text,'algorithm':algorithm_evidence,'curated':curated},ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
    return {'version':VERSION,'tags':tags,'knowledge':' + '.join(tags),'categories':categories,
            'status':'classified' if tags else 'pending','source':source,'confidence':confidence,
            'evidence':evidence,'unknown':list(dict.fromkeys(unknown)),
            'pendingCategories':[c for c in categories if c not in {category_path(t) for t in tags}],
            'inputHash':digest,'sourceTags':original,'supersededTags':removed}


def enrich_row(row, statement=None, official_tags=None, algorithm_evidence=None):
    value=copy.deepcopy(row)
    result=analyze_problem(value,statement,official_tags,algorithm_evidence)
    # A new snapshot should retain previous statement evidence when only re-encoding.
    previous=value.get('knowledgeAnalysis')
    if not statement and not algorithm_evidence and isinstance(previous,dict) and previous.get('version')==VERSION:
        kept=[t for t in normalize_tags(previous.get('tags',[]))['tags'] if t not in result['supersededTags']]
        result['tags']=list(dict.fromkeys(result['tags']+kept))
        result['knowledge']=' + '.join(result['tags'])
        obsolete={category_path(t) for t in result['supersededTags']}
        kept_categories=[c for c in previous.get('categories',[]) if c not in obsolete or c in result['categories']]
        result['categories']=list(dict.fromkeys(result['categories']+kept_categories))
        result['evidence']+= [e for e in previous.get('evidence',[]) if e.get('source','').startswith('statement-')]
        if result['tags']:result['status']='classified'
        if result['confidence']=='pending' and previous.get('confidence') in ('high','medium'):
            result['confidence']=previous['confidence'];result['source']=previous.get('source','statement-analysis')
    value.update(tags=result['tags'],knowledge=result['knowledge'],sourceTags=result['sourceTags'],
                 knowledgeCategories=result['categories'],knowledgeAnalysis=result)
    return value


class KnowledgeAnalysisCache:
    """Optional personal cache; stored outside the read-only archive."""
    def __init__(self,path):
        self.path=Path(path);self.lock=threading.RLock()
        from persistence import load_document
        self.state=load_document(self.path,{})

    def enrich(self,row,**kwargs):
        with self.lock:
            identity=str(row.get('id') or row.get('_id') or '')
            previous=self.state.get(identity)
            value=dict(row,**({'knowledgeAnalysis':previous} if previous else {}))
            value=enrich_row(value,**kwargs);analysis=value['knowledgeAnalysis']
            if identity and analysis!=previous:
                self.state[identity]=analysis;self.path.parent.mkdir(parents=True,exist_ok=True)
                from persistence import save_document
                save_document(self.path,self.state)
            return value

    def apply(self,row):
        """Read a stored analysis without creating files or baseline snapshots."""
        with self.lock:
            identity=str(row.get('id') or row.get('_id') or '')
            previous=self.state.get(identity)
            return enrich_row(dict(row,**({'knowledgeAnalysis':copy.deepcopy(previous)} if previous else {})))
