# -*- coding: utf-8 -*-
r"""
fetch_problem —— 一次抓完一场牛客比赛的题面
============================================

    python fetch_problem.py <cid 或比赛URL> [题号区间] [--out 目录]

例：
    python fetch_problem.py 140737
    python fetch_problem.py https://ac.nowcoder.com/acm/contest/139660 A-F
    python fetch_problem.py 140737 B-G --out "<数据根>/题解/牛客周赛/Round163/_work"

它做五件事：

  1. 调题单接口（problem-list，无需登录）**把题目数数清**——默认「写全部题目」，
     先知道是 A~F 还是 A~L，免得漏题。
  2. 打印题单表：题号 / 题名 / AC 数 / 提交人数 / **分档建议**
     （AC 数 ≥ 全场最高 AC 的一半 → 短写档，其余 → 详写档）。
  3. 逐题抓题面。公式从 `<img src="...?tex=Y">` 的 **src** 参数还原
     （alt 只是占位符 `latex`），并**就地转成 Unicode**——只求中间产物（`题面\`）好读；
     交付 md 里数学一律写 LaTeX（见《数学 LaTeX》）。
  4. 落盘 `<out>/raw/<题号>.html` 和 `<out>/题面/<题号>.txt`（再加一份合并的 `_全部.txt`）。
  5. **生成 `<out>/samples.py`**：官方样例的 Python 常量表，直接贴进 verify.py。

第 5 件是重点。《验证协议》里记过一个坑：交付前凭记忆手敲样例输入，敲错之后代码输出对不上
题解记录的答案，一度准备去"修"一个本来正确的程序。样例常量表由本工具从**原文**
机械生成，就没有"凭记忆"这一步了。

**输出目录默认自动定位**（2026-09-30 起）：去比赛主页里读「牛客周赛 Round N」，
落到 `<题解根>\RoundN\_work\`；读不到就退到暂存区 `<题解根>\_work\nk<cid>\` 并提示。
题单接口本身**不返回比赛名**（只有 contestId），所以这个名字是另外抓主页拿的。
`--out` 给的路径优先级最高。
"""

import html as htmllib
import json
import os
import re
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil                    # 数据根（config.json）的唯一来源

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

LIST_API = "https://ac.nowcoder.com/acm/contest/problem-list?token=&id=%s"
PAGE_URL = "https://ac.nowcoder.com/acm/contest/%s/%s"
CONTEST_URL = "https://ac.nowcoder.com/acm/contest/%s"

# 题解根：**按比赛分目录**，牛客周赛落在
# `<数据根>\题解\牛客周赛\RoundNNN\`；里面交付 md 放场次根，中间产物进 `_work\`。
# 别的比赛（Codeforces / AtCoder）以后平级再开一个目录。
# 数据根 = config.json 的 `data_root`（见《工作流》）。
ROOT = os.path.join(toolutil.DATA_ROOT, "题解", "牛客周赛")

STOP_WORDS = ("返回全部题目", "上一题", "下一题", "列表加载中", "讨论", "题解")

# LaTeX -> Unicode。只为中间产物（题面\）好读；交付 md 里数学一律写 LaTeX（见《数学 LaTeX》）。
#
# 实现要点：**用一个正则一次匹配整个命令名，再查字典**，不要按列表顺序做
# str.replace。按顺序替换会拿短命令当前缀吃掉长命令——实测把 `\left(` 转成了
# `≤ft(`（`\le` 排在了 `\left` 前面，先把 `\left` 的前两个字符吃掉了）。
CMD = {
    "leqq": "≤", "geqq": "≥", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "neq": "≠", "ne": "≠", "equiv": "≡", "approx": "≈", "sim": "∼",
    "times": "×", "cdot": "·", "div": "÷", "pm": "±", "mp": "∓",
    "dots": "…", "ldots": "…", "cdots": "…", "vdots": "⋮",
    "floor": "⌊", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉",
    "bullet": "•", "mid": "∣", "nmid": "∤", "parallel": "∥",
    "sum": "Σ", "prod": "Π", "in": "∈", "notin": "∉",
    "subseteq": "⊆", "subset": "⊂", "supseteq": "⊇", "supset": "⊃",
    "cup": "∪", "cap": "∩", "bigcup": "∪", "bigcap": "∩",
    "emptyset": "∅", "varnothing": "∅", "setminus": "\\",
    "infty": "∞", "to": "→", "rightarrow": "→", "Rightarrow": "⇒",
    "leftarrow": "←", "Leftarrow": "⇐", "iff": "⇔",
    "land": "且", "lor": "或", "lnot": "非", "neg": "非",
    "bmod": " mod ", "oplus": "⊕", "otimes": "⊗",
    "quad": " ", "qquad": "  ", "": "",
}
# 这些命令直接删掉（排版指令，本身不是内容）
DROP = {"left", "right", "big", "Big", "bigg", "Bigg",
        "displaystyle", "limits", "nolimits", "textstyle", "mathstrut"}
# 转义的字面符号
ESC = [("\\{", "{"), ("\\}", "}"), ("\\%", "%"), ("\\_", "_"),
       ("\\&", "&"), ("\\#", "#"), ("\\$", "$")]


def latex_to_text(t):
    """把一段 LaTeX 转成能直接读的 Unicode 文本（给中间产物用，不是交付格式）。

    先处理**带参数**的命令（\\frac / \\text / \\pmod …），因为它们的花括号参数
    里可能还有别的命令；再统一查表处理无参命令。
    """
    # 1) 带参数的命令
    t = re.sub(r"\\hspace\{[^}]*\}", "", t)
    t = re.sub(r"\\pmod\{([^{}]*)\}", r" (mod \1)", t)
    for _ in range(3):   # \frac{\frac{a}{b}}{c} 这种嵌套，多跑几轮
        t = re.sub(r"\\(?:tfrac|frac|dfrac)\{([^{}]*)\}\{([^{}]*)\}", r"(\1/\2)", t)
    for _ in range(3):
        t = re.sub(r"\\(?:texttt|mathrm|mathbf|mathit|mathsf|text|operatorname)"
                   r"\{([^{}]*)\}", r"\1", t)
    # 2) 无参命令：一次匹配整个名字再查表（顺序无关，不会被短命令前缀吃掉）
    t = re.sub(r"\\([a-zA-Z]+)",
               lambda m: "" if m.group(1) in DROP else CMD.get(m.group(1), m.group(1)),
               t)
    # 3) 转义的符号，再兜底去掉剩余反斜杠
    for a, b in ESC:
        t = t.replace(a, b)
    t = t.replace("\\ ", " ").replace("\\,", " ").replace("\\;", " ").replace("\\!", "")
    t = t.replace("\\", "")
    t = re.sub(r"\s+", " ", t).strip()
    # 4) 归一化括号内侧的空白。原文写作 `10^9 \right)`、`\left( a_1`，
    #    删掉 \left/\right 之后会各留一个空格；那是删除的副产物、不是内容，
    #    留着会读成 `(0 ≤ c_i ≤ 10^9 )` 这种别扭样子。
    t = re.sub(r"([(\[{])\s+", r"\1", t)
    t = re.sub(r"\s+([)\]}])(?=\s|$|[,;.])", r"\1", t)
    t = re.sub(r"\s+([)\]}])\s*$", r"\1", t)
    return t.strip()


# ---------------------------------------------------------------- 抓取
def curl(url, out=None):
    cmd = ["curl.exe", "-sL", "-A", UA, url]
    if out:
        cmd += ["-o", out]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        if r.returncode != 0:
            raise RuntimeError("curl 失败：%s" % r.stderr.decode(errors="replace")[:300])
        return open(out, encoding="utf-8", errors="replace").read()
    r = subprocess.run(cmd, capture_output=True, timeout=90)
    if r.returncode != 0:
        raise RuntimeError("curl 失败：%s" % r.stderr.decode(errors="replace")[:300])
    return r.stdout.decode("utf-8", errors="replace")


def parse_cid(s):
    """从纯数字或比赛 URL 里取 cid。"""
    m = re.search(r"/contest/(\d+)", s)
    if m:
        return m.group(1)
    if s.isdigit():
        return s
    raise SystemExit("给的是 %r，认不出 cid——要比赛 URL 或纯数字。" % s)


def find_round(cid):
    """去比赛主页读「牛客周赛 Round N」，返回 N（字符串）或 None。

    题单接口只给 contestId，**不返回比赛名**；比赛主页的 title / 中奖名单里
    带「牛客周赛 Round 163」这种字样，实测 cid 125954/126120/139660/140737
    四个都读得到。读不到不算错——退回暂存区，让调用方提示用 --out。
    """
    try:
        t = curl(CONTEST_URL % cid)
    except Exception:
        return None
    hits = re.findall(r"牛客周赛\s*Round\s*(\d+)", t)
    if not hits:
        return None
    # 页面上还可能链着别的场次，取出现次数最多的那个
    return max(set(hits), key=hits.count)


def parse_range(spec, all_letters):
    """'A-F' / 'ABF' / 'C' -> ['A','B','C','F']；空 -> 全部。"""
    if not spec:
        return list(all_letters)
    letters = [c for c in spec.upper() if "A" <= c <= "Z"]
    if not letters:
        raise SystemExit("题号区间 %r 里没有题号字母。" % spec)
    if "-" in spec:
        a, b = spec.upper().split("-", 1)[0].strip(), spec.upper().split("-", 1)[1].strip()
        if a and b and a[0].isalpha() and b[0].isalpha():
            letters = [chr(c) for c in range(ord(a[0]), ord(b[0]) + 1)]
    # 用题单里的真实题号过滤，且保持题单顺序
    return [c for c in all_letters if c in set(letters)]


# ---------------------------------------------------------------- 解析
_PLACE_IN = "\x01%d\x02"
_PLACE_RE = re.compile("\x01(\\d+)\x02")


def strip_tags(t):
    """剥 HTML 标签。

    坑（题面里真发生过）：tex 里可能有字面 `<`（比如 `1 < x`），直接剥标签会
    把 `<` 到下一个 `>` 之间整段正文吃掉。所以**先把公式换成占位符，剥完再换回**。
    """
    texes = []

    def hold(m):
        tag = m.group(0)
        ms = re.search(r'src=["\']([^"\']*)["\']', tag)
        raw = ""
        if ms:
            q = parse_qs(urlparse(htmllib.unescape(ms.group(1))).query)
            raw = unquote(q.get("tex", [""])[0])
        if not raw:
            ma = re.search(r'alt=["\']([^"\']*)["\']', tag)
            if ma and ma.group(1) not in ("latex", ""):
                raw = ma.group(1)
        txt = latex_to_text(raw)
        if not txt:
            return ""
        texes.append(txt)
        return _PLACE_IN % (len(texes) - 1)

    t = re.sub(r"(?is)<img[^>]*>", hold, t)
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", t)
    # 样例在页面里存两份：一份隐藏的 <textarea>（给"复制"按钮），一份可见的
    # <pre>。两份内容一样，不删掉正文里就会出现两遍。样例我们是从 textarea
    # 结构化提取的（extract_samples），所以这里整个丢掉不影响。
    t = re.sub(r"(?is)<textarea[^>]*>.*?</textarea>", "", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|td|tr|pre|h[1-6]|table|span|b|u|i|strong)>", "\n", t)
    t = re.sub(r"(?i)<(p|div|li|tr|pre|h[1-6]|table|span|b|u|i|strong)[^>]*>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = htmllib.unescape(t).replace("\xa0", " ")
    t = _PLACE_RE.sub(lambda m: texes[int(m.group(1))], t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # 去掉每行的首尾空白，再合并连续空行
    lines, out, blank = [ln.strip() for ln in t.split("\n")], [], False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def cut_body(text):
    """从整页文本里切出题面正文。"""
    i = text.find("题目描述")
    if i >= 0:
        text = text[i:]
    cut = len(text)
    for w in STOP_WORDS:
        j = text.find(w)
        if 0 < j < cut:
            cut = j
    return text[:cut].strip()


def extract_samples(raw_html):
    """结构化提取样例块。用 `question-oi` 块的 textarea，天然不会重复
    （页面上源码区和"复制"区看起来是两份，但 textarea 只有一份）。"""
    starts = [m.start() for m in re.finditer(r'<div class="question-oi">', raw_html)]
    if not starts:
        return []
    out = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else len(raw_html)
        blk = raw_html[st:en]
        ins = re.findall(r'<textarea[^>]*data-clipboard-text-id="input\d*"[^>]*>(.*?)</textarea>',
                         blk, re.S)
        outs = re.findall(r'<textarea[^>]*data-clipboard-text-id="output\d*"[^>]*>(.*?)</textarea>',
                          blk, re.S)
        if not ins and not outs:
            continue
        expl = re.search(r'<h2>\s*说明\s*</h2>\s*<div class="question-oi-cont">(.*?)</div>',
                         blk, re.S)
        out.append({
            "name": "样例 %d" % (k + 1),
            "in": htmllib.unescape(ins[0]).strip() if ins else "",
            "out": htmllib.unescape(outs[0]).strip() if outs else "",
            "expl": strip_tags(expl.group(1)) if expl else "",
        })
    return out


# ---------------------------------------------------------------- 主流程
def main(argv):
    # 位置参数与选项要**顺序扫**着分：`--out <路径>` 后面那个路径不是位置参数。
    # 实测坑（2026-10-01）：写成 `[a for a in argv if not a.startswith("--")]`，
    # `--out C:/tmp/题解/_work/nk125954` 里的路径会落到 args[1]，
    # 被当成题号区间——path 里的大写字母过滤后剩 CDE，于是「7 题只抓了 3 题」。
    args, opts, _skip = [], [], False
    for a in argv:
        if _skip:
            _skip = False
            continue
        if a == "--out":
            _skip = True
        elif a.startswith("--"):
            opts.append(a)
        else:
            args.append(a)
    if not args:
        print(__doc__)
        # `--help` / `-h` 是**主动要看用法**，退出码 0；什么都不给才是误用，退出码 2。
        # 两者都返回 2 的话，`python fetch_problem.py --help && ...` 这种链会假报失败。
        return 0 if ("--help" in argv or "-h" in argv) else 2

    cid = parse_cid(args[0])
    range_spec = args[1] if len(args) > 1 else ""
    out_dir = None
    for i, o in enumerate(argv):
        if o == "--out" and i + 1 < len(argv):
            out_dir = argv[i + 1]
    round_no = None
    if out_dir is None:
        round_no = find_round(cid)
        if round_no:
            out_dir = os.path.join(ROOT, "Round%s" % round_no, "_work")
        else:
            # 读不到场次名就退到题解根下的暂存区；**不瞎猜 Round 号**，
            # 猜错了会把两场题解混进同一个文件夹。
            out_dir = os.path.join(ROOT, "_work", "nk%s" % cid)

    raw_dir = os.path.join(out_dir, "raw")
    txt_dir = os.path.join(out_dir, "题面")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    print("比赛 cid = %s%s" % (cid, "，牛客周赛 Round %s" % round_no if round_no else ""))
    print("输出目录 = %s" % out_dir)
    if round_no is None and "--out" not in argv:
        print("  （主页里没读到「牛客周赛 Round N」，先落在暂存区。"
              "定下场次后：把本目录改名到 <题解根>\\RoundN\\_work，或加 --out 重跑。）")

    # --- 1. 题单
    try:
        lst = json.loads(curl(LIST_API % cid))
    except Exception as e:
        raise SystemExit("题单接口取不到（%s）。比赛还没开始就别抓。" % e)
    if lst.get("code") != 0:
        raise SystemExit("题单接口返回 code=%s msg=%s" % (lst.get("code"), lst.get("msg")))
    probs = lst["data"]["data"]
    if not probs:
        raise SystemExit("题单是空的。")
    all_letters = [p["index"] for p in probs]
    letters = parse_range(range_spec, all_letters)
    if not letters:
        raise SystemExit("区间 %r 和题单 %s 对不上。" % (range_spec, "".join(all_letters)))

    mx_ac = max(p["acceptedCount"] for p in probs)
    print()
    print("题单（共 %d 题，本次抓 %d 题：%s）"
          % (len(probs), len(letters), "".join(letters)))
    print("  %-4s %-22s %7s %9s %9s   %s"
          % ("题号", "题名", "AC数", "提交人数", "平均交次", "分档建议"))
    print("  " + "-" * 74)
    picked = []
    for p in probs:
        if p["index"] not in letters:
            continue
        picked.append(p)
        # 分档：AC 数 ≥ 全场最高 AC 的一半 -> 短写；否则详写。
        # 用绝对 AC 数而不是 AC 率——AC 率不单调（某道更难的题反而可能更高）。
        short = p["acceptedCount"] * 2 >= mx_ac
        tag = "短写" if short else "详写"
        print("  %-4s %-22s %7d %9d %9.2f   %s"
              % (p["index"], p["title"][:20], p["acceptedCount"],
                 p["submitPersonCount"], p.get("avgAcSubmitCount", 0), tag))
    print()
    print("  注：分档只是**建议**。用到前几场没出现过的新算法/数据结构的题，"
          "无论 AC 多高都按详写办（见《首次出现的概念要从零讲》）。")

    # --- 2. 逐题抓
    print()
    ok, failed = [], []
    all_samples = []
    for p in picked:
        L = p["index"]
        url = PAGE_URL % (cid, L)
        try:
            raw = curl(url, os.path.join(raw_dir, "%s.html" % L))
        except Exception as e:
            failed.append((L, str(e)))
            print("  %s：★抓取失败★ %s" % (L, e))
            continue
        body = cut_body(strip_tags(raw))
        samples = extract_samples(raw)
        if len(body) < 80:
            failed.append((L, "正文只有 %d 字节，像是没渲染出来" % len(body)))
            print("  %s：★正文太短★ 只拿到 %d 字节，看一眼 %s/raw/%s.html"
                  % (L, len(body), out_dir, L))
            continue

        buf = ["#" * 66, "# %s. %s" % (L, p["title"]),
               "# 来源：%s" % url, "#" * 66, "", body]
        if samples:
            buf += ["", "=" * 66, "官方样例", "=" * 66]
            for s in samples:
                buf += ["", "--- %s 输入 ---" % s["name"], s["in"],
                        "", "--- %s 输出 ---" % s["name"], s["out"]]
                if s["expl"]:
                    buf += ["", "--- %s 说明 ---" % s["name"], s["expl"]]
                all_samples.append((L, s))
        with open(os.path.join(txt_dir, "%s.txt" % L), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(buf) + "\n")
        ok.append(L)
        print("  %s. %-20s 题面 %5d 字节，样例 %d 组"
              % (L, p["title"][:18], len(body), len(samples)))
        sys.stdout.flush()

    # --- 3. 合并 + 样例常量表
    if ok:
        merged = []
        for L in ok:
            merged.append(open(os.path.join(txt_dir, "%s.txt" % L),
                               encoding="utf-8").read())
        with open(os.path.join(txt_dir, "_全部.txt"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("\n\n".join(merged))
        print()
        print("合并题面 -> %s" % os.path.join(txt_dir, "_全部.txt"))

    if all_samples:
        sp = os.path.join(out_dir, "samples.py")
        with open(sp, "w", encoding="utf-8", newline="\n") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write('"""官方样例常量表——由 fetch_problem.py 从题面原文机械生成，'
                    "不许手敲。\n\n")
            f.write("贴进 verify.py 的 SAMPLES。来源：%s\n" % (PAGE_URL % (cid, ok[0] if ok else "A")))
            f.write('"""\n\n')
            f.write("SAMPLES = [\n")
            for L, s in all_samples:
                f.write("    # ---- %s 题 %s\n" % (L, s["name"]))
                f.write("    (%r,\n     %r,\n     %r),\n" % (L + " " + s["name"], s["in"], s["out"]))
            f.write("]\n")
        print("样例常量表 -> %s  （贴进 verify.py，别手敲）" % sp)

    print()
    print("===== 汇总 =====")
    print("  抓成功：%s" % ("".join(ok) if ok else "无"))
    if failed:
        print("  失败  ：%s" % "、".join("%s(%s)" % (L, w) for L, w in failed))
        print("  失败的题**不许编造条件**：要么重抓，要么如实说明没拿到。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
