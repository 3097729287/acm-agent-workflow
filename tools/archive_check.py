# -*- coding: utf-8 -*-
r"""
archive_check —— 一场题解「归档四件套」的对账器
================================================

    python archive_check.py <RoundNNN 或 N> [--root <数据根>] [--quiet]

**归档 = 四处一起更新**（细则见《归档》），这个脚本替人记：

  1. 题解 md        <root>/题解/牛客周赛/RoundN/RoundN题解.md 在不在
  2. 算法库记录     <root>/算法/**/牛客周赛RoundN-*.md
                    每份查：固定五节（顺序不变、不加节）、题意节里有 `**数据范围**`、
                    纯 LF、UTF-8 无 BOM、无控制字符
  2b. 题目状态表    本场归档题（非签到题）的题号都要在状态表本场行里，表里不许有本场签到题
                    （默认 `<数据根>/题解/题目状态.md`，`--status` 可换；无归档记录只提醒）
  3. 全量索引       <root>/索引/题解算法索引.md
                    本场小节在不在、小节行数 == 本场记录数、全书条数 == 算法库记录数；
                    逐行对账「归档位置」列 ↔ 记录 md 实际所在文件夹 ↔ 记录 md 头部
                    `**归档文件夹**` 字段（文件名与题名只差空格 / 括号全半角算提醒）；
                    反查表覆盖：本场每题的链接都要出现（《归档》清单第 6 条）
  4. 知识库         `06-题解算法归档` 精简索引行数 == 本场记录数、声明条数 == 全书条数、
                    本场用到的算法文件夹在「算法 → 文件夹 对照表」里；
                    `09-已讲过概念清单` 逐条对账：题解里每个「从零讲」节名都要能在本场登记上
                    （没找到条目 / 已有条目但不在本场 / 还挂在「没讲过」表 → 都只提醒）；
                    题解指针（《归档》清单第 4 条）：全库 `题解指针.md` 格式 + 死指针，
                    反查表里标了「（指针）」的本场条目在对应文件夹的指针文件里要有那一行
  5. 顺手查         RoundN\ 里 .bak / .orig / ~ / .exe / .png 残留（`_work\` 只提醒）、
                    桌面副本的名字是不是 `<比赛名>RoundNNN题解.md`
                    （名字不对 = 问题；压根没有副本只算提醒，因为副本删留都不用管）

**退出码 0 = 归档完成**；有「问题」退 1；「提醒」不影响退出码。
本脚本目前只认牛客周赛（目录名写死 `牛客周赛`），以后加别的比赛时改 CONTEST。
"""

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402  （场次键的唯一解析实现）

CONTEST = "牛客周赛"
BS = chr(92)          # 反斜杠：拼路径时用，避免转义地雷
MEM_DEFAULT = os.path.join(toolutil.REPO_ROOT, "knowledge")   # 知识库（06 归档 / 09 台账）
DESKTOP = toolutil.DESKTOP_COPY_DIR                           # None = 不检查桌面副本

SEC5 = ["## 题意（精简）", "## 关键点（为什么用这个算法）", "## 复杂度", "## 踩过的坑", "## 相关"]

# 索引 / 反查表 / 指针文件里的三种记号
RE_URL = re.compile(r"https://ac\.nowcoder\.com/acm/contest/(\d+)/([A-Z])\b")
RE_ROW = re.compile(r"^\[([^\]]+)\]\((https://ac\.nowcoder\.com/acm/contest/\d+/[A-Z])\)$")
RE_PTR = re.compile(r"^- ([A-Z]) (.+)：`([^`]+)`$")
RE_PTR_MARK = re.compile(r"\[[^\]]*\]\((https://ac\.nowcoder\.com/acm/contest/\d+/[A-Z])\)（指针")

STATUS_DEFAULT = os.path.join(toolutil.DATA_ROOT, "题解", "题目状态.md")                            # 题目状态表（自测用 --status 换）
STATUS_HEADER = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]   # 与 status_report.py 一致


# --------------------------------------------------------------------------
# 报告器：三种状态，每条都给「证据」原文，别只报有/无
# --------------------------------------------------------------------------
class Rep(object):
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


def rd(p):
    return open(p, "rb").read()


def lf_report(rep, name, path):
    """行尾 / BOM / 控制字符：本库约定纯 LF、UTF-8 无 BOM"""
    b = rd(path)
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


def check_record(rep, path):
    """算法库记录 md：五节 / 数据范围 / 行尾"""
    base = os.path.basename(path)
    txt = rd(path).decode("utf-8", "replace")
    lines = txt.split("\n")
    heads = [l.rstrip() for l in lines if l.startswith("## ")]
    if heads != SEC5:
        rep.bad("记录-五节", "%s 的小节 = %s" % (base, " / ".join(h[3:] for h in heads)
                                              if heads else "（一个都没有）"))
    else:
        rep.ok("记录-五节", "%s 五节齐全、顺序对" % base)
    # 数据范围要在「题意」节里
    try:
        i0 = next(i for i, l in enumerate(lines) if l.rstrip() == SEC5[0])
        i1 = next(i for i, l in enumerate(lines) if l.startswith("## ") and i > i0)
        seg = lines[i0:i1]
    except StopIteration:
        seg = []
    hit = next((l for l in seg if l.startswith("**数据范围**")), None)
    if hit:
        rep.ok("记录-数据范围", "%s → %s" % (base, hit.strip()[:72]))
    else:
        rep.bad("记录-数据范围", "%s 的「题意」节里没有 `**数据范围**` 加粗行" % base)
    lf_report(rep, "记录-行尾", path)


# ---- 2b 题目状态表：本场非签到题都要在表里、表里不许有本场签到题 ----

def split_cells(line):
    """切表格行；尊重转义的 \\|、不当分隔符（与 status_report.py 同一套写法）。不是表格行返回 None"""
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


def status_letters(path, n):
    """题目状态表 → 本场题号集合。返回 (集合, 错误文案)。
    场次键走 toolutil.parse_contest：认不出的行打一行 ★（带行号）；别的比赛的
    行跳过并打一行说明；别的场次（同比赛）的行按老样子静默跳过。
    表头锚点照 status_report.py 的写法，但不 import 它——它表头缺失会 SystemExit，
    这里要报成「问题」并继续跑。"""
    if not os.path.exists(path):
        return None, "找不到状态表 %s（归档时本场非签到题要追加进这张表）" % path
    lines = rd(path).decode("utf-8", "replace").split("\n")
    i0 = next((i for i, l in enumerate(lines) if split_cells(l) == STATUS_HEADER), None)
    if i0 is None:
        return None, "状态表里没找到表头「| %s |」：%s" % (" | ".join(STATUS_HEADER), path)
    letters, unparsed, other = set(), [], []
    for i, l in enumerate(lines[i0 + 2:], i0 + 3):   # +2：表头下面紧跟一行分隔线
        c = split_cells(l)
        if not c or len(c) != len(STATUS_HEADER):
            break                        # 主表结束（后面是别的段落）
        if set("".join(c)) <= set("-: "):
            continue
        name, num = toolutil.parse_contest(c[0])
        if name is None:
            unparsed.append((i, c[0]))   # 认不出 → 报警，绝不按裸号处理
            continue
        if (name, num) != (CONTEST, n):
            if name != CONTEST:
                other.append((i, c[0]))  # 别的比赛的行 → 跳过并说明
            continue                     # 别的场次的行 → 老样子静默跳过
        lt = c[1].strip().upper()
        if re.fullmatch(r"[A-Z]", lt):
            letters.add(lt)
    for ln, txt in unparsed:
        print("★ 状态表第 %d 行场次认不出（跳过不处理）：%s" % (ln, txt))
    if other:
        print("说明：状态表跳过 %d 行别的比赛（不属于 %s、不参与本次对账）：%s"
              % (len(other), CONTEST,
                 "；".join("第 %d 行「%s」" % x for x in other[:6])
                 + ("…" if len(other) > 6 else "")))
    return letters, None


def check_status_table(rep, recs, rn, n, path):
    """A = 本场归档记录（= 非签到题）的题号，B = 状态表里本场的题号：
    A-B → 漏加；B-A → 不该在表里（多半是签到题）；A 为空只提醒（不报问题）。"""
    a = set()
    for x in recs:
        m = re.match(r"%s%s-([A-Za-z])(?:-|\.)" % (CONTEST, rn), os.path.basename(x))
        if m:
            a.add(m.group(1).upper())
    b, err = status_letters(path, n)
    if err:
        rep.bad("2b 题目状态表", err)
        return
    if not a:
        rep.warn("2b 题目状态表", "本场没有归档记录（算法库里没有 %s%s-*.md）——"
                 "状态表对账跳过（A 为空只提醒，不报问题）" % (CONTEST, rn))
        return
    miss = sorted(a - b)
    extra = sorted(b - a)
    if miss:
        rep.bad("2b 题目状态表", "漏加：本场这些归档题（非签到题）不在状态表本场行里：%s"
                % "、".join(miss))
    if extra:
        rep.bad("2b 题目状态表", "不该在表里：状态表本场有这些题号、但算法库里没有对应记录"
                "（可能是签到题，签到题不进此表）：%s" % "、".join(extra))
    if not miss and not extra:
        rep.ok("2b 题目状态表", "本场 %d 题（%s）都在状态表里，表里也没有多的本场行"
               % (len(a), "、".join(sorted(a))))


def index_rows(text, round_no):
    """全量索引：本场小节的数据行（含算法文件夹名）"""
    tag = "## %s Round %d" % (CONTEST, round_no)
    lines = text.split("\n")
    if tag not in lines:
        return None, []
    i0 = lines.index(tag)
    i1 = len(lines)
    for i in range(i0 + 1, len(lines)):
        if lines[i].startswith("## "):
            i1 = i
            break
    rows = []
    for l in lines[i0:i1]:
        s = l.strip()
        if not s.startswith("|") or s.startswith("| 题号") or "---" in s:
            continue
        rows.append(s)
    return tag, rows


def index_total(text):
    """全书条数：所有 `## 牛客周赛 Round N` 小节的数据行之和"""
    total = 0
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("## %s Round " % CONTEST):
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if s.startswith("## "):
                    break
                if s.startswith("|") and not s.startswith("| 题号") and "---" not in s:
                    total += 1
    return total


def row_fields(row):
    """索引数据行 → dict（题号 / 题名 / 链接 / cid / 难度 / 算法 / 归档位置）；解析不了返回 None"""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    if len(cells) != 5:
        return None
    m = RE_ROW.match(cells[1])
    if not m:
        return None
    u = RE_URL.match(m.group(2))
    return {"letter": cells[0].strip(), "name": m.group(1), "url": m.group(2),
            "cid": u.group(1), "diff": cells[2], "algo": cells[3],
            "loc": cells[4].strip("`").rstrip(BS)}


def back_section(itext):
    """全量索引里「## 一、反查表」段落原文；找不到返回 None"""
    if "## 一、反查表" not in itext:
        return None
    return itext.split("## 一、反查表", 1)[1].split("\n## 二、", 1)[0]


def norm_dir(p):
    """路径归一化：正斜杠换反斜杠、去尾部反斜杠，只用于比对"""
    return p.strip().replace("/", BS).rstrip(BS)


def norm_name(s):
    """题名归一化：去空格 + 全角括号转半角，只用于判「文件名与题名只是风格差」"""
    return (s.replace("（", "(").replace("）", ")")
             .replace(" ", "").replace("　", ""))


def loc_of(val, root):
    """记录头部 `**归档文件夹**` 的值 → 相对「<数据根>\\算法\\」的文件夹名。
    兼容三种写法：相对（`字典树\\` 或 `算法\\字典树\\`）、`<数据根>\\算法\\字典树\\` 占位、
    本数据根的绝对路径。绝对路径但不是本数据根（换过位置）→ 返回 None，只提醒不报问题。"""
    v = val.strip().replace("/", BS).rstrip(BS)
    v = re.sub(r"<数据根>|<ROOT>", "", v).strip(BS)
    vn = norm_dir(v)
    full_root = norm_dir(os.path.join(root, "算法"))
    if ":" in v or v.startswith(BS):          # 绝对路径
        if vn.lower().startswith(full_root.lower()):
            vn = vn[len(full_root):].strip(BS)
        else:
            return None
    elif vn.lower().startswith("算法" + BS):
        vn = vn[len("算法"):].strip(BS)
    return vn or None


def check_positions(rep, root, rn, rows):
    """索引「归档位置」列 ↔ 记录 md 实际所在文件夹 ↔ 记录 md 头部 `**归档文件夹**` 字段"""
    for row in rows:
        f = row_fields(row)
        if f is None:
            rep.bad("3 全量索引-行格式", "不是「题号 | [题名](链接) | 难度 | 算法 | 归档位置」五格：%s" % row[:90])
            continue
        tag = "%s %s" % (f["letter"], f["name"])
        want = os.path.join(root, "算法", f["loc"],
                            "%s%s-%s-%s.md" % (CONTEST, rn, f["letter"], f["name"]))
        if os.path.exists(want):
            head, val = os.path.join(root, "算法", f["loc"]), None
            for l in rd(want).decode("utf-8", "replace").split("\n"):
                m = re.search(r"- \*\*归档文件夹\*\*：\s*(.*)$", l)
                if not m:
                    continue
                mm = re.search(r"`([^`]+)`", m.group(1))
                val = mm.group(1) if mm else m.group(1).split("（")[0].strip()
                break
            if val is None:
                rep.bad("3 归档位置", "%s 的记录 md 里没有 `- **归档文件夹**：` 行 ← %s"
                        % (tag, os.path.relpath(want, root).replace("/", BS)))
            else:
                rloc = loc_of(val, root)
                if rloc is None:
                    rep.warn("3 归档位置", "%s 的记录 md 头部写「%s」——不是本数据根下的路径"
                             "（换过数据根？推荐写相对 `算法\\` 的文件夹名，如 `%s\\`），只提醒不算错"
                             % (tag, val, f["loc"]))
                elif norm_dir(rloc) != norm_dir(f["loc"]):
                    rep.bad("3 归档位置", "%s 的头写「%s」（→ `%s`），索引写 `%s` —— 对不上"
                            % (tag, val, rloc, f["loc"]))
                else:
                    rep.ok("3 归档位置", "%s → `%s%s`（记录 md 头部字段也一致）" % (tag, f["loc"], BS))
        else:
            hits = glob.glob(os.path.join(root, "算法", "**",
                                          "%s%s-%s-*.md" % (CONTEST, rn, f["letter"])), recursive=True)
            here, other = [], []
            for h in hits:
                m2 = re.match(r"%sRound\d+-%s-(.+)\.md$" % (CONTEST, f["letter"]),
                              os.path.basename(h))
                nm = m2.group(1) if m2 else os.path.basename(h)
                if norm_name(nm) != norm_name(f["name"]):
                    continue
                if norm_dir(os.path.dirname(h)) == norm_dir(os.path.join(root, "算法", f["loc"])):
                    here.append(h)
                else:
                    other.append(h)
            if here:
                rep.warn("3 归档位置", "%s 的记录在正确文件夹里，但文件名与题名有风格差（空格 / 括号全半角）：实际叫 %s"
                         % (tag, "、".join(os.path.basename(h) for h in here)))
            elif hits:
                at = "、".join(os.path.relpath(os.path.dirname(h), os.path.join(root, "算法")).replace("/", BS)
                              for h in hits)
                rep.bad("3 归档位置", "%s 索引写 `%s%s`，记录 md 实际在 `%s`" % (tag, f["loc"], BS, at))
            else:
                rep.bad("3 归档位置", "%s 索引写 `%s%s`，但算法库里找不到 %s%s-%s-*.md"
                        % (tag, f["loc"], BS, CONTEST, rn, f["letter"]))


def check_back_index(rep, itext, rows):
    """反查表（08 清单第 6 条）：本场每题都要在反查表出现。
    返回 {(cid, 题号): {文件夹}} = 反查表里标了「（指针）」的本场条目，供指针文件回验。"""
    want_ptr = {}
    sec = back_section(itext)
    if sec is None:
        rep.warn("3 反查表", "全量索引里找不到 `## 一、反查表` 小节，跳过")
        return want_ptr
    have = RE_URL.findall(sec)
    have_set = set(have)
    miss = []
    for row in rows:
        f = row_fields(row)
        if f and (f["cid"], f["letter"]) not in have_set:
            miss.append("%s %s" % (f["letter"], f["name"]))
    if miss:
        rep.bad("3 反查表", "本场这些题没在反查表出现：%s" % "、".join(miss))
    else:
        rep.ok("3 反查表", "本场 %d 题的链接都在反查表里（反查表共 %d 条题目链接）"
               % (len(rows), len(have)))
    for l in sec.split("\n"):
        s = l.strip()
        if not s.startswith("|") or s.startswith("| 算法") or "---" in s:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        dirs = re.findall("`([^`]+)`", cells[1])
        folder = dirs[0].rstrip(BS) if dirs else ""
        if not folder:
            continue
        for m in RE_PTR_MARK.finditer(cells[2]):
            u = RE_URL.match(m.group(1))
            want_ptr.setdefault((u.group(1), u.group(2)), set()).add(folder)
    return want_ptr


def check_ptr_files(rep, root, rows, want_ptr):
    """`题解指针.md`（08 清单第 4 条）：格式 + 死指针（全库扫描）+
    反查表标了「（指针）」的本场条目必须有对应指针行"""
    files = sorted(glob.glob(os.path.join(root, "算法", "**", "题解指针.md"), recursive=True))
    entries, fmt_bad, dead, style_warn = [], [], [], []
    for pf in files:
        self_dir = os.path.basename(os.path.dirname(pf))
        rel = os.path.relpath(pf, root)
        for i, l in enumerate(rd(pf).decode("utf-8", "replace").split("\n"), 1):
            s = l.strip()
            if not s:
                continue
            m = RE_PTR.match(s)
            if not m:
                fmt_bad.append("%s 第 %d 行：%s" % (rel, i, s[:70]))
                continue
            letter, name, target = m.group(1), m.group(2), m.group(3).rstrip(BS)
            entries.append((letter, name, target, self_dir))
            tdir = os.path.join(root, "算法", target)
            hit, style = False, None
            if os.path.isdir(tdir):
                for fn in os.listdir(tdir):
                    if not fn.startswith("%sRound" % CONTEST) or not fn.endswith(".md"):
                        continue
                    if fn.endswith("-%s-%s.md" % (letter, name)):
                        hit = True
                        break
                    m2 = re.match(r"%sRound\d+-%s-(.+)\.md$" % (CONTEST, letter), fn)
                    if m2 and norm_name(m2.group(1)) == norm_name(name):
                        style = fn
                if not hit and style:
                    hit = True
            if not hit:
                dead.append("%s 第 %d 行 → 主文件夹 `%s%s` 里找不到 Round*-%s-%s.md"
                            % (rel, i, target, BS, letter, name))
            elif style:
                style_warn.append("%s 第 %d 行：文件名与题名只差空格 / 括号全半角（实际文件名 %s）"
                                  % (rel, i, style))
            if target == self_dir:
                dead.append("%s 第 %d 行 → 指回自己所在的 `%s%s`（指针要指主文件夹）"
                            % (rel, i, target, BS))
    if fmt_bad:
        rep.bad("4 题解指针-格式", "共 %d 行不符「- <题号> <题名>：`主文件夹\\`」：%s"
                % (len(fmt_bad), "；".join(fmt_bad)))
    if dead:
        rep.bad("4 题解指针-死指针", "共 %d 处：%s" % (len(dead), "；".join(dead)))
    if files and not fmt_bad and not dead:
        rep.ok("4 题解指针", "全库 %d 个指针文件 / %d 行，格式全对且都指向存在的记录 md"
               % (len(files), len(entries)))
    if style_warn:
        rep.warn("4 题解指针-文件名风格差", "共 %d 处（记录找得到，只是文件名与题名差在空格 / 括号全半角）：%s"
                 % (len(style_warn), "；".join(style_warn)))
    mine = set((row_fields(r)["letter"], norm_name(row_fields(r)["name"]))
               for r in rows if row_fields(r))
    n_here = sum(1 for e in entries if (e[0], norm_name(e[1])) in mine)
    if n_here:
        rep.ok("4 题解指针-本场", "本场题目的指针 %d 行" % n_here)
    if want_ptr:
        # 口径：反查表某行（文件夹 F）给题目 T 标了「（指针）」= T 的记录不在 F，F 里
        # 应有一行指针指向 T 的主文件夹 —— 所以只查「F 的题解指针.md 里有没有 T 这一行」
        ptr_dirs = set((le, norm_name(na), sd) for (le, na, _t, sd) in entries)
        by_key = {}
        for r in rows:
            f = row_fields(r)
            if f:
                by_key[(f["cid"], f["letter"])] = f
        miss = []
        for (cid, letter), folders in sorted(want_ptr.items()):
            f = by_key.get((cid, letter))
            if f is None:
                continue                      # 反查表里别的场次的标记，不归本场管
            for folder in sorted(folders):
                # 指针文件里的 self_dir 取的是文件夹 basename（`DP\树形DP\` → `树形DP`），
                # 比对键也 basename 化；否则双层文件夹（DP\树形DP）的「（指针）」标记永远对不上
                if (letter, norm_name(f["name"]), folder.split(BS)[-1]) not in ptr_dirs:
                    miss.append("%s %s → `%s%s` 的题解指针.md 里没有这一行"
                                % (letter, f["name"], folder, BS))
        if miss:
            rep.bad("4 题解指针-反查表回验", "反查表标了「（指针）」但指针文件里没有：%s" % "；".join(miss))
        else:
            rep.ok("4 题解指针-反查表回验", "反查表里本场的「（指针）」标记都有对应指针行")


# ---- 11 台账：题解里的「从零讲」节名逐条对账 ----

_STOP_KEYS = {"什么", "怎么", "为什么", "一个", "我们", "可以", "就是", "这个", "那个",
              "一下", "如何", "以及", "怎么用", "是什么", "做什么", "这样", "那样"}
_SPLIT_KEYS = re.compile(r"[\s、，,。；;：:（）()「」『』“”\"'·+/=＝\-*`~|｜]+")


def concept_keys(name):
    """「从零讲」节名 → 在台账里匹配用的小片段（宁松勿严：本检查只出「提醒」）"""
    keys = set()
    for part in _SPLIT_KEYS.split(name):
        s = "".join(part.split()).lower()
        if len(s) < 2 or s in _STOP_KEYS:
            continue
        if re.fullmatch(r"[a-z0-9]{2}", s):
            continue          # 「DP」「ST」这类两字符缩写太泛，不作 key

        keys.add(s)
        if len(s) > 4 and re.search(r"[一-鿿]", s):
            for g in (3, 4):
                keys.update(s[i:i + g] for i in range(len(s) - g + 1))
    return keys


def check_11_topics(rep, solu, t11, n):
    """题解里每个「从零讲」节名 → 台账 11：未登记 / 登记在别场 / 还挂在「没讲过」表"""
    if not solu or not os.path.exists(solu):
        return
    stext = rd(solu).decode("utf-8", "replace")
    topics = []
    for t in re.findall(r"^### 从零讲：\s*(.*?)\s*$", stext, re.M):
        if t and t not in topics:
            topics.append(t)
    if not topics:
        rep.ok("4c 09 从零讲对账", "本场题解里没有「从零讲」节（没有新概念要登记）")
        return
    lines = t11.split("\n")
    norms = ["".join(l.split()).lower() for l in lines]
    i3 = next((i for i, l in enumerate(lines) if l.startswith("## 三、")), None)
    if i3 is None:
        rep.warn("4c 09 从零讲对账", "09 里找不到 `## 三、` 小节（结构变了？）——跳过")
        return
    i4 = next((i for i, l in enumerate(lines) if l.startswith("## 四、")), len(lines))
    iun = next((i for i, l in enumerate(lines) if l.startswith("### 高频")), i4)
    if not (i3 < iun < i4):
        iun = i4
    issues, okc = [], 0
    for topic in topics:
        keys = concept_keys(topic)
        hit3 = [i for i in range(i3, iun)
                if lines[i].startswith("|") and any(k in norms[i] for k in keys)]
        # 「未讲」表里的历史存档行（`~~…~~ **已移出**`）不算「还挂着」
        hitun = [i for i in range(iun, i4)
                 if lines[i].startswith("|") and "已移出" not in lines[i]
                 and any(k in norms[i] for k in keys)]
        mine = [i for i in hit3 if ("Round %d" % n) in lines[i]]
        if hitun:
            issues.append("「%s」还挂在「高频但还没从零讲过」表（第 %d 行）→ 本场已从零讲："
                          "照 11 第四节把它移出、登记进第三节" % (topic, hitun[0] + 1))
        if mine:
            okc += 1
        elif hit3:
            issues.append("「%s」已有条目、但里面没有本场（第 %d 行）→ 若是本场新讲的，"
                          "核对是否该降为指针；若 09 写错了首次出现，顺手改对" % (topic, hit3[0] + 1))
        elif not hitun:
            issues.append("「%s」在 11 里没找到条目 → 若是首次从零讲，登记进第三节"
                          "（概念名 / 首次出现 = 本场题号 / 讲在哪一节）" % topic)
    if issues:
        rep.warn("4c 09 从零讲对账",
                 "本场 %d 个「从零讲」节：%d 个已在本场登记、%d 条待看（只是提醒，不卡退出码）"
                 % (len(topics), okc, len(issues)))
        for it in issues:
            rep.warn("4c 09 从零讲对账", it)
    else:
        rep.ok("4c 09 从零讲对账", "本场 %d 个「从零讲」节都已在本场登记" % okc)


def main(argv=None):
    ap = argparse.ArgumentParser(description="题解归档四件套对账")
    ap.add_argument("round", help="RoundNNN 或 NNN")
    ap.add_argument("--root", default=toolutil.DATA_ROOT)
    ap.add_argument("--quiet", action="store_true", help="只打印问题与提醒")
    ap.add_argument("--mem", default=MEM_DEFAULT,
                    help="知识库目录（默认 <仓库>/knowledge）")
    ap.add_argument("--status", default=STATUS_DEFAULT,
                    help="题目状态表路径（默认 %s；自测可指向副本）" % STATUS_DEFAULT)
    a = ap.parse_args(argv)

    n = int(a.round.lower().replace("round", "").strip() or 0)
    rn = "Round%d" % n
    root = a.root.replace("/", os.sep)
    rep = Rep()

    # ---- 1. 题解 md ----
    solu = os.path.join(root, "题解", CONTEST, rn, "%s题解.md" % rn)
    if os.path.exists(solu):
        rep.ok("1 题解 md", "%s（%d 字节）" % (solu, os.path.getsize(solu)))
    else:
        rep.bad("1 题解 md", "找不到 %s" % solu)

    # ---- 2. 算法库记录 ----
    recs = sorted(glob.glob(os.path.join(root, "算法", "**", "%s%s-*.md" % (CONTEST, rn)),
                            recursive=True))
    if recs:
        rep.ok("2 算法库记录", "找到 %d 份：%s" % (len(recs), "、".join(os.path.basename(x) for x in recs)))
        for x in recs:
            check_record(rep, x)
    else:
        rep.bad("2 算法库记录", "算法库里没有 %s%s-*.md" % (CONTEST, rn))

    # ---- 2b. 题目状态表 ----
    check_status_table(rep, recs, rn, n, a.status.replace("/", os.sep))

    # ---- 3. 全量索引 ----
    idx_path = os.path.join(root, "索引", "题解算法索引.md")
    tag, rows, tot_idx = None, [], -1
    want_ptr = {}
    if not os.path.exists(idx_path):
        rep.bad("3 全量索引", "找不到 %s" % idx_path)
    else:
        itext = rd(idx_path).decode("utf-8", "replace")
        tag, rows = index_rows(itext, n)
        if tag is None:
            rep.bad("3 全量索引", "没有小节 `## %s Round %d`" % (CONTEST, n))
        else:
            if len(rows) == len(recs):
                rep.ok("3 全量索引", "小节 `%s` 有 %d 行，与记录数一致" % (tag, len(rows)))
            else:
                rep.bad("3 全量索引", "小节 `%s` 有 %d 行，但算法库记录 %d 份——对不上"
                        % (tag, len(rows), len(recs)))
            check_positions(rep, root, rn, rows)
            want_ptr = check_back_index(rep, itext, rows)
        tot_idx = index_total(itext)
        nfiles = sum(1 for _ in glob.glob(os.path.join(root, "算法", "**",
                                                       "%sRound*-*.md" % CONTEST), recursive=True))
        if tot_idx == nfiles:
            rep.ok("3 全量索引-总条数", "全书 %d 条 == 算法库 %d 个记录文件" % (tot_idx, nfiles))
        else:
            rep.warn("3 全量索引-总条数", "索引共 %d 条，算法库记录文件 %d 个——对不上（手工加过/漏过）"
                     % (tot_idx, nfiles))
        lf_report(rep, "3 全量索引-行尾", idx_path)

    # ---- 4. 知识库 06 / 09 ----
    p08 = os.path.join(a.mem, "06-题解算法归档.md")
    if not os.path.exists(p08):
        rep.bad("4 06 精简索引", "找不到 %s" % p08)
    else:
        t08 = rd(p08).decode("utf-8", "replace")
        want = "%s Round %d" % (CONTEST, n)
        rows08 = []
        for l in t08.split("\n"):
            c = [x.strip() for x in l.split("|")]
            if len(c) >= 6 and c[1].count("-") == 2 and c[2] == want:
                rows08.append(c)
        if len(rows08) == len(recs) and recs:
            rep.ok("4 06 精简索引", "本场 %d 行，与记录数一致" % len(rows08))
        else:
            rep.bad("4 06 精简索引", "本场 %d 行，算法库记录 %d 份——对不上" % (len(rows08), len(recs)))
        # 声明的条数
        m = re.search("共 (\\d+) 条", t08)
        if m and tot_idx >= 0:
            if int(m.group(1)) == tot_idx:
                rep.ok("4 06 声明条数", "「共 %s 条」== 全量索引 %d 条" % (m.group(1), tot_idx))
            else:
                rep.bad("4 06 声明条数", "08 写「共 %s 条」，全量索引实际 %d 条" % (m.group(1), tot_idx))
        # 对照表：本场用到的算法文件夹必须都在
        if tag is not None:
            sec6 = t08.split("## 六、")[-1].split("## 相关")[0] if "## 六、" in t08 else ""
            want_dirs = set()
            for r in rows:
                spans = re.findall("`([^`]+)`", r)
                if spans:
                    want_dirs.add(spans[-1].rstrip(BS))
            missing = [d for d in sorted(want_dirs) if ("`%s%s`" % (d, BS)) not in sec6]
            if not sec6:
                rep.warn("4 06 对照表", "08 里找不到 `## 六、` 对照表小节，跳过")
            elif missing:
                rep.bad("4 06 对照表", "本场用到但对照表里没有：%s" % "、".join(missing))
            else:
                rep.ok("4 06 对照表", "本场 %d 个文件夹都在对照表里：%s"
                       % (len(want_dirs), "、".join(sorted(want_dirs))))
        lf_report(rep, "4 06-行尾", p08)

    p11 = os.path.join(a.mem, "09-已讲过概念清单.md")
    if not os.path.exists(p11):
        rep.warn("4 09 台账", "找不到 %s" % p11)
    else:
        t11 = rd(p11).decode("utf-8", "replace")
        check_11_topics(rep, solu, t11, n)

    # ---- 4b. 题解指针（08 清单第 4 条）----
    check_ptr_files(rep, root, rows, want_ptr)

    # ---- 5. 残留 + 桌面副本 ----
    rdir = os.path.join(root, "题解", CONTEST, rn)
    if os.path.isdir(rdir):
        junk = []
        for dp, dns, fns in os.walk(rdir):
            for f in fns:
                if f.endswith((".bak", ".orig", "~", ".exe", ".png")):
                    junk.append(os.path.join(dp, f))
        if junk:
            rep.bad("5 残留", "题解区有 %d 个不该留的文件：%s"
                    % (len(junk), "、".join(os.path.relpath(x, rdir) for x in junk)))
        else:
            rep.ok("5 残留", "%s 里没有 .bak/.orig/~/exe/png" % rn)
        if os.path.isdir(os.path.join(rdir, "_work")):
            rep.warn("5 _work", "还有 `_work\\`（耗材，随手清；复验前重抓一次即可）")
    if not DESKTOP:
        rep.warn("5 桌面副本", "没配 desktop_copy_dir（config.json），跳过桌面副本检查")
    else:
        desk = sorted(glob.glob(os.path.join(DESKTOP, "*%s题解*.md" % rn)))
        if not desk:
            rep.warn("5 桌面副本", "%s 里没有 %s 的副本（副本删留都不用管，只是提醒）" % (DESKTOP, rn))
        else:
            want_name = "%s%s题解.md" % (CONTEST, rn)
            for d in desk:
                if os.path.basename(d) == want_name:
                    rep.ok("5 桌面副本", "名字对：%s" % want_name)
                else:
                    rep.bad("5 桌面副本", "名字是 %s；按规矩桌面副本一旦存在就必须叫 %s"
                            % (os.path.basename(d), want_name))

    # ---- 输出 ----
    order = {"问题": 0, "提醒": 1, "通过": 2}
    for st, name, details in sorted(rep.items, key=lambda x: order[x[0]]):
        if a.quiet and st == "通过":
            continue
        print("[%s] %s" % (st, name))
        for d in details:
            print("        " + d)
    print("-" * 74)
    n_bad = sum(1 for st, _, _ in rep.items if st == "问题")
    if n_bad:
        print("结论：★有 %d 项问题，归档没做完★（另有 %d 条提醒）" % (n_bad, rep.n_warn))
    else:
        print("结论：四处齐全，归档完成（%d 条提醒）" % rep.n_warn)
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
