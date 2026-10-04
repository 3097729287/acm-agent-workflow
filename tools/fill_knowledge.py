# -*- coding: utf-8 -*-
"""题目状态表：迁移 / 刷新「知识点」列（数据源 = 全量索引）。

用法：
    python fill_knowledge.py [dry|apply] [--file 状态表] [--index 索引] [--help]

做的事：
  1. 表头由旧版 `场次|题号|题名|难度|状态|日期|备注` 换成
     新版 `场次|题号|题名|知识点|难度|状态|日期`（删备注、知识点插在题名之后）；
  2. 用索引里每题的「算法 / 数据结构」列算出知识点，填进新列。
     场次键 = `toolutil.parse_contest` 给的 (比赛名, 场次号) + 题号，
     多平台不会撞号（Codeforces Round 161 与牛客 Round 161 各算各的）。

退出码：
  0  正常（dry / apply 都可能是 0）；
  2  状态表里认不出表头（旧版 / 新版 7 列表头都没有）；
  3  有「查不到知识点」的题（含场次认不出、被跳过的行），**或归一后仍有未登记知识点
     （2026-10-05 起：强制标准命名，未登记段报出来，逼着收编或改写法）**——
     dry 与 apply 一样；apply 仍照常写文件，只是退出码变大，方便上层察觉。

知识点写法（用户 2026-10-05 定稿，v2；写法规则唯一出处 = 词典「五、写法规则」）：
    `解法1[主] + 泛用知识点 ； 解法2 ； 解法3`
    · `；` = 解法分隔（正解排最前，其余是另解）；组内 ` + ` = 同一解法里并列使用的知识点
    · `[…]` 打包一组同时出现的小知识点（可嵌套）；`[主]` / `[次]` 标主次（可省略）
    · 旧格式 `主 ｜ 次1、次2`（全角竖线 U+FF5C）2026-10-05 起废止

归一：规则与词表的唯一出处 = `knowledge/15-知识点词典.md`，
解析器 = 同目录 `knowledge_dict.py`（本文件不再藏任何名字表）：
    · 标准名 = 词典「一、标准名表」（多数就是算法库文件夹名，含 DP 子文件夹）；
      同义合并（二分 → 二分查找）
    · 细节短语一律删（只留在单题题解里）；**两个不同的解法之间只能写 `；`，不许拿空格并排**
    · 已定稿题目查词典「四、已定稿题目」（人工过审）；新场次走自动归一
      （含组合名展开与修饰兜底）

只改表头行 + 数据行里对应单元格，其余行逐字节不动；apply 前自动备份；纯 LF 无 BOM。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil        # noqa: E402  （备份统一走它）
import knowledge_dict  # noqa: E402  （知识点归一/词表的唯一实现）

DEFAULT_FILE = os.path.join(toolutil.DATA_ROOT, "题解", "题目状态.md")
DEFAULT_INDEX = os.path.join(toolutil.DATA_ROOT, "索引", "题解算法索引.md")

USAGE = """用法：python fill_knowledge.py [dry|apply] [--file <状态表>] [--index <索引>] [--help]

题目状态表：迁移 / 刷新「知识点」列（数据源 = 全量索引；场次键 = 比赛名 + 场次号，
多平台不撞号）。默认 dry（只看不动）；加 apply 才写文件（写前按备份规则自动备份）。

退出码：
  0  正常；
  2  状态表里认不出表头（旧版 / 新版 7 列表头都没有）；
  3  有「查不到知识点」的题（含场次认不出、被跳过的行）—— dry 与 apply 一样；
     apply 仍照常写文件，只是退出码变大，方便上层察觉。
"""

HEAD_OLD = ["场次", "题号", "题名", "难度", "状态", "日期", "备注"]
HEAD_NEW = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]
LABEL = "## 题目状态表"
PUNCT = "\u3001"        # 顿号


# ---------------------------------------------------------------- 解析小工具
def split_cells(line):
    """切表格行（尊重转义 \\|）；不是表格行返回 None"""
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


# ---------------------------------------------------------------- 归一
# 词表与规则全在 `knowledge/15-知识点词典.md`，解析器是 `knowledge_dict.py`。
# 本文件只负责「读索引 → 查词典 → 写状态表」，不再藏名字表（数据驱动）。


# ---------------------------------------------------------------- 读索引
def read_index(path):
    """{(比赛名, 场次号, 字母): 知识点} + 诊断清单（场次键走 toolutil.parse_contest，不写死牛客）

    知识点 = 索引「算法 / 数据结构」列经词典归一（定稿表优先 → 自动归一）。
    返回 (out, unknown, mapped)：
      unknown = [(题键, 段, 建议)]   归一后仍非标准名的段（会被报出来，强制收编/改写法）
      mapped  = [(题键, 段, 标准名)] 修饰兜底命中的段（未经收编，供人工核对）"""
    kd = knowledge_dict.load()
    out = {}
    unknown, mapped = [], []
    name, rnd = None, None
    for line in io.open(path, encoding="utf-8").read().split("\n"):
        m = re.match(r"^##(?!#)\s+(.*)$", line)
        if m:
            name, rnd = toolutil.parse_contest(m.group(1))   # 非场次小节 → (None, None)
            continue
        if name is None:
            continue
        c = split_cells(line)
        if not c or len(c) != 5 or not re.fullmatch(r"[A-Z]", c[0]):
            continue
        u, mp = [], []
        out[(name, rnd, c[0])] = kd.final_knowledge(name, rnd, c[0], c[3],
                                                    unknown=u, mapped=mp)
        key = "%s R%d%s" % (name, rnd, c[0])
        unknown += [(key, x, s) for x, s in u]
        mapped += [(key, x, s) for x, s in mp]
    return out, unknown, mapped


# ---------------------------------------------------------------- 改状态表
def run(mode, fpath, ipath):
    idx, unknown, mapped = read_index(ipath)
    text = io.open(fpath, encoding="utf-8").read()
    lines = text.split("\n")
    i0 = next((i for i, l in enumerate(lines) if split_cells(l) == HEAD_OLD
               or split_cells(l) == HEAD_NEW), None)
    if i0 is None:
        print("\u2605找不到表头（旧版或新版 7 列都认不出）：", fpath)
        return 2
    old = split_cells(lines[i0]) == HEAD_OLD
    print("表头：%s（%s）" % ("旧版（含备注）" if old else "新版（含知识点）",
                           "将迁移成新版" if old else "只刷新知识点"))

    miss, unparsed, touched, newlines, present = [], [], 0, [], set()
    for i, l in enumerate(lines):
        c = split_cells(l)
        if i <= i0 or not c or len(c) != 7 or set("".join(c)) <= set("-: "):
            newlines.append(l)              # 表头 / 分隔线 / 非表格行
            continue
        name, rnd = toolutil.parse_contest(c[0])
        if name is None:
            unparsed.append((i + 1, c[0]))
            newlines.append(l)              # 认不出 → 原样留着，绝不当牛客处理
            continue
        if old:
            f, lt, ti, dif, st, dt = c[0], c[1], c[2], c[3], c[4], c[5]
        else:
            f, lt, ti, dif, st, dt = c[0], c[1], c[2], c[4], c[5], c[6]
        present.add((name, rnd, lt.upper()))
        know = idx.get((name, rnd, lt.upper()), "")
        if not know:
            miss.append("%s R%d%s" % (name, rnd, lt))
        new = "| %s | %s | %s | %s | %s | %s | %s |" % (f, lt, ti, know, dif, st, dt)
        if new != l:
            touched += 1
        newlines.append(new)

    newtext = "\n".join(newlines)
    newtext = newtext.replace("| " + " | ".join(HEAD_OLD) + " |",
                              "| " + " | ".join(HEAD_NEW) + " |", 1)
    extra = sorted(set(idx) - present)
    print("改动行数：%d ｜ 索引里查不到知识点的题：%s" % (touched, PUNCT.join(miss) or "无"))
    if extra:
        print("索引里有、状态表里没有的：%s" % PUNCT.join("%s R%d%s" % k for k in extra))
    for ln, txt in unparsed:
        print("★ 状态表第 %d 行场次认不出，跳过不填（绝不当牛客处理）：%s" % (ln, txt))
    if mapped:
        print("修饰兜底自动映射（未经收编，核对一下）：%s"
              % "；".join("%s「%s」→「%s」" % t for t in mapped))
    for key, x, s in unknown:
        print("★ 未登记知识点：%s「%s」%s（归一后仍非标准名——收编进词典或改写法）"
              % (key, x, ("（最接近：%s）" % s) if s else ""))
    bad = bool(miss or unparsed or unknown)
    if bad:
        items = list(miss) + ["第 %d 行「%s」" % (ln, txt) for ln, txt in unparsed]
        if items:
            print("★ 索引里查不到知识点（%d 个）：%s（先补索引或修表，别留空）"
                  % (len(items), PUNCT.join(items)))
        if unknown:
            print("★ 有未登记知识点（%d 个）——知识点强制走标准名，见词典写法规则"
                  % len(unknown))
    if mode != "apply":
        print("—— dry run，没写文件（要写加 apply）——")
        return 3 if bad else 0
    bak = toolutil.backup_to_repo(fpath)
    io.open(fpath, "w", encoding="utf-8", newline="\n").write(newtext)
    print("已写：%s\n备份：%s" % (fpath, bak))
    return 3 if bad else 0


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    mode = "apply" if "apply" in argv else "dry"
    a = argv[1:] if argv and argv[0] in ("dry", "apply") else argv
    fpath, ipath = DEFAULT_FILE, DEFAULT_INDEX
    for i, x in enumerate(a):
        if x == "--file":
            fpath = a[i + 1]
        if x == "--index":
            ipath = a[i + 1]
    return run(mode, fpath, ipath)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
