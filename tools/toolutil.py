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
    print("toolutil 自检 OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    _selftest()
