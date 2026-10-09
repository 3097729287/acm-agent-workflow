# -*- coding: utf-8 -*-
"""extract_math.py —— 对 md 跑一遍 unify_latex 转换（不落盘），抽出全部公式到 math.json。

抽出两类：行内 `$...$` 与跨行 `$$...$$` 块（记块首行行号）。
用法: python extract_math.py <md> [<md> ...]
"""
import io
import json
import re
import sys

import toolutil                 # 同目录：围栏状态机的唯一实现
import unify_latex as U


def extract(text):
    """抽出全部公式：行内 `$...$` + 跨行 `$$...$$` 块（记块首行行号）。

    单行 `$$x$$` 走行内规则（`$` 不在 [^$\n] 里，会从第 2 个 `$` 匹配到第 3 个）。
    未闭合的 `$$` 块不产出（配对问题由 check_solution 第 1 项负责报）。
    """
    items = []
    lines = text.split("\n")
    # ``` 与 ~~~ 都算围栏（本工具是全库唯一认 ~~~ 的，见 toolutil 的「口径缝」注释）
    mask = toolutil.fence_mask(lines, indent=True, tilde=True)
    in_disp, buf, start = False, [], 0
    for i, ln in enumerate(lines, 1):
        if mask[i - 1]:
            continue
        s = re.sub(r"`[^`]*`", "", ln)
        if in_disp:                      # 跨行 $$ 块内：攒到含 $$ 的那一行收尾
            k = s.find("$$")
            if k < 0:
                buf.append(s)
            else:
                buf.append(s[:k])
                items.append({"line": start, "tex": "\n".join(buf).strip()})
                in_disp = False
            continue
        m = re.match(r"^\s*\$\$(.*)$", s)
        if m and "$$" not in m.group(1):     # 行首 $$、本行没有闭合 → 开块
            in_disp, buf, start = True, [m.group(1)], i
            continue
        for m2 in re.finditer(r"\$([^$\n]+)\$", s):
            items.append({"line": i, "tex": m2.group(1)})
    return items


def main(paths):
    out = {}
    for p in paths:
        text = io.open(p, encoding="utf-8").read()
        stats = {"frags": 0, "lt": 0, "failed": []}
        new = U.process(text, stats)
        out[p] = extract(new)
    with io.open("math.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print("已抽取 %d 个公式 -> math.json" % sum(len(v) for v in out.values()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
