#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-solution skill 自检：包装是否接对了。三关，全过退出码 0。

    python skills/check-solution/selftest.py

  1. SKILL.md 的 frontmatter 合法：`---` 起止、`name` 与目录名一致、`description` 非空、
     值里没有 YAML 裸标量不能有的东西（ASCII 冒号加空格 / 制表符）；
  2. 反例必须报红：`examples/反例题解.md` 退出码 1（闸门不是摆设，跟仓库同一个哲学）；
  3. 示例必须报绿：`demo/题解/牛客周赛/Round163/Round163题解.md` 退出码 0。

只用 `--no-compile`（快、且不要求本机有 g++）：第 5 项打「不适用」，不影响上面两个结论。
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate  # noqa: E402  （复用它的仓库根查找，避免两套寻址）

GATE = os.path.join(HERE, "gate.py")
BAD = os.path.join("examples", "反例题解.md")
GOOD = os.path.join("demo", "题解", "牛客周赛", "Round163", "Round163题解.md")

fails = []


def check_frontmatter():
    path = os.path.join(HERE, "SKILL.md")
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return "SKILL.md 开头不是合法的 frontmatter（必须第一行 `---`、有闭合 `---`）"
    fm = m.group(1)
    fields = {}
    for line in fm.split("\n"):
        k, sep, v = line.partition(":")
        if not sep:
            return "frontmatter 第 %r 行不是 `键: 值`" % line
        fields[k.strip()] = v.strip()
    if fields.get("name") != os.path.basename(HERE):
        return "frontmatter 的 name=%r 与目录名 %r 不一致" % (fields.get("name"), os.path.basename(HERE))
    if not fields.get("description"):
        return "description 空（技能列表里会显示不出来）"
    for k, v in fields.items():
        if "\t" in v or ": " in v:
            return "frontmatter 的 %s 值里有制表符或「ASCII 冒号 + 空格」——YAML 裸标量会解析失败" % k
    return None


def run_gate(rel):
    """跑闸门，返回 (退出码, 输出尾巴)。找不到文件时如实返回 -1。"""
    r = subprocess.run([sys.executable, GATE, rel, "--no-compile", "--quiet"],
                       cwd=gate.find_repo(None, [rel])[0] or ".",
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       encoding="utf-8", errors="replace")
    tail = "\n".join(r.stdout.strip().split("\n")[-2:])
    return r.returncode, tail


def main():
    err = check_frontmatter()
    print("[%s] 1. SKILL.md frontmatter" % ("问题" if err else "通过"))
    if err:
        fails.append("1. " + err)

    repo = gate.find_repo(None, [os.path.join(HERE, "README.md")])[0]
    if not repo:
        print("[问题] 2/3. 找不到仓库根，跑不了闸门（在仓库里跑，或加 ACM_AGENT_WORKFLOW_ROOT）")
        fails.append("2/3. 找不到仓库根")
    else:
        for n, (rel, want, label) in enumerate(
                [(BAD, 1, "反例必须报红"), (GOOD, 0, "示例必须报绿")], start=2):
            code, tail = run_gate(rel)
            ok = (code == want)
            print("[%s] %d. %s：%s → 退出码 %d（要 %d）%s"
                  % ("通过" if ok else "问题", n, label, rel, code, want,
                     "" if ok else "  尾巴：" + tail.replace("\n", " / ")))
            if not ok:
                fails.append("%d. %s 期望退出码 %d，实得 %d" % (n, rel, want, code))

    print("-" * 74)
    if fails:
        print("结论：★skill 自身有问题★（%d 项）" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("结论：全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
