# -*- coding: utf-8 -*-
r"""
check_solution —— 题解 md 交付前的自检器
==========================================

    python check_solution.py <题解.md> [<题解2.md> ...] [--no-compile] [--quiet]

非题解类文档（规划 / 调研 md）加 `--no-record`：跳过第 6 / 9 / 10 / 11 项
（这些是「整场题解」专有口径）。

一趟查完 17 项，**每项都要给出原文片段**（只报「有/无」的检查不合格，
口径一歪差异看不出来，见《数学 LaTeX》）：

  1.  `$` **配对**：正文（去代码块、去行内代码）里成对的 `$...$` 抠掉后还剩
      孤立的 `$` / 未闭合的 `$$`。2026-10-02 口径**反转**：数学**应当**写
      LaTeX（Typora 已勾「内联公式」），以前报「有 $」，现在报「$ 不配对」
  1b. 反斜杠命令落在 `$` **外**（漏包）：`\le`、`\times` 这些出现在公式外面的
      —— 用的是**无歧义命令表**，不会把 Windows 路径 `牛客143\DSH`、`\crosscheck.py`
         误判成残留（详见《工具链》的坑表）
  2.  **LaTeX 完整度**：跑一遍 unify_latex 的转换逻辑（判定与转换器**同一套**），
      还有可转的片段 = 没跑过转换、或转换后被手改回去了。取代原「老式下标 a_i」
  3.  数学记号残留灰底：判定直接调用 unpair_ticks.keep()，跟转换器**同一套规则**，
      免得检查与转换各走各的
  4.  `<sub>` 被二次转义成 `&lt;sub&gt;`（常见坑）
  4b. 正文没有繁体字（交付 md 一律简体；长文手误高发，肉眼扫容易漏）
  5.  代码块逐个**真编译**（交付前必须做的那一次：验的是 md 里的代码，
      不是工作目录里的另一份）
  6.  实测记录在不在（**纯文字 ≤6 行，不用表格、不用 `- ` 列表**；
      2026-10-02 从 ≤3 行放宽，行数超限/表格/列表都当场报），
      里面有没有「约/大概/左右」这种不许出现的词
  6b. 记录里如实写了「未验证」（没跑的档就该这么写）
  7.  行尾一致且不是 CRLF 混排；编码 UTF-8 **无 BOM**
  7b. 表格单元格里别摊长裸 URL
  8.  表格行 `|` 数一致（不渲染竖线的表格会塌）
  9.  题解的**节白名单**（目录 / 实测记录 / `<字母>. <题名>` + 题内七种小节）
  10. 目录表列头必须是 `题号 | 题名 | 考点 | 难度`，每行四格
  11. 题内 `###` 的**顺序**（题意 → 从零讲 → 手算 → 思路 → 参考代码 → 复杂度 →
      易错点）与四项必写（题意 / 思路 / 参考代码 / 易错点）
  16. 公式落在**缩进代码块**里（行首 ≥4 空格、前面是空行的独立行）——
      Markdown 会把它当代码块，里面的 `$...$` 不渲染、原样显示
      （2026-10-02 实测：Round 123 有 8 处这样的「独立公式行」）
  17. **KaTeX 全量渲染**：每个公式（含跨行 `$$` 块）真渲染一遍 —— 公式
      **内部**的命令拼错 / 花括号不配，第 1 / 1b / 2 项都不看公式内部，
      只有它能抓（2026-10-02 加；管线 = extract_math + node katex_check.js）

注意：**裸的 Unicode 数学符号（≤ ≥ ≈ × 等）不查**——它们要么是中文叙述里的
连接符（「A → B」），要么是 unify_latex 有意放弃的片段（中文截断 / 括号不平衡），
保留 Unicode 在 Typora 里本来就能正常显示。真要拦的「该转没转」由第 2 项
（直接跑转换器本尊）负责，比列符号表准。

退出码 0 = 全是「通过」或「不适用」；1 = 有「问题」。
"""

import argparse
import json
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil                                       # 围栏状态机，跟各转换器共用
try:
    from unpair_ticks import keep as keep_ticks      # 灰底判定，跟转换器共用
except Exception:                                     # pragma: no cover
    def keep_ticks(s):
        return True
try:
    import unify_latex as _U                          # 第 2 项：LaTeX 完整度，
except Exception:                                     # 判定与转换器同一套
    _U = None
try:
    import extract_math as _EM                        # 第 17 项：公式抽取，
except Exception:                                     # 与 KaTeX 验证管线同一套
    _EM = None

# 无歧义 LaTeX 命令表：只列**绝不可能是 Windows 路径片段**的。
# `\DSH`、`\crosscheck`、`\max_*.in` 这类一概不进表，否则天天误报。
LATEX_CMDS = [
    "le", "le ", "leq", "leqq", "ge", "geq", "geqq", "neq", "ne ",
    "times", "cdot", "div", "pm", "mp", "frac", "tfrac", "dfrac",
    "sqrt", "lfloor", "rfloor", "lceil", "rceil", "left", "right",
    "begin", "end", "text", "mathrm", "mathbf", "mathit", "texttt",
    "operatorname", "sum", "prod", "int", "infty", "pmod", "bmod",
    "blacksquare", "qquad", "quad", "hspace", "overline", "underline",
    "underbrace", "overbrace", "binom", "cases", "equiv", "approx",
    "subseteq", "supseteq", "cup", "cap", "emptyset", "forall", "exists",
    "to", "rightarrow", "Rightarrow", "land", "lor", "lnot", "mid",
    "alpha", "beta", "gamma", "theta", "lambda", "pi ", "sigma",
]
LATEX_RE = re.compile(r"\\(" + "|".join(re.escape(c) for c in LATEX_CMDS) + r")(?![a-zA-Z])")
TICKS_RE = re.compile(r"`([^`\n]+)`")
# 高频繁体字：交付 md 一律简体，繁体出现基本=手误（或误引），报出来人工确认。
# 只列简繁不同形、简体语境下几乎不会正当出现的字；「乾/乾隆、台/臺」这类同形争议字不列。
TRAD_RE = re.compile(
    "[時個來這說對沒樣點裡邊開關產業學國會從們後還過進發現實際頭總體區問題見讓"
    "東華經濟為與專嗎麼該話語讀寫聽習萬億車數據網長內兩課錢銀場觀標書間議選舉"
    "處減買賣員權責戰軍農醫藥證認識記憶論談講圖館廠燈電話鍾髮裏爲]")


class Report:
    def __init__(self):
        self.items = []          # (状态, 名称, [细节行])

    def add(self, status, name, details=()):
        self.items.append((status, name, list(details)))

    def ok(self, n, name, d=()):
        self.add("通过", n + " " + name, d)

    def bad(self, n, name, d=()):
        self.add("问题", n + " " + name, d)

    def na(self, n, name, d=()):
        self.add("不适用", n + " " + name, d)

    @property
    def failed(self):
        return any(st == "问题" for st, _, _ in self.items)


def split_blocks(text):
    """把 md 拆成 [(是不是代码块, 内容, 起始行号)]，代码块外的才算正文。"""
    out, pos, lineno = [], 0, 1
    for m in re.finditer(r"^```([^\n]*)\n(.*?)^```\s*$", text, re.S | re.M):
        head = text[pos:m.start()]
        if head:
            out.append((False, head, lineno))
        fence = m.group(1).strip().lower()
        out.append((True, m.group(2), lineno + head.count("\n") + 1,
                    fence))
        lineno += text[pos:m.end()].count("\n")
        pos = m.end()
    tail = text[pos:]
    if tail:
        out.append((False, tail, lineno))
    return out


def prose_only(text):
    """把代码块的内容换成等行数的空行，返回**行号不变**的正文。

    正文类检查（LaTeX / 下标 / 灰底 / 二次转义）必须只看代码块外的部分：
    代码里写 `a_i`、`sum(a_i)`、注释里的 `\\frac` 都是合法的，对着全篇查会漫天误报
    （实测在一份真题解上误报 22 处，全在代码块和 // 注释里）。
    """
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=True)
    out = ["" if mask[i] else ln for i, ln in enumerate(lines)]
    return "\n".join(out)


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def snippet(text, idx, width=70):
    a = max(0, idx - width // 2)
    b = min(len(text), idx + width // 2)
    s = text[a:b].replace("\n", "⏎")
    return ("..." if a else "") + s + ("..." if b < len(text) else "")


def strip_inline_code(text):
    """行内代码 `...` 换成等长空格（行号、列号都不变）。"""
    return re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)


def strip_math(text):
    """把**成对**的公式换成等长空格（行号列号不变）：先 `$$...$$` 再 `$...$`。

    抠剩的 `$` 就是配不上对的；`(?<!\\)` 放过字面 `\\$`；行内公式要求内容
    **非空**（`+`），否则 `$$` 两个美元会被当成一个空公式抠掉、查不出未配对。
    """
    s = re.sub(r"\$\$.*?\$\$", lambda m: " " * len(m.group(0)), text, flags=re.S)
    return re.sub(r"(?<!\\)\$[^$\n]+\$", lambda m: " " * len(m.group(0)), s)


def check_latex(text, rep):
    """第 1 项：`$` 配对；第 1b 项：反斜杠命令落在 `$` 外（漏包）。

    2026-10-02 起数学一律写 LaTeX（Typora 勾了「内联公式」，见《数学 LaTeX》），
    本项口径与旧版**相反**：旧版报「有 $ 残留」，新版报「$ 不配对 / 没包进 $」。
    """
    bare = strip_math(strip_inline_code(text))
    orig = text.split("\n")
    hits = []
    for i, ln in enumerate(bare.split("\n"), 1):
        if "$$" in ln:
            hits.append("  第 %d 行：`$$` 没配对（行内公式用 `$...$`）：%s"
                        % (i, orig[i - 1][:80]))
        ln = ln.replace("$$", "  ")
        n = ln.count("$")
        if n % 2:
            hits.append("  第 %d 行：%d 个 `$` 配不上对：%s"
                        % (i, n, orig[i - 1][:80]))
    n_pair = (text.count("$") - bare.count("$")) // 2
    if hits:
        rep.bad("1.", "`$` 不配对（%d 处）" % len(hits),
                ["  成对的 $...$ 会被抠掉再数，剩下的就是配不上的"] + hits[:8])
    else:
        rep.ok("1.", "`$...$` 全部配对（%d 个公式段）" % n_pair)

    hits = []
    for m in LATEX_RE.finditer(bare):
        hits.append("  第 %d 行：\\%s 落在 $ 外：%s"
                    % (line_of(bare, m.start()), m.group(1).strip(),
                       snippet(text, m.start())))
    if hits:
        rep.bad("1b.", "反斜杠命令在 `$` 外（漏包，%d 处）" % len(hits), hits[:8])
    else:
        rep.ok("1b.", "没有 `$` 外的 LaTeX 命令")


# ── unify_latex 只跑一次（2026-10-02 加） ──────────────────────────────────
# 第 2 项与第 17 项都要「先过一遍 unify」，原本各跑一次 process；同一份文本
# 结果必然相同，缓存起来两处共用。键 = 文本内容哈希（prose 与 text 是两份）。
_UNIFY_CACHE = {}


def _unify_once(text):
    """跑一次 `unify_latex.process`，同文本复用。返回 (new, err)。"""
    if _U is None:
        return None, None
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key not in _UNIFY_CACHE:
        try:
            _UNIFY_CACHE[key] = (
                _U.process(text, {"frags": 0, "lt": 0, "failed": []}), None)
        except Exception as e:                   # 转换器自己炸了要报出来，别静默
            _UNIFY_CACHE[key] = (None, e)
    return _UNIFY_CACHE[key]


def check_latex_done(text, rep):
    """第 2 项：LaTeX 完整度 —— 还有没有「能转却没转」的片段。

    判定 = 直接跑 unify_latex 的转换（纯函数、不落盘），同 unpair_ticks 的
    思路：检查与转换**同一套规则**，不各走各的。取代旧版第 2 项
    「老式下标 a_i」（LaTeX 口径下已无意义）。
    """
    if _U is None:
        rep.na("2.", "unify_latex.py 不在同目录，跳过 LaTeX 完整度检查")
        return
    new, err = _unify_once(text)
    if err is not None:
        rep.bad("2.", "LaTeX 完整度检查没跑起来：%r" % err)
        return
    if new == text:
        rep.ok("2.", "没有可再转的片段（与 unify_latex 同口径，试跑 0 段改动）")
        return
    o, n = text.split("\n"), new.split("\n")
    hits = []
    if len(o) == len(n):
        for i, (a, b) in enumerate(zip(o, n), 1):
            if a != b:
                hits.append("  第 %d 行：\n     改前 %s\n     改后 %s"
                            % (i, a[:96], b[:96]))
    else:
        hits.append("  （行数 %d -> %d 会变，跑 apply 看 diff）" % (len(o), len(n)))
    rep.bad("2.", "还有 %d 行可转成 LaTeX（跑 `python unify_latex.py <md> apply`）"
            % len(hits), hits[:6])


def check_ticks(text, rep):
    """正文里有没有「该去灰底却还带着反引号」的段。判定跟转换器同一套。"""
    hits = []
    for m in TICKS_RE.finditer(text):
        s = m.group(1)
        if not keep_ticks(s):
            ln = line_of(text, m.start())
            hits.append("  第 %d 行：`%s` -> 应去掉反引号" % (ln, s))
    if hits:
        rep.bad("3.", "数学记号残留灰底", ["  共 %d 处（跑 unpair_ticks.py 可批量去掉）"
                                       % len(hits)] + hits[:20])
    else:
        rep.ok("3.", "数学记号没带灰底")


def check_sub_escape(text, rep):
    hits = ["  第 %d 行：%s" % (line_of(text, m.start()), snippet(text, m.start()))
            for m in re.finditer(r"&lt;sub&gt;|&lt;/sub&gt;", text)]
    if hits:
        rep.bad("4.", "<sub> 被二次转义成 &lt;sub&gt;", hits[:5])
    else:
        rep.ok("4.", "<sub> 没被二次转义")


def check_traditional(text, rep):
    """正文里的繁体字。2026-10-01 实测：规划长文里手误写出「時」只有肉眼看出来，
    非题解文档也跑本脚本，所以放在这里拦。误报（如引用繁体原文）由人看一眼放行。"""
    hits = ["  第 %d 行：%s" % (line_of(text, m.start()), snippet(text, m.start()))
            for m in TRAD_RE.finditer(text)]
    if hits:
        rep.bad("4b.", "正文有繁体字（交付 md 一律简体）",
                ["  共 %d 处" % len(hits)] + hits[:10])
    else:
        rep.ok("4b.", "无繁体字")


def check_compile(text, rep, tmpdir):
    CPP_FENCES = ("cpp", "c++", "cc", "")     # 空 fence 也当 cpp 试一把
    blocks = []
    for part in split_blocks(text):
        if not part[0]:
            continue
        code, ln = part[1], part[2]
        fence = part[3] if len(part) > 3 else ""
        if fence in CPP_FENCES:
            blocks.append((code, ln, fence))
    if not blocks:
        rep.na("5.", "没找到 cpp 代码块，跳过编译")
        return
    bad, okn = [], 0
    for i, (code, ln, fence) in enumerate(blocks, 1):
        if not re.search(r"int\s+main\s*\(", code):
            continue
        p = os.path.join(tmpdir, "blk%d.cpp" % i)
        exe = os.path.join(tmpdir, "blk%d.exe" % i)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        r = subprocess.run(["g++", "-O2", "-std=c++17", "-Wall", "-Wextra",
                            "-o", exe, p],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            bad.append("  第 %d 个代码块（md 第 %d 行起）编译失败：\n%s"
                       % (i, ln, "\n".join("      " + x for x in
                                           (r.stderr or "").strip().split("\n")[:12])))
        else:
            okn += 1
            if (r.stderr or "").strip():
                bad.append("  第 %d 个代码块编译有警告：\n%s"
                           % (i, "\n".join("      " + x for x in
                                           r.stderr.strip().split("\n")[:6])))
    warn = [x for x in bad if "警告" in x]
    err = [x for x in bad if "警告" not in x]
    if err:
        rep.bad("5.", "代码块编译（%d 个通过，%d 个失败）" % (okn, len(err)), err)
    elif warn:
        rep.add("通过", "5. 代码块全部编译通过（有警告，建议看一眼）", warn)
    else:
        rep.ok("5.", "代码块全部编译通过，无警告（共 %d 个）" % okn)


def check_record(text, rep):
    m = re.search(r"^#{2,4}\s*.*实测记录.*$", text, re.M)
    if not m:
        rep.bad("6.", "没找到「实测记录」小节",
                ["  03 要求文末有实测记录（实跑过哪几档 / 各组数 / 极限耗时）",
                 "  2026-09-30 起写成 ≤3 行**文字**即可（表格也认，但不推荐）"])
        return
    # 记录小节的窗口：到下一个同级或更高级标题为止，别溢到后面几节去
    nxt = re.search(r"^#{1,4}\s", text[m.end():], re.M)
    seg_end = m.end() + (nxt.start() if nxt else len(text) - m.end())
    seg = text[m.start():seg_end]
    BASE = m.start()          # seg 里的偏移 + BASE 才是全文偏移。
                              # 忘了加 BASE 就会报出一个根本不存在的行号
                              # （实测报过「第 14 行」，真凶在第 1630 行）。
    # 必须带上数字一起匹配。只查「约」会命中题名（「小月的对局」里就有个「约」），
    # 实测第一次跑就误报了——只报「有/无」的检查不合格，得让词和数一起出现才算。
    FUZZY_RE = re.compile(r"(约\s*[0-9０-９]|大概\s*[0-9０-９]|大约\s*[0-9０-９]"
                          r"|[0-9０-９]\s*(约|左右|上下|前后))")
    fuzzy = list(FUZZY_RE.finditer(seg))
    hits = ["  第 %d 行：%s" % (line_of(text, BASE + x.start()),
                               snippet(text, BASE + x.start()))
            for x in fuzzy]
    if fuzzy:
        rep.bad("6.", "实测记录里有模糊数（数字必须来自实跑输出）",
                ["  共 %d 处，如：%s" % (len(fuzzy),
                                        "、".join(x.group(0) for x in fuzzy[:5]))]
                + hits[:5])
    else:
        lines = [l for l in seg.split("\n")[1:]      # [0] 是标题行本身
                 if l.strip() and not l.strip().startswith("#")]
        rows = len([l for l in lines if l.strip().startswith("|")])
        bullets = [l for l in lines
                   if re.match(r"^\s*([-*+]|\d+[.)、])\s", l)]
        problems = []
        if rows:
            problems.append("  第 %d 行：用了表格（%d 行）——实测记录一律纯文字段落"
                            % (line_of(text, BASE + seg.find("|")), rows))
        if bullets:
            problems.append("  第 %d 行：用了列表——规范是纯文字段落，不用 `- `"
                            % line_of(text, BASE + seg.find(bullets[0])))
        if len(lines) > 6:
            problems.append("  正文 %d 行超过 6 行上限（2026-10-02 起；"
                            "压成 ≤6 行纯文字）" % len(lines))
        if problems:
            rep.bad("6.", "实测记录不合规范（%d 处）" % len(problems), problems)
        elif lines:
            rep.ok("6.", "实测记录小节在（文字 %d 行，≤6 行合规）" % len(lines), [])
        else:
            rep.bad("6.", "实测记录小节是空的（没写实跑过哪几档）", [])
    if "未验证" in seg:
        rep.add("通过", "6b. 记录里如实写了「未验证」（没跑的档就该这么写）", [])


def check_bytes(path, rep):
    b = open(path, "rb").read()
    if b.startswith(b"\xef\xbb\xbf"):
        rep.bad("7.", "文件带 UTF-8 BOM",
                ["  用户查看器可能把 BOM 显示成乱码，去掉"])
    else:
        rep.ok("7.", "无 BOM")
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    if crlf and lf:
        rep.bad("7b.", "行尾混排（CRLF %d 行 / 纯 LF %d 行）" % (crlf, lf),
                ["  混排会让 diff 与脚本锚点都不可靠；统一成一种"])
    elif crlf:
        rep.add("通过", "7b. 行尾统一 CRLF（%d 行）" % crlf, [])
    else:
        rep.ok("7b.", "行尾统一 LF（%d 行）" % lf)


def check_tables(text, rep):
    """按**连续的表格块**分别检查，不是全文件一起比。

    一份题解里有好几张表，列数本来就不一样；全局比会得到"5 种 | 数"这种
    什么也没说明的结论。真正要抓的是：**同一张表里某一行少了或多了竖线**
    （内容里混进未转义的 `|` 就会撑破单元格）。
    """
    rows = []
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=True)
    for i, ln in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        s = ln.strip()
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 3:
            rows.append((i, s.count("|"), s))

    blocks, cur = [], []
    for r in rows:
        if cur and r[0] != cur[-1][0] + 1:
            blocks.append(cur)
            cur = []
        cur.append(r)
    if cur:
        blocks.append(cur)
    if not blocks:
        rep.na("8.", "没找到表格")
        return

    weird = []
    for b in blocks:
        from collections import Counter
        cnt = Counter(n for _, n, _ in b)
        if len(cnt) > 1:
            for k in range(1, len(b)):
                if b[k][1] != b[k - 1][1]:
                    weird.append("  第 %d 行 | 数=%d（同一张表上一行 %d）：%s"
                                 % (b[k][0], b[k][1], b[k - 1][1], b[k][2][:72]))
    n_rows = sum(len(b) for b in blocks)
    if weird:
        rep.bad("8.", "表格竖线不齐（%d 张表 / %d 行）" % (len(blocks), n_rows), weird[:8])
    else:
        rep.ok("8.", "表格竖线齐（%d 张表 / %d 行，每张表内 | 数一致）"
               % (len(blocks), n_rows))


# ── 整场题解的「节白名单」（唯一定义处：《题解写法》的 2.1 节） ──────────────
# 2026-10-01 加。背景：整改前 8 份题解长出 8 种节结构 —— 5 份题内标题带编号
# （`### 1. 题意`）3 份不带、Round 143 用 `##` 跟题级平铺、Round 163 每道题
# 单开一个「正确性证明」节、Round 140 带附录 A/B/C。人眼逐份看不住，交给脚本。
LEAF = ("题意", "思路", "参考代码", "复杂度", "易错点", "手算")
LEAF_PREFIX = ("从零讲",)          # 「### 从零讲：叉积」这种
TOP = ("目录", "实测记录")          # 场级 `##`，除题号外的全部合法值
BANNED = ("正确性证明", "练习建议", "自己动手", "一句话总结", "术语小抄",
          "学习路线图", "套路迁移表", "写完自查清单", "这场比赛在考什么")


def check_sections(text, rep):
    """只认 `##`（题级 / 场级）与 `###`（题内）两级；`####` 及以下不管。"""
    lvl2, lvl3 = [], []
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=True)
    for i, ln in enumerate(lines, 1):
        if mask[i - 1]:                  # 代码块里的 # 是注释，不是标题
            continue
        s = ln.strip()
        m = re.match(r"^(#{2,3})\s+(.+?)\s*$", s)
        if m:
            (lvl2 if len(m.group(1)) == 2 else lvl3).append((i, m.group(2)))

    problems = []
    for ln, t in lvl2:
        if re.match(r"^[A-Z]\s*\.\s*\S", t):          # 题级：`## A. 题名`
            if "——" in t or "—" in t:
                problems.append("  第 %d 行：题级标题带了副标题（只写「字母. 题名」）：%s"
                                % (ln, t))
            continue
        if re.split(r"[：:（(]", t)[0].strip() in TOP:  # 场级：目录 / 实测记录
            continue
        problems.append("  第 %d 行：场级 `##` 标题不在白名单（只许「目录」「实测记录」"
                        "或「<字母>. <题名>」）：%s" % (ln, t))
    for ln, t in lvl3:
        if re.match(r"^\d+\s*[.、]", t):                # 题内不许带编号
            problems.append("  第 %d 行：题内标题带编号（「### 1. 题意」要写成「### 题意」）：%s"
                            % (ln, t))
            continue
        base = re.split(r"[：:（(]", t)[0].strip()
        if base in LEAF or base.startswith(LEAF_PREFIX):
            continue
        problems.append("  第 %d 行：题内 `###` 标题不在白名单（只许 %s）：%s"
                        % (ln, " / ".join(list(LEAF) + [p + "：…" for p in LEAF_PREFIX]), t))
    for ln, t in lvl2 + lvl3:
        hit = [b for b in BANNED if b in t]
        if hit:
            problems.append("  第 %d 行：出现禁用节名「%s」（规则见《题解写法》2.1 节）：%s"
                            % (ln, hit[0], t))

    if problems:
        rep.bad("9.", "节结构不合白名单（%d 处）" % len(problems), problems[:10])
    else:
        rep.ok("9.", "节结构合白名单（%d 个题级 + %d 个题内标题）"
               % (len(lvl2), len(lvl3)))


# ── 目录表列头 + 题内小节顺序（2026-10-02 加） ──────────────────────────────
# 背景：8 场题解的目录表长出了 8 种列（`题目/档位/一句话核心`、`题目/难度/做法关键词/
# 复杂度/通过·提交`、`题/题名/核心/复杂度` …），题内小节的顺序与「必写项」也各不相同
# （Round 140 是 题意>手算>思路、Round 163 把复杂度放在参考代码后、Round 123 放在前）。
# 用户 2026-10-02 拍板统一，这里把两个口径钉成脚本，防止以后又漂。
# 同日追加：难度列必须写 `CF <数字>`（R155 曾写裸 `800`，其余 8 场都带前缀；统一带前缀，
# 因为 `CF ` 才标明这是 CF rating 口径，不是牛客自己的难度分）。
DIR_HEAD = ["题号", "题名", "考点", "难度"]
ORDER = ["题意", "从零讲", "手算", "思路", "参考代码", "复杂度", "易错点"]
MUST = ("题意", "思路", "参考代码", "易错点")


def check_dir_table(text, rep):
    """`## 目录` 的表头必须是 `题号 题名 考点 难度`，每行四格，难度列写 `CF <数字>`。"""
    lines = text.split("\n")
    try:
        i0 = next(i for i, l in enumerate(lines) if l.strip() == "## 目录")
    except StopIteration:
        rep.na("10.", "没有「## 目录」小节，跳过目录表检查")
        return
    i1 = next((i for i in range(i0 + 1, len(lines))
               if lines[i].startswith("## ")), len(lines))
    prob, hdr, nrow = [], None, 0
    for i in range(i0, i1):
        s = lines[i].strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if re.match(r"^[\s\-|]+$", s):
            continue
        if hdr is None:
            hdr = cells
            if cells != DIR_HEAD:
                prob.append("  第 %d 行：目录表头是 %s，标准是 %s"
                            % (i + 1, " | ".join(cells), " | ".join(DIR_HEAD)))
            continue
        nrow += 1
        if len(cells) != len(DIR_HEAD):
            prob.append("  第 %d 行：%d 格（标准 4 格）：%s" % (i + 1, len(cells), s[:70]))
        elif not re.match(r"^CF \d+$", cells[3]):
            prob.append("  第 %d 行：难度列是「%s」，标准是「CF <数字>」（如 CF 800）——"
                        "`CF ` 前缀标明这是 CF rating 口径，不是牛客难度分：%s"
                        % (i + 1, cells[3], s[:70]))
    if prob:
        rep.bad("10.", "目录表不合「%s」（%d 处）" % (" | ".join(DIR_HEAD), len(prob)),
                prob[:8])
    else:
        rep.ok("10.", "目录表合标准（%s，%d 行数据）" % (" | ".join(DIR_HEAD), nrow), [])


def check_order(text, rep):
    """每道题内 `###` 的**顺序**必须合标准，且 题意/思路/参考代码/易错点 四项必写。"""
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=False)
    cur, blocks = None, []
    for i, ln in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        if re.match(r"^## [A-Z]\. ", ln):
            cur = (ln.strip(), [])
            blocks.append(cur)
            continue
        if ln.startswith("## "):
            cur = None
            continue
        if cur is not None and ln.startswith("### "):
            cur[1].append((i, ln[4:].strip()))
    if not blocks:
        rep.na("11.", "没找到题级标题，跳过小节顺序检查")
        return

    prob = []
    for title, secs in blocks:
        names = [re.split(r"[：:（(]", t)[0].strip() for _, t in secs]
        rank = [ORDER.index(n) if n in ORDER else 99 for n in names]
        if rank != sorted(rank):
            prob.append("  %s：小节顺序是 %s，标准是 %s"
                        % (title, " > ".join(names), " > ".join(ORDER)))
        miss = [m for m in MUST if m not in names]
        if miss:
            prob.append("  %s：缺必写小节 %s" % (title, "、".join(miss)))
        dup = [n for n in set(names) if names.count(n) > 1]
        if dup:
            prob.append("  %s：重复小节 %s" % (title, "、".join(sorted(dup))))
    if prob:
        rep.bad("11.", "题内小节顺序/必写项不合标准（%d 处）" % len(prob), prob[:8])
    else:
        rep.ok("11.", "题内小节顺序与必写项全合标准（%d 道题）" % len(blocks), [])


# ── 缩进代码块里的公式（2026-10-02 加，第 16 项） ────────────────────────────
# 背景：Round 123 有 8 处「行首缩进的独立公式行」（历史排版习惯），LaTeX 化后
# 代码块里的 `$...$` 全裸奔（Typora 把缩进 ≥4 空格的独立行渲染成代码块）。
def check_indent_block(text, rep):
    r"""第 16 项：公式落在「缩进代码块」里 —— `$` 不会被渲染。

    判据：行首 ≥4 空格（或 tab）、**前一行是空行**（或文首 / 刚出围栏）的
    独立行 —— 这才是缩进代码块；前面接着普通文字的缩进行只是段落续行，
    公式照常渲染，不算。块内任一行含 `$` 就按「块首行」报一处。
    修法：去掉缩进并回段落，或写成 `$$...$$` 独立块公式（见《数学 LaTeX》）。
    """
    lines = text.split("\n")
    mask = toolutil.fence_mask(lines, indent=True)
    hits = []
    for i, ln in enumerate(lines):
        if mask[i] or not re.match(r"^(?:\t| {4,})\S", ln):
            continue
        prev = lines[i - 1].strip() if i > 0 else ""
        if prev and not prev.startswith("```"):   # 段落续行，不是代码块
            continue
        j = i
        while (j < len(lines) and lines[j].strip()
               and re.match(r"^(?:\t| {4,})", lines[j])):
            j += 1
        block = lines[i:j]
        if any("$" in strip_inline_code(b) for b in block):
            hits.append("  第 %d 行起（%d 行）：%s"
                        % (i + 1, len(block), block[0].strip()[:72]))
    if hits:
        rep.bad("16.", "公式落在缩进代码块里（`$` 不渲染，%d 处）" % len(hits),
                ["  行首 ≥4 空格、前面是空行的独立行 = Markdown「缩进代码块」，"
                 "Typora 当代码块显示，里面的 $...$ 原样露出",
                 "  改法：去掉行首缩进并回段落，或写成 $$...$$ 独立块公式"]
                + hits[:8])
    else:
        rep.ok("16.", "没有落在缩进代码块里的公式")


# ── KaTeX 全量渲染（2026-10-02 加，第 17 项） ────────────────────────────────
# 公式**内部**的语法错误（命令拼错、花括号不配）第 1 / 1b / 2 项都不看，
# 只有真渲染能抓。管线与 07 一致：extract_math.extract → math.json →
# node katex_check.js；不另写一套抽取逻辑。
def check_katex(text, rep):
    r"""第 17 项：KaTeX 全量渲染 —— 每个 `$...$` / `$$...$$` 都真渲染一遍。"""
    tools = os.path.dirname(os.path.abspath(__file__))
    katex_js = os.path.join(tools, "katex_check.js")
    node = shutil.which("node")
    if node is None or not os.path.exists(katex_js):
        rep.na("17.", "没找到 node 或 katex_check.js，KaTeX 渲染检查跳过")
        return
    if not os.path.isdir(os.path.join(tools, "node_modules", "katex")):
        rep.na("17.", "没装 katex（在 tools/ 下跑 `npm install katex`，见 README），跳过")
        return
    if _EM is None:
        rep.na("17.", "extract_math 导入失败，KaTeX 渲染检查跳过")
        return
    src = text
    if _U is not None:                    # 与 07 的验证管线同口径：先过 unify
        new, _ = _unify_once(text)        # 与第 2 项共用同一次转换（2026-10-02）
        if new is not None:
            src = new
    items = _EM.extract(src)
    if not items:
        rep.na("17.", "没找到公式，KaTeX 渲染检查跳过")
        return
    fd, jpath = tempfile.mkstemp(suffix=".json", prefix="katex_math_")
    os.close(fd)
    try:
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump({"<md>": items}, f, ensure_ascii=False)
        try:
            r = subprocess.run([node, katex_js, jpath], capture_output=True,
                               text=True, encoding="utf-8", timeout=180,
                               cwd=tools)
        except Exception as e:            # node 起不来 / 超时：如实报，不静默
            rep.bad("17.", "KaTeX 检查没跑起来：%s" % e)
            return
    finally:
        try:
            os.unlink(jpath)
        except OSError:
            pass
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"共\s*(\d+)\s*个公式，(\d+)\s*个渲染失败", out)
    if r.returncode != 0 or not m:
        rep.bad("17.", "KaTeX 检查没跑成（node 退出码 %d）" % r.returncode,
                ["  " + x for x in out.strip().split("\n")[:8]])
        return
    total, nbad = int(m.group(1)), int(m.group(2))
    if nbad:
        detail = [x for x in out.split("\n")
                  if re.match(r"^<md> L\d+:", x) or x.startswith("   tex:")]
        rep.bad("17.", "KaTeX 渲染失败 %d 个（共 %d 个公式）" % (nbad, total),
                ["  公式内部的拼写 / 语法错误：第 1 / 1b / 2 项都不看公式内部，"
                 "只有 KaTeX 能抓",
                 "  改法：按下面的行号修公式，改完重跑本检查"]
                + ["  " + x for x in detail[:16]])
    else:
        rep.ok("17.", "KaTeX 全量渲染 %d 个公式，0 失败" % total)


def check_file(path, tmpdir, no_record=False):
    rep = Report()
    text = open(path, encoding="utf-8").read()
    prose = prose_only(text)          # 行号与 text 对齐，但代码块是空的
    print("=" * 74)
    print("自检：%s" % path)
    print("  共 %d 字符 / %d 行（其中代码块外的正文检查 %d 字符）"
          % (len(text), text.count("\n") + 1, len(prose.replace("\n", ""))))
    print("=" * 74)
    # 正文类检查一律只看代码块外；编译检查 (5) 才看代码块。
    check_latex(prose, rep)
    check_latex_done(text, rep)      # 第 2 项查全文：unify_latex 自己会跳代码块
    check_ticks(prose, rep)
    check_sub_escape(prose, rep)
    check_traditional(prose, rep)
    if no_record:
        rep.na("6.", "实测记录检查被 --no-record 跳过（非题解类文档）")
        rep.na("9.", "节白名单检查被 --no-record 跳过（非题解类文档）")
        rep.na("10.", "目录表检查被 --no-record 跳过（非题解类文档）")
        rep.na("11.", "小节顺序检查被 --no-record 跳过（非题解类文档）")
    else:
        check_record(text, rep)
        check_sections(text, rep)
        check_dir_table(text, rep)
        check_order(text, rep)
    check_bytes(path, rep)
    check_tables(text, rep)
    check_indent_block(text, rep)
    check_katex(text, rep)
    return rep, text


def main(argv=None):
    ap = argparse.ArgumentParser(description="题解 md 交付前自检")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--no-compile", action="store_true", help="跳过编译检查（快）")
    ap.add_argument("--no-record", action="store_true",
                    help="跳过实测记录与节白名单检查（非题解类文档，如规划/调研 md）")
    ap.add_argument("--quiet", action="store_true", help="只打印有问题的项")
    ap.add_argument("--list", action="store_true",
                    help="只打印 17 项检查清单就退出（不用给文件）")
    a = ap.parse_args(argv)
    if a.list:
        print(__doc__)
        return 0
    if not a.files:
        ap.error("至少要给一个 md 文件（只看检查清单用 --list）")

    any_fail = False
    for path in a.files:
        if not os.path.exists(path):
            print("找不到文件：%s" % path)
            any_fail = True
            continue
        with tempfile.TemporaryDirectory() as td:
            rep, text = check_file(path, td, no_record=a.no_record)
            if not a.no_compile:
                check_compile(text, rep, td)
            else:
                rep.na("5.", "编译检查被 --no-compile 跳过")
        order = {"问题": 0, "通过": 1, "不适用": 2}
        for st, name, details in sorted(rep.items, key=lambda x: order[x[0]]):
            if a.quiet and st == "通过":
                continue
            print("\n[%s] %s" % (st, name))
            for d in details:
                print(d)
        print()
        n_bad = sum(1 for st, _, _ in rep.items if st == "问题")
        print("-" * 74)
        print("结论：%s（%d 项有问题）"
              % ("★有问题，改完再交付★" if rep.failed else "全部通过", n_bad))
        any_fail = any_fail or rep.failed
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
