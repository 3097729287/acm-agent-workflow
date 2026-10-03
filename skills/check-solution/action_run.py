#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Action 入口：把 inputs 里的路径 / glob 展开成题解 md 列表，再交给 gate.py。

它是 `action.yml` 那一步真正跑的东西，也可以在本地直接跑（拿来预演 CI）：

    GATE_ROOT=<本仓库根> GATE_PATHS="demo/**/*题解*.md" python action_run.py

环境变量（action.yml 塞进来的）：

    GATE_ROOT   本 action 的仓库根（= `github.action_path`，里面有 `tools/check_solution.py`）
    GATE_PATHS  要检查的路径 / glob，**空格分隔可给多个**；目录会递归收 `*.md`
    GATE_ARGS   原样转给 `check_solution.py` 的额外参数（如 `--no-compile`、`--no-record`）

退出码：0 = 全部通过；1 = 有文件没过闸；2 = 本文件自己出错（没给路径 / 没匹配到 / 找不到仓库根）。
"""

import glob
import os
import shlex
import subprocess
import sys

GATE = os.path.join("skills", "check-solution", "gate.py")


def expand(patterns):
    """glob + 目录递归 + 去重排序 → 待检查的 md 列表。"""
    files = set()
    for pat in patterns:
        hits = glob.glob(pat, recursive=True)
        if not hits and os.path.exists(pat):
            hits = [pat]
        for h in hits:
            if os.path.isdir(h):
                files.update(glob.glob(os.path.join(h, "**", "*.md"), recursive=True))
            elif h.lower().endswith(".md"):
                files.add(h)
    return sorted(files)


def main():
    root = os.environ.get("GATE_ROOT") or ""
    if not root or not os.path.isfile(os.path.join(root, "tools", "check_solution.py")):
        print("[action] GATE_ROOT 没指到仓库根：%r（要找 tools/check_solution.py）" % root,
              file=sys.stderr)
        return 2

    patterns = os.environ.get("GATE_PATHS", "").split()
    if not patterns:
        print("[action] 没给 path 输入 —— 说要检查哪些题解 md，例如 `题解/**/*.md`",
              file=sys.stderr)
        return 2

    files = expand(patterns)
    if not files:
        print("[action] path=%s 没匹配到任何 .md" % " ".join(patterns), file=sys.stderr)
        return 2

    extra = shlex.split(os.environ.get("GATE_ARGS", ""))
    print("[action] 仓库根：%s" % root)
    print("[action] 待检查 %d 份：%s" % (len(files), "、".join(files)))

    # ::group:: 是 GitHub 的日志折叠标记；本地跑时它只是两行普通输出，无副作用。
    print("::group::check_solution.py（17 项格式闸）")
    cmd = [sys.executable, os.path.join(root, GATE), "--repo", root] + files + extra
    try:
        rc = subprocess.call(cmd)
    except OSError as e:
        print("[action] 起不了子进程：%s" % e, file=sys.stderr)
        return 2
    finally:
        print("::endgroup::")

    if rc == 0:
        print("[action] 全部通过（%d 份）" % len(files))
    else:
        print("::error title=题解格式闸::%d 份里有没过的，看上面的逐项输出（每项带行号原句）"
              % len(files))
    return rc


if __name__ == "__main__":
    sys.exit(main())
