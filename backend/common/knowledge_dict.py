# -*- coding: utf-8 -*-
r"""knowledge_dict —— 知识点词典的解析器 + 归一/校验的唯一实现。

词典文件 = `knowledge/15-知识点词典.md`（数据）；本模块（代码）读它干活——
代码里不再藏名字表（数据驱动）。调用方：

  · `fill_knowledge.py`    状态表「知识点」列的归一（final_knowledge / norm_name）
  · `import_solution.py`   题解包校验：标准名直通 / 别名自动映射 / 未登记照收 + 建议
  · `export_solution.py`   生成 manifest 的 knowledge 数组

用法：
    python knowledge_dict.py check 状态压缩DP 差分 李超线段树   # 查词：标准名 / 别名映射 / 建议
    python knowledge_dict.py selftest                            # 数据自检（词典本身 + 归一行为）

归一口径（2026-10-05 二次修订：**v2 格式** —— `+` 组内、`[..]` 打包、`[主]/[次]` 标注；
2026-10-06 修订：`；` 解法分隔废止——只写题解实际使用的那条解法，解析仍宽容、闸门报出）：
  · 按顶层 `；`（半角 `;` 也认）分解法组 → 组内按顶层 `+` / `、` 拆项（旧分隔符 `｜`
    宽容视同 `+`）→ 剥掉尾部 `[主]` / `[次]` 标注（`(主)`、`（主）` 也认，转正成 `[主]`）
    → 去（括号）说明 → 别名映射 → 命中删除表就删 → **组合名展开**（「前缀和与差分」→
    「前缀和 + 差分」，表在词典第三节）→ 修饰兜底 → 按原结构拼回（组间 ` ； `、组内 ` + `）
  · **修饰兜底**：段以某个已登记名字（标准名/别名）**开头或结尾**、且还剩修饰字
    → 归到它（`分组前缀和` → `前缀和`、`枚举一维` → `枚举`、`迭代 DFS` → `DFS`）。
    候选按长度降序（最长优先）；删除表**先于**兜底判定（`DFS 枚举因子` 整段删，不会
    被吃成 `DFS`）。兜底命中 = 未经收编的自动映射，调用方可收进 mapped 报告核对。
  · 归一后仍非标准名的段**原样保留** + 进 unknown 报告（写状态表/归档对账会拦）。
  · 首字母缩写大写（dfs → DFS）；`[…]` 与标注原样保留（打包组内可嵌套、递归归一）
  · 别名的匹配对大小写与空格不敏感（`状态压缩 dp` ≡ `状态压缩dp`）
  · 模块级 `split_names()` = 显示串 → 纯名字列表（剥结构与标注；export 生成 manifest
    的 knowledge 数组用它）
"""
import argparse
import difflib
import os
import re
import sys

import toolutil  # 同目录：REPO_ROOT + parse_contest（场次键的唯一解析）

from paths import resource
DEFAULT_PATH = str(resource("15-知识点词典.md"))
BAR = "｜"          # 全角竖线（旧格式分隔符：宽容视同 `+`；新写法不要再用）
SEMI = "；"         # 全角分号（历史解法分隔符：2026-10-06 起写法废止，解析仍宽容、闸门报出）
PUNCT = "、"        # 顿号（视同 `+`）
BS = chr(92)            # 反斜杠
NO_FOLDER = ("—", "-", "–", "", "无", "（无）")

_OPEN = "（([【"     # 括号深度（split 时不拆层内的分隔符）；`【】` 是 `[]` 的宽容写法
_CLOSE = "）)]】"
_ANNOT_RE = re.compile(r"[\[【(（]\s*(主|次)\s*[\]】)）]\s*$")


# ---------------------------------------------------------------- md 表格小工具
def _cells(line):
    """md 表格行 → 单元格列表；不是表格行返回 None（词典里不写转义竖线）"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def _is_sep(cells):
    return cells is not None and set("".join(cells)) <= set("-: ") and "".join(cells).strip() != ""


def _tables(lines):
    """把连续表格行切成一张张表（每张 = [表头行, 分隔行, 数据行…]）"""
    out, cur = [], []
    for l in lines:
        c = _cells(l)
        if c is None:
            if cur:
                out.append(cur)
                cur = []
            continue
        cur.append(c)
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- 归一算法（算法性小工具，不是词表）
def split_top(s):
    """按顶层 `+` / `、`（含旧式 `｜`）拆分；括号与 `[]` 内的不算"""
    out, buf, depth = [], "", 0
    for ch in s:
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
        if ch in ("+", "、", BAR) and depth == 0:
            out.append(buf)
            buf = ""
            continue
        buf += ch
    out.append(buf)
    return [x.strip() for x in out if x.strip()]


def split_groups(s):
    """按顶层 `；` / `;` 分解法组（**历史格式**：2026-10-06 起写法废止、解析仍宽容；括号与 `[]` 内的不算）"""
    out, buf, depth = [], "", 0
    for ch in s:
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
        if ch in (SEMI, ";") and depth == 0:
            out.append(buf)
            buf = ""
            continue
        buf += ch
    out.append(buf)
    return [x.strip() for x in out if x.strip()]


def has_semi(s):
    """归一结果里还有 `；` / `;` 解法分隔吗（2026-10-06 起废止的写法）。

    现行规则 = **只写题解实际使用的那条解法**（详见词典第五节）：解析层仍宽容
    （split_groups 照拆、历史值归一回原样），但闸门（check_solution 第 18 项 /
    archive_check 3c / fill_knowledge）拿本函数把带 `；` 的串报成问题，防写法回潮。
    """
    return SEMI in (s or "") or ";" in (s or "")


def _split_annot(s):
    """剥尾巴上的主次标注 → (主体, 标注)。`[主]`/`(主)`/`（主）`/`【主】` 都认，
    统一转正成 `[主]` / `[次]`；没有标注 → (s, "")。"""
    m = _ANNOT_RE.search(s)
    if not m:
        return s.strip(), ""
    return s[:m.start()].strip(), "[%s]" % m.group(1)


def split_names_all(s):
    """知识点串（v2 格式）→ 纯名字列表：去掉 `；`/`+`/`[]` 结构与 `[主]`/`[次]` 标注，
    保序、**保留重复**（同一个知识点写了几次就出现几次）。纯语法操作、不查词表——
    知识点频次统计用它（一题里重复写的要给多次计数）。"""
    out = []

    def walk(seg):
        for p in split_top(seg):
            body, _ = _split_annot(p)
            if not body:
                continue
            if body[0] in "[【" and body[-1] in "]】":
                walk(body[1:-1])
            else:
                out.append(body)

    for g in split_groups(s):
        walk(g)
    return out


def split_names(s):
    """知识点串（v2 格式）→ 纯名字列表：`split_names_all` 的保序去重版。
    纯语法操作、不查词表——export 生成 manifest 的 knowledge 数组用它。"""
    out = []
    for name in split_names_all(s):
        if name not in out:
            out.append(name)
    return out


def strip_paren(s):
    """去掉（...）/(...) 说明"""
    return re.sub(r"[（(][^（）()]*[）)]", "", s).strip()


def _key(s):
    """别名/标准名匹配键：去全部空白 + 小写（`状态压缩 dp` ≡ `状态压缩dp`）"""
    return re.sub(r"\s+", "", s or "").lower()


# ---------------------------------------------------------------- 词典
class KnowledgeDict(object):
    def __init__(self, path=None):
        self.path = path or DEFAULT_PATH
        self.standards = []      # [(标准名, 文件夹 or None)]，保持词典里的顺序
        self.folders = {}        # {标准名: 文件夹（无尾反斜杠，如 "DP\区间DP"）}
        self.folder_names = {}   # {lower(文件夹): 文件夹}
        self.alias = {}          # {_key(别名): 标准名}
        self._std_ci = {}        # {_key(标准名): 标准名}
        self.drop_exact = set()
        self.drop_sub = []
        self.expand = {}         # {_key(组合名): [标准名, …]}（组合名展开表：一名拆多名）
        self.groups = {}         # {父知识点: [子知识点, …]}（父子关系表：统计页折叠用，保序）
        self.final = {}          # {(比赛名, 场次号, 字母): 知识点串}
        self._cands = []         # [(key, 标准名)] 兜底候选，按长度降序
        self._parse()
        self._validate()

    # ---- 解析 ----
    def _parse(self):
        with open(self.path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        seen_hdr = set()
        for tb in _tables(lines):
            head = tb[0]
            if not head:
                continue
            if head[0] == "标准名":
                seen_hdr.add("std")
                for c in tb[1:]:
                    if _is_sep(c) or len(c) < 3 or not c[0]:
                        continue
                    name = c[0]
                    folder = c[1].strip("`").replace("/", BS).strip().strip(BS)
                    folder = None if folder in NO_FOLDER else folder
                    self.standards.append((name, folder))
                    if folder:
                        self.folders[name] = folder
                        # 两个标准名共用一个文件夹是合法的（如「前缀和」「差分」共用
                        # `前缀和与差分\`）；只拦「同键却是不同写法」的不一致
                        kf = _key(folder)
                        if kf in self.folder_names and self.folder_names[kf] != folder:
                            raise ValueError("词典里文件夹重复：`%s`" % folder)
                        self.folder_names[kf] = folder
                    if _key(name) in self._std_ci:
                        raise ValueError("词典里标准名重复：%s" % name)
                    self._std_ci[_key(name)] = name
                    for a in [x.strip() for x in re.split(r"[、,，]", c[2]) if x.strip()]:
                        ka = _key(a)
                        # 同键 = 只是写法差异（`区间dp` ≡ `区间 DP`）：指向同一个
                        # 标准名就跳过（冗余），指向不同才是真撞车 —— 报错让人修词典
                        if ka in self._std_ci:
                            if self._std_ci[ka] != name:
                                raise ValueError(
                                    "别名「%s」与标准名「%s」撞车（本行指向「%s」，请改名）"
                                    % (a, self._std_ci[ka], name))
                            continue
                        if ka in self.alias:
                            if self.alias[ka] != name:
                                raise ValueError("别名「%s」指向两个标准名：%s 与 %s"
                                                 % (a, self.alias[ka], name))
                            continue
                        self.alias[ka] = name
            elif head[0] == "细节短语":
                seen_hdr.add("drop")
                for c in tb[1:]:
                    if _is_sep(c) or len(c) < 2 or not c[0]:
                        continue
                    if c[1] == "精确":
                        self.drop_exact.add(c[0])
                    elif c[1] == "子串":
                        self.drop_sub.append(c[0])
                    else:
                        raise ValueError("删除表的「命中方式」只能是 精确 / 子串：%s" % c[1])
            elif head[0] == "比赛":
                seen_hdr.add("final")
                for c in tb[1:]:
                    if _is_sep(c) or len(c) < 4 or not c[0]:
                        continue
                    name, rnd = toolutil.parse_contest("%s %s" % (c[0], c[1]))
                    if name is None:
                        raise ValueError("词典定稿表场次认不出：%s %s"
                                         "（要写 `周赛 123` / `入门赛 52` 这种，2026-10-08 起不带 #）"
                                         % (c[0], c[1]))
                    self.final[(name, rnd, c[2].upper())] = c[3]
            elif head[0] == "组合名":
                # 组合名展开表（可选表；表在 = 内容必须合法，校验见 _validate）
                for c in tb[1:]:
                    if _is_sep(c) or len(c) < 2 or not c[0]:
                        continue
                    self.expand[_key(c[0])] = split_top(c[1])
            elif head[0].startswith("父"):
                # 父子关系表（可选表；统计页把子知识点折到父下）。父 = 自己起的分桶标签
                # （不必是标准名），子 = 已登记标准名列表（顿号 / 逗号分隔，保序）。
                for c in tb[1:]:
                    if _is_sep(c) or len(c) < 2 or not c[0]:
                        continue
                    kids = [x.strip() for x in re.split(r"[、,，]", c[1]) if x.strip()]
                    if not kids:
                        raise ValueError("父子关系表：`%s` 的子集合是空的" % c[0])
                    self.groups[c[0]] = kids
            # 其它表格（如说明用的）忽略
        if seen_hdr != {"std", "drop", "final"}:
            raise ValueError("词典缺表：%s" % ("、".join(sorted({"std", "drop", "final"} - seen_hdr))))

    def _validate(self):
        if not self.standards:
            raise ValueError("标准名表是空的")
        if not self.drop_exact:
            raise ValueError("细节短语删除表是空的")
        if not self.final:
            raise ValueError("已定稿题目表是空的")
        # 别名 ↔ 标准名 的同键撞车在 _parse 里就查过（同目标 = 冗余跳过，异目标 = 报错）
        std_names = [x for x, _ in self.standards]
        for a, n in self.alias.items():
            if n not in self.folders and n not in std_names:
                raise ValueError("别名指向不存在的标准名：%s" % n)
        # 组合名展开表（可选表）：展开目标必须都是标准名；组合名不能与标准名/别名撞车
        for k, segs in self.expand.items():
            for x in segs:
                if self.canonical(x) != x:
                    raise ValueError("组合名展开表：`%s` 展开出的「%s」不是标准名" % (k, x))
            if k in self._std_ci or k in self.alias:
                raise ValueError("组合名「%s」与标准名/别名撞车（只能登记在一处）" % k)
        # 父子关系表（可选表）：子 = 已登记标准名**或另一个桶**；一个子只能有一个父
        # （父桶可与自己的某个子同名，如 `DP` 桶含 `DP` 本身 = 原「DP」这个知识点 + 各 DP 变体）；
        # 2026-10-08 放宽：允许多级嵌套（桶可以同时是别的桶的子，如 `图论 → 树 → LCA`），
        # 但不许成环
        seen_child = {}
        for parent, kids in self.groups.items():
            for kid in kids:
                if kid not in self.groups and self.canonical(kid) != kid:
                    raise ValueError("父子关系表：`%s` 的子「%s」既不是标准名也不是桶" % (parent, kid))
                if kid in seen_child and seen_child[kid] != parent:
                    raise ValueError("父子关系表：「%s」同时挂在 `%s` 与 `%s` 下（一个子只能有一个父）"
                                     % (kid, seen_child[kid], parent))
                seen_child[kid] = parent
        for start in self.groups:
            seen, cur = set(), start
            while cur is not None:
                if cur in seen:
                    raise ValueError("父子关系表成环：「%s」一路数上去绕回了自己" % start)
                seen.add(cur)
                nxt = seen_child.get(cur)
                cur = None if nxt == cur else nxt   # 自指（桶含同名成员，如 `DP` 桶含 `DP`）不算边
        # 兜底候选表：标准名 + 别名 → 标准名，按 key 长度降序（最长优先）。
        # 标准名先入（setdefault）——同键时标准名赢，与精确查询口径一致。
        cands = {}
        for name, _ in self.standards:
            cands.setdefault(_key(name), name)
        for a, n in self.alias.items():
            cands.setdefault(a, n)
        self._cands = sorted(cands.items(), key=lambda x: -len(x[0]))

    # ---- 查询 ----
    def canonical(self, name):
        """名字 → 标准名（标准名直通 / 别名映射；大小写与空格不敏感）；认不出 → None"""
        k = _key(name)
        if not k:
            return None
        return self._std_ci.get(k) or self.alias.get(k)

    def folder_of(self, name):
        """标准名（或别名）→ 归档文件夹；无文件夹/认不出 → None"""
        c = self.canonical(name)
        return self.folders.get(c) if c else None

    def suggest(self, name):
        """给未登记名字一个最接近的标准名（difflib，仅供参考）"""
        k = _key(name)
        if not k:
            return None
        keys = list(self._std_ci.keys()) + list(self.alias.keys())
        m = difflib.get_close_matches(k, keys, n=1, cutoff=0.4)
        if not m:
            return None
        return self._std_ci.get(m[0]) or self.alias.get(m[0])

    def _wrap_hit(self, s):
        """修饰兜底：段以某个已登记名字**开头或结尾**（还剩修饰字）→ 该名字的标准名。

        `分组前缀和` → `前缀和`（`前缀和` 收尾）、`枚举一维` → `枚举`（`枚举` 开头）、
        `迭代 DFS` → `DFS`。候选按长度降序（最长优先，`换根dp` 赢 `dp`）；
        段与候选等长时不在此处理（精确查询在前）。认不出 → None。
        """
        k = _key(s)
        if not k:
            return None
        for ck, std in self._cands:
            if len(ck) < len(k) and (k.startswith(ck) or k.endswith(ck)):
                return std
        return None

    def resolve_folder(self, folder):
        """manifest 的 folder 字段 → 标准归档文件夹。

        返回 (folder | None, 说明 or None)：
          · 直接命中文件夹表 → (原名, None)
          · 别名 / 短名（`区间DP`、`算法\\位运算\\`）→ (标准名, "补全为 `…`")
          · 认不出 → (None, "未登记")——**照收不拒**，由合并时的收编流程处理
        """
        f = (folder or "").strip().strip("`").replace("/", BS).strip().strip(BS)
        if not f:
            return None, "空文件夹"
        if f.startswith("算法" + BS):          # 记录 md 头部写法：`算法\位运算\`
            f = f[len("算法") + 1:]
        cands = [f]
        last = f.split(BS)[-1]
        if last != f:
            cands.append(last)                 # 末段兜底：`DP\区间DP` 只写 `区间DP` 也认
        for i, c in enumerate(cands):
            k = _key(c)
            cname = self.canonical(c)
            if k in self.folder_names:
                real = self.folder_names[k]
            elif cname and cname in self.folders:
                real = self.folders[cname]
            else:
                continue
            if i == 0 and real == c:
                return real, None
            if i == 0:
                return real, "别名自动映射到 `%s`" % real
            return real, "补全为 `%s`" % real
        return None, "未登记"

    # ---- 归一 ----
    def _norm_item(self, item, unknown, mapped):
        """解法组内的一个项 → 归一后的项列表（通常 1 个；被删空 = 0 个；组合名展开 = 多个）

        项 = `名字 [标注]` 或 `[子组] [标注]`（打包组递归回 _norm_group）。
        """
        body, ann = _split_annot(item)
        if not body:
            return []
        if body[0] in "[【" and body[-1] in "]】":        # 打包组：递归；组内全被删 → 整组删
            inner = self._norm_group(body[1:-1], unknown, mapped)
            return ["[%s]%s" % (inner, ann)] if inner else []
        p = strip_paren(body)
        if not p:
            return []
        c = self.canonical(p)
        if c is None and (p in self.drop_exact or any(s in p for s in self.drop_sub)):
            return []                                    # 细节短语 → 删（先于展开/兜底）
        if c is None:
            exp = self.expand.get(_key(p))               # 组合名展开（一名拆多名）
            if exp:
                return [x + ann if i == 0 else x for i, x in enumerate(exp)]
        if c is None:
            c = self._wrap_hit(p)                        # 修饰兜底
            if c is not None and mapped is not None:
                mapped.append((p, c))
        if c is None:                                    # 仍未登记：原样保留 + 收集
            if unknown is not None and all(p != u for u, _ in unknown):
                unknown.append((p, self.suggest(p)))
            c = p
        c = re.sub(r"\b(dfs|bfs|dp|lca|rmq)\b", lambda m: m.group(1).upper(), c)
        return [c + ann]

    def _norm_group(self, seg, unknown, mapped):
        """解法组：按顶层 `+` / `、` 拆项 → 逐项归一 → 拼 ` + `（组内保序去重）"""
        out = []
        for p in split_top(seg or ""):
            for x in self._norm_item(p, unknown, mapped):
                if x not in out:
                    out.append(x)
        return " + ".join(out)

    def norm_name(self, alg, unknown=None, mapped=None):
        """自动归一（新场次用），输出 v2 格式：组内 ` + `、`[..]` 与标注原样保留。

        流程：按顶层 `；` 分解法组（历史格式，见 has_semi）→ 组内按 `+`/`、`/`｜` 拆项 → 每项剥尾巴标注
        （`(主)`、`（主）` 也认）→ 去（括号）说明 → 别名映射 → 命中删除表就删 →
        组合名展开 → 修饰兜底 → 按原结构拼回（组间 ` ； `、组内 ` + `）。

        unknown / mapped 传 list 时收集诊断（供写状态表 / 归档对账报告）：
          · unknown += [(段, 最接近的标准名 or None)] —— 归一后仍非标准名的段
            （落盘原样保留；调用方负责报出来，逼着收编或改写法）
          · mapped  += [(段, 标准名)] —— 靠「修饰兜底」归一的段（未经词典收编，
            人工核对用；`分组前缀和`→`前缀和` 这类）
        """
        groups = []
        for g in split_groups(alg or ""):
            s = self._norm_group(g, unknown, mapped)
            if s and s not in groups:                    # 整组被删 → 跳；同串解法组去重
                groups.append(s)
        return (" %s " % SEMI).join(groups)

    def final_knowledge(self, contest, rnd, letter, alg, unknown=None, mapped=None):
        """定稿表优先（人工过审）；查不到 → 自动归一（诊断信息透传，见 norm_name）"""
        hit = self.final.get((contest, int(rnd), str(letter).upper())) if rnd is not None else None
        return hit if hit else self.norm_name(alg, unknown=unknown, mapped=mapped)

    def fix_aliases(self, text, key="数据结构与算法"):
        """把 md 文本里 `- **<key>**：…` 那一行的**别名**换成标准名（纯函数，不写盘）。

        别名 = 同一个东西的另一种写法（`状态压缩DP` ≡ `状压 DP`）。不换掉它就会经
        索引列固化下来，别人的题解和自己的题解出现同一知识点的两种名字。
        未登记的名字不动（照收 + 待登记清单）。返回 (新文本, [(原名, 标准名)])。
        """
        m = re.search(r"^- \*\*%s\*\*：(.+)$" % re.escape(key), text, re.M)
        if not m:
            return text, []
        parts = re.split(r"([+、/；;])", m.group(1))   # 奇数位 = 分隔符
        used = []
        for i in range(0, len(parts), 2):
            s = parts[i].strip()
            if not s or (s[0] in "[【" and s[-1] in "]】"):
                continue                                 # 打包组：组内名字由归一负责
            body, _ann = _split_annot(s)                 # `A[主]` 只换 A 部分、标注保留
            if not body:
                continue
            c = self.canonical(body)
            if c is None:
                s2 = strip_paren(body)                   # `状态压缩DP（子集枚举）` 也认
                c2 = self.canonical(s2) if s2 else None
                if c2 and c2 != s2:
                    used.append((s2, c2))
                    parts[i] = parts[i].replace(s2, c2)
                continue
            if c != body:
                used.append((body, c))
                parts[i] = parts[i].replace(body, c)
        if not used:
            return text, []
        return text.replace(m.group(0), "- **%s**：%s" % (key, "".join(parts))), used

    def check_names(self, names):
        """一串知识点名字 → (resolved, mapped, unknown)。

        resolved = 落盘用的名字（别名已映射；未登记的原样保留——落盘不猜）；
        mapped   = [(原名, 标准名)] 别名自动纠正记录；
        unknown  = [(原名, 建议 or None)] 待登记清单（不拒收）。
        宽容：元素带 `[主]` / `[次]` 标注时剥掉再查（题解包 manifest 可能混入标注）。
        """
        resolved, mapped, unknown = [], [], []
        for raw in names:
            s = (raw or "").strip()
            if not s:
                continue
            body, ann = _split_annot(s)
            c = self.canonical(body)
            if c:
                if c + ann != s:
                    mapped.append((s, c))
                resolved.append(c + ann)
            else:
                unknown.append((s, self.suggest(s)))
                resolved.append(s)
        return resolved, mapped, unknown


_CACHE = {}


def load(path=None):
    """加载词典（带缓存）；path 缺省 = 仓库 `knowledge/15-知识点词典.md`"""
    p = path or DEFAULT_PATH
    if p not in _CACHE:
        _CACHE[p] = KnowledgeDict(p)
    return _CACHE[p]


# ---------------------------------------------------------------- CLI
USAGE = """用法：
    python knowledge_dict.py check <名字…>    # 查词：标准名 / 别名映射 / 最接近建议
    python knowledge_dict.py selftest          # 数据自检（词典本身 + 归一行为）
"""


def run_check(words):
    kd = load()
    for w in words:
        body, _ann = _split_annot(w)          # `A[主]` 这种也查得动（剥掉标注再查）
        c = kd.canonical(body)
        if c is None:
            exp = kd.expand.get(_key(body))
            if exp:
                print("%s → 组合名（归一时会拆成：%s）" % (w, " + ".join(exp)))
                continue
            w2 = kd._wrap_hit(body)
            if w2:
                print("%s → 未收编（自动归一时修饰兜底会归到：%s）" % (w, w2))
                continue
            s = kd.suggest(body)
            print("%s → 未登记（最接近的标准名：%s；仅供参考）"
                  % (w, s if s else "无"))
        elif c == w:
            print("%s → 标准名（已登记；文件夹 %s）"
                  % (w, ("`%s%s`" % (kd.folders[c], BS)) if c in kd.folders else "无"))
        else:
            print("%s → %s（别名自动映射）" % (w, c))
    return 0


def _selftest():
    """词典本身 + 归一行为的数据自检。

    **不写死数量**：词典是会长的数据（「待登记 → 收编」就是它的日常），
    数量断言会在每次合法收录新名字时误报。这里只查**不变量**与**行为回归**，
    数量只打印出来给人看。行为回归也先查「这条还在不在」——词典改名不该让自检红。
    """
    kd = load()
    assert kd.standards and kd.drop_exact and kd.drop_sub and kd.final

    # 不变量 1：定稿值不带半角竖线（会切断 md 表格）、不带全角竖线 / 分号（两个旧格式都已废止），
    # 拆出来的每个名字都是已登记标准名（v2：` + ` 并列、`[…]` 打包、`[主]/[次]` 标注）
    for (contest, rnd, letter), val in kd.final.items():
        assert "|" not in val, "定稿值里有半角竖线（会切断 md 表格）：%s" % val
        assert BAR not in val, "定稿值里还有全角竖线（旧格式没迁干净）：%s" % val
        assert not has_semi(val), \
            "定稿值里还有 `；` 解法分隔（2026-10-06 起废止，只写题解实际使用的那条）：%s" % val
        assert isinstance(rnd, int) and len(letter) == 1 and letter.isupper()
        names = split_names(val)
        assert names, "定稿值拆不出任何名字：%s" % val
        for p in names:
            assert kd.canonical(p) == p, "定稿值里的「%s」不是标准名（%s）" % (p, val)

    # 不变量 2：有文件夹的标准名都指到登记的那个文件夹（文件夹可多名共用，如
    # 「前缀和」「差分」共用 `前缀和与差分`）；文件夹本身无正斜杠 / 空段
    for name, folder in kd.standards:
        if folder:
            assert kd.folders.get(name) == folder
            assert "/" not in folder and folder == folder.strip(BS)
            assert all(seg.strip() == seg and seg for seg in folder.split(BS))

    # 不变量 3：别名解析对大小写 / 空格不敏感（拿词典里真实存在的条目验）
    for a, std in list(kd.alias.items())[:200]:
        assert kd.canonical("  " + a.upper() + " ") == std

    # 行为回归：词典里有这条才验（没有 = 词典改过名，不是故障）
    if kd.canonical("状压 DP"):
        assert kd.canonical("状态压缩DP") == "状压 DP"
        assert kd.canonical("状态压缩 dp") == "状压 DP"
        assert kd.canonical("状压dp") == "状压 DP"
    if kd.canonical("前缀和") and kd.canonical("差分"):
        # 2026-10-05：拆成两个标准名、共用一个归档文件夹（各写各的段，不再合并成一个名字）
        assert kd.folder_of("差分") == kd.folder_of("前缀和") == "前缀和与差分"
        assert kd.norm_name("置换环 + 差分 + 树状数组 + 二分") \
            == "置换环 + 差分 + 树状数组 + 二分查找"
        assert kd.fix_aliases("- **数据结构与算法**：置换环 + 差分 + 树状数组 + 二分")[1] \
            == [("二分", "二分查找")]
    if kd.expand.get(_key("前缀和与差分")):
        # 组合名展开（一名拆多名）：在原来的位置拆开，外面照常套 `[]` 与标注
        assert kd.norm_name("前缀和与差分") == "前缀和 + 差分"
        assert kd.norm_name("前缀和与差分[主]") == "前缀和[主] + 差分"
        assert kd.norm_name("[前缀和与差分][主] + 排序") == "[前缀和 + 差分][主] + 排序"
    if kd.canonical("二分查找"):
        assert kd.canonical("二分") == "二分查找"
    if kd.canonical("DFS 序"):
        assert kd.canonical("dfs 序") == "DFS 序"
    if kd.canonical("最短路"):
        assert kd.canonical("Dijkstra") == "最短路"
        assert kd.norm_name("Dijkstra（优先队列）+ 字典序双关键字松弛") == "最短路"
    assert kd.canonical("位运算") == "位运算"
    assert kd.canonical("李超线段树-unregistered-xyz") is None

    # 自动归一（纯规则，与具体词表无关）
    assert kd.norm_name("位运算（末尾零计数）+ 进制转换") == "位运算"
    assert kd.norm_name("dfs+dp") == "DFS + 线性 DP"
    assert kd.norm_name("连通块计数 + 洪水填充（BFS 迭代版）+ 四连通 / 八连通两套邻居定义") == "连通块计数"
    assert kd.norm_name("") == ""

    # v2 格式（2026-10-05 用户选定）：` + ` 组内并列、`[…]` 打包、`[主]`/`[次]` 标注
    assert kd.norm_name("位掩码[主] + 贪心") == "位运算[主] + 贪心"
    assert kd.norm_name("位掩码（主）+ 贪心") == "位运算[主] + 贪心"      # `（主）` 转正成 `[主]`
    assert kd.norm_name("位掩码 ｜ 贪心") == "位运算 + 贪心"              # 旧竖线宽容视同 ` + `
    assert kd.norm_name("位掩码 + 位运算") == "位运算"                    # 组内同名去重
    # `；` 解法分隔 = 历史格式（2026-10-06 起写法废止）：解析仍宽容、归一后原样保留，
    # 由闸门拿 has_semi() 报出来，防写法回潮
    assert kd.norm_name("位掩码 ； 贪心") == "位运算 ； 贪心"
    assert kd.norm_name("位掩码; 贪心") == "位运算 ； 贪心"               # 半角分号也认
    assert kd.norm_name("[位掩码 + 贪心][主] ； 枚举") == "[位运算 + 贪心][主] ； 枚举"
    assert kd.norm_name("枚举 ； 位掩码") == "枚举 ； 位运算"             # 不同解法组保留
    assert kd.norm_name("位掩码 ； 位运算") == "位运算"                   # 同串解法组去重
    assert split_names("[前缀和 + 差分][主] ； 枚举 ； DFS") \
        == ["前缀和", "差分", "枚举", "DFS"]
    assert has_semi("A ； B") and has_semi("A ; B")
    assert not has_semi("组合计数[主] + DFS") and not has_semi("")

    # 修饰兜底（2026-10-05）：段以已登记名字开头/结尾（还剩修饰字）→ 归到它。
    # 用虚构词（`…xyz`）验机制本身，词典以后收编同名不影响。
    if kd.canonical("前缀和"):
        assert kd.norm_name("前缀和xyz") == "前缀和"
        assert kd.norm_name("前缀和xyz + 位运算") == "前缀和 + 位运算"
    if kd.canonical("枚举"):
        assert kd.norm_name("枚举xyz") == "枚举"
    if kd.canonical("DFS"):
        assert kd.norm_name("迭代 DFS") == "DFS"
    # 删除表先于兜底：`DFS 枚举因子` 整段删，不会被吃成 `DFS`
    assert kd.norm_name("DFS 枚举因子 + 位运算") == "位运算"
    # 兜底不上的原样保留 + 进 unknown；兜底命中进 mapped
    u, m = [], []
    got = kd.norm_name("前缀和xyz + 未登记xyzabc", unknown=u, mapped=m)
    assert got == "前缀和 + 未登记xyzabc", got
    assert m == [("前缀和xyz", "前缀和")], m
    assert len(u) == 1 and u[0][0] == "未登记xyzabc", u
    assert kd.norm_name("未登记xyzabc") == "未登记xyzabc"

    # 定稿表优先：逐条拿「乱写的算法串」去查，必须原样返回定稿值
    for (contest, rnd, letter), val in kd.final.items():
        assert kd.final_knowledge(contest, rnd, letter, "乱写-" + letter) == val
    assert kd.final_knowledge("牛客周赛", 99999, "A", "位掩码+贪心") == "位运算 + 贪心"

    # 文件夹解析
    if kd.folder_of("区间dp"):
        assert kd.folder_of("区间dp") == "DP" + BS + "区间DP"
        assert kd.resolve_folder("区间DP")[0] == "DP" + BS + "区间DP"
    assert kd.resolve_folder("算法" + BS + "位运算" + BS)[0] == "位运算"
    assert kd.resolve_folder("没登记-abc-xyz") == (None, "未登记")

    # 校验报告：别名自动纠正 / 未登记照收 + 建议
    resolved, mapped, unknown = kd.check_names(["位运算", "李超线段树-xyz"])
    assert resolved == ["位运算", "李超线段树-xyz"]
    assert mapped == []
    assert len(unknown) == 1 and unknown[0][0] == "李超线段树-xyz"
    if kd.canonical("状压 DP"):
        resolved, mapped, unknown = kd.check_names(["状态压缩DP", "位运算"])
        assert resolved == ["状压 DP", "位运算"]
        assert mapped == [("状态压缩DP", "状压 DP")]
        assert unknown == []

    # 不变量 4（v17；2026-10-08 放宽为多级）：父子关系表（可选表）——
    # 子 = 标准名或另一个桶、一个子一个父、不许成环（这些在 _validate 里就拦了；这里再显式走一遍）
    child_owner = {}
    for parent, kids in kd.groups.items():
        for kid in kids:
            assert kid in kd.groups or kd.canonical(kid) == kid, \
                "父子表子「%s」既不是标准名也不是桶" % kid
            assert child_owner.get(kid, parent) == parent, "子「%s」挂了两个父" % kid
            child_owner[kid] = parent
    for start in kd.groups:
        seen, cur = set(), start
        while cur is not None:
            assert cur not in seen, "父子表成环：%s" % start
            seen.add(cur)
            nxt = child_owner.get(cur)
            cur = None if nxt == cur else nxt   # 自指（桶含同名成员）不算边

    print("knowledge_dict 自检 OK（%d 标准名 / %d 文件夹 / %d 别名 / %d 定稿 / %d 父桶）"
          % (len(kd.standards), len(kd.folder_names), len(kd.alias), len(kd.final),
             len(kd.groups)))


def main(argv):
    if not argv or "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0 if argv else 2
    if argv[0] == "check":
        if len(argv) < 2:
            print(USAGE)
            return 2
        return run_check(argv[1:])
    if argv[0] == "selftest":
        _selftest()
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
