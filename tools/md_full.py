# -*- coding: utf-8 -*-
r"""交付前那一次「完整复验」：从题解 md 里抽代码，连边界 / 对拍 / 极限一起跑。

为什么需要它
------------
`verify.py --from-md` 只做「编译 + 官方样例」两档 —— 它拿不到 `EDGES` / `LIMITS` / `gen`，
那三档一律报「没填」。可交付前真正想确认的是**md 里贴着的那一份代码**在**全部四档**上都对，
不只是样例对。历史上「工作目录里那版对、贴进 md 的那版错」是真发生过的（见《工作流》）。

原来这个活是靠每场手写一个驱动脚本（`Round124\_work\md_driver.py`）干的，
但驱动脚本放在 `_work\` 里，2026-09-30 清理时被删了 —— 于是把它固化成工具。

做法
----
你已经在 `<数据根>\题解\牛客周赛\RoundN\<区间>\<字母>\verify_<字母>.py` 里写好了
`gen` / `EDGES` / `LIMITS`（03 的第 3 步），本工具**直接 import 那一份**把它们取出来，
再连同 `md=` 一起转交给 `verify.main()`。所以两道闸验的是同一套用例，
唯一的差别是代码来源：一份来自磁盘、一份来自 md。

用法
----
    python md_full.py <题解.md> <字母> [--rounds N] [--seed N] [--force]

例：
    python md_full.py "<数据根>/题解/牛客周赛/Round124/Round124题解.md" D

`<题解.md>` 的同级目录里会去找 `*\<字母>\verify_<字母>.py`（`A-F\D\verify_d.py` 这种），
找不到就用 `--dir` 手动指定；再找不到会**明确报错**，不会退化成「只跑样例」还假装跑全了。

**默认先比对**（2026-10-02 起）：md 里抽出的代码与工作目录 `verify_<字母>.py` 里
`solution=` 指向的那份**逐字比对**（归一化只动行尾与首尾空行）——一致就跳过四档重跑
（那一份已在第 4 步验过），不一致则打印差异并照常全跑（验的是 md 里那份）。
改了 cpp 还没重验、或想要新的实跑输出，加 `--force` 强制实跑。
"""
import argparse
import difflib
import importlib.util
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify import main as vmain, extract_code_from_md  # noqa: E402


def _norm(s):
    """比对前的归一化：行尾统一成 LF、剥掉首尾空行（空行的有无不携带信息）。"""
    return s.replace("\r\n", "\n").strip("\n")


def find_probe(md_path, letter, hint=None):
    """找 `verify_<字母>.py`：先看 --dir，再在 md 同级目录往下找一层 `*\\<字母>\\`。"""
    letter = letter.upper()
    names = ["verify_%s.py" % letter.lower(), "verify_%s.py" % letter,
             "verify_%s.py" % letter.lower()[0], "verify.py"]

    def has_verify(d):
        return any(os.path.isfile(os.path.join(d, n)) for n in names)

    if hint:
        d = os.path.abspath(hint)
        if has_verify(d):
            return d
        raise SystemExit("--dir 里没有 verify_<字母>.py：%s" % d)

    root = os.path.dirname(os.path.abspath(md_path))
    # 1) 直接同级
    if has_verify(root):
        return root
    # 2) 下一层：先按「区间层\<字母>」，退化到「任意\<字母>」
    layers = [d for d in sorted(os.listdir(root))
              if os.path.isdir(os.path.join(root, d))]
    for lay in layers:
        d = os.path.join(root, lay, letter)
        if os.path.isdir(d) and has_verify(d):
            return d
    for lay in layers:
        base = os.path.join(root, lay)
        for sub in sorted(os.listdir(base)):
            d = os.path.join(base, sub)
            if os.path.isdir(d) and sub.upper() == letter and has_verify(d):
                return d
    raise SystemExit(
        "★没找到 %s 题的 verify 脚本★\n"
        "  在 %s 下找了 `*\\%s\\verify_%s.py`，没有。\n"
        "  先按 03 的第 3 步给这题补一份（只填 gen / EDGES / LIMITS），\n"
        "  或用 --dir 指定目录。" % (letter, root, letter, letter.lower()))


def load_probe(dirpath, letter):
    """取出 `verify_<字母>.py` 作者写的那一份参数，原样交给我们自己调。

    **不能只 getattr 读模块全局**：`brute` / `rounds` 这些通常写在
    `if __name__ == "__main__":` 里的 `main(...)` 实参中，不是模块级变量，
    import 进来根本读不到（第一版就是这么漏掉 `f_brute.cpp` 的，跑出来
    「随机对拍：跳过（没给暴力）」——**错是不出声的**，看着像这题本来就不对拍）。

    所以改成：先把 `verify.main` 换成一个「只记录实参、不执行」的桩，
    再以 `__name__ == "__main__"` 把脚本 exec 一遍 —— 于是它自己的那行
    `main(solution=..., brute=..., ...)` 会被桩接住，我们拿到**逐字原样的**参数表。
    """
    letter = letter.upper()
    import verify as vmod

    path = None
    for n in ("verify_%s.py" % letter.lower(), "verify_%s.py" % letter, "verify.py"):
        p = os.path.join(dirpath, n)
        if os.path.isfile(p):
            path = p
            break
    if path is None:
        raise SystemExit("不可能：load_probe 收到没有 verify 脚本的目录 %s" % dirpath)

    caught = {}
    real_main = vmod.main

    def _stub(**kw):
        caught.update(kw)
        return True

    vmod.main = _stub
    ns = {"__name__": "__main__", "__file__": path,
          "__builtins__": __builtins__}
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        exec(compile(src, path, "exec"), ns)
    finally:
        vmod.main = real_main

    # 桩没被调到（脚本没写 __main__ 块）就退回读模块全局
    if not caught:
        for k in ("gen", "EDGES", "LIMITS", "rounds", "seed", "brute", "solution"):
            if k in ns:
                caught[k] = ns[k]

    return path, caught


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="交付前完整复验：md 里的代码 × 边界/对拍/极限")
    ap.add_argument("md", help="题解 md 路径")
    ap.add_argument("letter", help="题号字母，如 D")
    ap.add_argument("--dir", dest="hint", help="指定该题的 verify_<字母>.py 所在目录")
    ap.add_argument("--rounds", type=int, default=None,
                    help="随机对拍组数（默认取 verify 脚本里写的 rounds）")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--force", action="store_true",
                    help="即使 md 里的代码与工作目录逐字一致，也强制四档全跑")
    a = ap.parse_args(argv)

    md = os.path.abspath(a.md)
    if not os.path.isfile(md):
        raise SystemExit("md 不存在：%s" % md)
    L = a.letter.strip().upper()
    if not re.fullmatch(r"[A-Z]", L):
        raise SystemExit("字母要写成单个 A~Z，收到：%r" % a.letter)

    d = find_probe(md, L, a.hint)
    p, cfg = load_probe(d, L)
    gen = cfg.get("gen")
    edges = cfg.get("edges")
    limits = cfg.get("limits")
    rounds = a.rounds if a.rounds is not None else (cfg.get("rounds") or 0)
    seed = a.seed if a.seed is not None else (cfg.get("seed") or 12345)

    # brute 在 verify_<字母>.py 里写的是相对它自己目录的文件名；
    # 但 main(md=...) 会把相对路径拼到 **md 所在目录**上，所以这里先转成绝对路径。
    brute = cfg.get("brute")
    if brute and not os.path.isabs(brute):
        brute = os.path.join(d, brute)

    # ── 先比对：「md 里那份」vs「工作目录那份」（2026-10-02 加）──────────────
    # 第 6 步要堵的缝就是「贴进 md 的和验过的不是同一份」。两份逐字一致时，
    # 工作目录那份已在第 4 步过完四档，这里直接放行；不一致才需要实跑
    # （验的正是 md 里那份）。--force 强制实跑。
    solution = cfg.get("solution") or ("%s.cpp" % L.lower())
    sol_path = os.path.join(d, solution)
    md_code = wk_code = None
    if not a.force and os.path.isfile(sol_path):
        try:
            md_code = _norm(extract_code_from_md(md, L))
            with open(sol_path, encoding="utf-8") as f:
                wk_code = _norm(f.read())
        except SystemExit:
            md_code = wk_code = None    # md 里抽不出这题：交给下面的 vmain 报错

    if md_code is not None and wk_code is not None:
        if md_code == wk_code:
            print("=" * 74)
            print("先比对：md 里的代码 vs 工作目录那份（2026-10-02 起默认先比）")
            print("  工作目录：%s" % sol_path)
            print("  结果    ：逐字一致（%d 行；归一化只动行尾与首尾空行）"
                  % (md_code.count("\n") + 1))
            print("  判断    ：这一份已在第 4 步（verify.py）过完样例/边界/对拍/极限四档，")
            print("            跳过重跑。结论依赖「第 4 步验的就是这一份」——")
            print("            若第 4 步之后改过 cpp，用 --force 强制实跑。")
            print("=" * 74)
            return 0
        print("=" * 74)
        print("★ md 里的代码与工作目录那份**不一致**——照常四档全跑（验的就是 md 里那份）★")
        diff = list(difflib.unified_diff(
            wk_code.split("\n"), md_code.split("\n"),
            fromfile="工作目录 %s" % os.path.basename(sol_path),
            tofile="md 里的代码", lineterm=""))
        for ln in diff[:40]:
            print("  " + ln)
        if len(diff) > 40:
            print("  ……（共 %d 行差异，只显示前 40 行）" % len(diff))
        print("=" * 74)

    print("=" * 74)
    print("完整复验（--from-md 的加料版）")
    print("  题解 md ：%s" % md)
    print("  题号    ：%s" % L)
    print("  用例来自：%s" % p)
    print("  取到    ：gen=%s  EDGES=%s  LIMITS=%s  rounds=%s  brute=%s"
          % ("有" if gen else "★无", len(edges) if edges else "★无",
             len(limits) if limits else "★无", rounds or "★无",
             os.path.basename(brute) if brute else "★无"))
    if not (edges or gen or limits):
        print("  ★警告：这份 verify 脚本里三档用例一个都没有，"
              "跑出来和 --from-md 没区别，别当成「完整复验」★")
    print("=" * 74)

    # 样例表在「题目录」或「md 同级」里也认一份（每题一份 samples.py 的布局；
    # 老的整场表在 `RoundN\_work\`，verify 自己会兜底找，这里不干预）
    samples_file = None
    for cand in (os.path.join(d, "samples.py"),
                 os.path.join(os.path.dirname(md), "samples.py")):
        if os.path.isfile(cand):
            samples_file = cand
            break

    ok = vmain(md=md, letter=L, gen=gen, edges=edges, limits=limits,
               rounds=rounds, seed=seed, brute=brute, samples_file=samples_file)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
