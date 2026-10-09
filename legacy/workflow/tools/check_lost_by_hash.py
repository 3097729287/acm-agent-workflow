# -*- coding: utf-8 -*-
"""对账尺子：比「快照」和「现状」，报出**快照里有、现状里按内容一份都找不到**的文件。

为什么按内容不按文件名：合并目录时同名文件会互相顶掉，六个 demo.cpp 按名字比
会以为「还在」，其实在的是另一个。见《工具链》的「搬目录会静默丢文件」。

用法：
    python check_lost_by_hash.py <快照目录> <现状目录> [--ext .cpp,.py,.cmd]
    python check_lost_by_hash.py <快照目录> <现状目录> --all
    python check_lost_by_hash.py <快照目录> <现状目录> --ext .cpp --scan <扫描根目录>

退出码：0 = 一个没丢；1 = 有丢的（方便串进 && 链）。
"""
import hashlib
import os
import sys


def h(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except OSError:
        return None


def walk(root, exts):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if exts is None or f.lower().endswith(exts):
                out.append(os.path.join(dp, f))
    return out


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print(__doc__)
        return 2
    snap, new = pos[0], pos[1]

    exts = None
    if "--ext" in argv:
        exts = tuple(x.strip().lower() for x in argv[argv.index("--ext") + 1].split(","))
    elif "--all" not in argv:
        exts = (".cpp", ".py", ".cmd", ".h", ".hpp")

    scan = []
    if "--scan" in argv:
        scan = [d for d in argv[argv.index("--scan") + 1].split(",")]

    if not os.path.isdir(snap):
        print("★ 快照目录不存在：%s" % snap)
        return 2
    if not os.path.isdir(new):
        print("★ 现状目录不存在：%s" % new)
        return 2

    s = walk(snap, exts)
    n = walk(new, exts)
    new_hash = {}
    for p in n:
        k = h(p)
        if k:
            new_hash.setdefault(k, []).append(p)

    lost = [p for p in s if h(p) not in new_hash]
    print("快照 %d 个 / 现状 %d 个；内容对不上的 %d 个" % (len(s), len(n), len(lost)))
    if not lost:
        print("一个没丢 ✅")
        return 0

    found = {}
    if scan:
        want = {h(p): p for p in lost}
        for R in scan:
            for dp, dn, fn in os.walk(R):
                if os.path.basename(dp) == "backups":
                    continue
                for f in fn:
                    p = os.path.join(dp, f)
                    k = h(p)
                    if k in want:
                        found.setdefault(want[k], []).append(p)

    print("\n%-56s %s" % ("快照里的位置", "别处有没有"))
    for p in sorted(lost):
        rel = os.path.relpath(p, snap).replace("\\", "/")
        got = found.get(p, [])
        print("   %-54s %s" % (rel, [os.path.relpath(g, snap) for g in got]
                               or ("★ 真没了" if scan else "—")))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
