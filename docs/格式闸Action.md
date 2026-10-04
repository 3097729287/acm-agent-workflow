# 把格式闸挂到你自己的仓库（GitHub Action）

给**想把 18 项题解格式检查挂进自己仓库 CI** 的人。本仓库根部的 `action.yml` 是**复合 Action**：
一行 `uses:` 让题解不合格时作业变红，只要求你告诉它**哪些 md 是题解**。

## 用法

在你自己仓库的 `.github/workflows/*.yml` 里加这么一段：

```yaml
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

推送即生效。不过闸的那份会列出**每一条问题 + 行号原句**，作业红。完整清单见 `python tools/check_solution.py --list`：`$` 配对、LaTeX 完整度（直接再跑一遍 `unify_latex` 查漏转）、灰底反引号、编译、实测记录格式、节白名单、目录四列、小节顺序与四项必写、缩进代码块里的公式、KaTeX 全量渲染、目录表「考点」列合知识点 v2 规范……

## 输入

| 输入 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `path` | **是** | — | 要检查的题解 md：文件 / 目录 / glob，**空格分隔可给多个**；给目录会递归收 `*.md`。例：`题解/**/*.md 文档/某篇.md`。故意**不给默认值**——默认成 `**/*.md` 会把 README 也扫进去，必然误报 |
| `extra-args` | 否 | 空 | 原样转给 `check_solution.py`，如 `--no-compile`（跳过编译检查，快）、`--no-record`（跳过实测记录项，适合非题解文档）、`--quiet`（只打印有问题的项） |
| `python-version` | 否 | `3.13` | 跑闸用的 Python |

## 退出码与依赖降级

| 码 | 含义 |
|---|---|
| 0 | 全部通过 |
| 1 | 有文件没过（作业红） |
| 2 | Action 自己出错：没给 `path` / `path` 没匹配到 md / 找不到仓库根 |

- **不装 g++**：需要编译的那几项如实记「未验证」，不报错也不假装通过。
- **不装 node + katex**：第 17 项（KaTeX 渲染）打「不适用」跳过。想开：`cd tools && npm install katex`，见 [README 的 FAQ 一节](../README.md#faq)。
- Action 里只跑 `actions/setup-python`，其余零依赖。

## 本地预演（不推 CI 先试）

同一套入口在本地跑得动，在仓库根目录把 `action.yml` 塞的环境变量自己给上即可（Windows 的 Git Bash / cmd 改 `set` 同理）：

```bash
GATE_ROOT="$PWD" GATE_PATHS="demo/题解/**/*题解.md" python skills/check-solution/action_run.py
# 带额外参数、故意喂一份做坏的
GATE_ROOT="$PWD" GATE_PATHS="examples/反例题解.md" GATE_ARGS="--quiet" \
  python skills/check-solution/action_run.py
```

退出码与 CI 一致，可以直接拿来对账。另有会话内手动跑的 skill 入口，见 [skills/check-solution/SKILL.md](../skills/check-solution/SKILL.md)。
