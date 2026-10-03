# 把格式闸挂到你自己的仓库（GitHub Action）

本仓库根部的 `action.yml` 是一个**复合 Action**：把 17 项题解格式闸打包成一行 `uses:`，
挂到自己仓库的 CI 上，题解不合格就变红。

它不要求你的仓库长成这个仓库的样子——只要求你告诉它**哪些 md 是题解**。

## 用法

在你自己仓库的 `.github/workflows/*.yml` 里加这么一段：

```yaml
name: 题解格式闸
on: [push, pull_request]

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: 3097729287/acm-agent-workflow@main
        with:
          path: '题解/**/*.md'
```

推送即生效。不过闸的那份会列出**每一条问题 + 行号原句**，作业红。

## 输入

| 输入 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `path` | **是** | — | 要检查的题解 md：文件 / 目录 / glob，**空格分隔可给多个**；给目录会递归收 `*.md`。例：`题解/**/*.md 文档/某篇.md` |
| `extra-args` | 否 | 空 | 原样转给 `check_solution.py`，如 `--no-compile`（跳过编译检查，快）、`--no-record`（跳过实测记录项，适合非题解文档）、`--quiet`（只打印有问题的项） |
| `python-version` | 否 | `3.13` | 跑闸用的 Python |

> `path` 故意**不给默认值**：默认成 `**/*.md` 会把 README 也扫进去，那不是题解、必然误报。

## 17 项查什么

`$` 配对、LaTeX 完整度（直接再跑一遍 `unify_latex` 查漏转）、灰底反引号、编译、实测记录格式、
节白名单、目录四列、小节顺序与四项必写、缩进代码块里的公式、KaTeX 全量渲染…… 完整清单：

```bash
python tools/check_solution.py --list
```

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 全部通过 |
| 1 | 有文件没过（作业红） |
| 2 | Action 自己出错：没给 `path` / `path` 没匹配到 md / 找不到仓库根 |

## 依赖与降级

- **不装 g++**：需要编译的那几项如实记「未验证」，不报错也不假装通过。
- **不装 node + katex**：第 17 项（KaTeX 渲染）打「不适用」跳过。想开：
  `cd tools && npm install katex`，见 [../README.md](../README.md) 的快速开始。
- Action 里只跑 `actions/setup-python`，其余零依赖。

## 本地预演（不推 CI 先试）

同一套入口在本地跑得动，把 `action.yml` 塞的环境变量自己给上即可：

```bash
# 在本仓库根目录
GATE_ROOT="$PWD" GATE_PATHS="demo/题解/**/*题解.md" python skills/check-solution/action_run.py

# 带额外参数、故意喂一份做坏的
GATE_ROOT="$PWD" GATE_PATHS="examples/反例题解.md" GATE_ARGS="--quiet" \
  python skills/check-solution/action_run.py
```

Windows（Git Bash / cmd 改 `set`）同理。退出码与 CI 一致，可以直接拿来对账。

## 与 skill 的关系

同一个闸有两个入口，都指向 `tools/check_solution.py`，规则不会走样：

| 形态 | 给谁用 | 怎么调 |
|---|---|---|
| **skill**（`skills/check-solution/`） | 装了 agent skill 的人，在自己的会话里手动跑 | 见该目录的 `SKILL.md` |
| **Action**（本文件） | 任何仓库的 CI，push 即跑 | `uses: 3097729287/acm-agent-workflow@main` |
