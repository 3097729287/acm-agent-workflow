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
  4. `parse_contest(s)` —— 场次文本 → `(比赛名, 场次号)` 的**唯一**解析实现。
     只认 `牛客周赛 Round 161` / `Codeforces Round 1000` / `AtCoder ABC 380`
     （ARC / AGC 同）三种写法；带后缀、没比赛名、其它形式一律 `(None, None)`
     —— **绝不猜**。多平台混排时别拿裸场次号当键（Codeforces Round 161 ≠ 牛客 Round 161）。
  5. `is_junk(rel)` / `walk_files(base)` / `copy_tree(...)` —— 题解包（导入导出）
     共用的垃圾过滤与收集：目录名命中 JUNK_DIRS 整棵跳过、后缀命中 JUNK_SUFFIX 剔。

自检：`python toolutil.py`（跑一组断言，全过打印 OK）。
"""
import datetime
import json
import os
import re
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- 配置
def config_path():
    """config.json 的位置：`$AGENT_CP_CONFIG` 优先，否则仓库根；都没有返回 None。"""
    env = os.environ.get("AGENT_CP_CONFIG")
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
BACKUP_ROOT = CONFIG["backup_root"]            # 备份仓：backup_to_repo 的落点
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


# ---------------------------------------------------------------- 场次键
_CONTEST_RES = (
    (re.compile(r"^牛客周赛\s+Round\s+(\d+)$"), "牛客周赛"),
    (re.compile(r"^Codeforces\s+Round\s+(\d+)$"), "Codeforces"),
    (re.compile(r"^AtCoder\s+(?:ABC|ARC|AGC)\s+(\d+)$"), "AtCoder"),
)


def parse_contest(s):
    """场次文本 → (比赛名, 场次号 int)；认不出 → (None, None)，绝不猜。

    只认这三种写法（以后要支持别的再改这一处，别提前发明规则）：
      `牛客周赛 Round 161` / `Codeforces Round 1000` / `AtCoder ABC 380`（ARC / AGC 同）。
    带后缀的（如 `Codeforces Round 1000 (Div. 2)`）、没比赛名的（`Round 161`）、
    其它形式一律 (None, None)。号是 int（`AGC 070` → 70）。
    """
    if not s:
        return None, None
    t = s.strip()
    for rx, name in _CONTEST_RES:
        m = rx.match(t)
        if m:
            return name, int(m.group(1))
    return None, None


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
    assert parse_contest("牛客周赛 Round 161") == ("牛客周赛", 161)
    assert parse_contest("Codeforces Round 1000") == ("Codeforces", 1000)
    assert parse_contest("AtCoder ABC 380") == ("AtCoder", 380)
    assert parse_contest("AtCoder ARC 200") == ("AtCoder", 200)
    assert parse_contest("AtCoder AGC 070") == ("AtCoder", 70)
    assert parse_contest("Codeforces Round 1000 (Div. 2)") == (None, None)
    assert parse_contest("Round 161") == (None, None)
    assert parse_contest("随便写的") == (None, None)
    assert parse_contest("") == (None, None)
    assert parse_contest(None) == (None, None)

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
