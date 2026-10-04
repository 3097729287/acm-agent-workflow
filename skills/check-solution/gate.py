#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-solution 的启动器：找到仓库根，再把参数原样交给仓库里的 tools/check_solution.py。

为什么要这个文件：skill 会被复制到 `~/.claude/skills/` 或别的项目的 `.claude/skills/`，
离开仓库之后它自己不知道该去哪找 `tools/check_solution.py`。本文件把这层寻址一次做掉。

用法（下面三个「本文件」选项之外的参数，原样转给 check_solution.py）：

    python gate.py <题解.md> [更多.md ...] [--no-compile] [--no-record] [--quiet]
    python gate.py --repo <仓库根> <题解.md> ...
    python gate.py --list          # 只打印 18 项检查清单就退出
    python gate.py --help

仓库根按下面的顺序找，第一个命中就用（想确认找没找对，看第一行提示）：

    1. `--repo <路径>`
    2. 环境变量 `ACM_AGENT_WORKFLOW_ROOT`
    3. 从**当前目录**逐级向上找 `tools/check_solution.py`
    4. 从每个**待查 md 所在目录**逐级向上
    5. 从**本文件所在目录**逐级向上（skill 直接放在仓库里用时命中这条）

退出码 = check_solution.py 的退出码：0 = 全部通过 / 1 = 有问题 / 2 = 本文件自己出错。
"""

import os
import subprocess
import sys

MARK = os.path.join("tools", "check_solution.py")


def search_up(start):
    """从 start 逐级向上找含 tools/check_solution.py 的目录，找不到返回 None。"""
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, MARK)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def find_repo(explicit, files):
    """返回 (仓库根, 来源说明)；都没找到返回 (None, 找过的地方列表)。"""
    tried = []
    if explicit:
        hit = search_up(explicit)
        tried.append("--repo %s" % explicit)
        return (hit, "--repo") if hit else (None, tried)

    env = os.environ.get("ACM_AGENT_WORKFLOW_ROOT")
    if env:
        tried.append("环境变量 ACM_AGENT_WORKFLOW_ROOT=%s" % env)
        hit = search_up(env)
        if hit:
            return hit, "环境变量 ACM_AGENT_WORKFLOW_ROOT"

    tried.append("当前目录 %s 向上" % os.getcwd())
    hit = search_up(os.getcwd())
    if hit:
        return hit, "当前目录向上"

    for f in files:
        if f.startswith("-") or not os.path.exists(f):
            continue
        tried.append("%s 所在目录向上" % f)
        hit = search_up(os.path.dirname(os.path.abspath(f)) or ".")
        if hit:
            return hit, "题解 md 所在目录向上"

    tried.append("本文件所在目录向上")
    hit = search_up(os.path.dirname(os.path.abspath(__file__)))
    if hit:
        return hit, "本文件所在目录向上"

    return None, tried


def split_args(argv):
    """剥出本文件自己的 --repo，其余原样保留（顺序不变）。"""
    repo, rest, i = None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo":
            if i + 1 >= len(argv):
                sys.exit("[gate] --repo 后面要给一个路径")
            repo = argv[i + 1]
            i += 2
            continue
        if a.startswith("--repo="):
            repo = a.split("=", 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    return repo, rest


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    repo_arg, rest = split_args(argv)
    repo, why = find_repo(repo_arg, rest)

    if not repo:
        print("[gate] 没找到仓库根（要找的是含 tools/check_solution.py 的目录）。找过这些地方：",
              file=sys.stderr)
        for t in why:
            print("        - %s" % t, file=sys.stderr)
        print("""
[gate] 三种解法，挑一个：
        ① 在仓库里跑：cd <克隆下来的 acm-agent-workflow> 之后再执行本脚本；
        ② 指定仓库根：python gate.py --repo <仓库根> <题解.md> ...；
        ③ 设一次环境变量：ACM_AGENT_WORKFLOW_ROOT=<仓库根>（Windows: setx 后重开终端）。
        还没有仓库？git clone https://github.com/3097729287/acm-agent-workflow""",
              file=sys.stderr)
        return 2

    print("[gate] 仓库根：%s（%s）" % (repo, why), file=sys.stderr)
    cmd = [sys.executable, os.path.join(repo, MARK)] + rest
    try:
        return subprocess.call(cmd)
    except OSError as e:
        print("[gate] 起不了子进程：%s\n[gate] 试试换一个 Python：python gate.py ..." % e,
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
