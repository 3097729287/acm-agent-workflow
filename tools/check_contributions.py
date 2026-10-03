# -*- coding: utf-8 -*-
r"""check_contributions —— `contributions\` 里每个题解包的机器闸门（设计 §5.2）

    python tools\check_contributions.py                 # 自检（好包绿 / 坏包红）+ 扫 contributions\
    python tools\check_contributions.py --fast          # 跳过 md 的 17 项闸门（只验管道，本机快跑）
    python tools\check_contributions.py --no-selftest   # 只扫 contributions\（CI 主路径就是这条）
    python tools\check_contributions.py --pack <路径>   # 只查一个包（收到 issue 附件时本地跑）

**扫描对象** = `contributions\` 下：每个含 `manifest.json` 的子目录 + 每个 `*.zip`。

**每个包怎么判**：在一个**临时空数据根**里跑一遍
`import_solution.py <包> --root <临时根>`（**dry，不写盘**）——
    · 退出码 0 = 这个包过关；
    · 未登记的知识点 / 文件夹只算**提醒**（照收）、不拦（它就是收编机制的入口）；
    · 非 0 = 不过关：1 = 包有硬伤，2 = 读不了（不是 zip / manifest 都不是）。

**自检**（默认跑，`--no-selftest` 可跳）现场从 `demo\` 造三个 fixture，**不往仓库里塞 zip**：
    · 好包    = `export_solution.py Round163` 现导 → 应绿（退出码 0）
    · 坏包①  = 好包里的 manifest 删掉一题的 `difficulty` → 应红（退出码 1，「不合格」那一类）
    · 坏包②  = 一个不是 zip 的文件 → 应红（退出码 2，「读不了」那一类）
自检跑在临时目录、跑完就删；机器闸门自己先被验一遍，才轮到它验别人的包。

退出码：0 = 自检符预期 + `contributions\` 里的包全过关；1 = 有包不过关 / 自检不符预期；
2 = 环境不对（缺 demo 数据根等）。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolutil  # noqa: E402

CONTRIB = os.path.join(toolutil.REPO_ROOT, "contributions")
DEMO = os.path.join(toolutil.REPO_ROOT, "demo")
KNOW = os.path.join(toolutil.REPO_ROOT, "knowledge")
TOOLS = os.path.join(toolutil.REPO_ROOT, "tools")


def run(args):
    """跑一个同目录脚本 → (退出码, stdout+stderr)"""
    cmd = [sys.executable, os.path.join(TOOLS, args[0])] + args[1:]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=toolutil.REPO_ROOT,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def new_root(base, name):
    """临时空数据根（+ 知识库副本：别让校验动仓库里的 knowledge\\）"""
    root = os.path.join(base, name)
    p = subprocess.run([sys.executable, os.path.join(toolutil.REPO_ROOT, "install.py"),
                        "--new-data", root], capture_output=True, text=True,
                       cwd=toolutil.REPO_ROOT, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise SystemExit("★ install.py --new-data 失败：\n" + (p.stdout or "") + (p.stderr or ""))
    return root


def check_pack(pack, root, mem, fast=False):
    """一个包 → (退出码, 输出)。dry，不写盘。"""
    return run(["import_solution.py", pack, "--root", root, "--mem", mem]
               + (["--no-check-solution"] if fast else []))


def last_result(out):
    for ln in reversed(out.strip().split("\n")):
        if ln.startswith(("结论：", "★")):
            return ln.strip()
    return out.strip().split("\n")[-1] if out.strip() else "（没有输出）"


def find_packs():
    """contributions\\ 下的包：含 manifest.json 的子目录 + *.zip（点开头的文件不看）"""
    out = []
    if not os.path.isdir(CONTRIB):
        return out
    for name in sorted(os.listdir(CONTRIB)):
        if name.startswith("."):
            continue
        p = os.path.join(CONTRIB, name)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "manifest.json")):
            out.append(p)
        elif os.path.isfile(p) and name.lower().endswith(".zip"):
            out.append(p)
    return out


# ---------------------------------------------------------------- 自检三件套
def good_pack(base):
    """好包：从 demo 现导整场 Round163（与 selfcheck_import 同一样本，路径已验证）"""
    zp = os.path.join(base, "good-Round163.zip")
    rc, out = run(["export_solution.py", "Round163", "-o", zp, "--root", DEMO,
                   "--contributor", "ci-fixture"])
    if rc != 0:
        raise SystemExit("★ 造「好包」失败（export_solution 退出码 %d）：\n%s" % (rc, out))
    return zp


def bad_pack_manifest(base, good):
    """坏包①：好包里删掉一题的 difficulty（硬伤）→ 该判「不合格」（退出码 1）"""
    work = os.path.join(base, "bad-manifest")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with zipfile.ZipFile(good) as z:
        z.extractall(work)
    mp = os.path.join(work, "manifest.json")
    with open(mp, encoding="utf-8") as f:
        man = json.load(f)
    man["problems"][0].pop("difficulty", None)
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return work                      # 目录形态的包一样收（open_pack 认目录）


def bad_pack_notzip(base):
    """坏包②：不是 zip 的东西 → 该判「读不了」（退出码 2）"""
    p = os.path.join(base, "bad-not-a-pack.zip")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("这不是一个 zip，也不是一个包目录。\n")
    return p


def selftest(base, mem, fast):
    """好包绿 / 坏包红 —— 三项断言，返回 (全对?, 逐行报告)"""
    good = good_pack(base)
    cases = (("好包（Round163 现导）", good, 0),
             ("坏包①（manifest 缺字段）", bad_pack_manifest(base, good), 1),
             ("坏包②（不是 zip）", bad_pack_notzip(base), 2))
    rows, ok_all = [], True
    for i, (tag, pack, want) in enumerate(cases):
        rc, out = check_pack(pack, new_root(base, "st%d" % i), mem, fast)
        ok = rc == want
        ok_all = ok_all and ok
        rows.append("[%s] %s：退出码 %d（期望 %d）→ %s"
                    % ("通过" if ok else "★未通过", tag, rc, want, last_result(out)))
    return ok_all, rows


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="contributions\\ 里题解包的机器闸门")
    ap.add_argument("--pack", help="只查这一个包（zip / 目录），不扫 contributions\\、不跑自检")
    ap.add_argument("--fast", action="store_true", help="跳过题解 md 的 17 项闸门（只验管道）")
    ap.add_argument("--no-selftest", action="store_true", help="跳过好包 / 坏包自检")
    ap.add_argument("--keep", action="store_true", help="留着临时目录（排查用）")
    a = ap.parse_args(argv)

    if not os.path.isdir(os.path.join(DEMO, "题解", "牛客周赛", "Round163")):
        print("★ 找不到 demo\\题解\\牛客周赛\\Round163\\（自检与样例都用它当样本）：%s" % DEMO)
        return 2
    base = tempfile.mkdtemp(prefix="check-contrib-")
    print("临时沙箱：%s%s" % (base, "（--keep，跑完不删）" if a.keep else ""))
    mem = os.path.join(base, "knowledge")
    shutil.copytree(KNOW, mem)
    n_bad = 0
    try:
        # 单包模式：只查这一个
        if a.pack:
            rc, out = check_pack(a.pack, new_root(base, "one"), mem, a.fast)
            print(out if rc else last_result(out))
            print("-" * 74)
            print("结论：%s（退出码 %d）" % ("这一包过关" if rc == 0 else "★这一包不过关", rc))
            return 0 if rc == 0 else 1

        # ① 自检：闸门自己先被验一遍
        if not a.no_selftest:
            ok, rows = selftest(base, mem, a.fast)
            print("【自检】好包绿 / 坏包红：")
            for r in rows:
                print("    " + r)
            print("-" * 74)
            if not ok:
                n_bad += 1

        # ② 扫 contributions\
        packs = find_packs()
        if not packs:
            print("【contributions】没有包（空 = 正常：PR 的包放下才扫）")
        else:
            print("【contributions】%d 个包：" % len(packs))
            for i, p in enumerate(packs):
                rc, out = check_pack(p, new_root(base, "c%d" % i), mem, a.fast)
                print("  [%s] %s —— %s" % ("通过" if rc == 0 else "★不通过",
                                          os.path.relpath(p, toolutil.REPO_ROOT), last_result(out)))
                if rc != 0:
                    n_bad += 1
                    print("        完整报告：")
                    for ln in out.rstrip().split("\n"):
                        print("        " + ln)
    finally:
        if not a.keep:
            shutil.rmtree(base, ignore_errors=True)
    print("-" * 74)
    if n_bad:
        print("结论：★有 %d 项没过 ★" % n_bad)
        return 1
    print("结论：全过 —— 自检符预期，contributions\\ 里的包都合格（未登记知识点只提醒、不拦）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
