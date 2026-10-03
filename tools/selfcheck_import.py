# -*- coding: utf-8 -*-
r"""selfcheck_import —— 题解导入/导出的机器闸门（设计 §4.4 验收）

    python tools\selfcheck_import.py            # 全跑（含 17 项闸门，约 2~3 分钟）
    python tools\selfcheck_import.py --fast     # 跳过 check_solution（只验管道，约 20 秒）

两项验收，各在一个**临时空数据根**里真跑一遍（不碰 config.json 指的数据根）：

  ① 往返：export Round163 → 导入空根 → `archive_check` 退出码 0
     另外逐文件比 sha256：包里带的东西必须**一字不差**地落到新根（往返无损）。
  ② 未登记名字包：故意写词典里没有的知识点名 / 文件夹名（还有别名写法、缺记录）
     → **照收**（导入退出码 0）+ 报告里出现「待登记清单」+ 名字真落进索引 +
     `archive_check` 退出码 0。

退出码：0 = 两项都过；1 = 有验收没过；2 = 环境不对（缺 demo 数据根等）。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402

BS = chr(92)
CONT = "牛客周赛"
TOOLS = os.path.join(toolutil.REPO_ROOT, "tools")


def run(args):
    """跑一个同目录脚本 → (退出码, stdout+stderr)"""
    cmd = [sys.executable, os.path.join(TOOLS, args[0])] + args[1:]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=toolutil.REPO_ROOT,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def new_root(base, name):
    """空数据根 + 知识库副本（--mem 指向副本，别让自检改坏仓库的 knowledge/）

    `install.py` 在仓库根、不在 tools\\ 下，所以不走 run() 那条路，单独调。
    """
    root = os.path.join(base, name)
    p = subprocess.run([sys.executable, os.path.join(toolutil.REPO_ROOT, "install.py"),
                        "--new-data", root], capture_output=True, text=True,
                       cwd=toolutil.REPO_ROOT, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise SystemExit("★ install.py --new-data 失败：\n" + (p.stdout or "") + (p.stderr or ""))
    mem = os.path.join(base, name + "-knowledge")
    shutil.copytree(os.path.join(toolutil.REPO_ROOT, "knowledge"), mem)
    return root, mem


def check_root(root, mem, rnd):
    rc, out = run(["archive_check.py", rnd, "--root", root, "--mem", mem,
                   "--status", os.path.join(root, "题解", "题目状态.md")])
    return rc, out


def last_result(out):
    for l in reversed(out.strip().split("\n")):
        if l.startswith(("结论：", "★")):
            return l.strip()
    return out.strip().split("\n")[-1] if out.strip() else ""


# ---------------------------------------------------------------- ① 往返
def t_roundtrip(base, root_src, fast):
    root, mem = new_root(base, "rt-data")
    zp = os.path.join(base, "Round163.zip")
    rc, out = run(["export_solution.py", "Round163", "-o", zp, "--root", root_src,
                   "--contributor", "selfcheck"])
    if rc != 0:
        return False, "导出失败（退出码 %d）\n%s" % (rc, out)
    rc, out = run(["import_solution.py", zp, "--apply", "--root", root, "--mem", mem]
                  + (["--no-check-solution"] if fast else []))
    if rc != 0:
        return False, "导入失败（退出码 %d）\n%s" % (rc, out)
    # 往返无损：包里带的东西必须一字不差
    n, bad = 0, []
    with zipfile.ZipFile(zp) as z:
        for m in z.namelist():
            if m == "manifest.json":
                continue
            tgt = os.path.join(root, m.replace("/", os.sep))
            if not os.path.exists(tgt):
                bad.append("缺：" + m)
            elif sha(tgt) != hashlib.sha256(z.read(m)).hexdigest():
                bad.append("内容不一致：" + m)
            else:
                n += 1
    if bad:
        return False, "往返不是无损（%d 项）：\n  %s" % (len(bad), "\n  ".join(bad[:8]))
    rc, out = check_root(root, mem, "Round163")
    if rc != 0:
        return False, "导入后 archive_check 退出码 %d：\n%s" % (rc, out)
    return True, "包内 %d 个文件逐字节一致，archive_check 退出码 0（%s）" % (n, last_result(out))


# ---------------------------------------------------------------- ② 照收
def t_unknown(base, root_src, fast):
    """造一个「手写包」：未登记名字 + 未登记文件夹 + 别名 + 缺记录"""
    root, mem = new_root(base, "un-data")
    zp = os.path.join(base, "Round163.zip")
    rc, out = run(["export_solution.py", "Round163", "-o", zp, "--root", root_src,
                   "--contributor", "selfcheck"])
    if rc != 0:
        return False, "导出失败（退出码 %d）\n%s" % (rc, out)
    work = os.path.join(base, "un-pack")
    shutil.rmtree(work, ignore_errors=True)
    with zipfile.ZipFile(zp) as z:
        z.extractall(work)
    mp = os.path.join(work, "manifest.json")
    man = json.load(open(mp, encoding="utf-8"))
    man["contributor"] = "someone-on-github"
    for pr in man["problems"]:
        pr.pop("back_rows", None)                       # 手写包：不带反查表原文
        if pr["letter"] == "F":
            pr["knowledge"] = ["李超线段树"]             # 词典里没有的名字
            pr["folder"] = "线段树" + BS                 # 词典里没有的文件夹
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # B 删掉记录 md（导入生成「精简记录」）；F 的记录换文件夹 + 算法行写别名
    os.remove(os.path.join(work, "算法", "位运算", "牛客周赛Round163-B-小月的十六进制.md"))
    src_f = os.path.join(work, "算法", "字典树", "牛客周赛Round163-F-小月的前缀.md")
    t = open(src_f, encoding="utf-8").read()
    t = t.replace("- **归档文件夹**：`字典树" + BS + "`", "- **归档文件夹**：`线段树" + BS + "`")
    i0 = t.index("- **数据结构与算法**：")
    i1 = t.index("\n", i0)
    t = t[:i0] + "- **数据结构与算法**：李超线段树（动态开点） + 状态压缩DP" + t[i1:]
    os.makedirs(os.path.join(work, "算法", "线段树"), exist_ok=True)
    with open(os.path.join(work, "算法", "线段树", os.path.basename(src_f)),
              "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    os.remove(src_f)
    shutil.rmtree(os.path.join(work, "算法", "字典树"))
    zp2 = os.path.join(base, "Round163-hand.zip")
    with zipfile.ZipFile(zp2, "w", zipfile.ZIP_DEFLATED) as z:
        for dp, _dns, fns in os.walk(work):
            for fn in sorted(fns):
                p = os.path.join(dp, fn)
                z.write(p, os.path.relpath(p, work).replace(os.sep, "/"))

    rc, out = run(["import_solution.py", zp2, "--apply", "--root", root, "--mem", mem]
                  + (["--no-check-solution"] if fast else []))
    if rc != 0:
        return False, "照收失败：导入退出码 %d（未登记不该是「问题」）\n%s" % (rc, out)
    if "【待登记清单】" not in out:
        return False, "报告里没有「待登记清单」一节"
    for want in ("李超线段树", "线段树"):
        if want not in out:
            return False, "待登记清单里没报出 %r" % want
    idx = os.path.join(root, "索引", "题解算法索引.md")
    itext = open(idx, encoding="utf-8").read()
    if "李超线段树" not in itext:
        return False, "未登记的名字没落进索引（照收 = 按原样落盘）"
    fr = os.path.join(root, "算法", "线段树", "牛客周赛Round163-F-小月的前缀.md")
    if not os.path.exists(fr):
        return False, "未登记的文件夹没照收（`线段树" + BS + "` 下没有记录 md）"
    if "状态压缩DP" in open(fr, encoding="utf-8").read():
        return False, "别名没被纠正（记录 md 里还留着 `状态压缩DP`）"
    if not os.path.exists(os.path.join(root, "算法", "位运算", "牛客周赛Round163-B-小月的十六进制.md")):
        return False, "缺记录的题没生成「精简记录」"
    rc, out = check_root(root, mem, "Round163")
    if rc != 0:
        return False, "照收后 archive_check 退出码 %d：\n%s" % (rc, out)
    return True, "未登记名照收 + 6/6 落盘 + 精简记录生成 + archive_check 退出码 0（%s）" % last_result(out)


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="导入/导出 机器闸门（自检）")
    ap.add_argument("--root", default=toolutil.DATA_ROOT, help="源数据根（缺省 config.json 的 demo）")
    ap.add_argument("--fast", action="store_true", help="跳过 check_solution 的 17 项闸门")
    ap.add_argument("--keep", action="store_true", help="留着临时目录（排查用）")
    a = ap.parse_args(argv)
    src = a.root.replace("/", os.sep)
    if not os.path.isdir(os.path.join(src, "题解", CONT, "Round163")):
        print("★ 源数据根里没有 %s\\Round163\\：%s（自检要用它当样本）" % (CONT, src))
        return 2
    base = tempfile.mkdtemp(prefix="selfcheck-import-")
    print("自检沙箱：%s%s" % (base, "（--keep，跑完不删）" if a.keep else ""))
    try:
        ok1, msg1 = t_roundtrip(base, src, a.fast)
        print("[%s] ① 往返（export → 导入空根 → 对账）" % ("通过" if ok1 else "★未通过"))
        print("        " + msg1.replace("\n", "\n        "))
        ok2, msg2 = t_unknown(base, src, a.fast)
        print("[%s] ② 未登记名字（照收 + 待登记清单 + 对账）" % ("通过" if ok2 else "★未通过"))
        print("        " + msg2.replace("\n", "\n        "))
    finally:
        if not a.keep:
            shutil.rmtree(base, ignore_errors=True)
    print("-" * 74)
    if ok1 and ok2:
        print("结论：两项验收全过——题解包能进能出，未登记的名字照收不误")
        return 0
    print("结论：★有验收没过（见上面 ★ 那行的报错）★")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
