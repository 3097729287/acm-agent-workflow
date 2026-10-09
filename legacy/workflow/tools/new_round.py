# -*- coding: utf-8 -*-
r"""new_round.py —— 新场次起手骨架：一次把 RoundN 的目录与题解 md 空壳建好

    python new_round.py <比赛URL 或 Round号>

前提：先跑过 `fetch_problem.py`（本脚本读 `RoundN\_work\题面\<字母>.txt`
里的题号与题名；题面不在就先别起手）。

做的事（**全部幂等、不覆盖任何已存在的文件**）：

  1. `RoundN\<区间>\<字母>\`：每题一个目录（区间 = 首字母-尾字母，如 `B-G`），
     题号与题名取自题面 txt 的第 2 行 `# B. 题名`；
  2. `RoundN\RoundN题解.md`：骨架 = 头部三行引用（比赛主页从题面里的
     `# 来源：` 反推）+ `## 目录` 四列表（题号 / 题名取真值，考点写「待填」、
     难度写「CF ???」——占位符会被 check_solution 第 10 项报出来，逼着填完）
     + 每题「题意 / 思路 / 参考代码 / 易错点」四个必写小节；
  3. **不写「## 实测记录」**：还没跑过的东西不许先摆上去（见《工作流》）——
     自检会报「没有实测记录」，这是提醒，不是 bug。

打印每题 samples.py 的样例组数（从 `_work\samples.py` 数），方便接着验证。

用法示例：
    python new_round.py 164
    python new_round.py https://ac.nowcoder.com/acm/contest/140737
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_problem as fp          # 复用 ROOT / parse_cid / find_round


def resolve(arg):
    """命令行参数 → (Round 号字符串, cid 或 None)。

    URL（含 /contest/）→ cid → 去主页认场次；纯数字 ≤ 999 直接当 Round 号
    （牛客周赛现在才 160 多场，跟 6 位数的 cid 不会撞）；再大当 cid。
    """
    if re.search(r"/contest/", arg):
        cid = fp.parse_cid(arg)
        n = fp.find_round(cid)
        if not n:
            raise SystemExit("主页里没读到「牛客周赛 Round N」（cid=%s）。"
                             "直接给 Round 号也行：python new_round.py 164" % cid)
        return n, cid
    if arg.isdigit() and int(arg) <= 999:
        return arg, None
    cid = fp.parse_cid(arg)
    n = fp.find_round(cid)
    if not n:
        raise SystemExit("cid=%s 认不出场次号；直接给 Round 号也行。" % cid)
    return n, cid


def read_problems(txt_dir):
    """[(字母, 题名)]，按字母序；题面目录不存在或一个 txt 都没有 → []。"""
    out = []
    if not os.path.isdir(txt_dir):
        return out
    for fn in sorted(os.listdir(txt_dir)):
        m = re.fullmatch(r"([A-Z])\.txt", fn)
        if not m:
            continue
        L = m.group(1)
        title = None
        with open(os.path.join(txt_dir, fn), encoding="utf-8", errors="replace") as f:
            for ln in f.read().split("\n")[:6]:
                m2 = re.match(r"^# ([A-Z])\.\s*(.+?)\s*$", ln)
                if m2 and m2.group(1) == L:
                    title = m2.group(2)
                    break
        if title is None:
            title = "（题名没读到，看 _work\\题面\\%s.txt）" % L
        out.append((L, title.replace("|", "\\|")))
    return out


def homepage_from_txt(txt_dir, letters):
    """题面里的 `# 来源：https://…/contest/<cid>/<L>` 反推比赛主页 URL。"""
    for L in letters:
        p = os.path.join(txt_dir, "%s.txt" % L)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            m = re.search(r"^# 来源：\s*(\S+)", f.read(), re.M)
        if m:
            m2 = re.match(r"(https?://[^/]+/acm/contest/\d+)", m.group(1))
            if m2:
                return m2.group(1)
    return None


def sample_counts(work_dir):
    r"""从 _work\samples.py 数每题样例组数 → {字母: N}；没有就 None。"""
    p = os.path.join(work_dir, "samples.py")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        t = f.read()
    cnt = {}
    for m in re.finditer(r"\(\s*['\"]([A-Z]) ", t):
        cnt[m.group(1)] = cnt.get(m.group(1), 0) + 1
    return cnt


def build_md(n, probs, rng, home):
    lines = [
        "# 牛客周赛 Round %s 题解" % n,
        "",
        "> 比赛主页：<%s>" % (home or "（待补）"),
        "> 题面来源：牛客比赛题目页直接抓取，只摘关键条件、不复述完整题面；"
        "样例与极限都实跑核对过，文末有实测记录。",
        "> 语言标准：C++17 ｜ 标识符英文、注释中文 ｜ 每题一个目录 `%s\\<字母>\\`" % rng,
        "",
        "## 目录",
        "",
        "| 题号 | 题名 | 考点 | 难度 |",
        "|---|---|---|---|",
    ]
    lines += ["| %s | %s | 待填 | CF ??? |" % (L, t) for L, t in probs]
    lines += [""]
    for L, t in probs:
        lines += [
            "---", "",
            "## %s. %s" % (L, t), "",
            "### 题意", "",
            "### 思路", "",
            "### 参考代码", "",
            "### 易错点", "",
        ]
    return "\n".join(lines)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2

    n, cid = resolve(argv[0])
    rdir = os.path.join(fp.ROOT, "Round%s" % n)
    work_dir = os.path.join(rdir, "_work")
    txt_dir = os.path.join(work_dir, "题面")
    probs = read_problems(txt_dir)
    if not probs:
        raise SystemExit(
            "没找到题面：%s\n先跑 fetch_problem.py 抓题面，再回来跑本脚本。" % txt_dir)

    letters = [L for L, _ in probs]
    rng = "%s-%s" % (letters[0], letters[-1])
    home = ("https://ac.nowcoder.com/acm/contest/%s" % cid) if cid \
        else homepage_from_txt(txt_dir, letters)

    print("Round %s（题面 %d 题：%s，区间 %s）" % (n, len(probs), "".join(letters), rng))
    made, kept = [], []
    for L, _ in probs:
        d = os.path.join(rdir, rng, L)
        if os.path.isdir(d):
            kept.append(L)
        else:
            os.makedirs(d, exist_ok=True)
            made.append(L)
    print("  目录：新建 %s%s；已存在跳过 %s"
          % ("".join(made) if made else "0 个",
             "（%s）" % os.path.join("Round%s" % n, rng) if made else "",
             "".join(kept) if kept else "无"))

    md = os.path.join(rdir, "Round%s题解.md" % n)
    if os.path.exists(md):
        print("  题解 md：已存在，不动 → %s" % md)
    else:
        with open(md, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_md(n, probs, rng, home))
        print("  题解 md：已建骨架 → %s" % md)

    cnt = sample_counts(work_dir)
    if cnt is not None:
        print("  samples.py：%s" % " / ".join("%s %d 组" % (L, cnt.get(L, 0)) for L in letters))
    else:
        print("  samples.py：没有（抓题面时没提到样例？）")

    print()
    print("下一步：")
    print("  1. 写代码 → %s\\<字母>\\<小写字母>.cpp（对拍题再加 _brute.cpp）"
          % os.path.join("Round%s" % n, rng))
    print("  2. 验证   → python tools/verify.py --from-md \"%s\" --letter <字母> --rounds 500" % md)
    print("  3. 自检   → python tools/check_solution.py \"%s\"（骨架期会报目录表占位、"
          "没有实测记录——都是提醒）" % md)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
