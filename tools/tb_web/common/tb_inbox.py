# -*- coding: utf-8 -*-
r"""tb_inbox —— 收件箱：把题解 md 放进去 → 自动收进 TB
============================================================

    python tb_inbox.py [--root <数据根>] [--status <TB>] [--apply]
                       [--on-conflict skip|overwrite] [--quiet] [--selftest]

收件箱 = `<数据根>\题解\_收件箱\`（不存在会自动创建）。把一个题解 md（单文件，
带「## 目录」表）放进去，打开 TB 工具（或按 F5）时自动扫描：

  · 目录表里 TB 没有的题 → **照单全收**（含签到题），追加到 TB 表尾
    （状态「未做」、日期空；知识点按词典归一）。
  · 已在 TB 且一致的题 → **静默跳过**（幂等：重复扫描不会重复动作）。
  · 已在 TB 但内容不一致（题名宽松比对 / 难度 / 知识点任一不同）→ **冲突**：
    GUI 里弹窗等拍板（全部跳过 / 覆盖更新 / 取消本次）；CLI 里按
    `--on-conflict skip|overwrite`。「全部跳过」按内容 sha1 记进
    `_收件箱\_跳过.json` —— 同一份 md 不改动就不再重复提示（删掉该文件即重置）。
  · 读不出场次 / 读不到目录表 → 报告并跳过该文件（绝不猜场次）。

md 留在原地（工具不动收件箱里的文件）。写 TB 走：备份 → 写前 mtime
乐观锁（与 status_gui v67 同口径）→ 原子替换 → 复读校验；且只许动
「目标行 + 表尾追加」，其余字节一个不改。

退出码：0 = 跑完；1 = 有文件读不了（errors 非空）；2 = 状态表不可读 / 参数错。
GUI 集成见 status_gui.py 的 _inbox_check（打开工具时 / F5 时调用）。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil        # noqa: E402
import knowledge_dict  # noqa: E402

INBOX_NAME = "_收件箱"
SKIP_NAME = "_跳过.json"      # 「全部跳过」备忘录（按内容 sha1；见模块头）
STATUS_DEFAULT = os.path.join(toolutil.DATA_ROOT, "题解", "TB.md")


# ---------------------------------------------------------------- 小工具
def rd(p):
    return open(p, encoding="utf-8").read()


def inbox_dir(root):
    return os.path.join(root.replace("/", os.sep), "题解", INBOX_NAME)


def norm_diff(s):
    """难度比对/落盘口径：去空白、去 `CF ` 前缀（2026-10-06 起表里是纯数字）。"""
    return re.sub(r"^CF\s*", "", (s or "").strip())


def plain_title(s):
    r"""题解目录表题名 → TB 纯文本：`$\gcd$` 这类 LaTeX 记号去掉、命令名留下。

    题名比对另走宽松口径（toolutil.norm_title）；这里只管落盘观感——
    TB 是数据表，不入 LaTeX（现表全表无 `$`，与本函数产物一致）。"""
    s = re.sub(r"\\[a-zA-Z]+", lambda m: m.group(0)[1:], s)   # \gcd → gcd
    return s.replace("$", "").strip()


RE_CONTEST_ANY = re.compile(
    r"(小白月赛|练习赛|挑战赛|周赛|入门赛|基础赛|月赛|ABC|ARC|AGC|Div\.\s*[234])"
    r"\s*#?\s*(\d+)")


def _search_contest(s):
    """在一段文本里找场次 → (场次文本, 系列名, 号) 或 None。绝不猜。

    2026-10-08 起命名：认 `周赛 164` / `入门赛 52` / `Div.2 1124`（写进标题 / 文件名）；
    标题里旧式 `入门赛 #52` 也照认；旧写法只兼容牛客周赛（`牛客周赛 Round N` → `周赛 N`）
    与 AtCoder（`AtCoder ABC N`）。
    """
    for m in RE_CONTEST_ANY.finditer(s or ""):
        t = toolutil.format_contest(m.group(1).replace(" ", ""), int(m.group(2)))
        if not t:
            continue
        name, num = toolutil.parse_contest(t)
        if name:
            return (t, name, num)
    m = re.search(r"牛客周赛\s*Round\s*(\d+)", s)
    if m:
        t = "周赛 %d" % int(m.group(1))
        return (t,) + toolutil.parse_contest(t)
    m = re.search(r"AtCoder\s+(ABC|ARC|AGC)\s*(\d+)", s)
    if m:
        t = "%s %d" % (m.group(1), int(m.group(2)))
        return (t,) + toolutil.parse_contest(t)
    return None


def find_contest(text, filename):
    """标题行（第一个 # 行）→ 前 30 行 → 文件名，依次兜底；认不出 → None。"""
    lines = text.split("\n")[:30]
    for l in lines:
        if l.lstrip().startswith("#"):
            r = _search_contest(l)
            if r:
                return r
    r = _search_contest("\n".join(lines))
    if r:
        return r
    return _search_contest(filename or "")


# ---------------------------------------------------------------- 跳过备忘录
def _skip_path(inbox):
    return os.path.join(inbox, SKIP_NAME)


def _load_skips(inbox):
    """读「全部跳过」备忘录 → {内容 sha1: [题号…]}；文件不在 / 读坏当空。"""
    try:
        data = json.loads(rd(_skip_path(inbox)))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: (v if isinstance(v, list) else []) for k, v in data.items()}


def _remember_skips(plan):
    """把本轮冲突按内容 sha1 记进备忘录（供下次扫描静默）；返回冲突题数。

    顺手瘦身：只保留仍在收件箱里的文件（按 sha1）的记录。"""
    keep = {f.get("sha") for f in plan["files"] if f.get("sha")}
    try:
        data = _load_skips(plan["inbox"])
    except Exception:
        data = {}
    for it in plan["conflicts"]:
        lst = data.setdefault(it["sha"], [])
        if it["letter"] not in lst:
            lst.append(it["letter"])
    data = {k: v for k, v in data.items() if k in keep}
    toolutil.write_text_atomic(_skip_path(plan["inbox"]),
                               json.dumps(data, ensure_ascii=False,
                                          indent=1, sort_keys=True) + "\n")
    return len(plan["conflicts"])


# ---------------------------------------------------------------- TB 读写
def _index_rows(lines):
    """TB 主表 → {(比赛名, 号): {题号: (行号 0 基, cells)}}；没表头 → RuntimeError。"""
    i0 = next((i for i, l in enumerate(lines)
               if toolutil.split_cells(l) == toolutil.TB_HEADER), None)
    if i0 is None:
        raise RuntimeError("TB 里没找到表头「| %s |」" % " | ".join(toolutil.TB_HEADER))
    out = {}
    for i in range(i0 + 2, len(lines)):
        c = toolutil.split_cells(lines[i])
        if not c or len(c) != len(toolutil.TB_HEADER):
            break                          # 主表结束（后面是别的段落）
        if set("".join(c)) <= set("-: "):
            continue
        name, num = toolutil.parse_contest(c[0])
        if name is None:
            continue                       # 场次认不出的行：与收件箱无关，跳过
        out.setdefault((name, num), {})[c[1].strip().upper()] = (i, c)
    return out


def tb_all(path):
    """读 TB 文件 → _index_rows 的结果。"""
    return _index_rows(rd(path).split("\n"))


def _row_segments(line):
    """表格行 → (每格 [起,止) 区间, cells)；非表格行 → (None, None)。

    口径同 status_gui.row_segments（保住 \\| 转义、只动目标格、其余字节原样）。"""
    if not line.lstrip().startswith("|"):
        return None, None
    pipes, i, n = [], 0, len(line)
    while i < n:
        if line[i] == "\\" and i + 1 < n and line[i + 1] == "|":
            i += 2
            continue
        if line[i] == "|":
            pipes.append(i)
        i += 1
    if len(pipes) < 2:
        return None, None
    segs, cells = [], []
    for k in range(len(pipes) - 1):
        a, b = pipes[k] + 1, pipes[k + 1]
        segs.append((a, b))
        cells.append(line[a:b].strip().replace("\\|", "|"))
    return segs, cells


def replace_cells(line, changes):
    """只替换 changes = {列下标: 新值} 的格子；该行其余字节原样保留。"""
    segs, _cells = _row_segments(line)
    if segs is None or len(segs) != len(toolutil.TB_HEADER):
        raise ValueError("不是状态表数据行：%r" % line)
    edits = []
    for idx, val in changes.items():
        text = (val or "").replace("|", "\\|")
        a, b = segs[idx]
        edits.append((a, b, (" " + text + " ") if text else "  "))
    for a, b, seg in sorted(edits, key=lambda e: e[0], reverse=True):
        line = line[:a] + seg + line[b:]
    return line


# ---------------------------------------------------------------- 扫描
def _read_md(path):
    """读一个收件箱 md → (场次文本, 比赛名, 号, 目录表, 内容 sha1, 错误)。"""
    try:
        raw = open(path, "rb").read()
        sha = hashlib.sha1(raw).hexdigest()
        text = raw.decode("utf-8-sig")     # utf-8-sig：防 BOM 把首行「# 标题」顶掉
    except (OSError, UnicodeDecodeError) as e:
        return None, None, None, None, None, "读不了：%s" % e
    r = find_contest(text, os.path.basename(path))
    if not r:
        return None, None, None, None, sha, \
            "认不出场次（标题行 / 文件名里没有「周赛 164」/「入门赛 52」这类写法）"
    t, name, num = r
    cat = toolutil.parse_catalog(path)
    if not cat:
        return t, name, num, None, sha, \
            "没读到「## 目录」表（要四列：题号 / 题名 / 考点 / 难度）"
    return t, name, num, cat, sha, None


def scan(root, status_path):
    """扫收件箱 → 计划 dict（纯读，不写盘）。

    {"inbox": 路径, "fatal": 状态表文案或 None, "fatal_inbox": 收件箱文案或 None,
     "adds": [item], "conflicts": [item], "unchanged": n, "memo_skips": n,
     "errors": [(文件名或 "(状态表)", 原因)],
     "files": [{"name","contest","error","sha"}...]}
    item = {file, contest_text, name, n, letter, title, know, diff, sha,
            diffs（仅冲突）}
    """
    root = root.replace("/", os.sep)
    plan = {"inbox": inbox_dir(root), "fatal": None, "fatal_inbox": None,
            "adds": [], "conflicts": [], "unchanged": 0, "memo_skips": 0,
            "errors": [], "files": []}
    try:
        os.makedirs(plan["inbox"], exist_ok=True)
    except OSError as e:
        plan["fatal_inbox"] = "收件箱目录建不出来：%s" % e
        return plan
    try:
        tb = tb_all(status_path)
    except (OSError, RuntimeError) as e:
        plan["fatal"] = str(e)
        plan["errors"].append(("(状态表)", str(e)))
        return plan
    kd = knowledge_dict.load()
    memo = _load_skips(plan["inbox"])
    try:
        names = sorted(n for n in os.listdir(plan["inbox"])
                       if n.lower().endswith(".md")
                       and not n.startswith(".") and not n.startswith("~$"))
    except OSError as e:
        plan["fatal_inbox"] = "收件箱读不了：%s" % e
        return plan
    seen = {}          # (比赛名, 号, 字母) → item（同题去重；值不同则报错）
    for fn in names:
        p = os.path.join(plan["inbox"], fn)
        if not os.path.isfile(p):
            continue
        t, name, num, cat, sha, err = _read_md(p)
        plan["files"].append({"name": fn, "contest": t, "error": err, "sha": sha})
        if err:
            plan["errors"].append((fn, err))
            continue
        rows = tb.get((name, num), {})
        for lt in sorted(cat):
            ti, kw_raw, df_raw = cat[lt]
            item = {"file": fn, "contest_text": t, "name": name, "n": num,
                    "letter": lt, "title": plain_title(ti), "sha": sha,
                    "know": kd.final_knowledge(name, num, lt, kw_raw),
                    "diff": norm_diff(df_raw)}
            key = (name, num, lt)
            if key in seen:
                prev = seen[key]
                if (prev["title"], prev["know"], prev["diff"]) != \
                        (item["title"], item["know"], item["diff"]):
                    plan["errors"].append(
                        (fn, "对 %s %s 题的定义与 %s 不一致——两处先改成一样再来"
                         % (t, lt, prev["file"])))
                continue                       # 同题只收一次
            seen[key] = item
            if lt in rows:
                cells = rows[lt][1]
                diffs = []
                if toolutil.norm_title(cells[2]) != toolutil.norm_title(ti):
                    diffs.append(("题名", cells[2], item["title"]))
                if norm_diff(cells[4]) != item["diff"]:
                    diffs.append(("难度", cells[4], item["diff"]))
                if cells[3] != item["know"]:
                    diffs.append(("知识点", cells[3], item["know"]))
                if diffs:
                    if lt in memo.get(sha, ()):
                        plan["memo_skips"] += 1        # 已记过「跳过」：静默
                    else:
                        item["diffs"] = diffs
                        plan["conflicts"].append(item)
                else:
                    plan["unchanged"] += 1
            else:
                plan["adds"].append(item)
    return plan


# ---------------------------------------------------------------- 写盘
def apply(plan, status_path, on_conflict="skip"):
    """按计划写 TB。on_conflict: skip（冲突保持现状 + 记备忘录）/ overwrite（按题解覆盖）。

    新增题总是收（跳过/覆盖两种选择都一样）；冲突题只有 overwrite 才动。
    返回 {"added","updated","skipped_existing","skipped_conflicts","bak"}。
    无动作时原样返回（不写盘、不备份；「跳过」照记备忘录）。
    """
    if plan.get("fatal") or plan.get("fatal_inbox"):
        raise RuntimeError(plan.get("fatal") or plan.get("fatal_inbox"))
    adds = list(plan["adds"])
    confs = list(plan["conflicts"]) if on_conflict == "overwrite" else []
    res = {"added": 0, "updated": 0, "skipped_existing": 0,
           "skipped_conflicts": 0, "bak": None}
    if on_conflict != "overwrite" and plan["conflicts"]:
        res["skipped_conflicts"] = _remember_skips(plan)
    if not adds and not confs:
        return res

    st0 = os.stat(status_path)                 # 乐观锁标记：先记，再读（v67 口径）
    old = rd(status_path).split("\n")
    lines = list(old)
    fresh = _index_rows(lines)                 # 新鲜表（防「扫描 → 写盘」之间别处改过）

    changed = set()
    for it in confs:                           # 覆盖冲突行（按新鲜表定位）
        hit = fresh.get((it["name"], it["n"]), {}).get(it["letter"])
        if hit is None:
            continue                           # 行没了（别处删过）→ 放弃这一条
        i = hit[0]
        new_line = replace_cells(lines[i], {2: it["title"], 3: it["know"], 4: it["diff"]})
        if new_line != lines[i]:
            lines[i] = new_line
            changed.add(i)
            res["updated"] += 1

    new_rows = []                              # 追加新增（跳过别处刚加过的，防重复）
    for it in adds:
        if it["letter"] in fresh.get((it["name"], it["n"]), {}):
            res["skipped_existing"] += 1
            continue
        new_rows.append("| %s | %s | %s | %s | %s | 未做 |  |"
                        % (it["contest_text"], it["letter"], it["title"],
                           it["know"], it["diff"]))
    if not changed and not new_rows:
        return res

    tail = toolutil.find_table_tail(lines)
    if tail is None:
        raise RuntimeError("TB 里没找到表头，写不了（先修表）")
    at = tail + 1
    new = lines[:at] + new_rows + lines[at:]

    n_new = len(new_rows)                      # 断言「只动了预期部分」
    for i in range(len(old)):
        if i < at and i not in changed and new[i] != old[i]:
            raise RuntimeError("内部错误：第 %d 行不该变而变了" % (i + 1))
        if i >= at and new[i + n_new] != old[i]:
            raise RuntimeError("内部错误：表尾之后第 %d 行被动了" % (i + 1))
    res["added"] = n_new

    text = "\n".join(new)
    res["bak"] = toolutil.backup_to_repo(status_path)
    st1 = os.stat(status_path)                 # 写前复核：期间被别处改过就放弃
    if (st1.st_mtime_ns, st1.st_size) != (st0.st_mtime_ns, st0.st_size):
        raise RuntimeError("TB 刚被其他程序改过（比如另一个 TB 窗口），本次收件箱写入已放弃；重按一次 F5")
    toolutil.write_text_atomic(status_path, text)
    if rd(status_path) != text:
        raise RuntimeError("写后复读不一致：%s" % status_path)
    return res


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="收件箱：题解 md 放进文件夹 → 自动收进 TB（默认 dry，只预演）")
    ap.add_argument("--root", default=toolutil.DATA_ROOT, help="数据根（缺省取 config.json）")
    ap.add_argument("--status", default=None, help="状态表路径（缺省 <root>\\题解\\TB.md）")
    ap.add_argument("--apply", action="store_true", help="真写盘（默认只预演）")
    ap.add_argument("--on-conflict", choices=("skip", "overwrite"), default="skip",
                    help="冲突题怎么办：skip = 保持 TB 现状 + 记备忘录（默认）；overwrite = 按题解覆盖")
    ap.add_argument("--quiet", action="store_true", help="只打印动到的部分")
    ap.add_argument("--selftest", action="store_true", help="沙箱自检（不碰真数据）")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    root = a.root.replace("/", os.sep)
    status = (a.status or os.path.join(root, "题解", "TB.md")).replace("/", os.sep)

    plan = scan(root, status)
    if plan["fatal"] or plan["fatal_inbox"]:
        print("★ %s" % (plan["fatal"] or plan["fatal_inbox"]))
        return 2
    if not a.quiet:
        print("收件箱：%s（%d 个 md）" % (plan["inbox"], len(plan["files"])))
        for f in plan["files"]:
            if f["error"]:
                print("  · %s —— 读不了：%s" % (f["name"], f["error"]))
            else:
                print("  · %s —— %s" % (f["name"], f["contest"]))
        print("-" * 74)
    for it in plan["adds"]:
        print("[新增] %s %s | %s | %s | %s | 未做 |  |"
              % (it["contest_text"], it["letter"], it["title"], it["know"], it["diff"]))
    for it in plan["conflicts"]:
        print("[冲突] %s %s %s：" % (it["contest_text"], it["letter"], it["title"]))
        for field, oldv, newv in it["diffs"]:
            print("        %s：TB「%s」→ 题解「%s」" % (field, oldv, newv))
    for name, why in plan["errors"]:
        print("[问题] %s：%s" % (name, why))
    if plan["unchanged"] and not a.quiet:
        print("[一致] %d 题已在表且一致（静默跳过）" % plan["unchanged"])
    if plan["memo_skips"] and not a.quiet:
        print("[省] %d 题冲突此前已确认「跳过」（%s）" % (plan["memo_skips"], SKIP_NAME))
    if not (plan["adds"] or plan["conflicts"] or plan["errors"]):
        print("（收件箱没有待处理内容）")
    if not a.apply:
        print("—— dry run（要写入加 --apply；冲突按 --on-conflict %s）——" % a.on_conflict)
        return 1 if plan["errors"] else 0
    res = apply(plan, status, a.on_conflict)
    if res["added"] or res["updated"]:
        print("结论：新增 %d 题、更新 %d 题（备份 %s）"
              % (res["added"], res["updated"], res["bak"]))
    elif res["skipped_conflicts"]:
        print("结论：冲突 %d 题按「跳过」保持现状（记进 %s，不再提示）"
              % (res["skipped_conflicts"], SKIP_NAME))
    else:
        print("结论：没有动作")
    return 1 if plan["errors"] else 0


# ---------------------------------------------------------------- 自检
def _put(inbox, name, text):
    with open(os.path.join(inbox, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _selftest():
    import shutil
    td = tempfile.mkdtemp(prefix="tb_inbox_selftest_")
    old_bk = toolutil.BACKUP_ROOT
    try:
        toolutil.BACKUP_ROOT = os.path.join(td, "_bak")     # 备份写沙箱，别碰真备份仓
        root = os.path.join(td, "root")
        tdir = os.path.join(root, "题解")
        os.makedirs(tdir)
        sp = os.path.join(tdir, "TB.md")
        hdr = "| %s |" % " | ".join(toolutil.TB_HEADER)
        sep = "|---|" + "---|" * (len(toolutil.TB_HEADER) - 1)
        with open(sp, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "# TB 自检沙箱\n\n## 题目状态表\n\n%s\n%s\n"
                "| 周赛 991 | B | 旧题名 | 构造 | 1200 | 未做 |  |\n"
                "| 周赛 991 | C | 小红的gcd构造 | 构造 | 1400 | 独立AC | 2026-10-01 |\n"
                "| 周赛 991 | D | 比那名居的桃子 | [模拟][主] + 枚举 | 1500 | 未做 |  |\n"
                "\n## 尾注\n不许动这一行\n" % (hdr, sep))

        # 1) 空收件箱：自动创建、无动作、无致命错
        inbox = inbox_dir(root)
        plan = scan(root, sp)
        assert plan["fatal"] is None and plan["fatal_inbox"] is None, plan
        assert os.path.isdir(inbox), "收件箱应自动创建"
        assert not plan["adds"] and not plan["conflicts"] and not plan["errors"], plan

        # 2) 新场次（含 LaTeX 题名）+ 冲突场次（题名 / 难度）+ 坏文件
        _put(inbox, "992题解.md",
             "# 周赛 992 题解\n\n## 目录\n\n| 题号 | 题名 | 考点 | 难度 |\n"
             "|---|---|---|---|\n| A | 好数 | 模拟 | 800 |\n| B | 小红的$\\gcd$题 | 素数 | 900 |\n\n## A. 好数\n")
        T991 = ("# 周赛 991 题解\n\n## 目录\n\n| 题号 | 题名 | 考点 | 难度 |\n"
                "|---|---|---|---|\n| B | 小红的B题 | 构造 | 1200 |\n"
                "| C | 小红的$\\gcd$构造 | 构造 | 1500 |\n"
                "| D | 比那名居的桃子 | [模拟][主] + 枚举 | 1500 |\n"
                "| E | 新题 | 构造 | 1600 |\n")
        _put(inbox, "周赛991题解.md", T991)
        _put(inbox, "bad.md", "# 没有场次的文件\n\n随便什么内容\n")
        plan = scan(root, sp)
        got_adds = sorted((it["n"], it["letter"]) for it in plan["adds"])
        assert got_adds == [(991, "E"), (992, "A"), (992, "B")], got_adds
        got_confs = sorted((it["n"], it["letter"]) for it in plan["conflicts"])
        assert got_confs == [(991, "B"), (991, "C")], got_confs
        assert plan["unchanged"] == 1, plan["unchanged"]      # 991 D 一致
        assert len(plan["errors"]) == 1 and plan["errors"][0][0] == "bad.md", plan["errors"]
        it_b = [x for x in plan["adds"] if x["n"] == 992 and x["letter"] == "B"][0]
        assert it_b["title"] == "小红的gcd题", it_b["title"]   # LaTeX 去了、命令名留下
        cf = {x["letter"]: x for x in plan["conflicts"]}
        assert [d[0] for d in cf["B"]["diffs"]] == ["题名"], cf["B"]["diffs"]
        assert [d[0] for d in cf["C"]["diffs"]] == ["难度"], cf["C"]["diffs"]

        # 3) 跳过式 apply：只加新增、冲突保持现状并记备忘录
        res = apply(plan, sp, "skip")
        after = rd(sp)
        assert res["added"] == 3 and res["updated"] == 0 \
            and res["skipped_conflicts"] == 2, res
        for want in ("| 周赛 992 | A | 好数 | 模拟 | 800 | 未做 |  |",
                     "| 周赛 992 | B | 小红的gcd题 | 素数 | 900 | 未做 |  |",
                     "| 周赛 991 | E | 新题 | 构造 | 1600 | 未做 |  |",
                     "| 周赛 991 | B | 旧题名 | 构造 | 1200 | 未做 |  |",
                     "| 周赛 991 | C | 小红的gcd构造 | 构造 | 1400 | 独立AC | 2026-10-01 |"):
            assert want in after, want
        assert after.endswith("## 尾注\n不许动这一行\n"), "表尾之后的行被动了"
        assert "\r" not in after
        assert os.path.exists(os.path.join(inbox, SKIP_NAME)), "应写下备忘录"

        # 4) 备忘录生效：同内容再扫，冲突静默
        plan = scan(root, sp)
        assert not plan["adds"], [x["letter"] for x in plan["adds"]]
        assert not plan["conflicts"], plan["conflicts"]
        assert plan["memo_skips"] == 2, plan["memo_skips"]
        assert plan["unchanged"] == 4, plan["unchanged"]      # 991 D + 991 E + 992 A/B

        # 5) md 一改（sha 变）→ 备忘录失效、冲突回来；覆盖式 apply 按题解改
        _put(inbox, "周赛991题解.md", T991 + "\n（本行不参与解析）\n")
        plan = scan(root, sp)
        assert sorted((i["n"], i["letter"]) for i in plan["conflicts"]) == \
            [(991, "B"), (991, "C")], plan["conflicts"]
        assert plan["memo_skips"] == 0, plan["memo_skips"]
        res = apply(plan, sp, "overwrite")
        after = rd(sp)
        assert res["updated"] == 2 and res["added"] == 0, res
        assert "| 周赛 991 | B | 小红的B题 | 构造 | 1200 | 未做 |  |" in after
        assert ("| 周赛 991 | C | 小红的gcd构造 | 构造 | 1500 "
                "| 独立AC | 2026-10-01 |") in after
        assert "## 尾注\n不许动这一行\n" in after

        # 6) 全一致 → 无动作、不写盘、不备份
        plan = scan(root, sp)
        assert not plan["adds"] and not plan["conflicts"], plan
        res = apply(plan, sp, "overwrite")
        assert res == {"added": 0, "updated": 0, "skipped_existing": 0,
                       "skipped_conflicts": 0, "bak": None}, res

        # 7) 同场两文件对同题定义不同 → 报错且只收一次
        _put(inbox, "993a题解.md",
             "# 周赛 993 题解\n\n## 目录\n\n| A | X | 模拟 | 800 |\n")
        _put(inbox, "993b题解.md",
             "# 周赛 993 题解\n\n## 目录\n\n| A | Y | 模拟 | 800 |\n")
        plan = scan(root, sp)
        assert len([x for x in plan["adds"] if x["n"] == 993]) == 1
        assert any("不一致" in why for _, why in plan["errors"]), plan["errors"]

        # 8) TB 不可读 → fatal、不崩、apply 拒绝
        plan2 = scan(root, os.path.join(tdir, "没有这个表.md"))
        assert plan2["fatal"], "TB 不可读要报 fatal"
        try:
            apply(plan2, sp, "skip")
            raise AssertionError("fatal 时 apply 该拒绝")
        except RuntimeError:
            pass

        # 9) 写前 mtime 乐观锁：apply 期间被别处改过 → 拒绝写
        _put(inbox, "994题解.md",
             "# 周赛 994 题解\n\n## 目录\n\n| A | Z | 模拟 | 800 |\n")
        plan = scan(root, sp)
        assert any(x["n"] == 994 for x in plan["adds"])
        orig_bak = toolutil.backup_to_repo

        def sneaky(path, src_root=None):
            b = orig_bak(path, src_root)
            with open(path, "a", encoding="utf-8") as f:
                f.write("x")                   # 模拟“备份期间别处又写了一条”
            return b
        toolutil.backup_to_repo = sneaky
        try:
            apply(plan, sp, "skip")
            raise AssertionError("mtime 变过应拒绝写入")
        except RuntimeError as e:
            assert "放弃" in str(e), e
        finally:
            toolutil.backup_to_repo = orig_bak
        assert "周赛 994" not in rd(sp), "拒绝写入时不许把新增写进去"

        # 10) 新平台系列也能收（标题带旧式 `#` 也认 → TB 落新口径 `入门赛 52` 行，题名前缀已剥）
        _put(inbox, "入门赛52题解.md",
             "# 入门赛 #52 题解\n\n## 目录\n\n| 题号 | 题名 | 考点 | 难度 |\n"
             "|---|---|---|---|\n| A | [语言月赛 202605] 分月饼 | 模拟 | 800 |\n")
        plan = scan(root, sp)
        assert any(x["n"] == 52 and x["name"] == "入门赛" for x in plan["adds"]), plan["adds"]
        apply(plan, sp, "skip")
        assert "| 入门赛 52 | A | 分月饼 | 模拟 | 800 | 未做 |  |" in rd(sp)
        print("    新系列（入门赛 #52）照收 → 场次 `入门赛 52`、题名剥前缀 ✓")

        print("tb_inbox 自检 OK")
        return 0
    finally:
        toolutil.BACKUP_ROOT = old_bk
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
