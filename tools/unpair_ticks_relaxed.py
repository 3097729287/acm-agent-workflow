# -*- coding: utf-8 -*-
"""unpair_ticks 的宽松版：给「已手写 LaTeX」的稿子去灰底（跳过「正文没有 $」校验）。

为什么需要它：unpair_ticks.py 假设输入是「纯 Unicode 数学 + 灰底」的老稿，自带一条
「正文没有 $ 号」校验——稿子里一旦有手写的 `$...$`（如 `$\\approx$`、`$60\\%$`），它会直接
「★校验失败，原文件未改动★」。这不是 bug、是它的输入前提；本脚本复用它的 keep() 判定
与表格竖线转义逻辑，只跳过那一条校验，其余处理完全一致，改动前照样按统一规则备份
（备份仓 = <backup_root>\\<来源目录镜像>\\，默认仓库根下的 .backups\\）。

用法：python unpair_ticks_relaxed.py <文件.md> [<文件2.md> ...]
说明：本脚本不写 unpair_diff.txt；跑完仍建议核对每份打印的「去掉清单」。
"""
import importlib.util
import os
import re
import sys

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unpair_ticks.py")
spec = importlib.util.spec_from_file_location("ut", TOOL)
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)


def main():
    files = sys.argv[1:]
    if not files:
        print(__doc__)
        sys.exit(1)

    for P in files:
        P = os.path.abspath(P)
        L = open(P, encoding="utf-8").read().split("\n")
        flag = False
        in_fence = []
        for l in L:
            if l.startswith("```"):
                in_fence.append(True)
                flag = not flag
            else:
                in_fence.append(flag)

        kept, dropped, esc = [], [], []
        out = []
        for i, l in enumerate(L):
            if in_fence[i] or "`" not in l:
                out.append(l)
                continue
            is_table = l.strip().startswith("|") and l.strip().endswith("|")

            def repl(m, is_table=is_table, ln=i + 1):
                s = m.group(1)
                if ut.keep(s):
                    kept.append((s, ln))
                    return m.group(0)
                dropped.append((s, ln))
                if "|" in s and is_table:      # 表格里去掉反引号后竖线会撑破单元格
                    esc.append((s, ln))
                    s = s.replace("|", "\\|")
                return s

            out.append(re.sub(r"`([^`]+)`", repl, l))

        new = "\n".join(out)
        n_changed = sum(1 for a, b in zip(L, out) if a != b)
        print("文件：%s" % P)
        print("  保留 %d 处 / 去掉 %d 处 / 改动 %d 行" % (len(kept), len(dropped), n_changed))
        print("  去掉清单：%s" % sorted(set(s for s, _ in dropped)))
        if esc:
            print("  !! 表格内竖线转义：%s" % esc)
        if n_changed == 0:
            print("  无改动")
            continue
        bak = ut.backups_repo(P)
        print("  已备份 → %s" % bak)
        open(P, "wb").write(new.encode("utf-8"))
        back = open(P, "rb").read().decode("utf-8")
        assert back == new, "写回后不一致"
        print("  已写回（%d 字节）" % os.path.getsize(P))


if __name__ == "__main__":
    main()
