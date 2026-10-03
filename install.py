# -*- coding: utf-8 -*-
"""安装助手：生成 config.json、环境体检、从零建一个自己的数据根。

用法（在仓库根目录跑）：

    python install.py                    # 生成 config.json（默认指向自带示例 demo\\）+ 环境体检
    python install.py --check            # 只体检，不写任何文件
    python install.py --new-data DIR     # 建一个自己的数据根（目录骨架 + 模板 + 空索引 + 空状态表）
    python install.py --data-root DIR [--backup-root DIR] [--desktop-copy DIR|off]

选项：

    --force    覆盖已存在的 config.json（默认不覆盖）

说明：脚本零依赖、只用标准库；不写任何东西到仓库之外（--new-data 建的目录除外）。
"""
import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(REPO, "config.json")
EXAMPLE = os.path.join(REPO, "config.example.json")
TOOLS = os.path.join(REPO, "tools")

DEFAULT_CONFIG = """{
  "data_root": "./demo",
  "backup_root": "./.backups",
  "desktop_copy_dir": null
}
"""

# ---------------------------------------------------------------- config.json

def write_config(args):
    if os.path.exists(CONFIG) and not args.force:
        print("[跳过] config.json 已存在（要覆盖加 --force）。当前内容：")
        print("        " + open(CONFIG, encoding="utf-8").read().strip().replace("\n", "\n        "))
        return 0
    if args.data_root or args.backup_root or args.desktop_copy is not None:
        cfg = {
            "data_root": args.data_root or "./demo",
            "backup_root": args.backup_root or "./.backups",
            "desktop_copy_dir": None if args.desktop_copy in (None, "off") else args.desktop_copy,
        }
        text = ('{\n  "data_root": %s,\n  "backup_root": %s,\n  "desktop_copy_dir": %s\n}\n'
                % (_j(cfg["data_root"]), _j(cfg["backup_root"]), _j(cfg["desktop_copy_dir"])))
    else:
        text = DEFAULT_CONFIG
    with open(CONFIG, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("[完成] 已写 config.json：")
    print("        " + text.strip().replace("\n", "\n        "))
    return 0


def _j(v):
    return "null" if v is None else '"%s"' % v


# ------------------------------------------------------------------- 体检

def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        line = (p.stdout or p.stderr).strip().splitlines()
        return p.returncode, line[0] if line else ""
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def check(args):
    print("== 环境体检 ==")
    v = sys.version_info
    print("  Python      %d.%d.%d  %s" % (v.major, v.minor, v.micro,
          "OK" if v >= (3, 8) else "★ 需要 3.8+"))
    rc, first = run(["g++", "--version"])
    print("  g++         %s  %s" % (first or "没找到", "OK" if rc == 0 else "（可选：没有它只能跳过编译/对拍档）"))
    rc, first = run(["node", "--version"])
    print("  node        %s  %s" % (first or "没找到", "OK" if rc == 0 else "（可选：没有它 KaTeX 公式渲染检查打「不适用」）"))

    # 数据根 + 示例闸门
    root = args.data_root or _config_data_root()
    print("  数据根      %s" % root)
    demo_round = os.path.join(root, "题解", "牛客周赛", "Round163")
    if os.path.isdir(demo_round):
        exe = os.path.join(TOOLS, "archive_check.py")
        sys.stdout.flush()  # 子进程直接继承控制台，先把自己的行刷出去，顺序才不乱
        print("  == 示例闸门：archive_check.py Round163（自带示例数据）==")
        p = subprocess.run([sys.executable, exe, "Round163"], cwd=REPO)
        print("  [%s] 退出码 %d（0 = 四处对账通过）" % ("通过" if p.returncode == 0 else "★ 未通过", p.returncode))
        return p.returncode
    print("  （数据根里没有 Round163 示例，跳过示例闸门；想看示例把 data_root 指回 ./demo）")
    return 0


def _config_data_root():
    p = os.path.join(REPO, "config.json")
    if os.path.exists(p):
        import json
        try:
            cfg = json.load(open(p, encoding="utf-8"))
            r = cfg.get("data_root", "./demo")
            return r if os.path.isabs(r) else os.path.normpath(os.path.join(REPO, r))
        except Exception:
            pass
    return os.path.join(REPO, "demo")


# ------------------------------------------------------------- 新建数据根

STATUS_MD = """# 题目状态

> 用途：跟踪每道比赛题的掌握状态。学习闭环 = 比赛限时自己做 → 不会才看公开题解 → 重做。
> 维护：一题一行、只存「当前状态」；**改状态时同时改「日期」**（日期 = 最后一次状态变更日）。
> 范围：**只跟踪非签到题**——签到题不进本表、也不进统计（判定与归档一致：签到题不归档、也不进本表）。
> 新场次：归档时由 AI 把本场非签到题行追加到表尾（状态默认「未做」、日期留空）。
> 报告：`python tools\\status_report.py`；图形端改状态：`python tools\\status_gui.py`。

## 状态定义

| 状态 | 含义 | 什么时候碰它 |
|---|---|---|
| 未做 | 尚未梳理，旧题默认（不进待办队列） | 只在统计里出现 |
| 不会 | 赛时没做出来（有思路没写完也算），待补 | 补题队列 |
| 待重写 | 看过题解后关掉重写没通过 | **最高优先**，次日先做 |
| 复现AC | 看题解后关掉重写通过 | D+7 重做 |
| 独立AC | 没看任何材料自己做出来（含赛时 AC） | D+7 重做 |
| 巩固 | 间隔复习也通过 | D+30 抽检 |

## 流转规则

- 赛后结算：赛时 AC → 独立AC；没做出来（有思路没写完也算）→ 不会。
- 补题：自己重想出来 → 独立AC；看题解后关掉重写通过 → 复现AC；重写失败 → 待重写。
- 待重写 → 次日重来通过 → 复现AC；反复失败 → 保持 待重写，继续排在队首。
- 独立AC / 复现AC → D+7 重做通过 → 巩固；没通过 → 待重写。
- 巩固 → D+30 抽检通过 → 刷新日期（状态仍是 巩固）；没通过 → 待重写。
- 「日期」列 = 最后一次状态变更日（刷新日期也算一次变更）；旧题回填时留空。

## 题目状态表

| 场次 | 题号 | 题名 | 知识点 | 难度 | 状态 | 日期 |
|---|---|---|---|---|---|---|
"""

INDEX_MD = """# 题解算法索引

> **用途**：记录每一场题解里，每道非签到题用到的数据结构与算法，以及它在 `<数据根>\\算法\\` 里的归档位置。
> **谁维护**：AI 在每场题解交付后更新——场次小节由 `tools\\index_sync.py` 从记录 md 头部生成，**不要手改**；反查表手工维护，归档时由 `tools\\archive_check.py` 兜底对账。
> **当前条数**：0 条 = 0 场非签到题之和 = 算法库里 0 份题目记录 md。
> **收工自检**：`python tools\\archive_check.py RoundNNN` —— 四处缺哪样直接报，退出码 0 = 归档完成。

---

## 一、反查表（算法 → 题目）

题名都写成链接；带「（指针）」的表示该题主记录在别的文件夹，这一行只是次要算法的入口。

| 算法 / 数据结构 | 文件夹 | 练过的题目 |
|---|---|---|
| （归档第一场后逐行补） | | |

## 二、说明

- **一题多算法**：主算法文件夹放详写记录；次要算法只在本表 + 该文件夹的 `题解指针.md` 里留一行，**不重复正文**。
- **归档记录固定五节**（顺序不许变、不许加节）：题意（精简）→ 关键点（为什么用这个算法）→ 复杂度 → 踩过的坑 → 相关。
- **难度口径**：CF 分制（900 / 1100 / 1300 / 1500 / 1800）。**不写 AC 数 / 提交数**（那是榜单快照，会变）。
- **编码约定**：UTF-8 无 BOM、行尾 LF；**数学写 LaTeX**（`$...$`）。
- **清理约定**：不留编译产物（`.exe`）、不留 PNG；要图就写可跑的字符画脚本（`tools\\vizgrid.py`）。

## 相关

《归档》《已讲过概念清单》《工具链》
"""


def new_data(root):
    root = os.path.abspath(root)
    made, kept = [], []
    for sub in (os.path.join("题解", "牛客周赛"), "算法", "索引"):
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            kept.append(sub)
        else:
            os.makedirs(d)
            made.append(sub)
    # 状态表 / 索引：空骨架（已存在则不动）
    for rel, text in ((os.path.join("题解", "题目状态.md"), STATUS_MD),
                      (os.path.join("索引", "题解算法索引.md"), INDEX_MD)):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            kept.append(rel)
        else:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            made.append(rel)
    # 记录模板：直接从示例数据复制一份（单一来源）
    tpl_src = os.path.join(REPO, "demo", "索引", "题目记录模板.md")
    tpl_dst = os.path.join(root, "索引", "题目记录模板.md")
    if os.path.exists(tpl_dst):
        kept.append(os.path.join("索引", "题目记录模板.md"))
    elif os.path.exists(tpl_src):
        with open(tpl_src, encoding="utf-8") as f:
            text = f.read()
        with open(tpl_dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        made.append(os.path.join("索引", "题目记录模板.md"))

    print("[完成] 数据根：%s" % root)
    for x in made:
        print("  新建  %s" % x)
    for x in kept:
        print("  已存在（不动）  %s" % x)
    print("""
下一步：
  1) 让 config.json 的 data_root 指向这个目录：
     python install.py --data-root %s
  2) 让 AI agent 读仓库根目录的 AGENTS.md，然后直接把一场比赛的 URL 发给它。
""" % root)
    return 0


# ------------------------------------------------------------------- main

def main(argv):
    ap = argparse.ArgumentParser(description="acm-agent-workflow 安装助手")
    ap.add_argument("--check", action="store_true", help="只体检，不写任何文件")
    ap.add_argument("--new-data", metavar="DIR", help="建一个自己的数据根（骨架 + 模板 + 空索引/状态表）")
    ap.add_argument("--data-root", metavar="DIR", help="写进 config.json 的数据根")
    ap.add_argument("--backup-root", metavar="DIR", help="写进 config.json 的备份根（默认 ./.backups）")
    ap.add_argument("--desktop-copy", metavar="DIR", help="可选：桌面副本目录；off = 关闭")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 config.json")
    a = ap.parse_args(argv)

    if a.new_data:
        rc = new_data(a.new_data)
        if a.data_root is None:
            return rc
    if not a.check:
        write_config(a)
    return check(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
