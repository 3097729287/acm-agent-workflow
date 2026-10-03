# -*- coding: utf-8 -*-
r"""
verify —— C++ 题解的本地验证骨架
=================================

每题**只写"填什么"**（样例自动带、暴力、生成器、边界、极限），不重写驱动。
驱动本身归本模块管。

一、目录长这样（`<L>` = 题号字母；2026-09-30 起的 `RoundNNN\` 布局）：

    Round163\
      Round163题解.md                交付物，放场次根
      B-G\F\
        f.cpp          正解（就是要贴进 md 的那份）
        f_brute.cpp    暴力（可选；跟正解**必须是不同的实现范式**，见《验证协议》）
        verify_f.py    每题的填空文件（见下）
        run.cmd        双击跑（纯 ASCII + CRLF）
      _work\
        samples.py     官方样例常量表——fetch_problem.py 生成，别手敲；
                       verify.py 会自动往上找（见 find_samples）

二、verify_f.py 就写这么多：

    import os, sys
    _p = os.environ.get("AGENT_CP_TOOLS")
    if not _p:                       # 向上找到含 tools/toolutil.py 的目录
        _p = os.path.dirname(os.path.abspath(__file__))
        while not os.path.isfile(os.path.join(_p, "tools", "toolutil.py")):
            _q = os.path.dirname(_p)
            if _q == _p:
                raise SystemExit("没找到仓库 tools/：请设置 AGENT_CP_TOOLS 环境变量")
            _p = _q
        _p = os.path.join(_p, "tools")
    sys.path.insert(0, _p)
    from verify import main

    def gen(rng):
        # 生成一组随机小输入，返回字符串
        n = rng.randint(1, 7)
        return "%d\\n" % n + ...

    EDGES = [                      # 手工期望值的边界用例（期望值必须手算/推出来）
        ("n=1 最小规模", "1\\n5\\n", "5\\n"),
        ("k=0", "0\\n", "0\\n"),
    ]

    LIMITS = [                     # 极限计时用例
        ("极限 n=2e5 全同数", lambda: "200000\\n" + "1 " * 200000 + "\\n"),
    ]

    if __name__ == "__main__":
        main(solution="f.cpp", brute="f_brute.cpp", gen=gen,
             edges=EDGES, limits=LIMITS)

三、命令行也能单独用：

    python verify.py f.cpp                        # 只编 + 跑样例
    python verify.py f.cpp --brute f_brute.cpp    # 加随机对拍
    python verify.py --from-md "../牛客周赛Round163题解(B-G).md" --letter F
                                                  # 从题解 md 里抽代码来验

第三种是**交付前必须跑的那一次**：03 记过的坑是"工作目录里的版本"跟"贴进 md 的
版本"不是同一份，于是验过的代码和交付的代码可以不一样。--from-md 直接compile
md 里的代码块，堵掉这个缝。

四、几条写在这里就不用每次记的规矩（来自 06）：

  · 子进程一律带 timeout，不带的会静默挂死（实测卡满 300 秒才发现）
  · 输入统一 encode 成 bytes 再喂，喂 str 会让写线程抛异常、子进程空等 stdin
  · 每进一个阶段先打一行——"没输出"和"挂死"看起来一模一样
  · 暴力跟正解**必须是不同实现范式**（递归 vs 迭代、位掩码 vs 集合、匹配 vs 枚举），
    并且各自先对着手算过的期望值校一遍再上随机；同源互拍等于没拍
  · 实测记录表里的每个数字都来自实跑输出，不写"约/大概"
"""

import argparse
import glob
import importlib.util
import os
import random
import re
import subprocess
import sys
import time

import toolutil                     # 同目录：围栏语义的唯一实现

HERE = os.path.dirname(os.path.abspath(__file__))
GXX_FLAGS = ["-O2", "-std=c++17", "-Wall", "-Wextra"]


# ------------------------------------------------------------------ 工具
def _say(*a):
    print(*a)
    sys.stdout.flush()


def find_samples(workdir, letter=None):
    r"""自动找 samples.py，省掉每题手写路径。

    查找顺序（先命中先用）：
      1. `<workdir>/samples.py`             —— 手工放同目录
      2. `<workdir>/_work/...`              —— `--from-md` 时 workdir 就是场次目录
      3. `<workdir>/../_work/...`           —— 旧布局：`题解\nk163F\` 的兄弟 `_work`
      4. `<workdir>/../../_work/...`        —— 新布局：`RoundN\A-F\A\` 的祖父 `RoundN\_work`
      5. 上面都挑不出就取最新的那份

    每个 `_work` 先看**直接摊在里面的** `samples.py`（2026-09-30 起的
    `RoundN\_work\samples.py`），再看子目录里的 `_work\*\samples.py`
    （旧布局 `_work\nk<场次>\samples.py`）。

    子目录那一档还要认字母：`_work` 默认按 cid 命名（`nk140737`，题单接口不返回
    比赛名，推不出"Round 163"），跟按场次命名的子目录对不上，于是
    samples.py 里每条样例的名字形如 `"F 样例1"`，按这个字母认领。
    选中的是哪一份会打印出来——挑错了当场看得见。
    """
    p = os.path.join(workdir, "samples.py")
    if os.path.exists(p):
        return p
    # `_work` 可能在**子目录**（`--from-md` 时 workdir 就是场次目录）、
    # **兄弟目录**（旧布局 `题解\nk163F\`）或**祖父目录**（新布局 `RoundN\A-F\A\`）。
    # 三处都要找——少找一处就会有场景永远报「没找到 samples.py」。
    wd = os.path.normpath(workdir)
    for work in (os.path.join(wd, "_work"),
                 os.path.join(os.path.dirname(wd), "_work"),
                 os.path.join(os.path.dirname(os.path.dirname(wd)), "_work")):
        if not os.path.isdir(work):
            continue
        m = re.match(r"nk(\d+)", os.path.basename(wd))
        if m:
            p = os.path.join(work, "nk%s" % m.group(1), "samples.py")
            if os.path.exists(p):
                return p
        cand = glob.glob(os.path.join(work, "samples.py"))
        cand += glob.glob(os.path.join(work, "*", "samples.py"))
        if letter and len(cand) > 1:
            hit = []
            for c in cand:
                try:
                    txt = open(c, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if re.search(r"[\"']%s[ 　]" % letter.upper(), txt):
                    hit.append(c)
            if hit:
                cand = hit
        if cand:
            return max(cand, key=os.path.getmtime)
    return os.path.join(workdir, "samples.py")     # 不存在，load_samples 会返回 []


def load_samples(path):
    """从 samples.py 读 SAMPLES（fetch_problem.py 生成的）。"""
    if not os.path.exists(path):
        return []
    spec = importlib.util.spec_from_file_location("_samples", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = []
    for item in getattr(mod, "SAMPLES", []):
        if len(item) == 3:
            out.append(tuple(item))
        elif len(item) == 2:
            out.append(("样例", item[0], item[1]))
    return out


def compile_cpp(src, exe=None):
    """编译一份 .cpp，返回 exe 路径。没装 g++ 或编译不过都抛 RuntimeError（由 main 记「未验证」）。"""
    src = os.path.abspath(src)
    exe = exe or (os.path.splitext(src)[0] + ".exe")
    cmd = ["g++"] + GXX_FLAGS + ["-o", exe, src]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except OSError:
        raise RuntimeError(
            "PATH 里找不到 g++ —— 装一个（Windows 走 MSYS2 的 ucrt64\\bin 加进 PATH，"
            "见知识库《环境准备》），或如实记「未验证」，不许假装跑过。")
    if r.returncode != 0:
        raise RuntimeError("编译失败：%s\n%s\n%s" % (src, " ".join(cmd), r.stderr))
    warn = (r.stderr or "").strip()
    return exe, warn


def run_exe(exe, inp, timeout=30):
    """跑一个程序喂一段输入。输入一律 encode；timeout 必须给。"""
    if isinstance(inp, str):
        inp = inp.encode()
    r = subprocess.run([exe], input=inp, capture_output=True, timeout=timeout)
    return (r.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
            r.returncode,
            r.stderr.decode("utf-8", "replace"))


def norm(s):
    """比对输出时的归一化：去掉行尾空白与末尾多余空行，中间空行保留。"""
    lines = [ln.rstrip() for ln in s.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def extract_code_from_md(md_path, letter):
    """从题解 md 里抽出某题的最后一个 ```cpp 代码块。

    只认「## <字母>. 」开头的二级标题划分的区段，避免抽错题的代码。
    """
    text = open(md_path, encoding="utf-8").read()
    # 找出所有 "## X. xxx" 的位置
    heads = [(m.start(), m.group(1)) for m in
             re.finditer(r"^##\s*([A-Z])[\.、\s]", text, re.M)]
    if not heads:
        raise SystemExit("md 里没找到「## X. 」形式的题目标题。")
    start = None
    for i, (pos, ch) in enumerate(heads):
        if ch == letter.upper():
            start = pos
            end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
            break
    if start is None:
        raise SystemExit("md 里没有 %s 题（找到的是 %s）。"
                         % (letter, "".join(c for _, c in heads)))
    seg = text[start:end]
    blocks = md_cpp_blocks(seg)
    if not blocks:
        raise SystemExit("%s 题那一段里没有 cpp 代码块。" % letter)
    return blocks[-1]


CPP_LANGS = ("cpp", "c++", "cc", "cxx")


def md_cpp_blocks(text):
    r"""按**行级围栏**抽 cpp 代码块，返回块内容（不含围栏行）。

    逐行读围栏（开围栏认语言、闭围栏收块），而不是 `re.findall(r"```cpp(.*?)```")`：
    题解里除了 cpp 块，还有裸 ``` 围起来的 ASCII 示意图和别的语言的块，
    逐行读才说得清"这个 ``` 到底是开还是闭、开的是哪种"。

    实测对照（2026-09-30）：两种写法在现有 6 场题解的 **38 个题目段落上结果完全一致**
    （含 Round163 E/F 那种夹着示意图的段落），所以这不是在修一个已经踩到的 bug，
    是把"围栏语义"写明确、免得以后遇到嵌套围栏时静默抽错——抽错的那份代码照样能编译、
    照样跑样例，**错是不出声的**。

    2026-10-02：实现统一到 `toolutil.fence_blocks`（全库围栏语义的唯一实现）；
    切换前后对 9 场题解抽块结果逐字一致。
    """
    return ["\n".join(b[2]) for b in toolutil.fence_blocks(text, languages=CPP_LANGS)]


# ------------------------------------------------------------------ 驱动
class Runner:
    def __init__(self, solution, brute=None, samples=None, md=None, letter=None,
                 rounds=0, seed=12345, workdir=None):
        self.workdir = os.path.abspath(workdir or os.path.dirname(os.path.abspath(
            md or solution)))
        self.md = md
        self.letter = letter
        self.rounds = rounds
        self.seed = seed
        self.samples = samples or []
        self.brute = brute
        self.results = {}          # 阶段 -> (是否通过, 一句话)
        # 「可粘贴文字」用的结构化实跑数字（跑过的档才有值）
        self.res_samples = None    # (组数, 是否全过)
        self.res_edges = None      # (条数, 是否全过)
        self.res_cross = None      # (实跑组数, 设计组数, 不一致组数)
        self.res_limits = None     # [(名字, 秒数；None = 超时), ...]

        if md:
            _say("[0/5] 从题解 md 里抽代码：%s" % os.path.basename(md))
            code = extract_code_from_md(md, letter)
            # 抽出来的临时 cpp/exe 丢进 _work，别污染题解目录的根
            scratch = os.path.join(self.workdir, "_work", "from_md")
            os.makedirs(scratch, exist_ok=True)
            self.src = os.path.join(scratch, "_from_md_%s.cpp" % letter.upper())
            with open(self.src, "w", encoding="utf-8", newline="\n") as f:
                f.write(code)
            _say("      抽出 %d 行 -> %s（这是**贴进 md 的那一份**，就验它）"
                 % (code.count("\n") + 1, os.path.relpath(self.src, self.workdir)))
        else:
            self.src = os.path.abspath(solution)

        self.exe = os.path.splitext(self.src)[0] + ".exe"
        self.bexe = None

    # -- 1 编译
    def step_compile(self):
        _say("[1/5] 编译正解：%s" % os.path.basename(self.src))
        self.exe, warn = compile_cpp(self.src, self.exe)
        _say("      通过。" + ("警告：\n" + warn if warn else "（无警告）"))
        if self.brute:
            bp = os.path.abspath(self.brute)
            _say("      编译暴力：%s" % os.path.basename(bp))
            self.bexe, bwarn = compile_cpp(bp)
            _say("      通过。" + ("警告：\n" + bwarn if bwarn else "（无警告）"))
        self.results["编译"] = ("pass", "通过" + ("（有警告）" if warn else "（无警告）"))

    # -- 2 官方样例
    def step_samples(self):
        if not self.samples:
            _say("[2/5] 官方样例：没找到 samples.py，跳过（先跑 fetch_problem.py 生成）")
            self.results["官方样例"] = ("skip", "没有样例常量表")
            return
        _say("[2/5] 官方样例（共 %d 组）..." % len(self.samples))
        ok = True
        for name, inp, expect in self.samples:
            got, rc, err = run_exe(self.exe, inp)
            same = norm(got) == norm(expect)
            ok = ok and same
            _say("      %-16s %s" % (name, "通过" if same else "★不通过★"))
            if not same:
                _say("        输入：%r" % inp)
                _say("        期望：%r" % norm(expect))
                _say("        实际：%r%s" % (norm(got),
                                             "  退出码=%d" % rc if rc else ""))
                if err:
                    _say("        stderr：%s" % err[:300])
        self.results["官方样例"] = ("pass" if ok else "fail",
                                    "%d 组全过" % len(self.samples) if ok else "有失败")
        self.res_samples = (len(self.samples), ok)

    # -- 3 边界
    def step_edges(self, edges):
        if not edges:
            _say("[3/5] 边界用例：没填，跳过")
            self.results["边界用例"] = ("skip", "没填边界用例")
            return
        _say("[3/5] 边界用例（期望值手工推出，共 %d 条）..." % len(edges))
        ok = True
        for name, inp, expect in edges:
            got, rc, err = run_exe(self.exe, inp)
            same = norm(got) == norm(expect)
            ok = ok and same
            _say("      %-28s %s" % (name, "通过" if same else "★不通过★"))
            if not same:
                _say("        输入：%r" % inp)
                _say("        期望：%r" % norm(expect))
                _say("        实际：%r%s" % (norm(got),
                                             "  退出码=%d" % rc if rc else ""))
                if err:
                    _say("        stderr：%s" % err[:300])
        self.results["边界用例"] = ("pass" if ok else "fail",
                                  "%d 条全过" % len(edges) if ok else "有失败")
        self.res_edges = (len(edges), ok)

    # -- 4 对拍
    def step_cross(self, gen):
        if not (self.brute and gen and self.rounds):
            _say("[4/5] 随机对拍：跳过（%s）"
                 % ("没给暴力" if not self.brute else
                    "没给生成器" if not gen else "rounds=0"))
            self.results["随机对拍"] = ("skip", "跳过")
            return
        _say("[4/5] 随机对拍（同一语言、不同实现范式，共 %d 组，seed=%d）..."
             % (self.rounds, self.seed))
        rng = random.Random(self.seed)
        bad = 0
        ran = 0                    # **实际跑过的组数**，不是设计的总组数。
                                   # 03 记的坑：把设计组数当已跑组数写进记录，
                                   # 就是一份看上去很漂亮的假记录。这里分开记。
        for it in range(self.rounds):
            inp = gen(rng)
            if not isinstance(inp, str):
                inp = str(inp)
            a, rca, _ = run_exe(self.exe, inp, timeout=30)
            b, rcb, _ = run_exe(self.bexe, inp, timeout=30)
            ran += 1
            if norm(a) != norm(b):
                bad += 1
                _say("      ★第 %d 组不一致★" % (it + 1))
                _say("        输入：%r" % inp[:400])
                _say("        正解：%r" % norm(a)[:400])
                _say("        暴力：%r" % norm(b)[:400])
                if bad >= 3:
                    _say("        连续 3 组不一致，提前停。")
                    break
            if (it + 1) % 200 == 0:
                _say("        已跑 %d 组 ..." % (it + 1))
        _say("      实际跑了 %d 组（设计 %d 组），不一致 %d 组。"
             % (ran, self.rounds, bad))
        if ran != self.rounds:
            _say("      ★提前中断：记录里写「%d 组」不要写「%d 组」★"
                 % (ran, self.rounds))
        self.results["随机对拍"] = ("pass" if (bad == 0 and ran == self.rounds) else "fail",
                                    "%d 组全一致" % ran if bad == 0 else
                                    "%d/%d 组不一致" % (bad, ran))
        self.res_cross = (ran, self.rounds, bad)

    # -- 5 极限
    def step_limits(self, limits):
        if not limits:
            _say("[5/5] 极限计时：没填，跳过")
            self.results["极限计时"] = ("skip", "没填极限用例")
            return
        _say("[5/5] 极限计时（%d 个用例）..." % len(limits))
        ok = True
        timings = []
        for name, maker in limits:
            inp = maker() if callable(maker) else maker
            t0 = time.time()
            try:
                out, rc, err = run_exe(self.exe, inp, timeout=120)
            except subprocess.TimeoutExpired:
                _say("      %s：★超过 120 秒还没跑完★" % name)
                timings.append((name, None))       # None = 超时，粘贴文字里照写
                ok = False
                continue
            dt = time.time() - t0
            timings.append((name, dt))
            _say("      %-34s %.3f s，输出 %d 行"
                 % (name, dt, len(out.strip().split("\n")) if out.strip() else 0))
            if rc != 0:
                _say("        ★退出码 %d，stderr：%s" % (rc, err[:300]))
                ok = False
        self.results["极限计时"] = ("pass" if ok else "fail",
                                    "、".join("%s %.3f s" % (n, d) if d is not None
                                              else "%s 超时" % n for n, d in timings)
                                    if timings else "没跑成")
        self.res_limits = timings

    # -- 可直接贴进 md 的实测记录（本题，≤6 行纯文字）
    def paste_lines(self):
        """check_solution 第 6 项口径：纯文字、不用表格 / 列表、数字逐字来自实跑"""
        out = []
        st, what = self.results.get("编译", ("skip", ""))
        if st == "pass":
            out.append("编译：通过（-O2 -std=c++17 -Wall -Wextra，%s）。"
                       % ("无警告" if "无警告" in what else "有警告"))
        elif st == "skip":
            out.append("编译：未验证。")
        else:
            out.append("编译：失败。")
        st = self.results.get("官方样例", ("skip", ""))[0]
        if st == "pass":
            out.append("官方样例：%d 组全过。" % len(self.samples))
        elif st == "skip":
            out.append("官方样例：未验证（没有 samples.py）。")
        else:
            out.append("官方样例：有失败（共 %d 组）。" % len(self.samples))
        st = self.results.get("边界用例", ("skip", ""))[0]
        if st == "pass":
            out.append("边界用例：%d 条全过。" % self.res_edges[0])
        elif st == "skip":
            out.append("边界用例：未验证（没填）。")
        else:
            out.append("边界用例：有失败（共 %d 条）。" % self.res_edges[0])
        if self.res_cross is None:
            out.append("随机对拍：未验证（没给暴力 / 生成器，或 rounds=0）。")
        else:
            ran, rounds, bad = self.res_cross
            if bad == 0 and ran == rounds:
                out.append("随机对拍：实跑 %d 组全一致（seed=%d）。" % (ran, self.seed))
            elif ran < rounds:
                out.append("随机对拍：实跑 %d 组（设计 %d 组）中 %d 组不一致（seed=%d）。"
                           % (ran, rounds, bad, self.seed))
            else:
                out.append("随机对拍：实跑 %d 组中 %d 组不一致（seed=%d）。"
                           % (ran, bad, self.seed))
        if self.res_limits is None:
            out.append("极限计时：未验证（没填用例）。")
        else:
            parts = []
            for n, d in self.res_limits:
                nn = re.sub(r"^极限[：:]\s*", "", n) or n   # 用例名常自带「极限：」前缀
                parts.append("%s %.3f s" % (nn, d) if d is not None
                             else "%s 超时（> 120 s）" % nn)
            out.append("极限计时：%s。" % "、".join(parts))
        return out

    # -- 汇总
    def report(self, title="实测记录"):
        LABEL = {"pass": "通过", "skip": "未验证", "fail": "失败"}
        _say()
        _say("=" * 62)
        _say("汇总")
        _say("=" * 62)
        for k in ("编译", "官方样例", "边界用例", "随机对拍", "极限计时"):
            if k not in self.results:
                continue
            st, what = self.results[k]
            _say("  %-8s %-6s %s" % (k, LABEL[st], what))
        _say()
        _say("  注：未验证 ≠ 失败。没跑的档就如实写「未验证」，"
             "不许拿别场的记录来凑（见《工作流》）。")
        _say()
        _say("--- 可直接贴进 md 的%s（本题，≤6 行纯文字）---" % title)
        for l in self.paste_lines():
            _say(l)
        _say("  注：整场记录把各题这几行合并改写；没跑的档如实写「未验证」（见《工作流》）。")
        graded = [v[0] for k, v in self.results.items()
                  if k in ("官方样例", "边界用例", "随机对拍", "极限计时")]
        return all(s == "pass" for s in graded)


def main(solution=None, brute=None, gen=None, edges=None, limits=None,
         md=None, letter=None, rounds=0, seed=12345, samples_file=None,
         workdir=None, title="实测记录"):
    if md:
        base = os.path.dirname(os.path.abspath(md))
        solution = solution or os.path.join(base, "_placeholder.cpp")
        workdir = workdir or base
    elif solution:
        workdir = workdir or os.path.dirname(os.path.abspath(solution))
    workdir = workdir or os.getcwd()

    if samples_file is None:
        # 字母从 --letter 或正解文件名取（`f.cpp` / `f_brute.cpp` -> F）
        lt = letter
        if not lt and solution:
            ch = os.path.basename(solution)[:1]
            lt = ch if ch.isalpha() else None
        samples_file = find_samples(workdir, lt)
    else:
        lt = letter
    samples = load_samples(samples_file)
    # fetch_problem.py 生成的是**整场**的样例表（14 组），而一次只验一道题。
    # 不过滤的话 f.cpp 会去跑 B/C/D/E/G 的样例，全红——看着像代码坏了。
    kept = 0
    if lt:
        sel = [s for s in samples if s[0].split()[0].strip().upper() == lt.upper()]
        if sel:
            kept, samples = len(samples) - len(sel), sel
    _say("样例常量表：%s（%d 组%s）"
         % (samples_file, len(samples),
            "，另有 %d 组别题的样例已滤掉" % kept if kept else
            "" if samples else "，没找到——先跑 fetch_problem.py"))
    if brute and not os.path.isabs(brute):
        brute = os.path.join(workdir, brute)
    if solution and not os.path.isabs(solution):
        solution = os.path.join(workdir, solution)

    r = Runner(solution=solution or os.path.join(workdir, "x.cpp"), brute=brute,
               samples=samples, md=md, letter=letter, rounds=rounds, seed=seed,
               workdir=workdir)
    _say()
    _say("正解源码：%s" % r.src)
    _say("工作目录：%s" % workdir)
    _say()
    try:
        r.step_compile()
        r.step_samples()
        r.step_edges(edges)
        r.step_cross(gen)
        r.step_limits(limits)
    except subprocess.TimeoutExpired as e:
        _say("★超时★ 卡在：%s" % e)
        _say("  超时不等于「结果为零」——先确认观测对象对不对（06 的探针自证）。")
    except RuntimeError as e:
        # 多半是「没装 g++」或「编译没过」——后者也不该甩 traceback，而是如实记「未验证」
        _say("★%s" % e)
        _say("  后面几档全部记「未验证」——这档没过就不许有结论。")
        for k in ("编译", "官方样例", "边界用例", "随机对拍", "极限计时"):
            r.results.setdefault(k, ("skip", "未验证（编译没过）"))
    return r.report(title)


def cli(argv=None):
    ap = argparse.ArgumentParser(description="C++ 题解本地验证骨架")
    ap.add_argument("solution", nargs="?", help="正解 .cpp")
    ap.add_argument("--brute", help="暴力 .cpp（跟正解不同实现范式）")
    ap.add_argument("--from-md", dest="md", help="从题解 md 里抽代码来验（交付前那一次）")
    ap.add_argument("--letter", help="配合 --from-md，指定题号字母")
    ap.add_argument("--rounds", type=int, default=0, help="随机对拍组数")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--samples", help="samples.py 路径（默认工作目录下）")
    ap.add_argument("--title", default="实测记录")
    a = ap.parse_args(argv)
    if a.md and not a.letter:
        raise SystemExit("--from-md 要配 --letter F 这样指定题号。")
    if not (a.solution or a.md):
        ap.print_help()
        return 2
    ok = main(solution=a.solution, md=a.md, letter=a.letter, rounds=a.rounds,
              seed=a.seed, samples_file=a.samples, title=a.title,
              brute=a.brute or None)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(cli(sys.argv[1:]))
