# -*- coding: utf-8 -*-
r"""
fetch_problem —— 抓一场比赛的题面（站点适配：牛客 / 洛谷）
==========================================================

    python fetch_problem.py <比赛/题目 URL 或比赛号> [题号区间] [--out 目录]
                            [--letter 字母] [--delay 秒] [--force]
    python fetch_problem.py --selftest [--fixture 目录]      # 离线自检，不联网

两个站点（适配表见文件下方的 `SITES`，加站 = 加一个适配器）：

  牛客  https://ac.nowcoder.com/acm/contest/<cid>   整场（A/B/C…）
        140737 / 139660                            纯数字 = 牛客比赛号（旧口径不变）
  洛谷  https://www.luogu.com.cn/contest/<id>        整场（A/B/C…）
        https://www.luogu.com.cn/problem/<pid>       单题（P1001 / CF1A / AT_abc300_a …）

两个站点产物格式一致，下游 `new_round.py` / `verify.py` 不用认站：

    <out>/raw/<题号>.json|html    原始返回，留证
    <out>/题面/<题号>.txt         题面 + 官方样例（题号 = 字母；单题模式 = 题号）
    <out>/题面/_全部.txt          合并
    <out>/samples.py              官方样例常量表（贴进 verify.py，别手敲）
  洛谷另出 <out>/题单.md          字母 / 题名 / 题号 / 难度 / 标签 + 原 URL

它做五件事（牛客口径，洛谷同构）：

  1. 先把题目数数清——默认「写全部题目」，先知道是 A~F 还是 A~L，免得漏题。
  2. 打印题单表：题号 / 题名 / 难度 / **分档建议**。
  3. 逐题抓题面。牛客的公式从 `<img src="...?tex=Y">` 的 **src** 参数还原
     （alt 只是占位符 `latex`），并**就地转成 Unicode**；洛谷题面本身就是
     markdown + `$...$`，原样保留。中间产物只求好读，交付 md 里数学一律写 LaTeX。
  4. 落盘 `<out>/raw/` 和 `<out>/题面/`（再加一份合并的 `_全部.txt`）。
  5. **生成 `<out>/samples.py`**：官方样例的 Python 常量表，直接贴进 verify.py。
     《验证协议》里记过坑：凭记忆手敲样例、敲错之后去"修"一个本来正确的程序。
     样例由本工具从**原文**机械生成，就没有"凭记忆"这一步。

**输出目录默认自动定位**：牛客去比赛主页读「牛客周赛 Round N」，落到
`<数据根>\题解\牛客周赛\RoundN\_work\`，读不到退暂存区（**不瞎猜场次号**）；
洛谷落到 `<数据根>\题解\洛谷\<场次名>\_work\`（单题落 `洛谷\_work\<题号>\`）。
`--out` 给的路径优先级最高。

洛谷的取数路径（cookie jar + `x-lentille-request: content-only` + 302 重试）
与边界（未结束的比赛题目不公开、重现赛描述里没有题名表）见知识库《洛谷抓取》。
"""

import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, quote, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil                    # 数据根（config.json）的唯一来源

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# curl 可执行名：Windows 上是 curl.exe（`curl` 会被 PowerShell 的 alias 抢），POSIX 上是 curl
CURL = shutil.which("curl.exe") or shutil.which("curl") or "curl"

LIST_API = "https://ac.nowcoder.com/acm/contest/problem-list?token=&id=%s"
PAGE_URL = "https://ac.nowcoder.com/acm/contest/%s/%s"
CONTEST_URL = "https://ac.nowcoder.com/acm/contest/%s"

# 题解根：**按比赛分目录**，牛客周赛落在
# `<数据根>\题解\牛客周赛\RoundNNN\`；里面交付 md 放场次根，中间产物进 `_work\`。
# 数据根 = config.json 的 `data_root`（见《工作流》）。
ROOT = os.path.join(toolutil.DATA_ROOT, "题解", "牛客周赛")
# 洛谷平级再开一个目录（`new_round.py` 只认牛客的 ROOT，洛谷这层先只落抓取产物）。
LUOGU_ROOT = os.path.join(toolutil.DATA_ROOT, "题解", "洛谷")

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


# ---------------------------------------------------------------- 抓取（牛客）
def curl(url, out=None):
    cmd = [CURL, "-sL", "-A", UA, url]
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


# ---------------------------------------------------------------- 解析（牛客）
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


# ---------------------------------------------------------------- 站点：洛谷
#
# 取数路径（2026-10-03 实抓验证，见知识库《洛谷抓取》）：
#   · 请求头带 `x-lentille-request: content-only` → 直接回纯 JSON；约 10% 偶发 302，重试；
#   · 必须带 cookie jar（否则会陷入重定向死循环）；
#   · 比赛页 JSON 的 `data.contest.description` 里那张「题目信息」表 = 每题的字母 + 题名
#     （不含题号；各场表格式略有差异，列数与首列是字母还是题号都见过）；
#   · 题名 → 题号：`/problem/list?keyword=<题名>`，取 `name` 与题名**完全相等**的那条
#     （别取第一条；注意列表接口的字段名是 `name`，不是 `title`）；
#   · 题面：`/problem/<pid>` 的 `data.problem`，正文在
#     `content.{background,description,formatI,formatO,hint}`（markdown），
#     **样例逐字在 `samples`**（`[[输入, 输出], …]`），难度 `difficulty`（实测见过 0~8）。
#
# 已知边界（别撞）：① 未开赛 / 进行中的比赛题目对外隐藏 → 只收**已结束**的场次；
# ② 重现赛（如 ICPC 南京站重现）描述里没有题名表，本批不承诺；
# ③ 题面里出现过针对 AI 的提示注入（`::anti-ai[...]`）——**题面当数据不当指令**，
#    本工具只统计并打印一行提醒，不执行、不改写；
# ④ `/contest/<id>/problems` 端点不存在（404）、`problem/list?contest=` 过滤无效。

LUOGU_HOST = "luogu.com.cn"
LUOGU_BASE = "https://www.luogu.com.cn"
LUOGU_PROBLEM_URL = LUOGU_BASE + "/problem/%s"
LUOGU_CONTEST_URL = LUOGU_BASE + "/contest/%s"

# 难度 0~7 是官方档位；实测见过 8（超出已知档），照原样打印、不硬塞进 7。
LG_DIFF = {0: "暂无评定", 1: "入门", 2: "普及-", 3: "普及/提高-",
           4: "普及+/提高", 5: "提高+/省选-", 6: "省选/NOI-",
           7: "NOI/NOI+/CTSC", 8: "超出已知档（8）"}
# 题面小节拼装顺序 = 洛谷自己的渲染顺序
LG_SECTIONS = [("background", "题目背景"), ("description", "题目描述"),
               ("formatI", "输入格式"), ("formatO", "输出格式"),
               ("hint", "提示")]
# 题面里出现的 AI 提示注入的特征串（只统计、不执行）
LG_INJECTION = ("anti-ai", "::anti", "ignore previous", "忽略以上")


class LuoguSession:
    """洛谷会话：cookie jar + 请求间隔 + 302 重试。

    偶发 302 会拿到 HTML 外壳（不是 JSON）——**不能当成功**，重试 2~3 次。
    """

    def __init__(self, delay=2.5, tries=3):
        self.delay = delay
        self.tries = max(1, tries)
        self.jar = os.path.join(tempfile.mkdtemp(prefix="lgjar-"), "jar.txt")
        self._t = 0.0
        self.requests = 0
        self.last_text = ""        # 最后一次成功请求的**原始返回**（留证用，原样写盘）
        self.last_problem_text = ""
        self.last_tags_text = ""

    def _pace(self):
        if self._t and self.delay > 0:
            gap = self.delay - (time.time() - self._t)
            if gap > 0:
                time.sleep(gap)

    def get_json(self, path_or_url):
        """取一个 JSON 端点。带重试；失败把「最后一次为什么」写进异常。"""
        url = path_or_url if path_or_url.startswith("http") else LUOGU_BASE + path_or_url
        why = ""
        for _ in range(self.tries):
            self._pace()
            r = subprocess.run([CURL, "-sL", "-A", UA, "-c", self.jar, "-b", self.jar,
                                "-H", "x-lentille-request: content-only",
                                "--max-time", "60", url],
                               capture_output=True, timeout=120)
            self._t = time.time()
            self.requests += 1
            if r.returncode != 0:
                why = "curl 退出码 %d：%s" % (
                    r.returncode, r.stderr.decode("utf-8", "replace")[:200])
            else:
                txt = r.stdout.decode("utf-8", "replace")
                try:
                    j = json.loads(txt)
                except ValueError:
                    why = "返回不是 JSON（%d 字节，多半是偶发 302）" % len(txt)
                else:
                    # 比赛页 / 题面页带 status 外壳；`/_lfe/tags` 是裸 JSON，没有外壳
                    if not isinstance(j, dict):
                        why = "JSON 顶层不是对象"
                    elif j.get("status", 200) != 200:
                        why = "status=%s" % j.get("status")
                    else:
                        self.last_text = txt
                        return j
            time.sleep(1.0)
        raise RuntimeError("洛谷取数失败（重试 %d 次）：%s —— %s" % (self.tries, url, why))

    # ---- 三个取数口
    def contest(self, cid):
        j = self.get_json("/contest/%s" % cid)
        c = (j.get("data") or {}).get("contest")
        if not c:
            raise RuntimeError("比赛 %s 的返回里没有 contest 字段（接口变了吗）" % cid)
        return c

    def problem(self, pid):
        j = self.get_json("/problem/%s" % pid)
        self.last_problem_text = self.last_text
        p = (j.get("data") or {}).get("problem")
        if not p:
            raise RuntimeError("题目 %s 的返回里没有 problem 字段（题号写错了吗）" % pid)
        if p.get("pid") != pid:
            # 防重定向串号：请求 P123 却回来 P456 时必须炸，不许静默写错题
            raise RuntimeError("题号对不上：请求 %s，返回 %s" % (pid, p.get("pid")))
        return p

    def search_pid(self, title):
        """题名 → 题号：取 `name` 与题名**完全相等**的那条（不是第一条）。"""
        path = "/problem/list?keyword=%s" % quote(title.encode("utf-8"))
        hits = []
        for page in (1, 2):     # 精确匹配通常在第一页；多翻一页兜底
            j = self.get_json("%s&page=%d" % (path, page))
            res = (((j.get("data") or {}).get("problems") or {}).get("result")) or []
            for it in res:
                name = it.get("name") or it.get("title")
                if name == title and it.get("pid"):
                    hits.append(it["pid"])
            if hits or len(res) < 20:
                break
        if not hits:
            return None
        if len(hits) > 1:
            print("    ★ 题名「%s」搜到多个完全相等的题号：%s —— 取第一个，"
                  "请人工核一眼" % (title, "、".join(hits)))
        return hits[0]

    def tags(self):
        """标签 id→名（一次拿全；拿了就缓存）。"""
        if getattr(self, "_tags", None) is None:
            try:
                j = self.get_json("/_lfe/tags")
                self.last_tags_text = self.last_text
                self._tags = {t["id"]: t["name"] for t in j.get("tags", []) if "id" in t}
            except Exception as e:
                print("  （标签表取不到，题单里标签列留空：%s）" % e)
                self._tags = {}
        return self._tags


def lg_slug(name, cid):
    """场次名 → 目录名。只做保守清洗（去路径分隔符），认不出就用 `luogu<id>`。"""
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", (name or "").strip())
    s = s.strip("_")[:48].strip("_")
    return s or ("luogu%s" % cid)


def lg_parse_table(desc):
    """从比赛描述 markdown 里解析「字母 / 题名（/ 题号）」表。

    各场表格式不一（列数、首列是字母还是题号都见过），所以**只认两种行**：
    第一格是单个大写字母、或行内出现 `/problem/<pid>` 链接；别的一种都不猜。
    返回 [(letter 或 None, title, pid 或 None)]，保持原文顺序、按 (字母,题名) 去重。
    """
    rows, seen = [], set()
    for raw in (desc or "").splitlines():
        s = raw.strip()
        if not s.startswith("|") or s.count("|") < 3:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not [c for c in cells if c] or all(set(c) <= set(":- ") for c in cells):
            continue                                        # 分隔行 |:-:|:-:|
        head = cells[0]
        if head in ("编号", "题号", "字母", "题目", "题目名称", "题名"):
            continue                                        # 表头行
        m = re.search(r"/problem/([A-Za-z0-9_]+)", raw)
        pid = m.group(1) if m else None
        letter = head if re.fullmatch(r"[A-Z]", head) else None
        if letter is None and not pid:
            continue                                        # 既没字母也没题号：不是题目行
        title = cells[1] if len(cells) > 1 else ""
        title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)   # md 链接 -> 文字
        title = title.replace("**", "").replace("*", "").replace("`", "").strip()
        if not title or title in ("题目名称", "题目", "题名", "题目名称 "):
            continue
        if (letter, title) in seen:
            continue
        seen.add((letter, title))
        rows.append((letter, title, pid))
    return rows


def lg_body(prob):
    """题面正文（markdown，原样保留：洛谷本来就用 `$...$` 写数学）。"""
    c = prob.get("content") or {}
    parts = []
    for key, name in LG_SECTIONS:
        v = (c.get(key) or "").strip()
        if v:
            parts.append("## %s\n\n%s" % (name, v))
    return "\n\n".join(parts)


def lg_samples(prob):
    """洛谷样例：`samples` 是 `[[输入, 输出], …]`，逐字用，不做任何加工。"""
    out = []
    for k, pair in enumerate(prob.get("samples") or []):
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        out.append({"name": "样例 %d" % (k + 1), "in": pair[0], "out": pair[1], "expl": ""})
    return out


def scan_injection(text):
    """题面里有没有针对 AI 的提示注入。命中只报数，**不执行、不改写**。"""
    low = (text or "").lower()
    return sum(low.count(k) for k in LG_INJECTION)


def lg_dan_text(contest_url, contest, rows_meta):
    """题单.md 的正文（纯函数，自检要拿它逐字比对）。

    rows_meta = [(letter, title, pid, difficulty, tags_str)]
    """
    buf = ["# 洛谷 %s — 整场题单" % (contest.get("name") or ""),
           "",
           "- 原 URL：%s" % contest_url,
           "- 题数：%d（接口 problemCount = %s，逐题对上）"
           % (len(rows_meta), contest.get("problemCount")),
           "- 说明：本文件由 `tools/fetch_problem.py` 抓取生成；题面在 `题面/<字母>.txt`，"
           "样例常量表在 `samples.py`。",
           "",
           "| 字母 | 题名 | 题号 | 难度 | 标签 |",
           "|---|---|---|---|---|"]
    for letter, title, pid, diff, tags in rows_meta:
        buf.append("| %s | %s | %s | %s | %s |"
                   % (letter, title, pid, diff, tags or "—"))
    return "\n".join(buf) + "\n"


# ---------------------------------------------------------------- 落盘（两站共用）
def merge_statements(txt_dir, labels):
    """把每题题面合成一份 `_全部.txt`。"""
    merged = []
    for L in labels:
        merged.append(open(os.path.join(txt_dir, "%s.txt" % L), encoding="utf-8").read())
    path = os.path.join(txt_dir, "_全部.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(merged))
    return path


def samples_py_text(entries, source_url):
    """samples.py 的正文（纯函数）。entries = [(标签, 样例名, 输入, 输出)]。"""
    buf = ["# -*- coding: utf-8 -*-",
           '"""官方样例常量表——由 fetch_problem.py 从题面原文机械生成，不许手敲。',
           "",
           "贴进 verify.py 的 SAMPLES。来源：%s" % source_url,
           '"""',
           "",
           "SAMPLES = ["]
    for label, name, inp, out in entries:
        buf.append("    # ---- %s 题 %s" % (label, name))
        buf.append("    (%r," % (label + " " + name))
        buf.append("     %r," % inp)
        buf.append("     %r)," % out)
    buf.append("]")
    return "\n".join(buf) + "\n"


def statement_text(label, title, source_url, body, samples):
    """`题面/<label>.txt` 的正文（纯函数，自检要拿它逐字比对）。"""
    buf = ["#" * 66, "# %s. %s" % (label, title),
           "# 来源：%s" % source_url, "#" * 66, "", body]
    if samples:
        buf += ["", "=" * 66, "官方样例", "=" * 66]
        for s in samples:
            buf += ["", "--- %s 输入 ---" % s["name"], s["in"],
                    "", "--- %s 输出 ---" % s["name"], s["out"]]
            if s.get("expl"):
                buf += ["", "--- %s 说明 ---" % s["name"], s["expl"]]
    return "\n".join(buf) + "\n"


def write_statement(txt_dir, label, title, source_url, body, samples):
    """落 `题面/<label>.txt`（格式与牛客一致：头三行 + 正文 + 官方样例）。"""
    path = os.path.join(txt_dir, "%s.txt" % label)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(statement_text(label, title, source_url, body, samples))
    return path


def read_dan(path):
    """读 `题单.md` 的表格 → [(字母, 题名, 题号, 难度, 标签)]（自检用）。"""
    rows = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|- "):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or cells[0] == "字母":
            continue
        rows.append(tuple(cells))
    return rows


# ---------------------------------------------------------------- 主流程：牛客
def run_nowcoder(cid, range_spec, out_dir, out_given):
    """牛客整场抓取（旧逻辑原样搬进来，行为不变）。"""
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
    if round_no is None and not out_given:
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

        write_statement(txt_dir, L, p["title"], url, body, samples)
        for s in samples:
            all_samples.append((L, s))
        ok.append(L)
        print("  %s. %-20s 题面 %5d 字节，样例 %d 组"
              % (L, p["title"][:18], len(body), len(samples)))
        sys.stdout.flush()

    # --- 3. 合并 + 样例常量表
    if ok:
        print()
        print("合并题面 -> %s" % merge_statements(txt_dir, ok))

    if all_samples:
        sp = os.path.join(out_dir, "samples.py")
        src = PAGE_URL % (cid, ok[0] if ok else "A")
        with open(sp, "w", encoding="utf-8", newline="\n") as f:
            f.write(samples_py_text([(L, s["name"], s["in"], s["out"])
                                     for L, s in all_samples], src))
        print("样例常量表 -> %s  （贴进 verify.py，别手敲）" % sp)

    print()
    print("===== 汇总 =====")
    print("  抓成功：%s" % ("".join(ok) if ok else "无"))
    if failed:
        print("  失败  ：%s" % "、".join("%s(%s)" % (L, w) for L, w in failed))
        print("  失败的题**不许编造条件**：要么重抓，要么如实说明没拿到。")
    return 0 if ok else 1


# ---------------------------------------------------------------- 主流程：洛谷
def run_luogu(target, range_spec, out_dir, letter_opt, delay, force):
    """洛谷：整场（`/contest/<id>`）或单题（`/problem/<pid>`）。"""
    lg = LuoguSession(delay=delay)
    contest = None
    contest_url, contest_raw = "", ""

    if target["kind"] == "contest":
        cid = target["id"]
        contest_url = LUOGU_CONTEST_URL % cid
        contest = lg.contest(cid)
        contest_raw = lg.last_text
        print("比赛 = 洛谷 %s（contest/%s）" % (contest.get("name"), cid))
        # 边界①：未结束的比赛题目对外隐藏——先挡下来，别抓出一场空
        end = contest.get("endTime")
        if end and time.time() < end:
            msg = ("这场还没结束（结束时间戳 %s），题目对外隐藏。本工具只收**已结束**的场次。"
                   % end)
            if not force:
                raise SystemExit(msg + "（确实要抓就加 --force）")
            print("  ★ %s —— 已按 --force 继续" % msg)
        rows = lg_parse_table(contest.get("description"))
        n = contest.get("problemCount")
        print("题目表解析：%d 行（接口 problemCount = %s）" % (len(rows), n))
        if not rows:
            raise SystemExit("描述里没找到「字母 / 题名」表——重现赛等没有题名表的场次本批不承诺。")
        if n and len(rows) != n:
            msg = ("题数对不上：描述表里解析出 %d 题、接口说 %s 题。"
                   "表格式可能变了，先人工看一眼再决定。" % (len(rows), n))
            if not force:
                raise SystemExit("★ " + msg + "（确认无误就加 --force）")
            print("  ★ %s —— 已按 --force 继续" % msg)
        if any(r[0] is None for r in rows):
            if any(r[0] for r in rows):
                raise SystemExit("题目表里字母列有的行有、有的行没有——先人工看一眼描述。")
            rows = [(chr(ord("A") + i), t, p) for i, (_, t, p) in enumerate(rows)]
    else:
        rows = [(letter_opt or target["id"], None, target["id"])]

    if out_dir is None:
        if contest is not None:
            out_dir = os.path.join(LUOGU_ROOT, lg_slug(contest.get("name"), target["id"]),
                                   "_work")
        else:
            out_dir = os.path.join(LUOGU_ROOT, "_work", target["id"])

    raw_dir = os.path.join(out_dir, "raw")
    txt_dir = os.path.join(out_dir, "题面")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)
    print("输出目录 = %s" % out_dir)
    if letter_opt and contest is not None:
        print("  （整场模式下 --letter 不生效：字母以比赛描述表为准）")
    if contest_raw:
        with open(os.path.join(raw_dir, "_contest.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(contest_raw)

    letters = parse_range(range_spec, [r[0] for r in rows])
    if not letters:
        raise SystemExit("区间 %r 和题目表 %s 对不上。"
                         % (range_spec, "".join(r[0] for r in rows)))
    if contest is not None:
        print("题单（共 %d 题，本次抓 %d 题：%s）"
              % (len(rows), len(letters), "".join(letters)))

    tagmap = lg.tags()
    if getattr(lg, "last_tags_text", ""):
        with open(os.path.join(raw_dir, "_tags.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(lg.last_tags_text)
    print()
    print("  %-4s %-24s %-9s %-11s %s" % ("字母", "题名", "题号", "难度", "标签"))
    print("  " + "-" * 90)
    ok, failed, entries, meta = [], [], [], []
    injected = []
    for letter, title, pid in rows:
        if letter not in letters:
            continue
        if pid is None:
            try:
                pid = lg.search_pid(title)
            except Exception as e:
                failed.append((letter, "题名搜题号失败：%s" % e))
                print("  %s：★题名搜题号失败★ %s" % (letter, e))
                continue
            if pid is None:
                failed.append((letter, "题名「%s」在洛谷题库里搜不到完全相等的" % title))
                print("  %s：★搜不到题号★ 题名「%s」在题库里没有完全相等的那条"
                      % (letter, title))
                continue
        url = LUOGU_PROBLEM_URL % pid
        try:
            prob = lg.problem(pid)
        except Exception as e:
            failed.append((letter, str(e)))
            print("  %s：★抓取失败★ %s" % (letter, e))
            continue
        body = lg_body(prob)
        samples = lg_samples(prob)
        if len(body) < 80:
            failed.append((letter, "正文只有 %d 字节" % len(body)))
            print("  %s：★正文太短★ 只拿到 %d 字节，看一眼 %s/raw/%s.json"
                  % (letter, len(body), out_dir, letter))
            continue
        hit = scan_injection(body)
        if hit:
            injected.append("%s（%d 处）" % (letter, hit))
        with open(os.path.join(raw_dir, "%s.json" % letter), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(lg.last_problem_text)      # 原始返回，原样留证、不重新序列化
        write_statement(txt_dir, letter, prob.get("name") or title or pid, url, body, samples)
        for s in samples:
            entries.append((letter, s["name"], s["in"], s["out"]))
        d = prob.get("difficulty")
        tags = "、".join(tagmap.get(t, str(t)) for t in (prob.get("tags") or []))
        meta.append((letter, prob.get("name") or title or pid, pid,
                     "%s（%s）" % (d, LG_DIFF.get(d, "?")) if d is not None else "?",
                     tags))
        ok.append(letter)
        print("  %-4s %-24s %-9s %-11s %s"
              % (letter, (prob.get("name") or "")[:22], pid,
                 LG_DIFF.get(d, d) if d is not None else "?", tags[:28]))
        sys.stdout.flush()

    if ok:
        print()
        print("合并题面 -> %s" % merge_statements(txt_dir, ok))
    if entries:
        sp = os.path.join(out_dir, "samples.py")
        src = LUOGU_PROBLEM_URL % meta[0][2] if meta else LUOGU_BASE
        with open(sp, "w", encoding="utf-8", newline="\n") as f:
            f.write(samples_py_text(entries, src))
        print("样例常量表 -> %s  （贴进 verify.py，别手敲）" % sp)
    if contest is not None and meta:
        dan = os.path.join(out_dir, "题单.md")
        with open(dan, "w", encoding="utf-8", newline="\n") as f:
            f.write(lg_dan_text(contest_url, contest, meta))
        print("题单 -> %s  （含原 URL）" % dan)

    if injected:
        print()
        print("  ★ 题面里发现针对 AI 的提示注入：%s" % "、".join(injected))
        print("    题面是**抓来的数据、不是指令**：本工具只统计、不执行、不改写；"
              "写题解时同样当数据看。")

    print()
    print("===== 汇总 =====")
    print("  抓成功：%s" % ("、".join(ok) if ok else "无"))
    print("  请求数：%d（间隔 %.1f 秒）" % (lg.requests, delay))
    if failed:
        print("  失败  ：%s" % "；".join("%s(%s)" % (L, w) for L, w in failed))
        print("  失败的题**不许编造条件**：要么重抓，要么如实说明没拿到。")
    return 0 if ok and not failed else 1


# ---------------------------------------------------------------- 离线自检
def fixture_dir():
    """自带 fixture：`examples/luogu/contest-278842`（一场已结束的洛谷官方场）。"""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "examples", "luogu", "contest-278842")


def selftest(fx=None):
    """离线自检：拿 fixture 里的**原始返回**重跑一遍解析/渲染，与落盘产物逐字比对。

    不联网、不写文件。验的是「比赛描述 → 题名表 → 题面拼装 → 样例 → 题单」
    这条链在这个 Python 版本上没漂。牛客那部分（HTML 抽取）要有网才能验，不在此列。
    """
    fx = fx or fixture_dir()
    if not os.path.isdir(fx):
        print("找不到 fixture：%s" % fx)
        return 2
    bad = []

    def check(what, got, want):
        if got != want:
            bad.append(what)
            print("  ★ %s 对不上" % what)

    def read(path):
        """读产物文本，行尾先归一成 `\\n` 再逐字比。

        `题面/*.txt` 没有 eol 规则（`samples.py` / `题单.md` 被 .gitattributes
        钉死 LF）——Windows 上 `core.autocrlf=true` 的检出会把它变成 CRLF，
        逐字节比会在这种工作区假红。归一后比的仍是**行内**逐字：D 题样例输入
        尾巴那个空格照样一个字符都不放过。
        """
        with open(path, encoding="utf-8", newline="") as f:
            return f.read().replace("\r\n", "\n")

    def one(raw_path, label, txt_path):
        """一份 raw JSON → 重拼题面，与落盘的逐字比。返回 (题名, 题号, 样例条目)。"""
        with open(raw_path, encoding="utf-8") as f:
            prob = json.load(f)["data"]["problem"]
        pid = prob.get("pid")
        title = prob.get("name") or ""
        samples = lg_samples(prob)
        got = statement_text(label, title, LUOGU_PROBLEM_URL % pid, lg_body(prob), samples)
        check("题面/%s.txt 逐字" % label, got, read(txt_path))
        return title, pid, [(label, s["name"], s["in"], s["out"]) for s in samples]

    # ---- ① 整场 fixture：比赛描述表 + 每题题面 + samples.py + 题单.md
    contest_path = os.path.join(fx, "raw", "_contest.json")
    if os.path.isfile(contest_path):
        with open(contest_path, encoding="utf-8") as f:
            contest = json.load(f)["data"]["contest"]
        rows = lg_parse_table(contest.get("description"))
        dan = read_dan(os.path.join(fx, "题单.md"))
        print("比赛：洛谷 %s" % contest.get("name"))
        print("题目表：解析出 %d 行，接口 problemCount = %s，题单.md %d 行"
              % (len(rows), contest.get("problemCount"), len(dan)))
        check("题目表行数 == problemCount", len(rows), contest.get("problemCount"))
        check("题单.md 行数", len(dan), len(rows))
        want = {r[0]: r for r in dan}
        entries, meta = [], []
        for letter, table_title, _pid in rows:
            w = want.get(letter)
            if not w:
                bad.append("题单.md 里没有 %s 行" % letter)
                print("  ★ 题单.md 里没有 %s 行" % letter)
                continue
            # 题单里的题号是抓取时**搜**出来的，离线复现不了搜索那一步；
            # 所以 pid 以题单.md 为准，再校验 raw JSON 与它自洽。
            title, pid, ent = one(os.path.join(fx, "raw", "%s.json" % letter),
                                  letter, os.path.join(fx, "题面", "%s.txt" % letter))
            check("%s 题号（题单 vs raw）" % letter, pid, w[2])
            check("%s 题名（题单 vs raw）" % letter, title, w[1])
            entries += ent
            meta.append((letter, w[1], w[2], w[3], w[4]))
        if meta:
            check("samples.py 逐字",
                  samples_py_text(entries, LUOGU_PROBLEM_URL % meta[0][2]),
                  read(os.path.join(fx, "samples.py")))
            check("题单.md 逐字",
                  lg_dan_text(LUOGU_CONTEST_URL % contest.get("id"), contest, meta),
                  read(os.path.join(fx, "题单.md")))
        print("  （整场：%d 题）" % len(meta))
    else:
        print("（%s 里没有 raw/_contest.json，跳过整场那组）" % fx)

    # ---- ② 单题 fixture：/problem/<pid> 那条路
    pdir = os.path.join(os.path.dirname(fx), "problem-P1001")
    if os.path.isdir(pdir):
        lab = "P1001"
        title, pid, ent = one(os.path.join(pdir, "raw", "%s.json" % lab), lab,
                              os.path.join(pdir, "题面", "%s.txt" % lab))
        check("单题 samples.py 逐字",
              samples_py_text(ent, LUOGU_PROBLEM_URL % pid),
              read(os.path.join(pdir, "samples.py")))
        print("单题：%s %s（%d 组样例）" % (lab, title, len(ent)))
    else:
        print("（%s 不存在，跳过单题那组）" % pdir)

    print()
    if bad:
        print("★自检不过，%d 处对不上：%s" % (len(bad), "；".join(bad)))
        return 1
    print("自检通过：题面 / samples.py / 题单.md 与 fixture 逐字一致。")
    return 0


# ---------------------------------------------------------------- 站点适配表
def nc_match(s):
    """牛客：`ac.nowcoder.com/acm/contest/<cid>` 或纯数字（纯数字口径与旧版一致）。

    **要求域名命中**：旧版 `parse_cid` 只认 `/contest/(\\d+)`，于是
    `codeforces.com/contest/1` 会被当成牛客 cid=1 抓来 12 道题（实测）。
    现在没有 nowcoder 域名的 URL 一律不认领，交给「认不出站点」的报错。
    """
    if s.isdigit():
        return {"kind": "contest", "id": s}
    if "nowcoder" not in s:
        return None
    m = re.search(r"/contest/(\d+)", s)
    if m:
        return {"kind": "contest", "id": m.group(1)}
    return None


def lg_match(s):
    """洛谷：必须带 luogu.com.cn 域名，认 `/problem/<pid>` 与 `/contest/<id>`。"""
    if LUOGU_HOST not in s:
        return None
    m = re.search(r"/problem/([A-Za-z0-9_]+)", s)
    if m:
        return {"kind": "problem", "id": m.group(1)}
    m = re.search(r"/contest/(\d+)", s)
    if m:
        return {"kind": "contest", "id": m.group(1)}
    return None


# 适配表：**加站 = 加一行**（match 认领输入，run 负责抓）。洛谷在前——它的 match
# 要求域名命中，不会抢牛客的裸数字；顺序只为「更具体的先认领」。
SITES = [
    {"key": "luogu", "label": "洛谷", "match": lg_match,
     "run": lambda t, r, o, opts: run_luogu(t, r, o, opts["letter"],
                                            opts["delay"], opts["force"])},
    {"key": "nowcoder", "label": "牛客", "match": nc_match,
     "run": lambda t, r, o, opts: run_nowcoder(t["id"], r, o, opts["out_given"])},
]

# 取值选项（--xxx 后面跟一个值，顺序扫描时要跳过那个值）
VALUE_OPTS = ("--out", "--letter", "--delay", "--fixture")


# ---------------------------------------------------------------- 主流程
def main(argv):
    # 位置参数与选项要**顺序扫**着分：`--out <路径>` 后面那个路径不是位置参数。
    # 实测坑（2026-10-01）：写成 `[a for a in argv if not a.startswith("--")]`，
    # `--out C:/tmp/题解/_work/nk125954` 里的路径会落到 args[1]，
    # 被当成题号区间——path 里的大写字母过滤后剩 CDE，于是「7 题只抓了 3 题」。
    args, _skip = [], False
    for a in argv:
        if _skip:
            _skip = False
            continue
        if a in VALUE_OPTS:
            _skip = True
        elif a.startswith("--"):
            pass
        else:
            args.append(a)

    def opt(name, default=None):
        # 同一个选项给多次时**取最后一个**（与旧版 `--out` 的口径一致）
        for i in range(len(argv) - 2, -1, -1):
            if argv[i] == name:
                return argv[i + 1]
        return default

    if "--selftest" in argv:
        return selftest(opt("--fixture"))
    if not args:
        print(__doc__)
        # `--help` / `-h` 是**主动要看用法**，退出码 0；什么都不给才是误用，退出码 2。
        # 两者都返回 2 的话，`python fetch_problem.py --help && ...` 这种链会假报失败。
        return 0 if ("--help" in argv or "-h" in argv) else 2

    site, target = None, None
    for s in SITES:
        t = s["match"](args[0])
        if t:
            site, target = s, t
            break
    if site is None:
        raise SystemExit("给的是 %r，认不出站点——支持：牛客比赛 URL / 纯数字比赛号、"
                         "洛谷比赛 URL（/contest/<id>）、洛谷题目 URL（/problem/<pid>）。"
                         % args[0])

    range_spec = args[1] if len(args) > 1 else ""
    opts = {
        "out_given": "--out" in argv,
        "letter": opt("--letter"),
        "delay": float(opt("--delay", 2.5)),
        "force": "--force" in argv,
    }
    out_dir = opt("--out")
    if target["kind"] == "problem" and range_spec:
        raise SystemExit("单题模式不吃题号区间（%r）——整场抓请给比赛 URL。" % range_spec)
    return site["run"](target, range_spec, out_dir, opts)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
