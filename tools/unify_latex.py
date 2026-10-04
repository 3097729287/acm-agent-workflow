# -*- coding: utf-8 -*-
r"""unify_latex.py —— 把题解正文里的 Unicode 数学统一成 LaTeX 行内公式 $...$

用法:
    python unify_latex.py <md 或目录> [dry|apply]
      dry   （默认）只打印逐行 diff 与警告，不改文件
      apply 改写文件（先按备份规则存一份到备份仓）

设计（2026-10-02 v2，为「8 份旧题解重排成 LaTeX」而写）:
  1. 保护段（行内代码 / 链接 / 裸 URL / HTML 注释 / HTML 标签）一个字不动；
     `<sub>` `<sup>` 例外——它们本身就是要转换的数学标记。
  2. 自由段先还原 &lt; &gt;（原文用实体避免被当 HTML 标签），再找触发点。
  3. 触发点 = 强数学信号；从触发点向左右吃 MATH_CHARS 得到极大小片段。
  4. balanced_trim 循环修剪两端（空白 / 连接符 / 悬空括号）。
  5. render：{ } 先占位 → <sub>/<sup> → √/sqrt → 符号映射 → ^/_ 括起
     → 结构后处理 → 还原 \{ \}。
  6. 「## 目录」节的表格行整行原样保留（2026-10-05 加）：目录表是结构化数据
     （第 3 列「考点」必须与状态表逐字一致的标准知识点串），不是散文——
     `DP[主]` 这类「缩写 + 下标括号」不该被当数学转成 `$DP$[主]`。
"""
import io
import os
import re
import sys

import toolutil                # 同目录：备份 / 围栏状态机的唯一实现

# ── 保护段（这些区间一个字不动） ──────────────────────────────────────
# HTML 标签只保护白名单里的已知标签（否则 "v<x 或" 这种「小于号+中文」会被误判成标签）
HTML_TAGS = (
    "a|abbr|audio|b|big|blockquote|body|br|caption|center|cite|code|dd|del|details|div|dl|"
    "dt|em|figcaption|figure|font|footer|h[1-6]|head|header|hr|html|i|iframe|img|ins|kbd|"
    "li|main|mark|nav|ol|p|path|pre|q|rp|rt|ruby|s|samp|section|small|source|span|strike|"
    "strong|style|summary|svg|table|tbody|td|tfoot|th|thead|tr|tt|u|ul|var|video"
)
PROT_PATTERNS = [
    r"`[^`]*`",                          # 行内代码
    r"\$\$.+?\$\$",                      # 同行的块公式 $$...$$（内容已是公式，不再转）
    r"\$[^$\n]*\$",                      # 已有的行内公式（保证脚本幂等）
    r"\[[^\[\]]*\]\([^()]*\)",           # markdown 链接 / 图片
    r"https?://\S+",                     # 裸 URL
    r"<!--.*?-->",                       # HTML 注释
    r"</?(?:" + HTML_TAGS + r")(?:\s[^<>]*)?/?>",   # HTML 标签（<sub>/<sup> 不在白名单）
    # 内容含中文的 <sub>/<sup>（如中文下标 Σ<sub>儿子 v</sub>）：中文会截断扩展，
    # 导致 <sub> 半截被吞 → 整对保留 HTML 原样（Typora 渲染 HTML 下标本来就没问题）
    r"<sub>[^<>]*[一-鿿][^<>]*</sub>",
    r"<sup>[^<>]*[一-鿿][^<>]*</sup>",
]
PROT_RES = [re.compile(p) for p in PROT_PATTERNS]

# ── 触发点 ────────────────────────────────────────────────────────────
TRIG_RE = re.compile(
    r"<sub>|<sup>"
    r"|[≤≥≠≈×÷·−≡∣∤∈∉∪∩⊂⊆⊃⊇∞⇒⇔⟹⟺⟶±↑↓←↔′Σ∑Π∏√⌊⌋⌈⌉∅]"
    r"|[⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ₀₁₂₃₄₅₆₇₈₉]"
    r"|\^"
    r"|[αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΨΦΩ]"
    r"|(?<![A-Za-z0-9])[a-z](?![A-Za-z0-9])"          # 小写单字母独立词
    r"|(?<![A-Za-z0-9])O\("                            # 复杂度 O(...)
    r"|(?<![A-Za-z])(?:log|sqrt|gcd|min|max)(?![A-Za-z])"   # 数学函数词
    r"|(?<=[A-Za-z0-9])\["                            # 标识符下标 a[i] / cnt[0]
    r"|\(\s*\d+\s*,\s*\d+\s*\)"                        # 坐标 (1,2)
)

# ── 数学字符（扩展时吸收） ────────────────────────────────────────────
MATH_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    " \t+-/^_=<>()[]{}'.,;:!%#"
    "≤≥≠≈×÷·−≡∣∤∈∉∪∩⊂⊆⊃⊇∞⇒⇔⟹⟺⟶±↑↓←↔′∅…→"
    "⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ₀₁₂₃₄₅₆₇₈₉"
    "αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΨΦΩ"
)

# ── 字符映射（片段内部） ──────────────────────────────────────────────
CHAR_MAP = {
    "≤": " \\le ", "≥": " \\ge ", "≠": " \\ne ", "≈": " \\approx ",
    "×": " \\times ", "÷": " \\div ", "·": " \\cdot ", "−": "-",
    "≡": " \\equiv ", "∣": " \\mid ", "∤": " \\nmid ", "∈": " \\in ",
    "∉": " \\notin ", "∪": " \\cup ", "∩": " \\cap ", "∞": " \\infty ",
    "⊂": " \\subset ", "⊆": " \\subseteq ", "⊃": " \\supset ", "⊇": " \\supseteq ",
    "⇒": " \\Rightarrow ", "⇔": " \\Leftrightarrow ",
    "⟹": " \\implies ", "⟺": " \\iff ",
    "Σ": " \\sum ", "∑": " \\sum ", "Π": " \\prod ", "∏": " \\prod ",
    "∅": " \\varnothing ",
    "⌊": " \\lfloor ", "⌋": " \\rfloor ", "⌈": " \\lceil ", "⌉": " \\rceil ",
    "→": " \\to ", "…": " \\ldots ",
    "⟶": " \\longrightarrow ", "±": " \\pm ",
    "↑": " \\uparrow ", "↓": " \\downarrow ",
    "←": " \\leftarrow ", "↔": " \\leftrightarrow ",
    "′": "'",
    "%": " \\% ", "#": " \\# ",
    "α": " \\alpha ", "β": " \\beta ", "γ": " \\gamma ", "δ": " \\delta ",
    "ε": " \\varepsilon ", "ζ": " \\zeta ", "η": " \\eta ", "θ": " \\theta ",
    "ι": " \\iota ", "κ": " \\kappa ", "λ": " \\lambda ", "μ": " \\mu ",
    "ν": " \\nu ", "ξ": " \\xi ", "π": " \\pi ", "ρ": " \\rho ",
    "σ": " \\sigma ", "τ": " \\tau ", "υ": " \\upsilon ", "φ": " \\varphi ",
    "χ": " \\chi ", "ψ": " \\psi ", "ω": " \\omega ",
    "Γ": " \\Gamma ", "Δ": " \\Delta ", "Θ": " \\Theta ", "Λ": " \\Lambda ",
    "Ξ": " \\Xi ", "Ψ": " \\Psi ", "Φ": " \\Phi ", "Ω": " \\Omega ",
}
FUNC_MAP = [
    (r"(?<![A-Za-z])log(?![A-Za-z])", r"\\log "),
    (r"(?<=[a-z0-9])log(?![A-Za-z])", r" \\log "),   # klog -> k \log
    (r"(?<![A-Za-z])gcd(?![A-Za-z])", r"\\gcd "),
    (r"(?<![A-Za-z])min(?![A-Za-z])", r"\\min "),
    (r"(?<![A-Za-z])max(?![A-Za-z])", r"\\max "),
    (r"(?<![A-Za-z])mod(?![A-Za-z])", r"\\bmod "),
]

JUNK = set("+-*/^_=,;")           # 片段两端可丢的连接符（信息保全：< > . ' % # 不丢）
# 弱触发：孤立就无意义的符号（需要片段里至少有字母数字才值得包 $）
WEAK_TRIG = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ₀₁₂₃₄₅₆₇₈₉\^]")
ALNUM_RE = re.compile(r"[0-9A-Za-z]")
# 片段左侧允许出现的"块标记前文"（列表符/引用符/标题符/空白/编号本身）
ALLOWED_BEFORE = re.compile(r"[\s\-+*>#0-9.]*$")
# 字母类命令（希腊字母等）：后跟非字母数字时去掉尾随空格（\tau (v) -> \tau(v)）
SYM_CMDS = (r"\\(?:alpha|beta|gamma|delta|varepsilon|zeta|eta|theta|iota|kappa|lambda|"
            r"mu|nu|xi|pi|rho|sigma|tau|upsilon|varphi|chi|psi|omega|Gamma|Delta|Theta|"
            r"Lambda|Xi|Psi|Phi|Omega|ldots|infty|varnothing|lfloor|rfloor|lceil|rceil)")
ALNUM = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
OPEN = {"(": ")", "[": "]", "{": "}"}
PRIV_L = "\ue000"                 # 原文 { 的占位符
PRIV_R = "\ue001"                 # 原文 } 的占位符


def find_protected(line):
    spans = []
    for r in PROT_RES:
        for m in r.finditer(line):
            spans.append((m.start(), m.end()))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def expand(s, a, b):
    """从 [a,b) 向左右吃 MATH_CHARS。"""
    n = len(s)
    while a > 0 and s[a - 1] in MATH_CHARS:
        a -= 1
    while b < n and s[b] in MATH_CHARS:
        b += 1
    return a, b


def balanced_trim(s, a, b):
    """循环修剪片段两端：空白 → 悬空连接符 → 悬空括号，直到稳定。"""
    changed = True
    while changed and a < b:
        changed = False
        while a < b and s[a] in " \t":
            a += 1
            changed = True
        while b > a and s[b - 1] in " \t":
            b -= 1
            changed = True
        # 右端悬空连接符
        if b > a and s[b - 1] in JUNK:
            b -= 1
            changed = True
            continue
        # 左端悬空连接符（"+-" 后紧跟字母数字 = 正负号，保留）
        if a < b and s[a] in JUNK:
            if s[a] in "+-" and a + 1 < b and s[a + 1] in ALNUM:
                pass
            else:
                a += 1
                changed = True
                continue
        # 右端多余的左括号（被中文截断留下的孤立 "{"，如 "w<sub>i</sub> = #{组"）
        if b > a and s[b - 1] in OPEN:
            seg = s[a:b]
            ch = s[b - 1]
            if seg.count(ch) > seg.count(OPEN[ch]):
                b -= 1
                changed = True
                continue
        # 右端多余的右括号
        if b > a and s[b - 1] in OPEN.values():
            seg = s[a:b]
            ch = s[b - 1]
            src = [k for k, v in OPEN.items() if v == ch][0]
            if seg.count(src) < seg.count(ch):
                b -= 1
                changed = True
                continue
        # 左端多余的左括号
        if a < b and s[a] in OPEN:
            seg = s[a:b]
            if seg.count(s[a]) > seg.count(OPEN[s[a]]):
                a += 1
                changed = True
                continue
        # 左端多余的右括号（被中文截断留下的孤立 ")"，如 "f(新) = 2 × c"）
        if a < b and s[a] in OPEN.values():
            seg = s[a:b]
            ch = s[a]
            src = [k for k, v in OPEN.items() if v == ch][0]
            if seg.count(src) < seg.count(ch):
                a += 1
                changed = True
                continue
    # 最终仍不平衡（如 "O(n + 中文)" 里括号被中文截断）→ 放弃该片段
    seg = s[a:b]
    for o, c in (("(", ")"), ("[", "]"), ("{", "}")):
        if seg.count(o) != seg.count(c):
            return None
    return a, b


def merge_ivs(ivs):
    ivs.sort()
    out = []
    for a, b in ivs:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


SUP_MAP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
           "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "ⁿ": "n"}
SUB_MAP = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5",
           "₆": "6", "₇": "7", "₈": "8", "₉": "9"}
SUP_RE = re.compile("[" + "".join(SUP_MAP) + "]+")
SUB_RE = re.compile("[" + "".join(SUB_MAP) + "]+")


def map_symbols(s):
    # 连续上标/下标字符合并成一个 ^{} / _{}（10¹⁸ -> 10^{18}）
    s = SUP_RE.sub(lambda m: "^{" + "".join(SUP_MAP[c] for c in m.group(0)) + "}", s)
    s = SUB_RE.sub(lambda m: "_{" + "".join(SUB_MAP[c] for c in m.group(0)) + "}", s)
    for k, v in CHAR_MAP.items():
        s = s.replace(k, v)
    for pat, rep in FUNC_MAP:
        s = re.sub(pat, rep, s)
    s = s.replace("...", " \\ldots ")
    s = re.sub(r",(?=\S)", ", ", s)
    s = re.sub(r"[ \t]+([,;])", r"\1", s)      # "\ldots ," 里逗号前的空格清掉
    s = re.sub(r"[ \t]+", " ", s)
    return s


def _inner(x):
    """<sub>/<sup>/√ 的参数：还原实体后做符号映射。"""
    x = x.replace("&lt;", "<").replace("&gt;", ">")
    return map_symbols(x).strip()


def render(s):
    """把一个片段转成 $...$ 形式；失败返回 None。"""
    if "$" in s:
        return None
    s = s.replace("&lt;", "<").replace("&gt;", ">")
    # 1) 原文花括号占位（最后还原成 \{ \}，避免被 KaTeX 当分组符吃掉）
    s = s.replace("{", PRIV_L).replace("}", PRIV_R)
    # 2) <sub>/<sup>
    s = re.sub(r"<sub>(.*?)</sub>", lambda m: "_{" + _inner(m.group(1)) + "}", s)
    s = re.sub(r"<sup>(.*?)</sup>", lambda m: "^{" + _inner(m.group(1)) + "}", s)
    s = s.replace("<sub>", "").replace("</sub>", "")      # 兜底：未闭合残壳
    s = s.replace("<sup>", "").replace("</sup>", "")
    # 3) √ / sqrt 统一成 \sqrt{...}
    s = re.sub(r"(?:√|(?<![A-Za-z])sqrt)\s*\(([^()]*)\)",
               lambda m: "\\sqrt{" + _inner(m.group(1)) + "}", s)
    s = re.sub(r"(?:√|(?<![A-Za-z])sqrt)\s*([A-Za-z0-9]+)",
               lambda m: "\\sqrt{" + _inner(m.group(1)) + "}", s)
    # 4) 符号映射
    s = map_symbols(s)
    # 5) ^ / _ 后多字符加花括号；单字符花括号归一
    s = re.sub(r"\^(\([^()]*\))", lambda m: "^{" + m.group(1)[1:-1] + "}", s)
    s = re.sub(r"\^([A-Za-z0-9]{2,})", r"^{\1}", s)
    s = re.sub(r"_([A-Za-z0-9]{2,})", r"_{\1}", s)
    s = re.sub(r"([_^])\{([A-Za-z0-9])\}", r"\1\2", s)
    # 6) 结构后处理（注意：\log n 这类"命令+空格+变量"不能去空格）
    s = re.sub(r"(\\(?:sum|prod|int))\s+_", r"\1_", s)
    s = re.sub(r"(\\(?:log|min|max|gcd))\s+_", r"\1_", s)
    s = re.sub(r"(\\(?:log|min|max|gcd|bmod))\s+(?=[(\[])", r"\1", s)
    # 7) 方/圆括号内侧多余空格
    s = re.sub(r"([\[\(])\s+(?=\S)", r"\1", s)
    s = re.sub(r"(?<=\S)\s+([\]\)])", r"\1", s)
    # 字母类命令后跟非字母数字：去掉多余空格（\tau (v) -> \tau(v)；\le 2 不受影响）
    s = re.sub(r"(" + SYM_CMDS + r") +(?=[^\w])", r"\1", s)
    # 8) 还原花括号
    s = s.replace(PRIV_L, "\\{").replace(PRIV_R, "\\}")
    s = s.strip()
    if not s:
        return None
    return "$" + s + "$"


def convert_freetext(s, stats):
    if "&lt;" in s or "&gt;" in s:
        stats["lt"] += 1
    s = s.replace("&lt;", "<").replace("&gt;", ">")
    triggers = list(TRIG_RE.finditer(s))
    if not triggers:
        return s
    ivs = []
    for m in triggers:
        a, b = expand(s, m.start(), m.end())
        # 代码运算符（g++ / i--）→ 放弃。放在 trim 前：否则尾部 "++" 会被当连接符剪掉，检查不到
        if "++" in s[a:b] or "--" in s[a:b]:
            continue
        # 含双下划线（C 标识符 __builtin_clzll）→ 放弃，别当数学转
        if "__" in s[a:b]:
            continue
        t = balanced_trim(s, a, b)
        if t is None:
            continue
        a, b = t
        if a >= b:
            continue
        # 行首块标记（有序列表 "5." / 引用 ">" / 标题 "#"）被吸进片段 → 反复切出去
        while ALLOWED_BEFORE.match(s[:a]):
            m2 = re.match(r"(?:\d+\.|[>#]+)[ \t]+(?=[0-9A-Za-z(\\])", s[a:b])
            if not m2:
                break
            a += m2.end()
        if a >= b:
            continue
        # 数据罗列/计时（"0.005 s"、"A 5 ms"）→ 放弃
        if re.search(r"[0-9] [a-zA-Z]{1,2}$", s[a:b]):
            continue
        # 输出格式词/大写词打头接运算符（"Yes + n-1"、"MOD - w"）→ 放弃
        if re.match(r"[A-Z][a-zA-Z]+ [+\-] ", s[a:b]):
            continue
        # 孤立上标/下标/^（片段里没有任何字母数字）→ 放弃（"值域²" 不该变 "值域$^2$"）
        if WEAK_TRIG.search(m.group(0)) and not ALNUM_RE.search(s[a:b]):
            continue
        ivs.append((a, b))
    ivs = merge_ivs(ivs)
    out, prev = [], 0
    for a, b in ivs:
        frag = s[a:b]
        new = render(frag)
        if new is None:
            out.append(s[prev:b])
            if len(stats["failed"]) < 20:
                stats["failed"].append(frag)
        else:
            out.append(s[prev:a])
            out.append(new)
            stats["frags"] += 1
        prev = b
    out.append(s[prev:])
    return "".join(out)


def convert_line(line, stats):
    spans = find_protected(line)
    out, prev = [], 0
    for a, b in spans:
        out.append(convert_freetext(line[prev:a], stats))
        out.append(line[a:b])
        prev = b
    out.append(convert_freetext(line[prev:], stats))
    return "".join(out)


def process(text, stats):
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=True)   # 代码块整块原样保留
    out, dblock, in_toc = [], False, False
    for i, ln in enumerate(lines):
        if mask[i]:
            out.append(ln)
            continue
        # 「## 目录」表格行：结构化数据，整行原样保留（见文件头设计第 6 条）
        s = ln.strip()
        if s == "## 目录":
            in_toc = True
            out.append(ln)
            continue
        if in_toc:
            if not s or s.startswith("|"):    # 空行（标题与表格之间）与表格行原样过
                out.append(ln)
                continue
            in_toc = False              # 其他非空行 = 目录节结束
        # 跨行 $$...$$ 块公式：整块原样保留（公式内容不该再被转）。
        # 单行内 `$$` 出现奇数次 = 块的开始 / 结束；同行 $$...$$ 由 PROT 段保护。
        if ln.count("$$") % 2:
            dblock = not dblock
            out.append(ln)
            continue
        if dblock:
            out.append(ln)
            continue
        out.append(convert_line(ln, stats))
    return "\n".join(out)


def backup(path):
    """改动前原件入备份仓（实现统一在 toolutil.backup_to_repo）。"""
    return toolutil.backup_to_repo(path)


def walk(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for r, _, fs in os.walk(p):
                for f in fs:
                    if f.endswith(".md"):
                        out.append(os.path.join(r, f))
        else:
            out.append(p)
    return out


def main(argv):
    mode = "dry"
    files = []
    for a in argv:
        if a in ("dry", "apply"):
            mode = a
        else:
            files.append(a)
    for path in walk(files):
        text = io.open(path, encoding="utf-8").read()
        stats = {"frags": 0, "lt": 0, "failed": []}
        new = process(text, stats)
        old_lines = text.split("\n")
        new_lines = new.split("\n")
        nchg = 0
        print("=" * 78)
        print("%s" % path)
        print("  转换 %d 个数学片段；还原 &lt;/&gt; %d 行；渲染失败 %d 个片段"
              % (stats["frags"], stats["lt"], len(stats["failed"])))
        if new.count("$") % 2:
            print("  !!! 警告：转换后 $ 总数为奇数（%d），可能有落单的 $" % new.count("$"))
        for f in stats["failed"]:
            print("  !!! 未转换片段: %r" % f)
        print("=" * 78)
        for i, (o, n) in enumerate(zip(old_lines, new_lines), 1):
            if o != n:
                nchg += 1
                if mode == "dry":
                    print("L%d  - %s" % (i, o))
                    print("     + %s" % n)
        print("→ 共 %d 行有改动" % nchg)
        if mode == "apply":
            if new != text:
                bak = backup(path)
                with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)
                print("→ 已改写，备份：%s" % bak)
            else:
                print("→ 无改动，未写")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
