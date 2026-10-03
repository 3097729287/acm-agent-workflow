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

归一口径（2026-10-03 定稿）：
  · 按顶层 `+` / `、` 拆 → 去（括号）说明 → 别名映射 → 命中删除表就删 → 拼 `主 ｜ 次1、次2`
  · 首字母缩写大写（dfs → DFS）；全角竖线 U+FF5C 作分隔符（半角会切断 md 表格）
  · 别名的匹配对大小写与空格不敏感（`状态压缩 dp` ≡ `状态压缩dp`）
"""
import argparse
import difflib
import os
import re
import sys

import toolutil  # 同目录：REPO_ROOT + parse_contest（场次键的唯一解析）

DEFAULT_PATH = os.path.join(toolutil.REPO_ROOT, "knowledge", "15-知识点词典.md")
BAR = "｜"          # 全角竖线
PUNCT = "、"        # 顿号
BS = chr(92)            # 反斜杠
NO_FOLDER = ("—", "-", "–", "", "无", "（无）")


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
    """按顶层 `+` / `、` 拆分（括号内的不算）"""
    out, buf, depth = [], "", 0
    for ch in s:
        if ch in "（(":
            depth += 1
        elif ch in "）)":
            depth = max(0, depth - 1)
        if ch in ("+", "、") and depth == 0:
            out.append(buf)
            buf = ""
            continue
        buf += ch
    out.append(buf)
    return [x.strip() for x in out if x.strip()]


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
        self.final = {}          # {(比赛名, 场次号, 字母): 知识点串}
        self._parse()
        self._validate()

    # ---- 解析 ----
    def _parse(self):
        lines = open(self.path, encoding="utf-8").read().split("\n")
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
                        if _key(folder) in self.folder_names:
                            raise ValueError("词典里文件夹重复：`%s`" % folder)
                        self.folder_names[_key(folder)] = folder
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
                        raise ValueError("词典第三节场次认不出：%s %s（要写 `Round N`）"
                                         % (c[0], c[1]))
                    self.final[(name, rnd, c[2].upper())] = c[3]
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
    def norm_name(self, alg):
        """自动归一（新场次用）：别名映射 → 删细节短语 → 拼 `主 ｜ 次1、次2`"""
        parts = []
        for p in [strip_paren(x) for x in split_top(alg or "")]:
            p = p.strip()
            if not p:
                continue
            p = self.canonical(p) or p
            if p in self.drop_exact or any(s in p for s in self.drop_sub):
                continue
            if p not in parts:
                parts.append(p)
        if not parts:
            return ""
        parts = [re.sub(r"\b(dfs|bfs|dp|lca|rmq)\b", lambda m: m.group(1).upper(), p)
                 for p in parts]
        res = parts[0]
        if len(parts) > 1:
            res += " " + BAR + " " + PUNCT.join(parts[1:])
        return res

    def final_knowledge(self, contest, rnd, letter, alg):
        """定稿表优先（人工过审）；查不到 → 自动归一"""
        hit = self.final.get((contest, int(rnd), str(letter).upper())) if rnd is not None else None
        return hit if hit else self.norm_name(alg)

    def fix_aliases(self, text, key="数据结构与算法"):
        """把 md 文本里 `- **<key>**：…` 那一行的**别名**换成标准名（纯函数，不写盘）。

        别名 = 同一个东西的另一种写法（`状态压缩DP` ≡ `状压 DP`）。不换掉它就会经
        索引列固化下来，别人的题解和自己的题解出现同一知识点的两种名字。
        未登记的名字不动（照收 + 待登记清单）。返回 (新文本, [(原名, 标准名)])。
        """
        m = re.search(r"^- \*\*%s\*\*：(.+)$" % re.escape(key), text, re.M)
        if not m:
            return text, []
        parts = re.split(r"([+、/])", m.group(1))     # 奇数位 = 分隔符
        used = []
        for i in range(0, len(parts), 2):
            s = parts[i].strip()
            if not s:
                continue
            c = self.canonical(s)
            if c is None:
                s2 = strip_paren(s)                  # `状态压缩DP（子集枚举）` 也认
                c2 = self.canonical(s2) if s2 else None
                if c2 and c2 != s2:
                    used.append((s2, c2))
                    parts[i] = parts[i].replace(s2, c2)
                continue
            if c != s:
                used.append((s, c))
                parts[i] = parts[i].replace(s, c)
        if not used:
            return text, []
        return text.replace(m.group(0), "- **%s**：%s" % (key, "".join(parts))), used

    def check_names(self, names):
        """一串知识点名字 → (resolved, mapped, unknown)。

        resolved = 落盘用的名字（别名已映射；未登记的原样保留——落盘不猜）；
        mapped   = [(原名, 标准名)] 别名自动纠正记录；
        unknown  = [(原名, 建议 or None)] 待登记清单（不拒收）。
        """
        resolved, mapped, unknown = [], [], []
        for raw in names:
            s = (raw or "").strip()
            if not s:
                continue
            c = self.canonical(s)
            if c:
                if c != s:
                    mapped.append((s, c))
                resolved.append(c)
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
        c = kd.canonical(w)
        if c is None:
            s = kd.suggest(w)
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

    # 不变量 1：定稿表的值用全角竖线（半角会切断 md 表格），且各段都是已登记名字
    for (contest, rnd, letter), val in kd.final.items():
        assert "|" not in val, "定稿值里有半角竖线（会切断 md 表格）：%s" % val
        assert isinstance(rnd, int) and len(letter) == 1 and letter.isupper()
        for p in re.split(r"\s*" + BAR + r"\s*|[、]", val):
            assert kd.canonical(p) == p, "定稿值里的「%s」不是标准名（%s）" % (p, val)

    # 不变量 2：有文件夹的标准名 ↔ 文件夹互为唯一；文件夹本身无正斜杠 / 空段
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
    if kd.canonical("前缀和与差分"):
        assert kd.canonical("差分") == "前缀和与差分"
        assert kd.folder_of("差分") == "前缀和与差分"
        assert kd.norm_name("置换环 + 差分 + 树状数组 + 二分") \
            == "置换环 " + BAR + " 前缀和与差分、树状数组、二分查找"
        assert kd.fix_aliases("- **数据结构与算法**：置换环 + 差分 + 树状数组 + 二分")[1] \
            == [("差分", "前缀和与差分"), ("二分", "二分查找")]
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
    assert kd.norm_name("dfs+dp") == "DFS " + BAR + " DP"
    assert kd.norm_name("连通块计数 + 洪水填充（BFS 迭代版）+ 四连通 / 八连通两套邻居定义") == "连通块计数"
    assert kd.norm_name("") == ""

    # 定稿表优先：逐条拿「乱写的算法串」去查，必须原样返回定稿值
    for (contest, rnd, letter), val in kd.final.items():
        assert kd.final_knowledge(contest, rnd, letter, "乱写-" + letter) == val
    assert kd.final_knowledge("牛客周赛", 99999, "A", "位掩码+贪心") == "位运算 " + BAR + " 贪心"

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

    print("knowledge_dict 自检 OK（%d 标准名 / %d 文件夹 / %d 别名 / %d 定稿）"
          % (len(kd.standards), len(kd.folders), len(kd.alias), len(kd.final)))


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
