# -*- coding: utf-8 -*-
r"""export_solution —— 把一场（或一题）的题解导出成标准「题解包」

    python export_solution.py Round163 [-o 输出.zip|输出目录] [--root <数据根>] [--contributor 名字]
    python export_solution.py Round163-G -o G.zip

包 = 数据根的一个子集 + 一份 `manifest.json`（装箱单）：

    牛客周赛Round163.zip
    ├── manifest.json                  ← 唯一的新格式，人可读可手写
    ├── 题解\牛客周赛\Round163\...      ← 整场题解 md + 每题目录（代码 / 验证驱动 / 图脚本）
    └── 算法\<文件夹>\牛客周赛Round163-*.md   ← 算法记录（五节模板）

**打包即过滤**（口径 = `toolutil.is_junk`）：`_work\` / `__pycache__\` / `.exe` / `.png` /
`.bak` 等耗材不进包——包只装源码与文档。

题面各字段全部取自**算法库记录 md 的头部**（单一事实来源，走 `index_sync.parse_record`）；
`manifest.problems[].back_rows` 是从索引反查表里摘出的本场行原文（可选字段；
带上它，导入侧能把反查表原样复原——手写包不带也行，导入会按知识点自动生成简版）。

输出：`-o` 以 `.zip` 结尾 → 打 zip；否则当目录写。缺省 = 当前目录下 `<比赛名>RoundN.zip`。
"""
import argparse
import json
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil        # noqa: E402
import knowledge_dict  # noqa: E402
import index_sync      # noqa: E402  （记录 md 的唯一解析实现）

BS = chr(92)
CONT = "牛客周赛"                      # 与 archive_check / index_sync 同一口径
RE_TARGET = re.compile(r"^(?:%s)?\s*Round\s*(\d+)(?:\s*-\s*([A-Za-z]))?$" % CONT)
RE_ROW_LINK = re.compile(r"\[([A-Z]) ([^\]]+)\]\((https://ac\.nowcoder\.com/acm/contest/(\d+)/[A-Z])\)")
PLACEHOLDER = "（归档第一场后逐行补）"


def rd(p):
    return open(p, encoding="utf-8").read()


def fail(msg):
    print("★ " + msg)
    return 2


# ---------------------------------------------------------------- 反查表
def back_rows_of(index_text, cid):
    """索引反查表里 3rd 格含本场（cid）链接的行原文（按出现顺序）"""
    if "## 一、反查表" not in index_text:
        return []
    sec = index_text.split("## 一、反查表", 1)[1].split("\n## 二、", 1)[0]
    out = []
    for l in sec.split("\n"):
        s = l.strip()
        if not s.startswith("|") or PLACEHOLDER in s or "---" in s:
            continue
        if any(m.group(4) == cid for m in RE_ROW_LINK.finditer(s)):
            out.append(s)
    return out


def letters_in(row):
    return sorted({m.group(1) for m in RE_ROW_LINK.finditer(row)})


# ---------------------------------------------------------------- 收集
def collect(root, n, letter=None):
    """→ (problems, files, notes)；problems 按题号排序，files = [(绝对路径, 包内相对路径)]"""
    kd = knowledge_dict.load()
    notes = []
    recs, errs = [], []
    pat = os.path.join(root, "算法", "**", "%sRound%d-*.md" % (CONT, n))
    import glob
    for p in sorted(glob.glob(pat, recursive=True)):
        r, e = index_sync.parse_record(p, root)
        if e:
            errs.append(e)
            continue
        if letter and r["letter"] != letter.upper():
            continue
        recs.append(r)
    if errs:
        return None, None, errs
    if not recs:
        return None, None, ["算法库里找不到 %sRound%d-*.md 的记录 md（先归档再导出）" % (CONT, n)]

    idx_path = os.path.join(root, "索引", "题解算法索引.md")
    cid, brows = None, []
    if os.path.exists(idx_path):
        itext = rd(idx_path)
        m = re.search(r"acm/contest/(\d+)/%s" % recs[0]["letter"], recs[0]["url"])
        cid = m.group(1) if m else None
        if cid:
            brows = back_rows_of(itext, cid)
    if not brows:
        notes.append("索引反查表里没摘到本场行（反查表还没补？）——"
                     "manifest 不带 back_rows，导入侧将按知识点自动生成简版反查表行")

    problems, files = [], []
    for r in recs:
        know_one = kd.final_knowledge(CONT, n, r["letter"], r["algo"])
        know = [x.strip() for x in re.split(r"[｜、]", know_one) if x.strip()]
        if not know:
            return None, None, ["%s 的知识点归一后为空（记录 md 的「数据结构与算法」写了什么？）" % r["letter"]]
        mine = [x for x in brows if r["letter"] in letters_in(x)]
        prob = {"letter": r["letter"], "title": r["name"], "difficulty": r["diff"],
                "scoring": "非签到", "knowledge": know, "folder": r["rel"], "url": r["url"]}
        if mine:
            prob["back_rows"] = mine
        problems.append(prob)
        # 算法记录
        # 包内相对路径一律反斜杠（与 toolutil.walk_files 同口径）：MSYS2 的 python
        # `os.sep` 是 "/"，直接用 os.path.join 会拼出正斜杠，下游按 `算法\` 前缀
        # 判断的地方（打包时的别名规范化、单题包筛选）就全部落空。
        files.append((r["path"], os.path.join("算法", r["rel"],
                                              os.path.basename(r["path"])).replace("/", BS)))
    problems.sort(key=lambda x: x["letter"])

    # 题解区（整场 md + 每题目录）
    rdir = os.path.join(root, "题解", CONT, "Round%d" % n)
    if not os.path.isdir(rdir):
        return None, None, ["找不到题解目录 %s" % rdir]
    for src, rel in toolutil.walk_files(rdir):
        files.append((src, os.path.join("题解", CONT, "Round%d" % n, rel).replace("/", BS)))
    md = os.path.join(rdir, "Round%d题解.md" % n)
    if not os.path.exists(md):
        return None, None, ["题解区缺 Round%d题解.md" % n]

    # 每题目录齐不齐（缺只提醒：单题包 / 只交 md 也算合法）
    for p in problems:
        hits = [f for f in files if (BS + p["letter"] + BS) in f[1] + BS]
        if not hits:
            notes.append("题 %s 在题解区没有自己的目录（只有整场 md 里的小节）" % p["letter"])
    return problems, files, notes


# ---------------------------------------------------------------- 打包
def write_manifest(path, problems, n, contributor):
    man = {
        "format": "acm-agent-workflow/solution-pack",
        "format_version": 1,
        "contest": CONT,
        "round": n,
        "contributor": contributor,
        "problems": problems,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write("\n")


def default_contributor():
    import subprocess
    try:
        p = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True,
                           timeout=10, cwd=toolutil.REPO_ROOT,
                           encoding="utf-8", errors="replace")
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    except OSError:
        pass
    return os.environ.get("USERNAME") or os.environ.get("USER") or ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="导出题解包（一场或一题）")
    ap.add_argument("target", help="Round163 或 Round163-G")
    ap.add_argument("-o", "--out", help="输出 .zip 或目录（缺省 = 当前目录 <比赛名>RoundN.zip）")
    ap.add_argument("--root", default=toolutil.DATA_ROOT, help="数据根（缺省取 config.json）")
    ap.add_argument("--contributor", default=None, help="署名（缺省取 git config user.name）")
    a = ap.parse_args(argv)

    m = RE_TARGET.match(a.target.strip())
    if not m:
        return fail("认不出目标「%s」——写法：`Round163`（整场）或 `Round163-G`（单题）" % a.target)
    n = int(m.group(1))
    letter = m.group(2).upper() if m.group(2) else None
    root = a.root.replace("/", os.sep)

    problems, files, notes = collect(root, n, letter)
    if problems is None:
        for x in notes:
            print("★ " + x)
        return 2
    contributor = a.contributor if a.contributor is not None else default_contributor()

    # 单题包：题解 md 是整场的，包里只有该题目录（其余题的文件不带走）
    if letter:
        keep = []
        for src, rel in files:
            if rel.startswith("算法" + BS) or rel.endswith("Round%d题解.md" % n) \
                    or (BS + letter + BS) in rel + BS:
                keep.append((src, rel))
        files = keep

    out = a.out or ("%sRound%d%s.zip" % (CONT, n, ("-" + letter) if letter else ""))
    out = os.path.abspath(out)
    is_zip = out.lower().endswith(".zip")
    if not is_zip and os.path.exists(out) and os.listdir(out):
        return fail("输出目录已存在且非空：%s（换个目录或先清空）" % out)

    import tempfile
    td = tempfile.mkdtemp(prefix="pack-")
    try:
        pdir = os.path.join(td, "pack")
        os.makedirs(pdir)
        write_manifest(os.path.join(pdir, "manifest.json"), problems, n, contributor)
        kd = knowledge_dict.load()
        n_alias = []
        for src, rel in files:
            dst = os.path.join(pdir, toolutil.to_os(rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            if rel.startswith("算法" + BS):
                # 包里只装标准名：别名（`状态压缩DP` ≡ `状压 DP`）在打包时就换掉，
                # 收包的人看到的记录与 manifest 口径一致，往返也能逐字节对上。
                new, used = kd.fix_aliases(rd(dst))
                if used:
                    with open(dst, "w", encoding="utf-8", newline="\n") as f:
                        f.write(new)
                    n_alias.extend("%s→%s" % x for x in used)
        if is_zip:
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for dp, dns, fns in os.walk(pdir):
                    for fn in sorted(fns):
                        p = os.path.join(dp, fn)
                        # zip 内部名一律正斜杠（两个 os.sep 都要替：MSYS2 下 os.sep 是 "/"）
                        z.write(p, os.path.relpath(p, pdir).replace(os.sep, "/").replace(BS, "/"))
        else:
            toolutil.copy_tree(pdir, out, files=toolutil.walk_files(pdir), overwrite=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    # 报告
    print("导出题解包：%s" % out)
    print("  场次：%s Round %d ｜ 题：%s ｜ 署名：%s"
          % (CONT, n, "、".join(p["letter"] for p in problems), contributor or "（空）"))
    print("  文件：%d 个（已过滤 _work\\ / __pycache__\\ / .exe / .png / .bak 等耗材）" % (len(files) + 1))
    if n_alias:
        print("  别名已规范化（包里只装标准名）：%s" % "、".join(n_alias))
    for p in problems:
        print("    %s %s ｜ %s ｜ %s ｜ 知识点 %s"
              % (p["letter"], p["title"], p["difficulty"], p["folder"] + BS,
                 "、".join(p["knowledge"])))
    for x in notes:
        print("  [提醒] " + x)
    if not is_zip:
        print("输出的不是 zip（%s）——要 zip 就把 -o 写成 xxx.zip" % out)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
