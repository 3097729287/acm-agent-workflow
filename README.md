# acm-agent-workflow

**算法竞赛的「题解 + 补题」流水线——从抓题面到归档，全程交给 AI agent，每一步都有机器闸门。**

不是「请 agent 认真一点」，而是**跑一条命令、看退出码**：验证数字逐字来自实跑，题解格式 18 项逐条查，归档对账退出码 0 才算完。你只负责 review。

[![ci](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml) [![release](https://img.shields.io/github/v/release/3097729287/acm-agent-workflow?include_prereleases&label=release)](https://github.com/3097729287/acm-agent-workflow/releases) ｜ [English](README.en.md) ｜ [在线文档](https://3097729287.github.io/acm-agent-workflow/) ｜ [MIT](LICENSE) ｜ **v0.1.0 早期演示版**，欢迎来 [Issues](https://github.com/3097729287/acm-agent-workflow/issues) 提意见

---

## 先选一条路

| 你是谁 | 从这里开始 | 花多久 |
|---|---|---|
| **竞赛选手**：想直接用，不想折腾 agent | [**路线 A：用起来**](#路线-a用起来) | 3 分钟 |
| **手里有 AI agent**（Claude Code / Codex / Cursor…） | [**路线 B：交给 agent**](#路线-b交给-ai-agent) | 一句话 |
| **要投稿题解 / 挂 CI / 改代码** | [**路线 C：投稿与开发**](#路线-c投稿与开发) | 按需 |
| 只想先看它**凭什么可信** | [四个闸门](#它凭什么可信四个闸门) | 1 分钟 |

## 路线 A：用起来

**不装 Python（Windows）：** 到 [Releases](https://github.com/3097729287/acm-agent-workflow/releases) 下载 `TimuZhuangtai-v0.1.0-win64.zip` → 解压 → 双击 `TimuZhuangtai.exe`。

一个窗口管你的《题目状态.md》：今天的补题队列、按 `1`~`6` 改状态（写前自动备份）、导入导出别人的题解包。包里自带示例数据，开箱即看；想打开**你自己的**数据，改包里的 `config.json`（见[配置](#配置configjson)）。

**有 Python 3.9+（Windows / macOS / Linux）：**

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow
python install.py                # 环境体检 + 拿自带示例把所有闸门跑一遍
python tools/status_report.py    # 今天的队列：①待重写 ②待补题 ③复习 ④抽检
python tools/status_gui.py       # 图形端
```

`status_report.py` 还能筛着问：`--todo --knowledge DP`（还没做出来的 DP 题）、`--status 未做,不会 --difficulty 1200-1600`。

图形端键位：`1`~`6` 直接改状态 ｜ `Enter` 浮层 ｜ `Ctrl+Z` 连撤 / `Ctrl+Y` 复原 ｜ `Ctrl+←`/`→` 换排序字段 ｜ `Ctrl+F` 跳搜索框 ｜ `Shift+Enter` 开原题 ｜ `F11` 全屏 ｜ 搜索框一个框搜六字段（场次 / 题号 / 题名 / 知识点 / 难度 / 状态）。只动目标行、写前自动备份、非法状态拒写。

想自己打一个 exe 带走（与命令行同一份代码，`TimuZhuangtai.exe --pack-check 包.zip` 这样带参数也能跑）：见 [docs/打包图形端exe.md](docs/打包图形端exe.md)。

<img src="docs/demo-gui.gif" width="900" alt="status_gui.py 实跑：按数字键改状态 → Ctrl+Z 连撤 → 打开原题与归档记录">

> 想让 agent 替你**写**题解、跑验证？往下走路线 B。

## 路线 B：交给 AI agent

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow
python install.py      # 只要 Python 3.9+，零第三方库；g++ / node 可选
```

用 agent 打开这个目录（Claude Code 直接 `cd` 进去就行），说一句话：

> 读仓库根目录的 AGENTS.md，然后处理这个比赛：`https://ac.nowcoder.com/acm/contest/<比赛号>`

（换成洛谷整场的 URL 一样认。）它会自己走完六步：

**抓题面 → 定档 → 写代码 + 验证驱动 → 四档验证 → 写题解 + 18 项自检 → 复验 + 归档对账**

你要看的只有两样：**它报的实测数字**（必须逐字来自实跑）和**退出码 0**。

<img src="docs/demo-install.gif" width="900" alt="安装脚本实跑：环境体检三行 + 示例闸门退出码 0">

每一步的产出落在哪里，见[一场跑完，盘上留下什么](#一场跑完盘上留下什么)。

**接自己的数据**（默认数据根是仓库自带的示例 `demo\`）：

```bash
python install.py --new-data D:\my-cp     # 建自己的数据根（骨架 + 模板 + 空索引 / 状态表）
python install.py --data-root D:\my-cp    # 让 config.json 指过去
```

## 路线 C：投稿与开发

**投稿一场题解。** 先导出题解包：

```bash
python tools/export_solution.py Round163     # → 牛客周赛Round163.zip
```

| 你的情况 | 怎么投 |
|---|---|
| 会 git | fork → 把 zip 放进 `contributions\` → 提 PR，CI 自动替你校验 |
| 不会 git | 加维护者 QQ **3660535264**（备注「题解投稿」）直接发；或把 zip 当附件发到 [Issues](https://github.com/3097729287/acm-agent-workflow/issues) |
| 连包都不会导 | 题解 md + 代码文件直接发过来，维护者替你打包 |

三条路**走同一个导入器、同一套校验，署名照留**。细节见 [CONTRIBUTING.md](CONTRIBUTING.md)。

**把格式闸挂到自己仓库**（GitHub Action，一行 `uses:`，题解不合格就变红）：

```yaml
- uses: actions/checkout@v4
- uses: 3097729287/acm-agent-workflow@main
  with:
    path: '题解/**/*.md'      # 哪些 md 是题解，你自己说（支持多个 / 目录 / glob）
```

不要求你的仓库长成这个仓库的样子。输入、退出码、依赖降级见 [docs/格式闸Action.md](docs/格式闸Action.md)。

**只想要题解质检 skill**（Claude Code）：

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cp -r acm-agent-workflow/skills/check-solution ~/.claude/skills/
```

装完说「对 我的题解.md 跑一遍题解质检」：18 项格式闸，每条问题带行号 + 原句（第 18 项＝目录表「考点」列必须是**知识点 v2 规范串**（与状态表「知识点」列同一套口径，口径出处 = `knowledge/15-知识点词典.md` 第五节））。见 [skills/check-solution/README.md](skills/check-solution/README.md)。

**改代码**：先跑对应自检（多数有 `--help`）：`status_gui.py --selftest`、`selfcheck_filter.py`、`selfcheck_import.py`、`check_contributions.py`、`knowledge_dict.py selftest`、`fetch_problem.py --selftest`。注意 `verify_<字母>.py` 验证驱动**没有 `--help`**——直接跑就是执行验证。

## 它凭什么可信：四个闸门

| 闸门 | 命令 | 通过 = |
|---|---|---|
| 验证闸 | `verify_<字母>.py` | 四档（样例 / 边界 / 对拍 / 极限）逐档给出**实测数字** |
| 格式闸 | `check_solution.py <md>` | 18 项全过，每项附行号原句 |
| 归档闸 | `archive_check.py RoundNNN` | **退出码 0** = 算法库 / 索引 / 知识库四处对账一致 |
| 安装闸 | `python install.py --check` | 拿自带示例把所有闸门跑一遍（只体检，不写任何文件） |

两条硬规矩：**实测记录不许生成**——没跑的档如实写「未验证」，仓库里留着一份[反面教材](knowledge/11-反面教材.md)，就是写得像真的、复跑第一组就翻车的记录；**索引不许手改**——索引表由记录 md 生成（`index_sync.py`），单一事实来源。

## 自带示例

`demo\` 是两场**真实**数据：牛客周赛 Round 163（完整一场）+ Round 161 的 C~E（迷你一场，演示跨场次台账）。clone 下来就能跑：

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

<img src="docs/demo-verify.gif" width="900" alt="verify_b.py 实跑：编译 / 样例 / 边界 / 对拍 / 极限五段全过">

（上面的输出逐字来自实跑，秒数随机器的快慢浮动，以你自己机器上的实跑为准。）

`examples\` 里还有一份**故意做坏的反例**：同一把格式闸跑上去当场报 8 项红、退出码 1——闸门拦得住什么，跑一次就看见。

这套流程不是演示稿：**9 场牛客周赛走过六步，43 道题在状态表里逐题流转，57 份归档记录覆盖 31 个算法文件夹**（截至 2026-10-03）。

---

# 技术信息

## 一场跑完，盘上留下什么

| 步骤 | agent 会跑 | 产出 | 闸门 |
|---|---|---|---|
| ① 抓题面 | `python tools/fetch_problem.py <URL>`（牛客 / 洛谷都认） | `RoundN\_work\` 下的题面 / 样例 + 难度分档建议 | 抓取数 == 题目数 |
| ② 定档 | 查《已讲过概念清单》+ 分档表 | 每题讲什么、讲多深 | — |
| ③ 写代码 | 每题一个目录 `RoundN\<区间>\<字母>\` | `x.cpp` + `x_brute.cpp` + `verify_x.py` | — |
| ④ 验证 | `python verify_x.py` | 四档实测数字 | 全过且数字来自实跑 |
| ⑤ 写题解 + 自检 | `python tools/check_solution.py <md>` | `RoundN题解.md` | 18 项全过 |
| ⑥ 复验 + 归档 | `python tools/md_full.py <md> <字母>` → `archive_check.py RoundN` | 算法库记录 / 索引 / 状态表 | **退出码 0** |

<img src="docs/demo-gates.gif" width="900" alt="check_solution.py 实跑：逐条通过、结论 0 项有问题">

一场一个自包含文件夹：

```
<数据根>\
├── 题解\牛客周赛\RoundN\
│   ├── RoundN题解.md            ← 交付 md（节模板白名单）
│   ├── <区间>\<字母>\            ← 每题：正解 + 暴力 + 验证驱动 + 可选配图脚本
│   └── _work\                   ← 耗材（题面 / 样例），可随手删、重抓即回来
├── 算法\                        ← 归档：按主算法分文件夹，一题一份精简记录
├── 索引\题解算法索引.md          ← 全量索引（场次小节由脚本生成）
└── 题解\题目状态.md              ← 补题状态表
```

## 题解包：导入 / 导出

题解包 = 「一场题解 + 算法归档」的可搬格式，包内文件逐字节可往返（`selfcheck_import.py` 验的就是这个）。

```bash
python tools/export_solution.py Round163              # → 牛客周赛Round163.zip
python tools/export_solution.py Round163-G -o G.zip   # 只要一题

python tools/import_solution.py 牛客周赛Round163.zip          # 先看校验报告（不动盘）
python tools/import_solution.py 牛客周赛Round163.zip --apply  # 落盘 + 串齿轮 + 对账
```

`--apply` 的自动链条：复制文件 → 补索引反查表 → 写题解指针 → 更新状态表（新题默认「未做」）→ 生成索引场次小节 → 刷「知识点」列 → **`archive_check.py` 退出码 0**。**退出码 0 才算收完**，不是「文件复制过去了」就算。

两条口径：**知识点名字有唯一词典**（`knowledge\15-知识点词典.md`）——同一个概念的两种写法（`状态压缩DP` ≡ `状压 DP`）在导入导出两侧都自动归一，索引列不会裂成两半；**没登记的名字不拦、照收**，只在报告里出一份「待登记清单」（附最接近的标准名建议）。打回只有硬伤：字段缺 / 文件名认不出 / 格式闸不过 / 会覆盖已有文件。

不碰命令行也行：图形端菜单「题解包」= **导入 / 导出**，选包 → 出报告 → 点「应用到数据根」才真落盘（导入本来就先跑 dry 校验；目录包走命令行 `--pack-import`）。

## 工具清单

| 脚本 | 干什么 |
|---|---|
| `install.py` | 安装助手：config.json / 环境体检 / 建新数据根 |
| `fetch_problem.py` | 抓题面 + 样例常量表：牛客整场（自动认场次号）/ 洛谷整场或单题；`--selftest` 离线复跑解析链 |
| `new_round.py` | 新场次起手骨架（目录 + md 空壳，幂等不覆盖） |
| `verify.py` | 四档验证驱动：编译 → 样例 → 边界 → 对拍 → 极限 |
| `md_full.py` | 交付前复验：抽 **md 里贴着的那份代码** 四档全跑 |
| `check_solution.py` | 题解 md 的 18 项格式闸门（每项带行号原句；第 18 项＝目录表「考点」列必须是**知识点 v2 规范串**（与状态表「知识点」列同一套口径，口径出处 = `knowledge/15-知识点词典.md` 第五节）） |
| `archive_check.py` | 归档对账，**退出码 0 = 归档完成** |
| `index_sync.py` | 索引两表自动生成（记录 md 是单一事实来源） |
| `status_report.py` / `status_gui.py` / `fill_knowledge.py` | 状态表三件套（报告 + 筛选 / 图形端 / 知识点列） |
| `selfcheck_filter.py` | 筛选逻辑的机器闸门（28 组单元断言 + 20 组命令行端到端命中集合） |
| `export_solution.py` / `import_solution.py` | **题解包**：导出一场（或一题）给别人 / 收下别人的包 |
| `knowledge_dict.py` | 知识点词典的解析与查询（标准名 / 别名 / 未登记建议） |
| `selfcheck_import.py` | 导入导出的机器闸门（往返无损 + 未登记照收） |
| `check_contributions.py` | 投稿包校验：`contributions\` 里每个包在临时空数据根里 `import --dry` 一遍（CI 跑） |
| `skills/check-solution` | 题解质检 skill：把 18 项格式闸包成「clone 下来就能用」 |
| `vizgrid.py` | 终端字符画引擎（讲数据结构配「可跑的图」） |
| `unify_latex.py` / `unpair_ticks.py` / `unpair_ticks_relaxed.py` / `extract_math.py` + `katex_check.js` | LaTeX 工具（转换 / 去灰底 / KaTeX 真渲染） |
| `check_lost_by_hash.py` | 搬目录后的内容哈希对账（按文件名比对会骗人） |
| `lfcheck.py` | 行尾 / BOM 规范化检查 |

每个脚本的设计取舍与坑，见 [knowledge/10-工具链.md](knowledge/10-工具链.md)。

## 配置（config.json）

```json
{
  "data_root": "./demo",        // 数据根：题解 / 算法 / 索引 / 状态表都放这
  "backup_root": "./.backups",  // 备份根（改文件前自动备份到这里）
  "desktop_copy_dir": null      // 可选：交付 md 的桌面副本目录；null = 关
}
```

脚本不写死路径：环境变量 `AGENT_CP_TOOLS` 指向 `tools\`、`AGENT_CP_CONFIG` 指向别的 config.json 即可换布局。

## 知识库

`knowledge\` 是规则明细（16 篇），根目录的 `AGENTS.md` 只写主干，agent 按需取用。

| 篇 | 内容 |
|---|---|
| 02-工作流 | 主干流程：分档 / 落盘结构 / 验证档位的唯一定义处 |
| 03-题解写法 / 05-数学LaTeX | 题解 md 的节模板白名单；数学一律 LaTeX |
| 04-验证协议 | 先钉基准、禁止同源互拍、验证工具自身怎么验 |
| 06-题解算法归档 / 09-已讲过概念清单 | 归档四处一起更新；跨场次「讲没讲过」台账 |
| 07-配图 / 08-从零讲 | 可跑的终端字符画；新概念从零讲的四段式 |
| 11-反面教材 | 已证伪的「实测记录」原文（不许生成结论的实据） |
| 12-算法坑集 / 13-环境准备 / 14-牛客抓取 / 16-洛谷抓取 | 实现坑合集；工具链安装；两个站的页面结构与抓取配方（含题面里的提示注入怎么处理） |
| 15-知识点词典 | **知识点名字的唯一出处**：标准名 / 文件夹 / 别名 / 已定稿写法 |
| 01-学习偏好 / 10-工具链 | 讲解风格约定；全部脚本的参考页 |

## 平台与 CI

核心流程三平台 CI 全绿（Ubuntu / macOS / Windows × Python 3.9 / 3.13）：环境体检、示例闸门、索引同步、词典自检、抓取解析自检跑满六格；四档复验、18 项格式闸（含 KaTeX 渲染）、反例必须被拦、Action 入口三条退出码跑 Linux + 3.13 一格；题解包导入导出与投稿校验跑 Linux / Windows + 3.13。

`status_gui.py` 图形端与部分 `.cmd` 是 Windows 向；图形端在 Linux 上若提示缺 tkinter，装 `python3-tk` 即可。路径都走 config，指过去就行。

## FAQ

**必须用 Claude Code 吗？** 不。任何能读文件 + 跑命令的 agent 都行（Codex / Cursor / 自建 agent）；AGENTS.md 就是给它们读的。人也可以照着六步手动跑。

**没有 g++ / node 能用吗？** 能。没 g++ 时验证档如实降级为「未验证」（流程允许，但要写明）；node 只影响 KaTeX 公式渲染检查（第 17 项打「不适用」）。装法：`cd tools && npm install katex`。

**考试/训练数据会传出去吗？** 不会。数据根在你自己的机器上，仓库里只有示例；网络访问只发生在抓题面（牛客 / 洛谷）和可选的 KaTeX 渲染。

## 设计原则

1. **机器闸门 > 嘱咐**：每条关键结论都对应一个退出码，不许「我觉得没错」。
2. **不许生成结论**：实测记录逐字来自实跑；没跑的档写「未验证」。
3. **单一事实来源**：索引表由记录 md 生成，不许手改。
4. **留证据**：翻车记录原样进《反面教材》，坑写成祈使句进《算法坑集》。
5. **耗材与资产的边界**：`.exe` / `_work\` / `__pycache__` 随手删；`.cpp` / `.py` / `.md` 只有主人点名才删。

## 目录结构

```
acm-agent-workflow\
├── AGENTS.md            ← 给 AI agent 的规则主干（11 条铁律）
├── README.md / README.en.md
├── CONTRIBUTING.md      ← 怎么投稿一场自己的题解（三条路径 / 包格式）
├── install.py           ← 安装助手（config.json / 体检 / 建新数据根）
├── config.example.json
├── knowledge\           ← 知识库明细（16 篇）
├── tools\               ← 全部脚本
├── templates\           ← verify 驱动模板
├── skills\              ← check-solution：题解质检闸（复制到 ~/.claude/skills/ 即用）
├── docs\                ← 格式闸 Action / 打包 exe / 图形端布局说明 + 文档站
├── contributions\       ← 投稿投递箱（放进包提 PR，CI 自动校验）
├── 题库\                ← 发布用的数据根（结构同 demo\）
├── examples\            ← 可跑反例（故意做坏的题解，闸门当场报红）+ 洛谷抓取回归 fixture
└── demo\                ← 自带示例数据（Round 163 全场 + Round 161 的 C~E）
```

## 联系与投稿

- **QQ：3660535264**（备注「题解投稿」）——最省事的投稿路径：把 `export_solution.py` 导出的题解包 zip 拖进聊天窗口就行；不会导出也没关系，题解 md、代码文件直接发，我这边替你打包。讨论题、报 bug、提建议也欢迎加。
- 不想加 QQ 的话，[Issues](https://github.com/3097729287/acm-agent-workflow/issues) / PR 照旧。

## License

[MIT](LICENSE)
