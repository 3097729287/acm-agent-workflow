# acm-agent-workflow

**给 AI agent 用的算法竞赛「题解 + 补题」流水线。** 把「写完题解就烂尾」变成一条有机器闸门的流水线：抓题面 → 写代码 → 四档验证 → 生成题解 → 格式自检 → 归档对账，外加一个跟踪每道题掌握程度的状态表（带图形端）。

[![ci](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml) ｜ [English](README.en.md) ｜ Windows 优先（脚本纯 Python，跨平台可用）｜ MIT License

---

## 这是什么

你在打算法竞赛（牛客 / Codeforces / 洛谷），赛后要补题、写题解、归档算法模板——但这些事**没人管质量**：题解格式飘、验证靠嘴说、归档全靠记性。

这个仓库把整套流程交给 **AI agent**（Claude Code / Codex / 任何能读文件 + 跑命令的 agent），并且**每一步都有机器闸门**——不是「请 agent 认真一点」，而是**跑一条命令、看退出码**：

| 闸门 | 命令 | 通过的标志 |
|---|---|---|
| 验证闸 | `verify.py` | 四档（样例/边界/对拍/极限）逐档给出实测数字 |
| 格式闸 | `check_solution.py` | 17 项检查全过，每项附行号原句 |
| 归档闸 | `archive_check.py RoundNNN` | **退出码 0** = 算法库 / 索引 / 知识库四处对账一致 |
| 演示闸 | `python install.py --check` | 装完当场把自带示例跑穿一遍 |

## 它解决什么

- **「实测记录」靠生成？** 不允许。这套流程里验证数字必须逐字来自实跑，没跑的档如实写「未验证」——仓库里留着一份[反面教材](knowledge/11-反面教材.md)：写得像真的、复跑第一组就翻车的记录长什么样。
- **题解格式每场都不一样？** 节模板有白名单（题意 / 从零讲 / 手算 / 思路 / 参考代码 / 复杂度 / 易错点），`check_solution.py` 按行号执法。
- **讲过的算法又讲一遍？** 有跨场次台账（《已讲过概念清单》），讲过的只给指针、首次出现的强制从零讲。
- **补题队列记不住？** 每场非签到题自动进 `题目状态.md`，六态流转（不会/待重写/复现AC/独立AC/巩固/未做），`status_report.py` 排今天的队列，图形端一键改状态。
- **搬目录丢文件？** 有内容哈希对账工具（按文件名比对会骗人——同名文件互相顶掉时「看着还在、其实在的是另一个」）。

## 快速开始（5 分钟）

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow

python install.py           # 生成 config.json（默认指向自带示例）+ 环境体检 + 跑示例闸门
```

体检通过会看到：Python / g++ / node 三行，以及 **示例闸门退出码 0**（`archive_check.py Round163` 把自带示例数据对了一遍账）。

```
  Python      3.14.7  OK
  g++         g++ (Rev4, Built by MSYS2 project) 16.2.0  OK
  node        v24.18.1  OK
  数据根      <仓库路径>/demo
  == 示例闸门：archive_check.py Round163（自带示例数据）==
  [通过] 退出码 0（0 = 四处对账通过）
```

（g++ 与 node 都是可选的：没有 g++ 时验证档如实写「未验证」，node 只影响 KaTeX 公式渲染检查。）

然后亲手跑一遍四档验证（仓库里就带着一场完整示例：牛客周赛 Round 163）：

```bash
python demo/题解/牛客周赛/Round163/B-G/B/verify_b.py
```

```
  编译       通过     通过（无警告）
  官方样例     通过     3 组全过
  边界用例     通过     9 条全过
  随机对拍     通过     500 组全一致
  极限计时     通过     极限：|x|=8×10^5 全零串, k=10^5 0.007 s、极限：|x|=8×10^5 随机十六进制, k=10^5 0.007 s
```

（上面的输出是逐字实测结果；秒数随机器的快慢浮动，以你自己机器上的实跑为准。）

## 使用教程：完整跑一场比赛

### 第 0 步：让 agent 读规则

把仓库给 agent（Claude Code 直接打开这个目录），然后说：

> 读仓库根目录的 AGENTS.md，然后处理这个比赛：`https://ac.nowcoder.com/acm/contest/<比赛号>`

`AGENTS.md` 是规则的**主干**（10 条铁律 + 索引表），明细全在 `knowledge\`（14 篇），agent 按需取用。

### 六步流水线

| 步骤 | 命令（agent 自己会跑） | 产出 | 闸门 |
|---|---|---|---|
| ① 抓题面 | `python tools/fetch_problem.py <URL>` | `RoundN\_work\` 下的题面 / 样例常量表 + 难度分档建议 | 抓取数 == 题目数 |
| ② 定档 | （agent 查《已讲过概念清单》+ 分档表） | 每题讲什么、讲多深 | — |
| ③ 写代码 | 每题一个目录 `RoundN\<区间>\<字母>\` | `x.cpp` + `x_brute.cpp` + `verify_x.py` | — |
| ④ 验证 | `python verify_x.py` | 四档实测数字 | 全过且数字来自实跑 |
| ⑤ 写题解 + 自检 | `python tools/check_solution.py <md>` | `RoundN题解.md` | 17 项全过 |
| ⑥ 复验 + 归档 | `python tools/md_full.py <md> <字母>` → `archive_check.py RoundN` | 算法库记录 / 索引 / 状态表 | **退出码 0** |

一场一个自包含文件夹，落盘结构：

```
<数据根>\
├── 题解\牛客周赛\Round163\
│   ├── Round163题解.md          ← 交付 md（节模板白名单）
│   ├── B-G\B\                   ← 每题：正解 + 暴力 + 验证驱动 + 可选配图脚本
│   └── _work\                   ← 耗材（题面/样例），可随手删、重抓即回来
├── 算法\                        ← 归档：按主算法分文件夹，一题一份精简记录
├── 索引\题解算法索引.md          ← 全量索引（场次小节由脚本生成）
└── 题解\题目状态.md              ← 补题状态表
```

### 接自己的数据

```bash
python install.py --new-data D:\my-cp       # 建自己的数据根（骨架+模板+空索引/状态表）
python install.py --data-root D:\my-cp      # 让 config.json 指过去
```

### 配套：补题状态表

```bash
python tools/status_report.py    # 今天的队列：①待重写 ②待补题 ③D+7 复习 ④D+30 抽检
python tools/status_gui.py       # 图形端（Tkinter）
```

图形端键位：`1`~`6` 直接改状态 ｜ `Enter` 浮层 ｜ `Ctrl+Z` 连撤 ｜ `Shift+Enter` 开原题 ｜ `F11` 全屏。只动目标行、写前自动备份、非法状态拒写。

## 工具清单

| 脚本 | 干什么 |
|---|---|
| `install.py` | 安装助手：config.json / 环境体检 / 建新数据根 |
| `fetch_problem.py` | 抓牛客比赛题面 + 样例常量表（自动认场次号） |
| `new_round.py` | 新场次起手骨架（目录 + md 空壳，幂等不覆盖） |
| `verify.py` | 四档验证驱动：编译 → 样例 → 边界 → 对拍 → 极限 |
| `md_full.py` | 交付前复验：抽 **md 里贴着的那份代码** 四档全跑 |
| `check_solution.py` | 题解 md 的 17 项格式闸门（每项带行号原句） |
| `archive_check.py` | 归档对账，**退出码 0 = 归档完成** |
| `index_sync.py` | 索引两表自动生成（记录 md 是单一事实来源） |
| `status_report.py` / `status_gui.py` / `fill_knowledge.py` | 状态表三件套（报告 / 图形端 / 知识点列） |
| `vizgrid.py` | 终端字符画引擎（讲数据结构配「可跑的图」） |
| `unify_latex.py` / `unpair_ticks.py` / `extract_math.py` + `katex_check.js` | LaTeX 三件套（转换 / 去灰底 / KaTeX 真渲染） |
| `check_lost_by_hash.py` | 搬目录后的内容哈希对账 |

完整参考（每个脚本的设计取舍与坑）：[knowledge/10-工具链.md](knowledge/10-工具链.md)。

## 知识库（knowledge\，14 篇）

| 篇 | 内容 |
|---|---|
| 02-工作流 | 主干流程：分档 / 落盘结构 / 验证档位的唯一定义处 |
| 03-题解写法 / 05-数学LaTeX | 题解 md 的节模板白名单；数学一律 LaTeX |
| 04-验证协议 | 先钉基准、禁止同源互拍、验证工具自身怎么验 |
| 06-题解算法归档 / 09-已讲过概念清单 | 归档四处一起更新；跨场次「讲没讲过」台账 |
| 07-配图 / 08-从零讲 | 可跑的终端字符画；新概念从零讲的四段式 |
| 11-反面教材 | 已证伪的「实测记录」原文（不许生成结论的实据） |
| 12-算法坑集 / 13-环境准备 / 14-牛客抓取 | 实现坑合集；工具链安装；牛客页面结构 |
| 01-学习偏好 / 10-工具链 | 讲解风格约定；全部脚本的参考页 |

## 配置（config.json）

```json
{
  "data_root": "./demo",        // 数据根：题解/算法/索引/状态表都放这
  "backup_root": "./.backups",  // 备份根（改文件前自动备份到这里）
  "desktop_copy_dir": null      // 可选：交付 md 的桌面副本目录；null = 关
}
```

脚本不写死路径：环境变量 `AGENT_CP_TOOLS` 指向 `tools\`、`AGENT_CP_CONFIG` 指向别的 config.json 即可换布局。

## FAQ

**必须用 Claude Code 吗？** 不。任何能读文件 + 跑命令的 agent 都行（Codex / Cursor / 自建 agent）；AGENTS.md 就是给它们读的。人也可以照着六步手动跑。

**没有 g++ / node 能用吗？** 能。没有 g++ 时验证档如实降级为「未验证」（流程允许，但要写明）；node 只影响 KaTeX 公式渲染检查（第 17 项打「不适用」）。

**非 Windows 能用吗？** 脚本是纯 Python（标准库为主），核心流程跨平台；`status_gui.py` 与部分 `.cmd` 是 Windows 向的。路径都走 config，Linux/macOS 下把 `config.json` 指过去即可。

**公式渲染检查怎么装？** `cd tools && npm install katex`（可选）。

## 设计原则（为什么不直接让 agent「自由发挥」）

1. **机器闸门 > 嘱咐**：每条关键结论都对应一个退出码，不许「我觉得没错」。
2. **不许生成结论**：实测记录逐字来自实跑；没跑的档写「未验证」。
3. **记录与索引单一事实来源**：索引表由记录 md 生成（`index_sync.py`），不许手改。
4. **留证据**：翻车记录原样进《反面教材》，坑写成祈使句进《算法坑集》。
5. **耗材与资产的边界**：`.exe` / `_work\` / `__pycache__` 随手删；`.cpp` / `.py` / `.md` 只有主人点名才删。

## 自带示例

`demo\` 是**一场完整的数据**（牛客周赛 Round 163 的 B~G）：完整题解 md、每题代码、验证脚本（B 题演示框架写法 `verify_b.py`、F 题是自包含脚本）、6 份算法库记录、索引、状态表。它是这套流程的活样例——`install.py --check` 与 `archive_check.py Round163` 都直接对它跑。

## 目录结构

```
acm-agent-workflow\
├── AGENTS.md            ← 给 AI agent 的规则主干（10 条铁律）
├── README.md / README.en.md
├── LICENSE（MIT）
├── install.py           ← 安装助手
├── config.example.json
├── knowledge\           ← 知识库明细（14 篇）
├── tools\               ← 全部脚本
├── templates\           ← verify 驱动模板
└── demo\                ← 自带示例数据（Round 163）
```

## 贡献

Issue / PR 欢迎。改脚本前先跑一遍它对应的自检（多数脚本有 `--help`；`status_gui.py --selftest`、`selfcheck_unpair.py` 是现成的回归）。注意 `verify_<字母>.py` 验证驱动**没有 `--help`**——直接跑（不带参数）就是执行验证。

## License

[MIT](LICENSE)
