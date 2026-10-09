# -*- coding: utf-8 -*-
"""
去掉正文里"数学/记号"的反引号（灰底），保留"真代码"的灰底。

用户要的是「Word 那种排版」：变量、公式、复杂度、集合、坐标、区间 → 去掉灰底；
C++/Python 关键字、类型、标准库函数、我们代码里出现过的标识符与数组访问、
文件路径/文件名/命令/链接、字符串与字符字面量 → 保留灰底。

判定（自上而下，先命中先算）：
  0. 落在 ``` 代码块里的一个字都不动；
  1. 含纯数学符号（· ∈ ≡ × ≈ √ ⌈ ⌊ ∑ ⟺ θ ∞ ≠ ⊆ ∪ ∩ ∀ ∃ ≤ ≥）→ 去掉；
  2. 整段就是一个或几个 [..]（纯区间记号，不是数组下标）→ 去掉；
  2b. 老式下标（x_i / cnt_i / a_j，一个下划线 + 1~2 字母的尾巴）→ 去掉；
  3. 逐字命中 KEEP_EXACT，或**形状**像标识符（snake_case / camelCase / 模块.函数
     / 带 - 或 / 的名字，见 IDENT、DOTNAME、SLASHNAME），或含 KEEP_SUB 里任一子串 → 保留。

用法：python unpair_ticks.py <文件.md> [dry]
      dry = 只打印不写文件，并把逐行 diff 写到 <同目录>/unpair_diff.txt。

幂等：已去过灰底的文件再跑一次，改动行数为 0。
"""
import os
import re
import sys

import toolutil                       # 同目录：备份 / 围栏状态机的唯一实现

# 1) 精确等于这些 → 保留（关键字 / 类型 / 标准库 / 我们代码里的名字 / 命令）
KEEP_EXACT = {
    "int", "long long", "long double", "unsigned char", "string", "bool", "vector",
    "stack", "map", "ll", "cout", "cin", "scanf", "printf", "puts", "endl", "true",
    "false", "main", "break", "sort", "gcd", "__gcd", "std::gcd", "next_permutation",
    "upper_bound", "tolower", "isdigit", "to_string", "push_back", "typeid", "max", "min",
    "allZero", "best", "ch", "cnt", "id", "mn", "mx",
    "tot", "vis", "pos", "py", "python", "g++", "cd", "YES", "NO", "QUERIES", "SETUP",
    "Done.", "一致 ✔", "sort(b)", "part1()", "kth(0)", "fractions.Fraction",
    "set PYTHONIOENCODING=utf-8", "MAXN = 500005", "<numeric>", "nk163E",
    "__builtin_ctz(d)", "ctz(d)", "ptr + t", "for (char cc : s)",
    "if (best)", "if (best) --cnt[best];",
    # 2026-09-30 补：C++ 的 128 位整型。它带下划线，去掉反引号会被 markdown
    # 当成强调（__int128__ → 斜体），所以必须留在保留表里。
    "__int128", "unsigned __int128", "__int128_t",
    # 2026-09-30 补（刷老教程时实测）：这些是**真代码**（关键字 / 标准库 / 我们代码里的名字），
    # 老文件里没被认出、灰底被误去掉：`while` `return` `continue` `lower_bound` `sum(i)`
    # `add(i, v)` `lowbit(i)` `unordered_map` `unique` `erase` `v.size()` `dfs`。
    # 规矩照旧：补名单，不改判定规则。
    "while", "return", "continue", "do-while", "lower_bound", "unordered_map",
    "unique", "erase", "lowbit", "sum", "add", "dfs", "v.size()", "find",
    # 2026-10-01 补：裸单词的参数名（没有下划线也没有驼峰，形状判定够不着，
    # 只能进名单）。vignette / contrast / warm 是鎏金河 render.py 的配置项。
    "vignette", "contrast", "warm",
    # 2026-10-01 补：Claude Code 的命令名（火山引擎接入手册里 `claude` 被误判），
    # 跟已有的 python / g++ / cd 同类。
    "claude",
}

# 2) 含这些子串 → 保留（代码语法 / 路径 / 文件名 / 字符串字面量 / 我们代码里的标识符）
KEEP_SUB = [
    "[", "]", "::", ";", "++", "--", "&&", "||", "==", "!=", "<<", ">>", "+=", "-=", "->",
    # 2026-09-30 补：文件名/路径带这些扩展名的一律算「真代码」（.rnote 是 Rnote 手写文档）
    ".cpp", ".py", ".cmd", ".exe", ".md", ".txt", ".png", ".rnote", ".html", ".json",
    ".bat",                       # 同上（老教程里有 .bat 批处理）
    # 2026-10-01 补：交付物不都是题解，也有视频/图片/数据文件（鎏金河 LED 背景那个项目）；
    # 这些扩展名同样是「文件名」而非数学记号，一律保留灰底。
    ".mp4", ".mkv", ".mov", ".avi", ".wav", ".mp3", ".srt",
    ".jpeg", ".jpg", ".gif", ".webp", ".bmp", ".npz", ".csv",
    "lower_bound", "upper_bound", # 带上参数的调用形式：`lower_bound(b, l)`
    "unordered_map", "lowbit",    # 带下划线的标识符，按子串留
    "sum(", "add(", "dfs(",       # 函数调用形式（裸词在 KEEP_EXACT 里）
    "\\", "https://", '"', "'",
    "if (", "for (", "while (",
    # 我们代码里真出现过的标识符：出现就说明这段是在对着代码说话
    "ch", "cnt", "id[", "id ", "best", "mn", "mx", "tot", "vis", "pos", "allZero",
    "cross", "gcd", "ptr", "d1", "d2", "d3", "d4",
]

# 3) 只要出现这些纯数学符号，一律去掉灰底（哪怕里面夹着代码名字）
MATH_MARKERS = "·∈≡×≈√⌈⌊∑⟺θ∞≠⊆∪∩∀∃≤≥"

# 4) 即便命中上面两条，这些也照样去掉（人工复核后钉的例外）
REMOVE_ANYWAY = {"V'"}

# 5) 纯区间记号（整段就是一个或几个 [..]），是数学不是数组下标 → 去掉
INTERVAL = re.compile(r"^\[[^\]]*\](,\s*\[[^\]]*\])*$")

# 5b) **老式下标**（x_i / cnt_i / a_j / s_k）→ 数学记号，去掉灰底。
#     形状特征：**基名很短（≤3 字符）+ 正好一个下划线 + 尾巴只有 1~2 个字母**。
#     两个条件缺一不可，都是实测撞出来的：
#       只看尾巴 → caustic_hi / caustic_lo 被误杀（hi/lo 在真代码里是常见后缀）；
#       只看基名 → flow_k / water_x 会被误杀。
#     这条必须排在 IDENT 前面 —— cnt_i 的基名 3 字符是能过 IDENT 的（实测漏过一次）。
SUBSCRIPT = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,2}_[a-z]{1,2}$")

# 6) 全大写下划线常量（含简单四则）→ 真代码：INT_MAX / LLONG_MAX / MOD = 998244353 /
#    STATUS_STACK_OVERFLOW（2026-09-30 刷老文件时这三类被误去掉灰底）
CAPS = re.compile(r"^[A-Z][A-Z0-9_]{2,}(\s*[-+*/<>!=]+\s*[0-9A-Za-z_]+)*$")

# 7) 标识符形状 → 真代码。2026-10-01 补（鎏金河 LED 交付说明）：
#    flow_reps / water_glow / bloom_str / grabCut / DepthFlow 这些配置项名、函数名
#    被整片误判成数学记号（一份 26 处里 24 处是误报）。
#    只认「一眼就是标识符」的形状：snake_case、camelCase，可带一层调用括号。
#    **裸单词故意不放过** —— 放过裸词就等于放过数学变量 n / x / s，那才是真该去灰底的。
IDENT = re.compile(r"^(?:"
                   r"_*[a-z][a-z0-9]{2,}(?:_[a-z0-9]+)+"               # snake_case
                   r"|_*[A-Za-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*"         # camelCase / CamelCase
                   r")(?:\([^()]*\))?$")
# 首段要求 ≥3 字符是刻意的：x_i / n_max / dp_i 这些是**老式下标**（数学记号，该去灰底），
# 而真实标识符的首段总是长词（flow_reps / water_glow / bloom_str）。

# 8) 带 - 或 / 的名字（路径片段 / 仓库名）：_work/ 、particular-drift 、a/b 。
#    加长度下限 4，免得把 l-r 这种区间数学记号也放过去。
#    2026-10-01 补：允许前导 /（/api/plan 这类协议路径，写接入手册时需要）。
SLASHNAME = re.compile(r"^/?_*[A-Za-z][A-Za-z0-9]*(?:[-/][A-Za-z0-9._/-]*)+$")

# 8b) 斜杠命令（2026-10-01 补：Claude Code 手册里 /status、/model 被误判成
#     数学记号）。单段小写、至少 2 个字母 —— 单字母 /x 不放过（那种更像除法）。
SLASHCMD = re.compile(r"^/[a-z][a-z0-9-]+$")

# 9) 点分名字：模块.函数（cv2.remap / np.clip / math.sqrt）→ 真代码。
#    两道保险挡住小数与公式：首字符必须是字母或下划线（3.14 不进）、
#    每个点后面也必须以字母或下划线开头（x.2 不进）。
DOTNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def keep(s):
    if s in REMOVE_ANYWAY:
        return False
    if any(c in s for c in MATH_MARKERS):
        return False
    if INTERVAL.match(s.strip()):
        return False
    if SUBSCRIPT.match(s.strip()):
        return False
    if s in KEEP_EXACT:
        return True
    t = s.strip()
    if CAPS.match(t) or IDENT.match(t) or DOTNAME.match(t) or SLASHCMD.match(t):
        return True
    if len(t) >= 4 and SLASHNAME.match(t):
        return True
    return any(t in s for t in KEEP_SUB)


def backups_repo(path):
    """改动前先存一份到备份仓 —— 原目录不留任何 .bak / .orig（备份规则）。

    实现统一在 `toolutil.backup_to_repo`（镜像子目录 + 秒级时间戳；
    同一秒里再备一次自动加 -2，不覆盖旧备份）。
    """
    return toolutil.backup_to_repo(path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    P = os.path.abspath(sys.argv[1])
    dry = ("dry" in sys.argv[2:])

    L = open(P, encoding="utf-8").read().split("\n")
    in_fence = toolutil.fence_mask(L, indent=False)

    will_keep, will_drop, in_table_hits = [], [], []

    out = []
    for i, l in enumerate(L):
        if in_fence[i] or "`" not in l:
            out.append(l)
            continue
        is_table = l.strip().startswith("|") and l.strip().endswith("|")

        def repl(m):
            s = m.group(1)
            if keep(s):
                will_keep.append((s, i + 1))
                return m.group(0)                     # 原样（连反引号）
            will_drop.append((s, i + 1))
            if "|" in s and is_table:                 # 表格里去掉反引号后竖线会撑破单元格
                in_table_hits.append((s, i + 1))
                s = s.replace("|", "\\|")
            return s

        out.append(re.sub(r"`([^`]+)`", repl, l))

    print("文件：%s" % P)
    print("代码块外反引号对：保留 %d 处 / 去掉 %d 处" % (len(will_keep), len(will_drop)))
    print()

    uniq_keep = sorted(set(s for s, _ in will_keep))
    print("=== 保留灰底的（去重 %d 种）===" % len(uniq_keep))
    for s in uniq_keep:
        print("   %s" % s)
    print()

    uniq_drop = sorted(set(s for s, _ in will_drop))
    print("=== 去掉灰底的（去重 %d 种）===" % len(uniq_drop))
    for s in uniq_drop:
        print("   %s" % s)
    print()

    if in_table_hits:
        print("=== 表格里要去掉反引号、且含竖线（需转义）===")
        for s, ln in in_table_hits:
            print("   行 %-5d %s" % (ln, s))
    else:
        print("=== 表格里没有「含竖线的反引号对」，不用额外转义 ===")

    # 去灰底后会不会意外变成 markdown 语法（星号/下划线/行首符号）
    risky = sorted(set(s for s, _ in will_drop if "*" in s or "_" in s))
    if risky:
        print("\n=== 注意：这些去掉灰底后含 * 或 _ ===")
        for s in risky:
            print("   %s" % s)

    new = "\n".join(out)

    # 逐行 diff 落盘，供人工复核
    d = []
    for i, (a, b) in enumerate(zip(L, out)):
        if a != b:
            d.append("@@ 行 %d" % (i + 1))
            d.append("- " + a)
            d.append("+ " + b)
    n_changed = sum(1 for a, b in zip(L, out) if a != b)
    if n_changed:
        diff_path = os.path.join(os.path.dirname(P), "unpair_diff.txt")
        open(diff_path, "w", encoding="utf-8").write("\n".join(d))
        print("\n改动行数：%d（diff 已写 %s）" % (n_changed, diff_path))
    else:
        print("\n改动行数：0（没动就不写 diff，不往你目录里留空文件）")

    # ---------- 校验 ----------
    print()
    print("--- 校验 ---")
    ok = []

    def fences(t):
        res, fl, buf = [], False, []
        for l in t.split("\n"):
            if l.startswith("```"):
                buf.append(l)
                fl = not fl
                if not fl:
                    res.append("\n".join(buf))
                    buf = []
                continue
            if fl:
                buf.append(l)
        return res

    orig = "\n".join(L)
    ok.append(("行数没变", len(L) == len(out)))
    ok.append(("代码块逐字未改", fences(orig) == fences(new)))
    ok.append(("``` 成对", new.count("```") % 2 == 0))
    ok.append(("没有 CRLF", "\r" not in new))
    # $ 号只看**代码块外、行内反引号外**的正文：老教程里的 bash `$(seq 1 1000)`、
    # PowerShell `$sw = ...` 都是合法代码，整篇扫会把整个文件挡下来（2026-09-30 实测被挡过）。
    outside = "\n".join(re.sub(r"`[^`]+`", "", l)
                        for i, l in enumerate(out) if not in_fence[i])
    ok.append(("没有 $ 号（正文）", "$" not in outside))
    ok.append(("<sub> 数量不变", new.count("<sub>") == orig.count("<sub>")))
    ok.append(("<sub>/</sub> 配平", new.count("<sub>") == new.count("</sub>")))
    ok.append(("反引号对计数一致", len(will_keep) + len(will_drop) ==
               sum(len(re.findall(r"`[^`]+`", l)) for i, l in enumerate(L) if not in_fence[i])))
    bad_tab = []
    for i, (a, b) in enumerate(zip(L, out)):
        if a.strip().startswith("|") and a.strip().endswith("|"):
            if a.count("|") != b.count("|"):
                bad_tab.append(i + 1)
    ok.append(("表格每行竖线数不变", not bad_tab))
    if bad_tab:
        print("      出问题的行：%s" % bad_tab)

    for n, v in ok:
        print("  %s %s" % ("[OK]" if v else "[失败]", n))

    if dry:
        print("\n（dry 模式，没有写文件）")
        return

    if not all(v for _, v in ok):
        print("\n★校验失败，原文件未改动。★")
        sys.exit(1)

    bak = backups_repo(P)
    print("\n已备份 → %s（%d 字节）" % (bak, os.path.getsize(bak)))

    open(P, "wb").write(new.encode("utf-8"))
    back = open(P, "rb").read().decode("utf-8")
    assert back == new, "写回后不一致！"
    print("已写回 %s（%d 字节 / %d 行）" % (P, os.path.getsize(P), len(back.split("\n"))))


if __name__ == "__main__":
    main()
