# -*- coding: utf-8 -*-
r"""import_solution —— 导入一个标准「题解包」（默认只校验，--apply 才落盘）

    python tools\import_solution.py <包.zip 或 包目录>              # dry：只校验 + 预览
    python tools\import_solution.py <包> --apply                    # 真要导入
    python tools\import_solution.py <包> --apply --root <数据根>     # 指定数据根

**分级门槛**（设计口径，「硬」不合格就打回）：
  硬 │ 包可读 + manifest 字段齐 ｜ 题解 md 过 `check_solution.py` 17 项 ｜
       文件名 / 标题行能解析 ｜ 目标位置没有同题（防覆盖）｜ 记录 md 与 manifest 一致
  软 │ 知识点未登记 → **不拒收**：照收 + 进「待登记清单」（附最接近的标准名建议）
  可缺省 │ 算法记录（生成「精简记录」，标注 收录级别：精简）

**落盘后自动串齿轮**（一条命令跑完，见设计 §4.3）：
    复制文件 → 补反查表行 + 题解指针 → index_sync → 追加状态表行 → fill_knowledge
    → archive_check RoundN（退出码 0 = 收工）

退出码：0 = 成功（archive_check 也过）；1 = 校验有问题（dry 时）/ 齿轮某步失败；
        2 = 包不可读 / 参数错。
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil        # noqa: E402
import knowledge_dict  # noqa: E402
import index_sync      # noqa: E402
import archive_check   # noqa: E402  （复用它的 Rep 与记录 md 判据）

BS = chr(92)
CONT = "牛客周赛"
MANIFEST = "manifest.json"
FORMAT = "acm-agent-workflow/solution-pack"
STATUS_HEADER = archive_check.STATUS_HEADER
PLACEHOLDER = "（归档第一场后逐行补）"
RE_URL = re.compile(r"^https://ac\.nowcoder\.com/acm/contest/(\d+)/([A-Z])$")
RE_DIFF = re.compile(r"^CF\s*\d+$")
RE_PTR_MARK = re.compile(r"（指针）\s*\|?\s*$")


def rd(p):
    return open(p, encoding="utf-8").read()


def wr(p, text):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def norm(p):
    return p.replace("/", BS).rstrip(BS)


def same_dir(a, b):
    return norm(a).lower() == norm(b).lower()


def run_py(script, args):
    """跑同目录脚本，stdout 直接继承（用户要看的报告原样透出）；返回退出码"""
    cmd = [sys.executable, os.path.join(toolutil.REPO_ROOT, "tools", script)] + args
    print("$ python tools%s%s %s" % (BS, script, " ".join(args)))
    sys.stdout.flush()
    return subprocess.run(cmd, cwd=toolutil.REPO_ROOT).returncode


# ---------------------------------------------------------------- 读包
def open_pack(path, td):
    """包 → 目录路径。zip 解到 td 下。返回 (dir 或 None, 错误)"""
    if os.path.isdir(path):
        return os.path.abspath(path), None
    if not os.path.exists(path):
        return None, "找不到 %s" % path
    if zipfile.is_zipfile(path):
        dst = os.path.join(td, "pack")
        try:
            with zipfile.ZipFile(path) as z:
                for m in z.namelist():
                    # 防 zip 路径穿越（../ 或绝对路径）
                    tgt = os.path.abspath(os.path.join(dst, m))
                    if not tgt.startswith(os.path.abspath(dst) + os.sep) and tgt != os.path.abspath(dst):
                        return None, "zip 里有不安全路径：%s" % m
                z.extractall(dst)
        except zipfile.BadZipFile as e:
            return None, "zip 解不开：%s" % e
        return dst, None
    return None, "%s 既不是目录也不是 zip" % path


# ---------------------------------------------------------------- 校验
class Item(object):
    def __init__(self, letter):
        self.letter = letter
        self.title = ""
        self.diff = ""
        self.scoring = "非签到"
        self.raw_know = []
        self.know = []
        self.url = ""
        self.cid = ""
        self.folder_raw = ""
        self.folder = ""          # 落盘用的（解析成功 = 词典名；未登记 = 原样）
        self.folder_note = None
        self.mapped = []          # [(原名, 标准名)] 别名自动映射记录
        self.unknown_names = []   # [(名字, 建议 or None)] 待登记清单
        self.rec_src = None       # 包里的记录 md（None = 生成精简记录）
        self.rec_rel = None       # 记录 md 相对 算法\ 的路径
        self.new_record = False
        self.files = []           # [(src, 包内相对)] 题解区属于本题的文件
        self.back_rows = []       # manifest 带来的反查表原文（可选；带上则往返无损）


def validate(pack_dir, root, rep, mem, check_sol=True):
    """→ (problems, plan, 元信息) ；校验结论全写进 rep"""
    kd = knowledge_dict.load()
    p = os.path.join(pack_dir, MANIFEST)
    if not os.path.exists(p):
        rep.bad("1 包结构", "包里没有 %s（题解包 = 数据根子集 + manifest.json）" % MANIFEST)
        return None, None, None
    try:
        man = json.loads(rd(p))
    except ValueError as e:
        rep.bad("1 包结构", "%s 不是合法 JSON：%s" % (MANIFEST, e))
        return None, None, None
    if not isinstance(man, dict):
        rep.bad("1 包结构", "%s 的顶层不是对象" % MANIFEST)
        return None, None, None

    if man.get("format") != FORMAT:
        rep.bad("1 包结构", "manifest.format = %r，应为 %r" % (man.get("format"), FORMAT))
    v = man.get("format_version")
    if v != 1:
        rep.bad("1 包结构", "manifest.format_version = %r，本工具只认 1（更新版工具在仓库里）" % v)
    contest, rnd = man.get("contest"), man.get("round")
    name, num = toolutil.parse_contest("%s Round %s" % (contest, rnd))
    if name != CONT:
        rep.bad("1 包结构", "manifest.contest/round = %r/%r —— 本工具的导入目前只支持「%s Round N」"
                "（别的比赛先按原样写在 manifest 里，等通用化批次）" % (contest, rnd, CONT))
    meta = {"contest": CONT, "round": num, "contributor": str(man.get("contributor") or "")}
    if num:
        rep.ok("1 包结构", "manifest 可读：%s Round %s ｜ 署名 %s"
               % (CONT, num, meta["contributor"] or "（空）"))
    if not meta["contributor"]:
        rep.warn("1 包结构", "manifest.contributor 是空的（署名会丢）——建议写 GitHub 用户名")
    problems = man.get("problems")
    if not isinstance(problems, list) or not problems:
        rep.bad("1 包结构", "manifest.problems 要是非空数组")
        return None, None, meta

    letters, cid0 = set(), None
    items = []
    for pr in problems:
        if not isinstance(pr, dict):
            rep.bad("2 manifest 字段", "problems 里有一项不是对象")
            continue
        L = str(pr.get("letter") or "").strip().upper()
        it = Item(L)
        it.title = str(pr.get("title") or "").strip()
        it.diff = str(pr.get("difficulty") or "").strip()
        it.scoring = str(pr.get("scoring") or "").strip() or "非签到"
        it.folder_raw = str(pr.get("folder") or "").strip()
        it.url = str(pr.get("url") or "").strip()
        raw = pr.get("knowledge")
        it.raw_know = [str(x).strip() for x in raw] if isinstance(raw, list) else []
        it.back_rows = [str(x).strip() for x in (pr.get("back_rows") or []) if str(x).strip()]
        miss = [k for k, val in (("letter", L), ("title", it.title), ("difficulty", it.diff),
                                 ("knowledge", it.raw_know), ("folder", it.folder_raw),
                                 ("url", it.url)) if not val]
        if miss:
            rep.bad("2 manifest 字段", "题 %s 缺字段：%s" % (L or "？", "、".join(miss)))
            continue
        if not re.fullmatch(r"[A-Z]", L):
            rep.bad("2 manifest 字段", "题号 %r 不合规（单个 A-Z 字母）" % L)
            continue
        if L in letters:
            rep.bad("2 manifest 字段", "题号 %s 在 manifest 里出现两次" % L)
            continue
        letters.add(L)
        if it.scoring not in ("非签到", "签到"):
            rep.warn("2 manifest 字段", "题 %s 的 scoring = %r（只认 非签到 / 签到），按非签到处理"
                     % (L, it.scoring))
            it.scoring = "非签到"
        if not RE_DIFF.match(it.diff):
            rep.warn("2 manifest 字段", "题 %s 的 difficulty = %r（口径是 `CF 900` 这样）" % (L, it.diff))
        m = RE_URL.match(it.url)
        if not m:
            rep.bad("2 manifest 字段", "题 %s 的 url = %r 不是牛客题面链接"
                    "（https://ac.nowcoder.com/acm/contest/<cid>/<字母>）" % (L, it.url))
            continue
        it.cid = m.group(1)
        if m.group(2) != L:
            rep.bad("2 manifest 字段", "题 %s 的 url 末尾是 %s，与 letter 不符" % (L, m.group(2)))
            continue
        if cid0 is None:
            cid0 = it.cid
        elif it.cid != cid0:
            rep.bad("2 manifest 字段", "同一场的题 url 里比赛号不一致：%s 与 %s（是不是拼了两场？）"
                    % (cid0, it.cid))

        # 知识点（软：未登记照收 + 待登记清单）
        it.know, mapped, unknown = kd.check_names(it.raw_know)
        it.mapped, it.unknown_names = mapped, unknown
        for x, y in mapped:
            rep.warn("3 知识点-别名自动映射", "题 %s：%s → %s（已按标准名落盘）" % (L, x, y))
        for x, sug in unknown:
            rep.warn("3 知识点-待登记（照收，不拒收）",
                     "题 %s：%r 词典里没有——建议 %s；合并时一键定夺（收为别名 / 立新标准名）"
                     % (L, x, ("收为 %r 的别名" % sug) if sug else "立为新标准名（没找到相近的）"))
        # todo: 归档文件夹（软：未登记照收不猜）
        it.folder, it.folder_note = kd.resolve_folder(it.folder_raw)
        if it.folder is None:
            it.folder = it.folder_raw.strip(BS)
            it.folder_note = "未登记"
            rep.warn("3 知识点-文件夹未登记（照收，不拒收）",
                     "题 %s 的 folder = %r 不在词典的文件夹表里——落盘时原样建文件夹，"
                     "合并时定夺（收为别名 / 立新标准名）" % (L, it.folder_raw))
        elif it.folder_note:
            rep.warn("3 知识点-文件夹自动映射", "题 %s：%s → %s（%s）"
                     % (L, it.folder_raw, it.folder, it.folder_note))
        items.append(it)
    if not items:
        return None, None, meta

    rn = "Round%d" % num
    # 题解 md
    md_rel = os.path.join("题解", CONT, rn, "%s题解.md" % rn)
    md = os.path.join(pack_dir, md_rel)
    if os.path.exists(md):
        n_missing = []
        if check_sol:
            cs = os.path.join(toolutil.REPO_ROOT, "tools", "check_solution.py")
            pr = subprocess.run([sys.executable, cs, md, "--quiet"],
                                capture_output=True, text=True)
            tail = (pr.stdout or pr.stderr).strip().splitlines()
            if pr.returncode == 0:
                rep.ok("4 题解 md", "%s 过 17 项自检（%s）"
                       % (md_rel, tail[-1].strip("— ") if tail else "退出码 0"))
            else:
                rep.bad("4 题解 md", "%s 没过 check_solution.py（退出码 %d）：%s"
                        % (md_rel, pr.returncode, " ｜ ".join(x for x in tail[-4:] if x.strip())))
        else:
            rep.warn("4 题解 md", "按 --no-check-solution 跳过了 17 项闸门")
    else:
        rep.bad("4 题解 md", "包里没有 %s（题解包必须带整场题解 md）" % md_rel)

    # 每题：记录 md + 题解区目录
    sub = os.path.join(pack_dir, "题解", CONT, rn)
    round_files = toolutil.walk_files(sub) if os.path.isdir(sub) else []
    for it in items:
        pat = os.path.join(pack_dir, "算法", "**", "%sRound%d-%s-*.md" % (CONT, num, it.letter))
        hits = sorted(glob.glob(pat, recursive=True))
        for h in hits:
            rec, err = index_sync.parse_record(h, pack_dir)
            if err:
                rep.bad("5 算法记录", err)
                continue
            if archive_check.norm_name(rec["name"]) != archive_check.norm_name(it.title):
                rep.bad("5 算法记录", "包里的记录 %s 题名是「%s」，与 manifest 的「%s」不符"
                        % (os.path.basename(h), rec["name"], it.title))
                continue
            # 记录 md 的五节 / 数据范围 / 行尾（判据复用 archive_check）
            archive_check.check_record(rep, h)
            if rec["url"] != it.url:
                rep.bad("5 算法记录", "题 %s 的记录 md 原题链接 = %s，与 manifest 的 %s 不符"
                        % (it.letter, rec["url"], it.url))
            if not same_dir(rec["rel"], it.folder):
                rep.bad("5 算法记录", "题 %s 的记录 md 归档文件夹 = `%s%s`，"
                        "与 manifest 的 folder = `%s%s` 不符（两处要一样）"
                        % (it.letter, rec["rel"], BS, it.folder, BS))
            else:
                it.rec_src = h
                it.rec_rel = os.path.join(it.folder, os.path.basename(h))
                # 知识点口径：manifest 与记录 md 对一下（软——都照收，只是提醒对齐）
                want = kd.final_knowledge(CONT, num, it.letter, rec["algo"])
                got = kd.final_knowledge(CONT, num, it.letter, " + ".join(it.know))
                if want != got:
                    rep.warn("5 算法记录-知识点口径", "题 %s：manifest 写「%s」，记录 md 的"
                             "「数据结构与算法」归一后是「%s」——索引 / 状态表按**记录 md** 走，"
                             "两处对齐一下" % (it.letter, got, want))
                break
        if not it.rec_src:
            it.new_record = True
            it.rec_rel = os.path.join(it.folder, "%sRound%d-%s-%s.md"
                                      % (CONT, num, it.letter, it.title))
            rep.warn("5 算法记录（可缺省）", "题 %s 没带算法记录 → 导入时生成「精简记录」"
                     "（正文是空壳，好题建议合并后补）" % it.letter)
        # 题解区目录（本题的代码 / 验证驱动 / 图脚本）
        it.files = [(s, os.path.join("题解", CONT, rn, r)) for s, r in round_files
                    if (BS + it.letter + BS) in r + BS]
        if not it.files:
            rep.warn("6 题解区目录（可缺省）", "题 %s 在包里没有自己的代码目录（只有整场 md 里的小节）"
                     % it.letter)

    # 整场共用文件（不属于任何题，如根目录的图脚本）—— 一并带走，别静默丢
    md_name = "%s题解.md" % rn
    shared = [(s, os.path.join("题解", CONT, rn, r)) for s, r in round_files
              if r != md_name and not any((BS + x.letter + BS) in r + BS for x in items)]
    if shared:
        rep.warn("6 题解区-共用文件", "有 %d 个文件不属于任何题（整场共用？），会一并复制：%s"
                 % (len(shared), "、".join(r for _, r in shared)))

    # 目标冲突（防覆盖）
    rdir = os.path.join(root, "题解", CONT, rn)
    if os.path.exists(os.path.join(rdir, "%s题解.md" % rn)):
        rep.bad("7 防覆盖", "%s 已存在（这场已经导入过？先看 dry 报告再决定）"
                % os.path.join(rdir, "%s题解.md" % rn))
    for it in items:
        hits = glob.glob(os.path.join(root, "算法", "**",
                                      "%sRound%d-%s-*.md" % (CONT, num, it.letter)), recursive=True)
        if hits:
            rep.bad("7 防覆盖", "题 %s 在数据根里已有记录：%s"
                    % (it.letter, "、".join(os.path.relpath(x, root) for x in hits)))
    idx_path = os.path.join(root, "索引", "题解算法索引.md")
    if not os.path.exists(idx_path):
        rep.bad("7 防覆盖", "数据根里找不到 %s（数据根没建好？先跑 "
                "`python install.py --new-data <目录>`）" % idx_path)

    return items, {"md": md_rel if os.path.exists(md) else None, "rn": rn, "n": num,
                   "cid": cid0, "root": root, "pack": pack_dir, "shared": shared}, meta


# ---------------------------------------------------------------- 落盘计划
def rows_for(kd, it):
    """本题的反查表行：manifest 带 back_rows 就用原文（往返无损）；没带 → 按知识点生成"""
    if it.back_rows:
        return list(it.back_rows)
    return gen_back_rows(kd, it)


def gen_back_rows(kd, it):
    """按知识点生成反查表行（手写包没带 back_rows 时）。

    第 1 个知识点 = 主（落在 manifest 的 folder 里，出主行）；其余：词典里有别的
    文件夹 → 出「（指针）」行；词典里没有文件夹（如「置换环」）→ 出无文件夹行；
    与主文件夹相同 → 主行已覆盖，不重复出行。
    """
    rows = ["| %s | `%s%s` | [%s %s](%s) |"
            % (it.know[0], it.folder, BS, it.letter, it.title, it.url)]
    for k in it.know[1:]:
        f = kd.folder_of(k)
        if f is None:
            rows.append("| %s | 未单独建文件夹，写在记录正文的「关键点」里 | [%s %s](%s) |"
                        % (k, it.letter, it.title, it.url))
        elif not same_dir(f, it.folder):
            rows.append("| %s | `%s%s` | [%s %s](%s)（指针） |"
                        % (k, f, BS, it.letter, it.title, it.url))
    return rows


def ptr_lines(kd, it):
    """本题反查表里标了「（指针）」的行 → 该在对应文件夹的题解指针.md 里补的行"""
    out = []
    for r in rows_for(kd, it):
        f, isptr = row_folder(r)
        if isptr and f:
            out.append((f, "- %s %s：`%s%s`" % (it.letter, it.title, it.folder, BS)))
    return out


def row_folder(row):
    """反查表行 → (文件夹, 是否指针)。文件夹 = 第 2 格的 `…`；没有反引号 → (None, False)"""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    if len(cells) < 3:
        return None, False
    ptr = bool(RE_PTR_MARK.search(cells[2]))
    m = re.search("`([^`]+)`", cells[1])
    return (m.group(1).rstrip(BS) if m else None), ptr


def short_record(it, n, desc, meta):
    """没带记录 md 的题 → 生成「精简记录」正文

    标题行必须是 `# 牛客周赛 Round N X - 题名`（index_sync.parse_record 认这种写法），
    场次号与 `Round` 之间要有空格。
    """
    rn = "Round%d" % n
    return """# %(cont)s Round %(n)d %(L)s - %(title)s

- **难度**：%(diff)s
- **原题链接**：%(url)s
- **题解位置**：`<数据根>%(bs)s题解%(bs)s%(cont)s%(bs)s%(rn)s%(bs)s%(rn)s题解.md`（整场题解，含完整推导）
- **归档文件夹**：`%(folder)s%(bs)s`
- **数据结构与算法**：%(desc)s
- **具体知识点**：见题解 md 的「%(L)s. %(title)s」一节
- **收录级别**：精简（原贡献者未附算法记录）

## 题意（精简）

（未附：原贡献者未提供算法记录，完整题意见题解 md 的「%(L)s. %(title)s」一节）

**数据范围**：（未附，见题解 md）

## 关键点（为什么用这个算法）

（未附：原贡献者未提供。）

## 复杂度

（未附：见题解 md 的「复杂度」小节。）

## 踩过的坑

（未附：原贡献者未提供。）

## 相关

- 本文件夹其它题目：见 `题解指针.md`
- 导入来源：%(who)s 的题解包（收录级别：精简）
""" % {"cont": CONT, "n": n, "rn": rn, "L": it.letter, "title": it.title, "diff": it.diff,
       "url": it.url, "bs": BS, "folder": it.folder, "desc": desc,
       "who": meta["contributor"] or "（未署名）"}


def merge_table_rows(path, header, new_rows, placeholder=None):
    """把 new_rows 追加进 path 里以 header 开头的表格（表尾）。

    返回 (新增行数, 跳过的重复行, 删掉的占位行数)。找不到表头 → (-1, [], 0)。
    """
    lines = rd(path).split("\n")
    i0 = next((i for i, l in enumerate(lines)
               if [c.strip() for c in l.strip().strip("|").split("|")] == header), None)
    if i0 is None:
        return -1, [], 0
    i = i0 + 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        i += 1
    body = lines[i0 + 2:i]
    have = set(x.strip() for x in body)
    add, dup = [], []
    for r in new_rows:
        (dup if r.strip() in have else add).append(r)
        have.add(r.strip())
    keep = [x for x in body if placeholder is None or placeholder not in x]
    n_rm = len(body) - len(keep)
    if not add and not n_rm:
        return 0, dup, 0
    new = lines[:i0 + 2] + keep + add + lines[i:]
    toolutil.backup_to_repo(path)
    wr(path, "\n".join(new))
    return len(add), dup, n_rm


def fix_record_aliases(path, kd):
    """把记录 md 的「数据结构与算法」行里的**别名**换成标准名（未登记的原样留着）。

    规则在 `knowledge_dict.fix_aliases`（纯函数，导出侧共用一份）；本函数只管
    落盘与备份。返回 [(原名, 标准名)]。
    """
    new, used = kd.fix_aliases(rd(path))
    if not used:
        return []
    toolutil.backup_to_repo(path)
    wr(path, new)
    return used


def ensure_dirs_in_08(mem, folders, meta):
    """06 第六节「算法 → 文件夹 对照表」里缺的文件夹 → 补一行。

    导入是「照收」：新文件夹原样落地后，必须同时出现在对照表里，`archive_check`
    的「4 06 对照表」那一项才会过（那是它唯一的硬闸门）。补的行会标「待登记」，
    合并时人再看一眼（收为别名 / 保留为新标准名）。返回补过的文件夹名列表。
    """
    p = os.path.join(mem, "06-题解算法归档.md")
    if not os.path.exists(p):
        print("  [2/5] 提醒：找不到 %s（知识库不在？对账会报「4 06 精简索引」问题）" % p)
        return []
    t = rd(p)
    if "## 六、" not in t:
        print("  [2/5] 提醒：06 里没有 `## 六、` 对照表，跳过补行（对账会提醒）")
        return []
    sec6 = t.split("## 六、")[-1].split("## 相关")[0]
    kd = knowledge_dict.load()
    rev = {}
    for name, f in kd.folders.items():
        rev.setdefault(f, name)
    rows, added = [], []
    for f in sorted(folders):
        if ("`%s%s`" % (f, BS)) in sec6:
            continue
        nm = rev.get(f)
        who = meta.get("contributor") or "未署名"
        if nm:
            rows.append("| %s | `%s%s` | Round %d 记录（导入） |" % (nm, f, BS, meta["round"]))
        else:
            rows.append("| %s（**待登记**：导入自 %s 的包） | `%s%s` | Round %d 记录（导入） |"
                        % (f, who, f, BS, meta["round"]))
        added.append(f)
    if rows:
        n, dup, _ = merge_table_rows(p, ["算法 / 数据结构", "文件夹", "里面有什么"], rows)
        print("  [2/5] 06 对照表：补 %d 行（%s）%s"
              % (max(n, 0), "、".join(added), "（去重跳过 %d）" % len(dup) if dup else ""))
    return added


def apply_plan(plan, rep):
    """落盘 + 串齿轮。返回退出码（archive_check 的）"""
    root, rn, n = plan["root"], plan["rn"], plan["n"]
    kd = knowledge_dict.load()

    # 1) 复制文件（题解区 + 记录 md）+ 生成精简记录
    n_copy = 0
    if plan["md"]:
        src = os.path.join(plan["pack"], plan["md"])
        dst = os.path.join(root, plan["md"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        n_copy += 1
    for it in plan["items"]:
        if it.rec_src:
            dst = os.path.join(root, "算法", toolutil.to_os(it.rec_rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(it.rec_src, dst)
            n_copy += 1
            for a, std in fix_record_aliases(dst, kd):
                print("        题 %s 的记录 md：别名 %s → %s（已纠正落盘）"
                      % (it.letter, a, std))
        else:
            desc = " + ".join(it.know)
            wr(os.path.join(root, "算法", toolutil.to_os(it.rec_rel)),
               short_record(it, n, desc, plan["meta"]))
            n_copy += 1
        for src, rel in it.files:
            dst = os.path.join(root, toolutil.to_os(rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            n_copy += 1
    for src, rel in plan["shared"]:
        dst = os.path.join(root, toolutil.to_os(rel))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        n_copy += 1
    print("  [1/5] 落盘 %d 个文件（题解 md + 记录 md + 每题目录）" % n_copy)

    # 2) 反查表行 + 06 对照表（新文件夹：照收，但对照表里得有它）
    idx_path = os.path.join(root, "索引", "题解算法索引.md")
    n_add, dup, n_rm = merge_table_rows(idx_path, ["算法 / 数据结构", "文件夹", "练过的题目"],
                                        plan["back_rows"], placeholder=PLACEHOLDER)
    print("  [2/5] 反查表：新增 %d 行%s%s" % (max(n_add, 0),
          ("，清掉占位行 %d" % n_rm) if n_rm else "",
          ("，跳过重复 %d 行" % len(dup)) if dup else ""))
    ensure_dirs_in_08(plan["mem"], [it.folder for it in plan["items"]], plan["meta"])

    # 3) 题解指针
    n_ptr = 0
    for folder, line in plan["ptr"]:
        p = os.path.join(root, "算法", toolutil.to_os(folder), "题解指针.md")
        if os.path.exists(p):
            t = rd(p)
            if line in [x.strip() for x in t.split("\n")]:
                continue
            toolutil.backup_to_repo(p)
            wr(p, t.rstrip("\n") + "\n" + line + "\n")
        else:
            wr(p, line + "\n")
        n_ptr += 1
    print("  [3/5] 题解指针：新增 %d 行" % n_ptr)

    # 4) 齿轮：index_sync → 状态表行 → fill_knowledge
    rc = run_py("index_sync.py", ["apply", "--root", root, "--mem", plan["mem"]])
    if rc != 0:
        print("★ index_sync 退出码 %d——停在这里，先修再跑" % rc)
        return rc

    sp = os.path.join(root, "题解", "题目状态.md")
    if os.path.exists(sp):
        rows = []
        for it in plan["items"]:
            kstr = kd.final_knowledge(CONT, n, it.letter,
                                      " + ".join(it.know)) if it.scoring != "签到" else ""
            if it.scoring == "签到":
                continue
            # 场次列要写成 `牛客周赛 Round 163`（带空格）——parse_contest 只认这种写法
            rows.append("| %s Round %d | %s | %s | %s | %s | 未做 |  |"
                        % (CONT, n, it.letter, it.title, kstr, it.diff))
        ch, dup, _ = merge_table_rows(sp, STATUS_HEADER, rows)
        print("  [4/5] 状态表：新增 %d 行%s" % (max(ch, 0),
              ("，跳过重复 %d 行" % len(dup)) if dup else ""))
        rc = run_py("fill_knowledge.py", ["apply", "--file", sp, "--index", idx_path])
        if rc != 0:
            print("★ fill_knowledge 退出码 %d（3 = 有题查不到知识点，看上面清单）" % rc)

    # 5) 对账
    print("  [5/5] 对账 archive_check：")
    rc = run_py("archive_check.py", [rn, "--root", root, "--status", sp, "--mem", plan["mem"]])
    return rc


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="导入题解包（默认 dry）")
    ap.add_argument("pack", help="包.zip 或包目录")
    ap.add_argument("--apply", action="store_true", help="真落盘（默认只校验）")
    ap.add_argument("--root", default=toolutil.DATA_ROOT, help="数据根（缺省取 config.json）")
    ap.add_argument("--mem", default=os.path.join(toolutil.REPO_ROOT, "knowledge"),
                    help="知识库目录（06 精简索引的落点）")
    ap.add_argument("--no-check-solution", action="store_true",
                    help="跳过题解 md 的 17 项闸门（只在自己已跑过时用）")
    a = ap.parse_args(argv)
    root = a.root.replace("/", os.sep)
    kd = knowledge_dict.load()
    rep = archive_check.Rep()

    with tempfile.TemporaryDirectory() as td:
        pack_dir, err = open_pack(a.pack, td)
        if err:
            print("★ " + err)
            return 2
        items, plan, meta = validate(pack_dir, root, rep, a.mem,
                                     check_sol=not a.no_check_solution)
        # 报告
        order = {"问题": 0, "提醒": 1, "通过": 2}
        for st, name, details in sorted(rep.items, key=lambda x: order[x[0]]):
            print("[%s] %s" % (st, name))
            for d in details:
                print("        " + d)
        print("-" * 74)
        n_bad = sum(1 for st, _, _ in rep.items if st == "问题")
        if items is None or plan is None:
            print("结论：★包不合格（%d 项问题）★" % n_bad)
            return 1 if n_bad else 2
        if n_bad:
            print("结论：★包不合格（%d 项问题）★——改完重传；未登记的知识点不算问题（照收）" % n_bad)
            return 1

        # 待登记清单（软：不拒收，合并时定夺）—— 单独列出来，别埋在提醒里
        un_names = [(it.letter, x, s) for it in items for x, s in it.unknown_names]
        un_dirs = [(it.letter, it.folder) for it in items if it.folder_note == "未登记"]
        if un_names or un_dirs:
            print("【待登记清单】（**不拒收**：按原样落盘，合并时再定夺）")
            for L, x, sug in un_names:
                print("  · 题 %s 的知识点 %r —— 建议 %s"
                      % (L, x, ("收为「%s」的别名" % sug) if sug else "立为新标准名（没找到相近的）"))
            for L, f in un_dirs:
                print("  · 题 %s 的文件夹 `%s%s` —— 词典文件夹表里没有，落盘照收，"
                      "并在 06 对照表补一行（标了「待登记」）" % (L, f, BS))
            print("-" * 74)

        # 计划预览
        plan.update({"items": items, "root": root, "mem": a.mem, "meta": meta,
                     "pack": pack_dir})
        brows = []
        for it in items:
            brows.extend(rows_for(kd, it))
        plan["back_rows"] = brows
        ptr, seen_ptr = [], set()
        for it in items:
            for pair in ptr_lines(kd, it):
                if pair not in seen_ptr:
                    seen_ptr.add(pair)
                    ptr.append(pair)
        plan["ptr"] = ptr

        n_files = ((1 if plan["md"] else 0) + sum(len(it.files) + 1 for it in items)
                   + len(plan["shared"]))
        n_from_manifest = sum(1 for it in items if it.back_rows)
        print("导入计划（%s Round %d，%s）：" % (CONT, plan["n"],
              "落到 " + root if a.apply else "dry run，不写盘"))
        print("  落盘文件 %d 个：题解 md%s ｜ 每题：%s"
              % (n_files, "（%s）" % plan["md"] if plan["md"] else "★缺",
                 "、".join("%s %s" % (it.letter, "带记录 md" if it.rec_src else "生成精简记录")
                           for it in items)))
        print("  反查表：新增 %d 行（%s）"
              % (len(brows), "manifest 原文，%d/%d 题带" % (n_from_manifest, len(items))
                 if n_from_manifest else "按知识点自动生成"))
        for r in brows:
            print("      " + r)
        print("  题解指针：新增 %d 行" % len(ptr))
        for f, line in ptr:
            print("      `%s%s` 里加：%s" % (f, BS, line))
        rows = ["| %s Round %d | %s | %s | %s | %s | 未做 |  |"
                % (CONT, plan["n"], it.letter, it.title,
                   kd.final_knowledge(CONT, plan["n"], it.letter, " + ".join(it.know)), it.diff)
                for it in items if it.scoring != "签到"]
        print("  状态表：新增 %d 行（签到题不进表）" % len(rows))
        for r in rows:
            print("      " + r)
        if not a.apply:
            print("—— dry run：没写任何文件（要导入加 --apply）——")
            return 0

        print("-" * 74)
        print("开始导入：")
        rc = apply_plan(plan, rep)
        print("-" * 74)
        if rc == 0:
            print("结论：导入完成，archive_check 退出码 0（四处齐全）")
        else:
            print("结论：★导入跑完但 archive_check 退出码 %d（看上面的问题清单）★" % rc)
        return rc


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
