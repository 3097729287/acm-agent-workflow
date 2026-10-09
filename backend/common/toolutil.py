# -*- coding: utf-8 -*-
"""toolutil.py —— 本仓库 `tools/` 各脚本的共用底座

只放「两份以上脚本都要用、且抄多份会漂」的东西：

  0. `load_config()` —— 全仓库唯一读 `config.json` 的地方。
     查找顺序：`$AGENT_CP_CONFIG` 环境变量 → 仓库根 `config.json` → 内置默认值；
     相对路径一律相对 config.json 所在目录解析（没有 config 时相对仓库根）。
     字段：`data_root`（资料根）/ `backup_root`（备份仓）/ `desktop_copy_dir`（可选，null = 关）。
  1. `backup_to_repo(path)`  —— 备份规则的唯一实现：
     把**原文件**存进 `<backup_root>/<来源目录镜像>/`，
     时间戳到秒、原目录不留 `.bak`。别再往脚本里抄第二份。
  2. `fence_mask(lines, indent=, tilde=)` —— md 围栏（``` / ~~~）的逐行状态机。
     全库「跳过代码块」的检查共用它；各家的口径差异只剩两个开关：
       - `indent`：行首有空格的围栏算不算（本库文档一律顶格，放宽只为容错）
       - `tilde` ：`~~~` 算不算围栏（目前只有 extract_math 认）
     **已知口径缝**（2026-10-02 记录）：`unify_latex` 用 indent=True/tilde=False、
     `extract_math` 用 indent=True/tilde=True——md 里若出现 `~~~` 块，
     前者当正文转换、后者又跳过它，两边等于没对上。**交付 md 别写 ~~~ 块。**
  3. `fence_blocks(text, languages=, indent=)` —— 逐行扫围栏取块（verify / 对账用）。
  4. `parse_contest(s)` / `format_contest()` / `parse_series_num()` / `contest_paths()` ——
     场次键的**唯一**解析与命名实现（2026-10-08 起不带 `#`）：标准文本 = `周赛 164` /
     `入门赛 52` / `月赛 304` / `ABC 478` / `Div.2 1124`…；目录 = `题解\\<平台>\\<系列>\\<号>\\`。
     认不出一律 `(None, None)` —— **绝不猜**。`SERIES` 表 = 系列 → 目录 / 平台家族 / 文本模板；
     旧写法（`牛客周赛 Round 161` 等）已随全库迁移废弃。
  5. `is_junk(rel)` / `walk_files(base)` / `copy_tree(...)` —— 题解包（导入导出）
     共用的垃圾过滤与收集：目录名命中 JUNK_DIRS 整棵跳过、后缀命中 JUNK_SUFFIX 剔。
  6. `run_sibling(script, args)` —— 跑 `tools\\` 里的兄弟脚本 → 退出码：源码环境起
     子进程（与手跑一致），frozen（PyInstaller 打的 exe，没有解释器可用）进程内
     import 调 `main()` —— 两种形态行为对齐，capture=True 时都把输出抓成字符串。

自检：`python toolutil.py`（跑一组断言，全过打印 OK）。
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

if getattr(sys, "frozen", False):
    # PyInstaller 打包的 exe：代码在临时解包目录里，资源（config.json / knowledge\ /
    # demo\）都在 **exe 旁边** —— REPO_ROOT 跟着 exe 走，别去找一次性临时目录。
    REPO_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------- 配置
def config_path():
    """config.json 的位置：`$AGENT_CP_CONFIG` 优先，否则仓库根；都没有返回 None。"""
    env = os.environ.get("TB_ARCHIVE_CONFIG")
    if env:
        return env if os.path.isfile(env) else None
    p = os.path.join(REPO_ROOT, "config.json")
    return p if os.path.isfile(p) else None


def _abspath(base, p):
    p = os.path.expanduser(os.path.expandvars(str(p)))
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def load_config():
    """读 config.json（没有就回落内置默认值），返回 dict。

    相对路径相对 config.json 所在目录解析；没有 config.json 时相对仓库根。
    配置写坏（JSON 语法错）直接报错退出 —— 静默回落会让人把数据写到错地方。
    """
    cfg_path = config_path()
    base = os.path.dirname(os.path.abspath(cfg_path)) if cfg_path else REPO_ROOT
    raw = {}
    if cfg_path:
        try:
            with open(cfg_path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            sys.exit("config.json 读取失败（%s）：%s" % (cfg_path, e))
    d = raw.get("desktop_copy_dir")
    return {
        "data_root": _abspath(base, raw.get("data_root") or "demo"),
        "backup_root": _abspath(base, raw.get("backup_root") or ".backups"),
        "desktop_copy_dir": _abspath(base, d) if d else None,
    }


CONFIG = load_config()
DATA_ROOT = CONFIG["data_root"]                # 资料根：<它>/题解、<它>/算法、<它>/索引
BACKUP_ROOT = os.environ.get("TB_BACKUP_DIR") or str(__import__("paths").STATE / "backups")            # 备份仓：backup_to_repo 的落点
DESKTOP_COPY_DIR = CONFIG["desktop_copy_dir"]  # None = 关闭桌面副本功能


# ---------------------------------------------------------------- 备份
def backup_to_repo(path, src_root=None):
    """把 path 的原件备份进 backups\\<来源目录镜像>\\，返回 .bak 路径。

    镜像名 = 来源目录去掉冒号、反斜杠 / 斜杠换下划线（`C:\\proj\\data`
    → `C_proj_data`）。src_root 缺省取 path 自己的 dirname。
    同一秒里对同一文件再备一次会自动加 `-2`、`-3`——宁可名字微变也不覆盖，
    两个 .bak 都在，回溯能力不打折。
    """
    path = os.path.abspath(path)
    d = os.path.abspath(src_root) if src_root else os.path.dirname(path)
    mirror = d.replace(":", "").replace("\\", "_").replace("/", "_")
    bdir = os.path.join(BACKUP_ROOT, mirror)
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.basename(path) + "." + ts
    dst = os.path.join(bdir, base + ".bak")
    k = 2
    while os.path.exists(dst):
        dst = os.path.join(bdir, "%s-%d.bak" % (base, k))
        k += 1
    shutil.copy2(path, dst)
    return dst


# ---------------------------------------------------------------- 围栏
def _is_fence(s, tilde):
    return s.startswith("```") or (tilde and s.startswith("~~~"))


def fence_mask(lines, indent=False, tilde=False):
    """逐行布尔列表：该行是否属于围栏块（**含围栏行本身**）。

    未闭合的开围栏 → 之后所有行都算块内（与全库既有实现一致：宁可多跳不误伤）。
    """
    out, on = [], False
    for ln in lines:
        s = ln.strip() if indent else ln
        if _is_fence(s, tilde):
            out.append(True)
            on = not on
        else:
            out.append(on)
    return out


_FENCE_RE = re.compile(r"^```\s*([\w+]*)\s*$")


def fence_blocks(text, languages=None, indent=False):
    """逐行扫围栏取块，返回 [(info, start, body, end)]。

    info   = 开围栏行去掉 ``` 后的信息串（小写；` ```cpp ` → `cpp`）
    start  = 开围栏行号（0 基）；end = 闭围栏行号；body = 块内容行列表（不含围栏行）
    languages 给集合时只收 info 命中的块——**裸围栏 info="" 要显式放进集合才收**
    （verify 不收裸块、check_solution 第 5 项收，就是靠这个区分）。
    未闭合的开围栏**不产出**（不猜结尾）；与围栏模式不匹配的 ``` 开头行
    （如 ` ```c++ foo `）按普通内容行进 body，不翻转状态。
    """
    lines = text.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        cur = lines[i]
        s = cur.rstrip() if indent else cur
        m = _FENCE_RE.match(s)
        if not m:
            i += 1
            continue
        info = m.group(1).lower()
        # 找闭围栏
        j = i + 1
        close = None
        while j < n:
            s2 = lines[j].rstrip() if indent else lines[j]
            if _FENCE_RE.match(s2):
                close = j
                break
            j += 1
        if close is None:
            break                      # 未闭合：整段丢，不再产出
        if languages is None or info in languages:
            out.append((info, i, lines[i + 1:close], close))
        i = close + 1
    return out


# ---------------------------------------------------------------- 垃圾过滤
# 题解包（导出 / 导入）共用的过滤口径：包里只装源码与文档，装不装都行的耗材一律剔除。
#   目录名命中 → 整棵跳过；文件名后缀命中 → 剔。
# 与《归档》的「清理约定」同一口径（不留 .exe / png；_work\ 是耗材）。
JUNK_DIRS = {"_work", "__pycache__", ".git", ".claude", ".vs", ".vscode", "node_modules"}
JUNK_SUFFIX = (".exe", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pyc",
               ".o", ".obj", ".bak", ".orig", "~", ".zip", ".7z", ".rar", ".log")
BS_SEP = chr(92)          # 反斜杠


def is_junk(rel):
    """相对路径是否为垃圾（包过滤口径）。目录名命中即算，别只比文件名。"""
    parts = rel.replace("\\", "/").strip("/").split("/")
    if any(p in JUNK_DIRS for p in parts):
        return True
    fn = parts[-1]
    return fn.endswith(JUNK_SUFFIX)


def to_os(rel):
    """库内相对路径（一律反斜杠写法）→ 本机路径分隔符。

    题解包 / 索引 / manifest 里的相对路径**统一写反斜杠**（跨机器一个口径），
    拼本机路径前必须换成本机分隔符：Windows 上是 no-op，Linux/macOS 上换成 `/`。
    不换的话 `os.path.join(root, "题解\\牛客周赛\\x.md")` 在 Linux 上会变成
    **一个名字里带反斜杠的文件**，而不是三层目录。
    """
    if os.sep == BS_SEP:
        return rel
    return rel.replace(BS_SEP, os.sep)


def walk_files(base):
    """递归列文件 → [(绝对路径, 相对 base 的路径)]，垃圾已过滤、按相对路径排序。

    相对路径统一用反斜杠（Windows 习惯，与库里其它工具一致；os.walk 会保留
    输入路径的斜杠风格，这里强制归一，别让 `B-G/B/b.cpp` 和 `B-G\\B\\b.cpp` 两种写法并存）。
    """
    out = []
    for dp, dns, fns in os.walk(base):
        dns[:] = sorted(d for d in dns if d not in JUNK_DIRS)
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, base).replace(os.sep, BS_SEP).replace("/", BS_SEP)
            if is_junk(rel):
                continue
            out.append((p, rel))
    out.sort(key=lambda x: x[1])
    return out


def copy_tree(src_base, dst_base, files=None, overwrite=False):
    """把 files（[(绝对路径, 相对路径)]，缺省 = walk_files(src_base)）复制到 dst_base 下。

    返回 (copied, skipped)：skipped = 目标已存在且 overwrite=False 的相对路径。
    只建需要的子目录；行尾 / 编码原样保留（二进制复制）。
    """
    if files is None:
        files = walk_files(src_base)
    copied, skipped = [], []
    for src, rel in files:
        dst = os.path.join(dst_base, to_os(rel))
        if os.path.exists(dst) and not overwrite:
            skipped.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied, skipped


# ---------------------------------------------------------------- 场次键（2026-10-07 新命名方案）
#
# 命名方案（用户 2026-10-07 拍板，全库统一；2026-10-08 修订：入门赛 / 基础赛不再带 `#`）：
#   TB 场次列 = `<系列> <号>`（留空格、统一不带 `#`）
#   题解目录 = `题解\<平台>\<系列>\<号>\`；题解 md = `<号>题解.md`
# 各系列的「号」：牛客 = 系列期号；洛谷 = 入门赛/基础赛的期号、月赛的 LGR 号（省略 LGR 前缀）；
# AtCoder = ABC/ARC 号；CF = Round 号（同号有 Div.1/Div.2 两场，所以 Div 进系列名）。
# 旧写法（`牛客周赛 Round 161` / `Codeforces Round 1000` / `AtCoder ABC 380`）已随
# 2026-10-07 的全库迁移废弃——别再往白名单里加回来。
SERIES = {
    # 系列名: 题解根下目录链 / 平台家族 / 场次文本模板
    "周赛":     {"dir": ("牛客", "周赛"),        "plat": "nowcoder",  "fmt": "%s %d"},
    "小白月赛": {"dir": ("牛客", "小白月赛"),    "plat": "nowcoder",  "fmt": "%s %d"},
    "练习赛":   {"dir": ("牛客", "练习赛"),      "plat": "nowcoder",  "fmt": "%s %d"},
    "挑战赛":   {"dir": ("牛客", "挑战赛"),      "plat": "nowcoder",  "fmt": "%s %d"},
    "入门赛":   {"dir": ("洛谷", "入门赛"),      "plat": "luogu",     "fmt": "%s %d"},
    "基础赛":   {"dir": ("洛谷", "基础赛"),      "plat": "luogu",     "fmt": "%s %d"},
    "月赛":     {"dir": ("洛谷", "月赛"),        "plat": "luogu",     "fmt": "%s %d"},
    "ABC":      {"dir": ("AtCoder", "ABC"),      "plat": "atcoder",   "fmt": "%s %d"},
    "ARC":      {"dir": ("AtCoder", "ARC"),      "plat": "atcoder",   "fmt": "%s %d"},
    "AGC":      {"dir": ("AtCoder", "AGC"),      "plat": "atcoder",   "fmt": "%s %d"},
    "Div.2":    {"dir": ("Codeforces", "Div.2"), "plat": "codeforces", "fmt": "%s %d"},
    "Div.3":    {"dir": ("Codeforces", "Div.3"), "plat": "codeforces", "fmt": "%s %d"},
    "Div.4":    {"dir": ("Codeforces", "Div.4"), "plat": "codeforces", "fmt": "%s %d"},
}


def _m_atcoder(m):
    return m.group(1), int(m.group(2))


def _m_div(m):
    return "Div." + m.group(1), int(m.group(2))


_CONTEST_RES = (
    (re.compile(r"^周赛\s+(\d+)$"), "周赛"),
    (re.compile(r"^小白月赛\s+(\d+)$"), "小白月赛"),
    (re.compile(r"^练习赛\s+(\d+)$"), "练习赛"),
    (re.compile(r"^挑战赛\s+(\d+)$"), "挑战赛"),
    (re.compile(r"^入门赛\s*#?\s*(\d+)$"), "入门赛"),      # `#` 可选：兼容 2026-10-08 前的旧文本
    (re.compile(r"^基础赛\s*#?\s*(\d+)$"), "基础赛"),
    (re.compile(r"^月赛\s+(\d+)$"), "月赛"),
    (re.compile(r"^(ABC|ARC|AGC)\s+(\d+)$"), _m_atcoder),
    (re.compile(r"^Div\.\s*([234])\s+(\d+)$"), _m_div),
)


def parse_contest(s):
    """场次文本 → (系列名, 场次号 int)；认不出 → (None, None)，绝不猜。

    认这几种写法（2026-10-08 起不带 `#`；旧文本 `入门赛 #52` 也照认）：
      `周赛 164` / `小白月赛 137` / `练习赛 157` / `挑战赛 92` /
      `入门赛 52` / `基础赛 40` / `月赛 304` /
      `ABC 478` / `ARC 231`（AGC 同）/ `Div.2 1124`（Div.3 / Div.4 同）。
    其它形式一律 (None, None)。号是 int。
    """
    if not s:
        return None, None
    t = s.strip()
    for rx, name in _CONTEST_RES:
        m = rx.match(t)
        if not m:
            continue
        if callable(name):
            return name(m)
        return name, int(m.group(1))
    return None, None


def format_contest(name, num):
    """(系列名, 号) → 场次列的标准文本（parse_contest 的逆）。认不出的系列 → None。"""
    spec = SERIES.get(name)
    if not spec:
        return None
    return spec["fmt"] % (name, int(num))


def parse_series_num(s):
    """CLI 友好解析：`周赛164` / `周赛 164` / `Div.2 1124` / `Div.21124` / `入门赛#52`
    → (系列名, 号)；认不出 (None, None)。

    与 parse_contest 的分工：那个解析 **TB 里的标准文本**（严格）；
    这个放宽给命令行用（系列名和号之间可以有空格 / 无空格 / `#`）。
    """
    if not s:
        return None, None
    t = s.strip()
    for name in sorted(SERIES, key=len, reverse=True):   # 长的优先（小白月赛 > 月赛）
        if t.startswith(name):
            rest = t[len(name):].lstrip(" \t#·-—　")
            if rest.isdigit():
                return name, int(rest)
    return None, None


def contest_paths(data_root, name, num):
    """(系列, 号) → (题目录, 题解 md 路径)；认不出的系列 → (None, None)。

    题目录 = `<data_root>\\题解\\<平台>\\<系列>\\<号>`；md = 目录里的 `<号>题解.md`。
    """
    spec = SERIES.get(name)
    if not spec:
        return None, None
    d = os.path.join(data_root, "题解", *spec["dir"], str(int(num)))
    return d, os.path.join(d, "%d题解.md" % int(num))


# ---------------------------------------------------------------- md 表格
def split_cells(line):
    """切一行 md 表格；尊重转义的 \\|。不是表格行（不以 | 开头）→ None。

    （status_report / status_gui 各自保留历史实现；新代码一律走这里，别再加第三份。）"""
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


def parse_catalog(path):
    """读一份题解 md 的「## 目录」表 → {字母: (题名, 考点, 难度)}。

    表固定四列（题号 / 题名 / 考点 / 难度，check_solution 第 10 项把关）。
    2026-10-06 起 = TB「知识点」列与题解包取数的唯一入口（算法库 / 全量索引已删）。
    2026-10-08：题名出口一律过 `strip_title_prefix`（比赛代号前缀不落 TB / 题解包）——
    防回流单一实现点；题解 md 若还带前缀，读出来也是干净的。"""
    out = {}
    inside = False
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    for line in lines:
        if not inside:
            if re.match(r"^##(?!#)\s+目录\s*$", line):
                inside = True
            continue
        if re.match(r"^##(?!#)\s", line):        # 下一个二级标题 → 目录节结束
            break
        c = split_cells(line)
        if c and len(c) == 4 and re.fullmatch(r"[A-Z][0-9]?", c[0]):
            out[c[0]] = (strip_title_prefix(c[1]), c[2], c[3])
    return out


# ---------------------------------------------------------------- 对账报告器 / 状态表（TB）
_TITLE_PREFIX_RE = re.compile(r"^[\[「【][^\]」】]*[\]」】][ \t　]*")


def strip_title_prefix(s):
    """题名去掉开头的比赛代号前缀（用户 2026-10-08 口径，全库统一）：
    `[语言月赛 202605] 火车` → `火车`；`[Algo Beat Contest 017 B] 线性筛` → `线性筛`；
    `「YLLOI-R4-T2」听妈妈的话` → `听妈妈的话`。

    只剥开头的第一个方括号 / 书名号块（连同其后空白）；剥完为空则原样返回（防误伤）。
    版本后缀（`(easy)` / `(Hard ver.)` / `(Ver. 1)`）在题名里不在开头，不受影响。
    """
    t = (s or "").strip()
    out = _TITLE_PREFIX_RE.sub("", t).strip()
    return out or t


def norm_title(s):
    """题名宽松比对键：去 LaTeX（`$`、`\\命令`）、括号全半角统一、去空白。

    题解 md 是交付文档（数学一律写 LaTeX、`$\\gcd$` 那种），TB 是数据表（纯文本）——
    两处题名格式本来就允许不同，所以题名只做宽松比对、只出「提醒」。
    （2026-10-07 从 tb_sync 上收——tb_inbox 共用同一份。）
    2026-10-08：先过 `strip_title_prefix` —— 带前缀与不带前缀的同名题不误报不一致。"""
    s = strip_title_prefix(s)
    s = re.sub(r"\\[a-zA-Z]+", lambda m: m.group(0)[1:], s)     # \gcd → gcd
    """题名宽松比对键：去 LaTeX（`$`、`\\命令`）、括号全半角统一、去空白。

    题解 md 是交付文档（数学一律写 LaTeX、`$\\gcd$` 那种），TB 是数据表（纯文本）——
    两处题名格式本来就允许不同，所以题名只做宽松比对、只出「提醒」。
    （2026-10-07 从 tb_sync 上收——tb_inbox 共用同一份。）"""
    s = re.sub(r"\\[a-zA-Z]+", lambda m: m.group(0)[1:], s)     # \gcd → gcd
    s = s.replace("$", "").replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", s)


TB_HEADER = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]   # TB.md 主表表头（唯一口径）


class Rep(object):
    """三种状态的对账报告器：每条都给「证据」原文，别只报有 / 无。

    （2026-10-06 archive_check 删后收进底座；tb_sync / import_solution 共用这一份。）"""

    def __init__(self):
        self.items = []          # (状态, 名称, [明细...])

    def _add(self, st, name, detail):
        for it in self.items:
            if it[0] == st and it[1] == name:
                it[2].append(detail)
                return
        self.items.append((st, name, [detail]))

    def ok(self, name, detail=""):
        self._add("通过", name, detail)

    def bad(self, name, detail=""):
        self._add("问题", name, detail)

    def warn(self, name, detail=""):
        self._add("提醒", name, detail)

    @property
    def failed(self):
        return any(st == "问题" for st, _, _ in self.items)

    @property
    def n_warn(self):
        return sum(1 for st, _, _ in self.items if st == "提醒")


def print_report(rep, quiet=False):
    """Rep → 标准输出（问题在前、提醒次之、通过最后）；返回「问题」条数。"""
    order = {"问题": 0, "提醒": 1, "通过": 2}
    for st, name, details in sorted(rep.items, key=lambda x: order[x[0]]):
        if quiet and st == "通过":
            continue
        print("[%s] %s" % (st, name))
        for d in details:
            print("        " + d)
    return sum(1 for st, _, _ in rep.items if st == "问题")


def lf_report(rep, name, path):
    """行尾 / BOM / 控制字符：本库约定纯 LF、UTF-8 无 BOM（返回是否通过）"""
    b = open(path, "rb").read()
    crlf = b.count(b"\r\n")
    bom = b[:3] == b"\xef\xbb\xbf"
    txt = b.decode("utf-8", "replace")
    bad = sorted({hex(ord(c)) for c in txt if ord(c) < 32 and c not in "\n\t"})
    if crlf or bom or bad:
        msg = []
        if crlf:
            msg.append("CRLF %d 处" % crlf)
        if bom:
            msg.append("有 BOM")
        if bad:
            msg.append("控制字符 %s" % ", ".join(bad))
        rep.bad(name, "行尾/编码：%s  ← %s" % ("；".join(msg), path))
        return False
    rep.ok(name, "纯 LF、无 BOM、无控制字符  ← %s" % path)
    return True


def status_rows(path, contest, n):
    """TB 里某一场的数据行 → ([(行号 1-based, cells)], 错误文案, [(行号, 场次文本)] 认不出的行)。

    表头锚点 = TB_HEADER；读不到表头 / 文件不在 → 返回错误文案（不抛异常，调用方自己报）。
    行首场次走 parse_contest 认；认不出的行绝不按裸号处理（单独收集，调用方决定怎么报）。"""
    if not os.path.exists(path):
        return [], "找不到状态表 %s" % path, []
    lines = open(path, encoding="utf-8").read().split("\n")
    i0 = next((i for i, l in enumerate(lines) if split_cells(l) == TB_HEADER), None)
    if i0 is None:
        return [], "状态表里没找到表头「| %s |」：%s" % (" | ".join(TB_HEADER), path), []
    rows, unparsed = [], []
    for i, l in enumerate(lines[i0 + 2:], i0 + 3):   # +2：表头下面紧跟一行分隔线
        c = split_cells(l)
        if not c or len(c) != len(TB_HEADER):
            break                        # 主表结束（后面是别的段落）
        if set("".join(c)) <= set("-: "):
            continue
        name, num = parse_contest(c[0])
        if name is None:
            unparsed.append((i, c[0]))
            continue
        if (name, num) == (contest, n):
            rows.append((i, c))
    return rows, None, unparsed


def find_table_tail(lines):
    """TB 主表最后一个数据行的行号（容忍表尾空行）；找不到表头 → None。

    （2026-10-07 从 tb_sync 上收——tb_inbox 共用同一份；「表尾之后」的内容一律不碰。）"""
    i0 = next((i for i, l in enumerate(lines)
               if split_cells(l) == TB_HEADER), None)
    if i0 is None:
        return None
    last = i0 + 1
    for i in range(i0 + 2, len(lines)):
        if split_cells(lines[i]) is not None:
            last = i
        elif lines[i].strip() == "":
            continue                      # 表尾空行：继续往后找表格行
        else:
            break                         # 第一个有内容的非表格行 = 表结束
    return last


def write_text_atomic(path, text):
    """整文件原子替换：同目录临时文件（mkstemp）→ flush + fsync → os.replace。

    v67（status_gui）口径上收：直接 open('w') 截断写在写一半崩掉时会把原文件留成半截；
    现在最坏只是临时文件残留、原文件完好。临时文件必须与目标同目录（同卷 rename 才是原子）。
    写出永远是 UTF-8 无 BOM、不翻译换行（即纯 LF）；写后校验交给调用方。"""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- 跑兄弟脚本
def run_sibling(script, args, capture=False):
    """跑 `tools\\` 下的兄弟脚本 → 退出码（capture=True 时 → (退出码, 输出文本)）。

    源码环境 = 起子进程跑 `python tools\\<script> ...`（输出继承控制台 / 捕获，与手跑
    完全一致）；frozen（PyInstaller 打的 exe 里没有解释器可用）= 进程内 import 后调
    `main()`，capture=True 时临时把 stdout / stderr 换成字符串缓冲——调用方在两种
    环境看到的行为对齐。子脚本清单必须随 exe 一起打包（见打包说明的 --hidden-import）。
    """
    if not getattr(sys, "frozen", False):
        cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", script)] + list(args)
        if capture:
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT,
                               encoding="utf-8", errors="replace")
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode
    # frozen：没有解释器 → 进程内调用（模块已随 exe 打包）
    import importlib
    import io
    import traceback
    buf = io.StringIO() if capture else None
    old = (sys.stdout, sys.stderr) if buf is not None else None
    if old:
        sys.stdout = sys.stderr = buf
    try:
        # import 也放进 try：子脚本**模块顶层**出错（如自己调 stdout.reconfigure）
        # 要跟子进程里一样得到「traceback + 退出码 1」，而不是把调用方整个炸掉。
        mod = importlib.import_module(script[:-3] if script.endswith(".py") else script)
        rc = mod.main(list(args))
    except SystemExit as e:                       # 子脚本个别处若调了 exit()：当退出码
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:
        traceback.print_exc()                     # 与子进程的 stderr traceback 对齐
        rc = 1
    finally:
        if old:
            sys.stdout, sys.stderr = old
    if buf is not None:
        return rc, buf.getvalue()
    return rc


# ---------------------------------------------------------------- 自检
def _selftest():
    lines = ["a", "```cpp", "int x;", "```", "b", "```", "图表", "```", "c"]
    m = fence_mask(lines)
    assert m == [False, True, True, True, False, True, True, True, False], m
    m2 = fence_mask(["  ```", "x", "  ```"], indent=True)
    assert m2 == [True, True, True], m2
    assert fence_mask(["```", "x"], indent=False) == [True, True]   # 未闭合
    assert fence_mask(["~~~", "x", "~~~"], tilde=True) == [True, True, True]

    text = "前言\n```cpp\nint a;\nint b;\n```\n中间\n```\n裸块\n```\n后记\n```c++ foo\n假围栏行\n```\n"
    bs = fence_blocks(text, languages=("cpp",))
    assert len(bs) == 1 and bs[0][0] == "cpp"
    assert bs[0][2] == ["int a;", "int b;"]
    assert (bs[0][1], bs[0][3]) == (1, 4)
    bs2 = fence_blocks(text, languages=("cpp", ""))
    assert [b[0] for b in bs2] == ["cpp", ""]
    # ` ```c++ foo ` 不匹配围栏模式 → 当内容；其后 ``` 收尾
    bs3 = fence_blocks("```cpp\nx\n```c++ foo\ny\n```\n", languages=None)
    assert bs3[0][2] == ["x", "```c++ foo", "y"], bs3
    assert fence_blocks("```cpp\n没有闭围栏\n") == []

    # 场次键：只认三种写法，认不出绝不猜（不许取最后一个数字兜底）
    assert parse_contest("周赛 164") == ("周赛", 164)
    assert parse_contest("小白月赛 137") == ("小白月赛", 137)
    assert parse_contest("练习赛 157") == ("练习赛", 157)
    assert parse_contest("挑战赛 92") == ("挑战赛", 92)
    assert parse_contest("入门赛 52") == ("入门赛", 52)
    assert parse_contest("基础赛 40") == ("基础赛", 40)
    assert parse_contest("入门赛 #52") == ("入门赛", 52)      # 旧文本（2026-10-08 前）兼容
    assert parse_contest("基础赛 #40") == ("基础赛", 40)
    assert parse_contest("月赛 304") == ("月赛", 304)
    assert parse_contest("ABC 478") == ("ABC", 478)
    assert parse_contest("ARC 231") == ("ARC", 231)
    assert parse_contest("AGC 70") == ("AGC", 70)
    assert parse_contest("Div.2 1124") == ("Div.2", 1124)
    assert parse_contest("Div. 4 1090") == ("Div.4", 1090)
    assert parse_contest("牛客周赛 Round 161") == (None, None)      # 旧写法已废
    assert parse_contest("Codeforces Round 1000") == (None, None)
    assert parse_contest("Round 161") == (None, None)
    assert parse_contest("随便写的") == (None, None)
    assert parse_contest("") == (None, None)
    assert parse_contest(None) == (None, None)
    assert format_contest("周赛", 164) == "周赛 164"
    assert format_contest("入门赛", 52) == "入门赛 52"
    assert format_contest("基础赛", 40) == "基础赛 40"
    assert format_contest("Div.2", 1124) == "Div.2 1124"
    assert format_contest("查无此赛", 1) is None
    assert parse_series_num("周赛164") == ("周赛", 164)
    assert parse_series_num("周赛 164") == ("周赛", 164)
    assert parse_series_num("Div.2 1124") == ("Div.2", 1124)
    assert parse_series_num("Div.21124") == ("Div.2", 1124)
    assert parse_series_num("入门赛#52") == ("入门赛", 52)
    assert parse_series_num("月赛 304") == ("月赛", 304)
    assert parse_series_num("小白月赛 137") == ("小白月赛", 137)
    assert parse_series_num("Round164") == (None, None)
    assert contest_paths("X:/R", "周赛", 164) == \
        (os.path.join("X:/R", "题解", "牛客", "周赛", "164"),
         os.path.join("X:/R", "题解", "牛客", "周赛", "164", "164题解.md"))
    assert contest_paths("X:/R", "查无此赛", 1) == (None, None)

    # 题名前缀剥离（2026-10-08 口径）+ 宽松比对口径
    assert strip_title_prefix("[语言月赛 202605] 火车") == "火车"
    assert strip_title_prefix("[语言月赛202606]贴纸整理") == "贴纸整理"
    assert strip_title_prefix("[入门赛 #52] 中秋灯谜") == "中秋灯谜"
    assert strip_title_prefix("[Algo Beat Contest 017 B] 线性筛") == "线性筛"
    assert strip_title_prefix("「YLLOI-R4-T2」听妈妈的话") == "听妈妈的话"
    assert strip_title_prefix("小红的出牌（easy）") == "小红的出牌（easy）"     # 无前缀不动
    assert strip_title_prefix("Gap Swap (easy)") == "Gap Swap (easy)"
    assert strip_title_prefix("[只有括号]") == "[只有括号]"                  # 剥完为空 → 原样返回
    assert strip_title_prefix("") == "" and strip_title_prefix(None) == ""
    assert norm_title("[语言月赛 202605] 火车") == norm_title("火车")        # 带 / 不带前缀同键

    # md 表格：切格 + 题解目录表解析（parse_catalog 的取数口）
    assert split_cells("| A | 题名 | 考点 | CF 800 |") == ["A", "题名", "考点", "CF 800"]
    assert split_cells("| a\\|b | c |") == ["a|b", "c"]
    assert split_cells("不是表格") is None
    import tempfile
    tf = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8",
                                     newline="\n")
    tf.write("# 某场题解\n\n## 目录\n\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n"
             "| A | 签到 | 模拟 | CF 800 |\n| B | 好题 | 二分查找 | CF 1500 |\n"
             "| C | [语言月赛 202605] 火车 | 模拟 | CF 800 |\n"
             "\n## A. 签到\n\n正文\n")
    tf.close()
    cat = parse_catalog(tf.name)
    os.unlink(tf.name)
    assert cat == {"A": ("签到", "模拟", "CF 800"), "B": ("好题", "二分查找", "CF 1500"),
                   "C": ("火车", "模拟", "CF 800")}, cat        # C：前缀在出口被剥掉

    # 垃圾过滤：目录名命中整棵跳过、后缀命中剔；真源码一律留
    assert is_junk("B\\_work\\tmp.txt")
    assert is_junk("__pycache__\\a.pyc")
    assert is_junk("B\\b.exe")
    assert is_junk("B\\图.png")
    assert is_junk("B\\b.cpp.bak")
    assert is_junk("B\\b.orig")
    assert is_junk("B\\b.cpp~")
    assert not is_junk("B\\b.cpp")
    assert not is_junk("B\\verify_b.py")
    assert not is_junk("B\\samples.py")
    assert not is_junk("Round163题解.md")
    assert not is_junk("专题\\例子分析器.py")
    print("toolutil 自检 OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    _selftest()
