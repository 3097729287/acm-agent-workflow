# acm-agent-workflow

**给 AI agent 用的算法竞赛「题解 + 补题」流水线。** 把「写完题解就烂尾」变成一条有机器闸门的流水线：抓题面 → 写代码 → 四档验证 → 生成题解 → 格式自检 → 归档对账，外加一个跟踪每道题掌握程度的状态表（带图形端）。

[![ci](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml) [![release](https://img.shields.io/github/v/release/3097729287/acm-agent-workflow?include_prereleases&label=release)](https://github.com/3097729287/acm-agent-workflow/releases) ｜ [English](README.en.md) ｜ Windows 优先（图形端）｜ 核心流程三平台 CI 全绿：Ubuntu / macOS / Windows × Python 3.9 / 3.13 ｜ MIT License ｜ 当前为 **v0.1.0 早期演示版**，欢迎来 [Issues](https://github.com/3097729287/acm-agent-workflow/issues) 提意见

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

## 战绩

这套流程不是演示稿，是一直在跑的日常流水线（截至 2026-10-03 的统计）：

- **9 场牛客周赛**（Round 123 ~ 163）全程走六步，其中 Round 163（完整一场）与 Round 161 的 C~E（迷你一场，演示跨场次台账）收进了本仓库 `demo\`；
- **43 道题**在补题状态表里逐题流转（不会 → 待重写 → 复现 AC → 独立 AC → 巩固）；
- **32 个**四档验证驱动随时代码可复跑；
- 算法库归档 **57 份记录**、覆盖 **31 个算法文件夹**。

## 快速开始（5 分钟）

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow

python install.py           # 生成 config.json（默认指向自带示例）+ 环境体检 + 跑示例闸门
```

体检通过会看到：Python / g++ / node 三行，以及 **示例闸门退出码 0**（`archive_check.py` 把自带的两场示例数据各对了一遍账）。

```
  Python      3.14.7  OK
  g++         g++ (Rev4, Built by MSYS2 project) 16.2.0  OK
  node        v24.18.1  OK
  数据根      <仓库路径>/demo
  == 示例闸门：archive_check.py Round163（自带示例数据）==
  [通过] Round163 退出码 0（0 = 四处对账通过）
  == 示例闸门：archive_check.py Round161（自带示例数据）==
  [通过] Round161 退出码 0（0 = 四处对账通过）
```

（g++ 与 node 都是可选的：没有 g++ 时验证档如实写「未验证」，node 只影响 KaTeX 公式渲染检查。）

<img src="docs/demo-install.gif" width="900" alt="python install.py --check 实跑：环境体检三行 + 示例闸门退出码 0">

然后亲手跑一遍四档验证（仓库里就带着两场示例：牛客周赛 Round 163 完整一场，Round 161 的 C~E 迷你一场）：

```bash
python demo/题解/牛客周赛/Round163/B-G/B/verify_b.py
python demo/题解/牛客周赛/Round161/A-F/C/verify_c.py
```

```
  编译       通过     通过（无警告）
  官方样例     通过     3 组全过
  边界用例     通过     9 条全过
  随机对拍     通过     500 组全一致
  极限计时     通过     极限：|x|=8×10^5 全零串, k=10^5 0.007 s、极限：|x|=8×10^5 随机十六进制, k=10^5 0.007 s
```

（上面的输出是逐字实测结果；秒数随机器的快慢浮动，以你自己机器上的实跑为准。）

<img src="docs/demo-verify.gif" width="900" alt="verify_b.py 实跑：编译 / 样例 / 边界 / 对拍 / 极限五段全过">

## 使用教程：完整跑一场比赛

### 第 0 步：让 agent 读规则

把仓库给 agent（Claude Code 直接打开这个目录），然后说：

> 读仓库根目录的 AGENTS.md，然后处理这个比赛：`https://ac.nowcoder.com/acm/contest/<比赛号>`

`AGENTS.md` 是规则的**主干**（11 条铁律 + 索引表），明细全在 `knowledge\`（16 篇），agent 按需取用。

### 六步流水线

| 步骤 | 命令（agent 自己会跑） | 产出 | 闸门 |
|---|---|---|---|
| ① 抓题面 | `python tools/fetch_problem.py <URL>`（牛客 / 洛谷都认） | `RoundN\_work\` 下的题面 / 样例常量表 + 难度分档建议 | 抓取数 == 题目数 |
| ② 定档 | （agent 查《已讲过概念清单》+ 分档表） | 每题讲什么、讲多深 | — |
| ③ 写代码 | 每题一个目录 `RoundN\<区间>\<字母>\` | `x.cpp` + `x_brute.cpp` + `verify_x.py` | — |
| ④ 验证 | `python verify_x.py` | 四档实测数字 | 全过且数字来自实跑 |
| ⑤ 写题解 + 自检 | `python tools/check_solution.py <md>` | `RoundN题解.md` | 17 项全过 |
| ⑥ 复验 + 归档 | `python tools/md_full.py <md> <字母>` → `archive_check.py RoundN` | 算法库记录 / 索引 / 状态表 | **退出码 0** |

<img src="docs/demo-gates.gif" width="900" alt="check_solution.py 实跑：17 项逐条通过、结论 0 项有问题">

一场一个自包含文件夹，落盘结构：

```
<数据根>\
├── 题解\牛客周赛\RoundN\        ← demo 里是 Round163（全场）+ Round161（C~E 迷你场）
│   ├── RoundN题解.md            ← 交付 md（节模板白名单）
│   ├── <区间>\<字母>\            ← 每题：正解 + 暴力 + 验证驱动 + 可选配图脚本
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
python tools/status_report.py --todo --knowledge DP          # 换个问法：还没做出来的 DP 题
python tools/status_report.py --status 未做,不会 --difficulty 1200-1600
python tools/status_gui.py       # 图形端（Tkinter）
```

筛选（`--knowledge` / `--status` / `--difficulty`，三条 AND）= 命令行的「筛出 N 题」清单，
图形端筛选**引的是同一份实现** —— 两边同条件必然同一份结果。

图形端键位：`1`~`6` 直接改状态 ｜ `Enter` 浮层 ｜ `Ctrl+Z` 连撤 ｜ `Shift+Enter` 开原题 ｜ `F11` 全屏 ｜ 搜索框 `↓` 展开筛选面板（知识点 / 难度 / 状态多选）。只动目标行、写前自动备份、非法状态拒写。

想改界面？每个部位的标准叫法（第一行 / 筛选面板 / 选包窗 / 报告窗…）见 [docs/status_gui-布局说明.md](docs/status_gui-布局说明.md)，照那个名字提需求就行。

<img src="docs/demo-gui.gif" width="900" alt="status_gui.py 实跑：按数字键改状态 → Ctrl+Z 连撤 → 打开原题与归档记录">

## 题解共享：一场题解的导入 / 导出

题解不该只躺在自己硬盘里。**题解包**是「一场题解 + 算法归档」的可搬格式——
你用 agent 跑完六步，一条命令打包；别人下载后一条命令收进自己的数据根，
索引、状态表、已讲过概念台账**自动跟上**。

```bash
python tools/export_solution.py Round163              # → 牛客周赛Round163.zip
python tools/export_solution.py Round163-G -o G.zip   # 只要一题

python tools/import_solution.py 牛客周赛Round163.zip          # 先看校验报告（不动盘）
python tools/import_solution.py 牛客周赛Round163.zip --apply  # 落盘 + 串齿轮 + 对账
```

导入后的自动链条：复制文件 → 补索引反查表 → 写题解指针 → 更新状态表（新题默认「未做」）
→ 生成索引场次小节 → 刷「知识点」列 → **`archive_check.py` 退出码 0**。
**退出码 0 才算收完**，不是「文件复制过去了」就算。

两条口径值得单说：

- **知识点名字有唯一词典**（`knowledge\15-知识点词典.md`，42 个标准名 / 35 个可归档文件夹 / 别名表）。
  同一个东西的两种写法（`状态压缩DP` ≡ `状压 DP`）在导入导出两侧都自动换成标准名——
  「我写的」和「别人传的」在索引里永远同一个名字，索引列不会裂成两半。
- **没登记的名字不拦、照收**。打回只有硬伤（字段缺、文件名认不出、格式闸不过、会覆盖已有文件）；
  词典里查不到的名字**原样落盘**，同时在报告里出一份**「待登记清单」**（附最接近的标准名建议），
  合并时一次性收编。上传的人不会因为「名字没对齐」被拒之门外。

包内文件逐字节可往返（`python tools/selfcheck_import.py` 就是验这个：导出 → 导入空数据根 →
逐文件 sha256 比对 + 对账退出码 0；另有一项专门验「未登记名字照收」）。

### 不碰命令行的话：图形端三个入口

`status_gui.py` 菜单「题解包」= **导入题解包… / 导出题解包… / 一键校验…** ——
选包 → 后台出报告 → 点「应用到数据根」才真落盘。图形端可以打包成单文件 exe
（[docs/打包图形端exe.md](docs/打包图形端exe.md)），它与命令行**同一份代码、同一套 argv**
（`TimuZhuangtai.exe --pack-check 包.zip` 也能跑）。

想把自己的一场题解**投给这个仓库**：见 [CONTRIBUTING.md](CONTRIBUTING.md) ——
把导出的包放进 `contributions\` 提 PR，CI 会替维护者把每个包先校验一遍；
收下的包导进 `题库\`（发布用的数据根，结构与 `demo\` 一样），投递箱随之清空。

## 把格式闸挂到你自己的仓库（GitHub Action）

同一个 17 项格式闸，也能当 GitHub Action 用——一行 `uses:` 挂到**你自己**仓库的 CI 上，
题解不合格就变红：

```yaml
- uses: actions/checkout@v4
- uses: 3097729287/acm-agent-workflow@main
  with:
    path: '题解/**/*.md'      # 哪些 md 是题解，你自己说（支持多个 / 目录 / glob）
```

不要求你的仓库长成这个仓库的样子。输入、退出码、依赖降级（没 g++ / 没 katex 会如实降级而不是误报）
与本地预演办法见 [docs/格式闸Action.md](docs/格式闸Action.md)。

## 工具清单

| 脚本 | 干什么 |
|---|---|
| `install.py` | 安装助手：config.json / 环境体检 / 建新数据根 |
| `fetch_problem.py` | 抓题面 + 样例常量表（**站点适配表**）：牛客整场（自动认场次号）/ 洛谷整场或单题；`--selftest` 离线复跑解析链 |
| `new_round.py` | 新场次起手骨架（目录 + md 空壳，幂等不覆盖） |
| `verify.py` | 四档验证驱动：编译 → 样例 → 边界 → 对拍 → 极限 |
| `md_full.py` | 交付前复验：抽 **md 里贴着的那份代码** 四档全跑 |
| `check_solution.py` | 题解 md 的 17 项格式闸门（每项带行号原句） |
| `archive_check.py` | 归档对账，**退出码 0 = 归档完成** |
| `index_sync.py` | 索引两表自动生成（记录 md 是单一事实来源） |
| `status_report.py` / `status_gui.py` / `fill_knowledge.py` | 状态表三件套（报告 + 筛选 / 图形端 / 知识点列） |
| `selfcheck_filter.py` | 筛选逻辑的机器闸门（28 组单元断言 + 20 组命令行端到端命中集合） |
| `export_solution.py` / `import_solution.py` | **题解包**：导出一场（或一题）给别人 / 收下别人的包（见下节） |
| `knowledge_dict.py` | 知识点词典的解析与查询（标准名 / 别名 / 未登记建议） |
| `selfcheck_import.py` | 导入导出的机器闸门（往返无损 + 未登记照收） |
| `check_contributions.py` | 投稿包校验：`contributions\` 里每个包在临时空数据根里 `import --dry` 一遍（CI 跑） |
| `skills/check-solution` | 题解质检 skill：把 17 项格式闸包成「clone 下来就能用」（见该目录 README） |
| `vizgrid.py` | 终端字符画引擎（讲数据结构配「可跑的图」） |
| `unify_latex.py` / `unpair_ticks.py` / `extract_math.py` + `katex_check.js` | LaTeX 三件套（转换 / 去灰底 / KaTeX 真渲染） |
| `check_lost_by_hash.py` | 搬目录后的内容哈希对账 |

完整参考（每个脚本的设计取舍与坑）：[knowledge/10-工具链.md](knowledge/10-工具链.md)。

## 知识库（knowledge\，16 篇）

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

**非 Windows 能用吗？** 核心流程三平台 CI 全绿（Ubuntu / macOS / Windows × Python 3.9 / 3.13，见顶部徽章）：环境体检、示例闸门、索引同步、四档复验、17 项格式闸都在 Linux/macOS 上跑过。`status_gui.py` 的图形端与部分 `.cmd` 是 Windows 向的。路径都走 config，指过去即可。

**公式渲染检查怎么装？** `cd tools && npm install katex`（可选）。

## 设计原则（为什么不直接让 agent「自由发挥」）

1. **机器闸门 > 嘱咐**：每条关键结论都对应一个退出码，不许「我觉得没错」。
2. **不许生成结论**：实测记录逐字来自实跑；没跑的档写「未验证」。
3. **记录与索引单一事实来源**：索引表由记录 md 生成（`index_sync.py`），不许手改。
4. **留证据**：翻车记录原样进《反面教材》，坑写成祈使句进《算法坑集》。
5. **耗材与资产的边界**：`.exe` / `_work\` / `__pycache__` 随手删；`.cpp` / `.py` / `.md` 只有主人点名才删。

## 自带示例

`demo\` 是**两场数据**：牛客周赛 Round 163 的 B~G（完整一场，题解 md、每题代码、验证脚本——B 题演示框架写法 `verify_b.py`、F 题是自包含脚本）、以及 Round 161 的 C~E（迷你一场，三题都配框架写法验证驱动）。合起来 9 份算法库记录、索引、状态表。它是这套流程的活样例——`install.py --check` 与 `archive_check.py Round163` / `Round161` 都直接对它跑。

第二场不只是凑数：它演示**跨场次台账**怎么落——同一批算法文件夹里进来第二场的记录后，《已讲过概念清单》要按「首次出现取最早那场」登记新从零讲的概念，并把「还没讲过」表里被讲掉的那条划掉（`knowledge\09-已讲过概念清单.md` 里能看到真实写法）。

另配一份**故意做坏的反例**（`examples\`）：同一把格式闸跑上去当场报 8 项红、退出码 1——闸门到底拦得住什么，跑一次就看见。`examples\luogu\` 是另一类：抓题面工具的**原始返回 + 落盘产物**，给 `fetch_problem.py --selftest` 做不联网的逐字回归。

## 目录结构

```
acm-agent-workflow\
├── AGENTS.md            ← 给 AI agent 的规则主干（11 条铁律）
├── README.md / README.en.md
├── LICENSE（MIT）
├── CONTRIBUTING.md      ← 怎么投稿一场自己的题解（两条路径 / 包格式）
├── install.py           ← 安装助手
├── config.example.json
├── knowledge\           ← 知识库明细（16 篇）
├── tools\               ← 全部脚本
├── templates\           ← verify 驱动模板
├── skills\              ← 技能包（check-solution：题解质检闸，复制到 ~/.claude/skills/ 即用）
├── docs\                ← 打包图形端 exe 等说明
├── contributions\       ← 投稿投递箱（放进包提 PR，CI 自动校验）
├── 题库\                ← 发布用的数据根骨架（结构同 demo\）
├── examples\            ← 可跑反例（故意做坏的题解，闸门当场报红）+ 洛谷抓取回归 fixture
└── demo\                ← 自带示例数据（Round 163 全场 + Round 161 的 C~E）
```

## 贡献

Issue / PR 欢迎；想投稿自己的题解，见 [CONTRIBUTING.md](CONTRIBUTING.md)（把导出的包放进 `contributions\` 提 PR，CI 会先替你把包校验一遍）。改脚本前先跑一遍它对应的自检（多数脚本有 `--help`；`status_gui.py --selftest`、`selfcheck_filter.py`、`selfcheck_import.py`、`check_contributions.py`、`knowledge_dict.py selftest`、`fetch_problem.py --selftest` 是现成的回归）。注意 `verify_<字母>.py` 验证驱动**没有 `--help`**——直接跑（不带参数）就是执行验证。

## License

[MIT](LICENSE)
