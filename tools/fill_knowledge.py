# -*- coding: utf-8 -*-
"""题目状态表：迁移 / 刷新「知识点」列（数据源 = 全量索引）。

用法：
    python fill_knowledge.py [dry|apply] [--file 状态表] [--index 索引] [--help]

做的事：
  1. 表头由旧版 `场次|题号|题名|难度|状态|日期|备注` 换成
     新版 `场次|题号|题名|知识点|难度|状态|日期`（删备注、知识点插在题名之后）；
  2. 用索引里每题的「算法 / 数据结构」列算出知识点，填进新列。
     场次键 = `toolutil.parse_contest` 给的 (比赛名, 场次号) + 题号，
     多平台不会撞号（Codeforces Round 161 与牛客 Round 161 各算各的）。

退出码：
  0  正常（dry / apply 都可能是 0）；
  2  状态表里认不出表头（旧版 / 新版 7 列表头都没有）；
  3  有「查不到知识点」的题（含场次认不出、被跳过的行）—— **dry 与 apply 一样**；
     apply 仍照常写文件，只是退出码变大，方便上层（GUI / 批处理）察觉。

知识点写法（用户 2026-10-02 定稿）：
    `主知识点 ｜ 次1、次2`   —— 分隔符是全角竖线 U+FF5C（半角 | 会把 md 表格切断）
    · 按**顶层** `+` 拆分（写在括号里的 `+` 不算，如「构造（上界 + 达到上界）」只有一段）
    · 每段去掉括号说明（括号 = 赘述，用户要求删）
    · 第一段 = 主；其余去重后 = 次要，用「、」连接；没有次要就不带竖线

归一（用户 2026-10-03 定稿，规则见下方 CANON / DROP / FINAL 三张表）：
    · 标准名 = 算法库文件夹名；同义合并（二分 / 排序二分查表 → 二分查找）
    · 细节短语一律删（只留在 D 盘单题题解里）；多解法题主解法并列写竖线左边
    · 本库 43 题走 `FINAL` 人工定稿表；新场次没登记时走 `normalize()` 自动归一

只改表头行 + 数据行里对应单元格，其余行逐字节不动；apply 前自动备份；纯 LF 无 BOM。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402  （备份统一走它）

DEFAULT_FILE = os.path.join(toolutil.DATA_ROOT, "题解", "题目状态.md")
DEFAULT_INDEX = os.path.join(toolutil.DATA_ROOT, "索引", "题解算法索引.md")

USAGE = """用法：python fill_knowledge.py [dry|apply] [--file <状态表>] [--index <索引>] [--help]

题目状态表：迁移 / 刷新「知识点」列（数据源 = 全量索引；场次键 = 比赛名 + 场次号，
多平台不撞号）。默认 dry（只看不动）；加 apply 才写文件（写前按备份规则自动备份）。

退出码：
  0  正常；
  2  状态表里认不出表头（旧版 / 新版 7 列表头都没有）；
  3  有「查不到知识点」的题（含场次认不出、被跳过的行）—— dry 与 apply 一样；
     apply 仍照常写文件，只是退出码变大，方便上层察觉。
"""

HEAD_OLD = ["场次", "题号", "题名", "难度", "状态", "日期", "备注"]
HEAD_NEW = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]
LABEL = "## 题目状态表"
BAR = "\uff5c"          # 全角竖线
PUNCT = "\u3001"        # 顿号


# ---------------------------------------------------------------- 解析小工具
def split_cells(line):
    """切表格行（尊重转义 \\|）；不是表格行返回 None"""
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s.strip("|")
    parts, buf, i = [], "", 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if s[i] == "|":
            parts.append(buf.strip())
            buf = ""
            i += 1
            continue
        buf += s[i]
        i += 1
    parts.append(buf.strip())
    return parts


def top_split(s):
    """按顶层 `+` 拆分（括号内的 `+` 不算）"""
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


# ---------------------------------------------------------------- 归一（2026-10-03 用户定稿）
# 【标准名从哪来】一律取算法库 `<数据根>\算法\` 里的文件夹名（含 DP 下的子文件夹：
#   分布压缩DP / 区间DP / 树形DP / 状压DP）。此外固定四个非文件夹标准名：
#   二分答案 / DFS 序 / Hall 定理 / 连通块计数。
# 【三条规则】① 同义合并：同一算法只留一个标准名（二分 / 排序二分查表 → 二分查找）；
#   ② 细节降级：题目专属的描述性短语一律删（洪水填充、字典序双关键字松弛、边的点覆盖…），
#      它们只留在那一场的单题题解 md 里；
#   ③ 多解法题：主解法并列写在竖线左边（如 `DFS BFS ｜ 连通块计数`），次要用「、」连。
CANON = {
    "二分": "二分查找",
    "排序二分查表": "二分查找",
    "单调判定上的二分": "二分答案",
    "暴力枚举": "枚举",
    "连续段计数": "连续段",
    "排序去重": "排序",
    "位掩码": "位运算",
    "dfs 序": "DFS 序",
    "Dijkstra": "最短路",
    "质因数分解": "素数",
    "同向双指针": "双指针",
    "二维前缀和": "前缀和与差分",
    "后缀和": "前缀和与差分",
    "树上差分": "前缀和与差分",
    "区间dp": "区间 DP",
    "树形dp": "树形 DP",
    "状压dp": "状压 DP",
    "分布压缩dp": "分布压缩 DP",
}
# 细节短语（自动归一用）：整串命中 → 删
DROP_EXACT = {
    "在线维护", "增量更新", "构造方案", "排序扫描", "度数统计", "最优结构的刻画与计数",
    "阈值分解", "洪水填充", "四连通 / 八连通两套邻居定义", "自定义排序比较器",
    "字典序双关键字松弛", "异或消去律", "按数字分桶的后缀和", "结构观察", "边的点覆盖",
    "异侧判定", "逐位比较", "补集计数", "开桶查表", "数位 DP 式区间计数", "字符串",
    "一次扫描", "前缀最大值", "逐段贪心", "结构刻画", "路径参数化", "代表元去重",
    "字符串长度的翻倍递推", "DFS 枚举因子", "前缀覆盖计数", "进制转换", "圆上区间 DP",
}
# 细节短语（自动归一用）：含这些子串 → 删
DROP_SUB = ("刻画", "（BFS 迭代版）", "邻居定义", "比较器", "松弛", "消去律", "分桶")


def normalize(alg):
    """自动归一（新场次用）：CANON 合并同义 → DROP 删细节 → 拼 `主 ｜ 次1、次2`"""
    parts = []
    for p in [strip_paren(x) for x in top_split(alg)]:
        p = p.strip()
        if not p:
            continue
        p = CANON.get(p, p)
        if p in DROP_EXACT or any(s in p for s in DROP_SUB):
            continue
        if p not in parts:
            parts.append(p)
    if not parts:
        return ""
    parts = [re.sub(r"\b(dfs|bfs|dp|lca|rmq)\b", lambda m: m.group(1).upper(), p) for p in parts]
    res = parts[0]
    if len(parts) > 1:
        res += " " + BAR + " " + PUNCT.join(parts[1:])
    return res


# 人工定稿表：本库 43 题的最终写法（2026-10-03 逐题过了一遍）
FINAL = {
    (123, "C"): "构造",
    (123, "D"): "组合计数",
    (123, "E"): "连续段",
    (123, "F"): "连续段",
    (123, "G"): "双指针 ｜ 排序",
    (124, "C"): "连续段 ｜ 排序",
    (124, "D"): "图论",
    (124, "E"): "结论与计数 ｜ 快速幂",
    (124, "F"): "区间 DP ｜ 栈",
    (140, "B"): "栈",
    (140, "C"): "枚举",
    (140, "D"): "并查集",
    (140, "E"): "并查集",
    (140, "F"): "构造",
    (140, "G"): "生成树 ｜ 并查集",
    (143, "C"): "素数 ｜ 快速幂",
    (143, "D"): "二分查找 ｜ 排序",
    (143, "E"): "贪心",
    (143, "F"): "分布压缩 DP",
    (155, "B"): "计算几何 ｜ 枚举",
    (155, "C"): "枚举",
    (155, "D"): "位运算",
    (155, "E"): "位运算",
    (155, "F"): "构造",
    (159, "C"): "前缀和与差分 ｜ 二分查找",
    (159, "D"): "位运算",
    (159, "E"): "字典树 ｜ 前缀和与差分",
    (159, "F"): "DFS 序 ｜ 树状数组",
    (161, "B"): "前缀和与差分",
    (161, "C"): "位运算 ｜ 排序",
    (161, "D"): "DFS BFS ｜ 连通块计数",
    (161, "E"): "最短路",
    (161, "F"): "折半枚举 ｜ 二分查找",
    (162, "C"): "取模与同余 ｜ 前缀和与差分",
    (162, "D"): "递推",
    (162, "E"): "稀疏表 ｜ 二分答案",
    (162, "F"): "树形 DP",
    (163, "B"): "位运算",
    (163, "C"): "二分图匹配 ｜ Hall 定理",
    (163, "D"): "构造",
    (163, "E"): "计算几何",
    (163, "F"): "字典树",
    (163, "G"): "置换环 ｜ 差分、树状数组、二分查找",
}


def final_knowledge(name, rnd, letter, alg):
    """定稿表只覆盖牛客周赛；别的比赛走自动归一（不串平台）"""
    if name == "牛客周赛":
        return FINAL.get((rnd, letter)) or normalize(alg)
    return normalize(alg)


# ---------------------------------------------------------------- 读索引
def read_index(path):
    """{(比赛名, 场次号, 字母): 知识点}（场次键走 toolutil.parse_contest，不写死牛客）"""
    out = {}
    name, rnd = None, None
    for line in io.open(path, encoding="utf-8").read().split("\n"):
        m = re.match(r"^##(?!#)\s+(.*)$", line)
        if m:
            name, rnd = toolutil.parse_contest(m.group(1))   # 非场次小节 → (None, None)
            continue
        if name is None:
            continue
        c = split_cells(line)
        if not c or len(c) != 5 or not re.fullmatch(r"[A-Z]", c[0]):
            continue
        out[(name, rnd, c[0])] = final_knowledge(name, rnd, c[0], c[3])
    return out


# ---------------------------------------------------------------- 改状态表
def run(mode, fpath, ipath):
    idx = read_index(ipath)
    text = io.open(fpath, encoding="utf-8").read()
    lines = text.split("\n")
    i0 = next((i for i, l in enumerate(lines) if split_cells(l) == HEAD_OLD
               or split_cells(l) == HEAD_NEW), None)
    if i0 is None:
        print("\u2605找不到表头（旧版或新版 7 列都认不出）：", fpath)
        return 2
    old = split_cells(lines[i0]) == HEAD_OLD
    print("表头：%s（%s）" % ("旧版（含备注）" if old else "新版（含知识点）",
                           "将迁移成新版" if old else "只刷新知识点"))

    miss, unparsed, touched, newlines, present = [], [], 0, [], set()
    for i, l in enumerate(lines):
        c = split_cells(l)
        if i <= i0 or not c or len(c) != 7 or set("".join(c)) <= set("-: "):
            newlines.append(l)              # 表头 / 分隔线 / 非表格行
            continue
        name, rnd = toolutil.parse_contest(c[0])
        if name is None:
            unparsed.append((i + 1, c[0]))
            newlines.append(l)              # 认不出 → 原样留着，绝不当牛客处理
            continue
        if old:
            f, lt, ti, dif, st, dt = c[0], c[1], c[2], c[3], c[4], c[5]
        else:
            f, lt, ti, dif, st, dt = c[0], c[1], c[2], c[4], c[5], c[6]
        present.add((name, rnd, lt.upper()))
        know = idx.get((name, rnd, lt.upper()), "")
        if not know:
            miss.append("%s R%d%s" % (name, rnd, lt))
        new = "| %s | %s | %s | %s | %s | %s | %s |" % (f, lt, ti, know, dif, st, dt)
        if new != l:
            touched += 1
        newlines.append(new)

    newtext = "\n".join(newlines)
    newtext = newtext.replace("| " + " | ".join(HEAD_OLD) + " |",
                              "| " + " | ".join(HEAD_NEW) + " |", 1)
    extra = sorted(set(idx) - present)
    print("改动行数：%d ｜ 索引里查不到知识点的题：%s" % (touched, PUNCT.join(miss) or "无"))
    if extra:
        print("索引里有、状态表里没有的：%s" % PUNCT.join("%s R%d%s" % k for k in extra))
    for ln, txt in unparsed:
        print("★ 状态表第 %d 行场次认不出，跳过不填（绝不当牛客处理）：%s" % (ln, txt))
    bad = bool(miss or unparsed)
    if bad:
        items = list(miss) + ["第 %d 行「%s」" % (ln, txt) for ln, txt in unparsed]
        print("★ 索引里查不到知识点（%d 个）：%s（先补索引或修表，别留空）"
              % (len(items), PUNCT.join(items)))
    if mode != "apply":
        print("—— dry run，没写文件（要写加 apply）——")
        return 3 if bad else 0
    bak = toolutil.backup_to_repo(fpath)
    io.open(fpath, "w", encoding="utf-8", newline="\n").write(newtext)
    print("已写：%s\n备份：%s" % (fpath, bak))
    return 3 if bad else 0


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    mode = "apply" if "apply" in argv else "dry"
    a = argv[1:] if argv and argv[0] in ("dry", "apply") else argv
    fpath, ipath = DEFAULT_FILE, DEFAULT_INDEX
    for i, x in enumerate(a):
        if x == "--file":
            fpath = a[i + 1]
        if x == "--index":
            ipath = a[i + 1]
    return run(mode, fpath, ipath)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
