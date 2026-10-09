# check-solution：题解格式闸（Claude Code skill）

给交题解前想跑机器检查的人：对题解 md 跑 **18 项格式检查**（LaTeX 配对与完整度、公式真渲染、代码块真编译、
节结构白名单、目录表、表格竖线、编码行尾、实测记录…），每条问题都带**行号 + 原句**。不需要先懂这个项目。
第 18 项＝目录表「考点」列必须是**知识点 v2 规范串**（与状态表「知识点」列同一套口径，口径出处 = `knowledge/15-知识点词典.md` 第五节）。

**装**（复制到 `~/.claude/skills/`；开着的会话打 `/reload-skills`，还看不到就重开会话。只想给单个项目用就放它的 `.claude/skills/`）：

```bash
git clone https://github.com/3097729287/acm-agent-workflow             # 还没有仓库的话
mkdir -p ~/.claude/skills && cp -r acm-agent-workflow/skills/check-solution ~/.claude/skills/
# Windows 等价：xcopy /E /I skills\check-solution %USERPROFILE%\.claude\skills\check-solution
```

**用**：在 Claude Code 里说「对 `<你的题解.md>` 跑一遍题解质检」，或直接跑（在克隆下来的仓库里）：

```bash
python skills/check-solution/gate.py <你的题解.md>                # 完整 18 项
python skills/check-solution/gate.py <你的题解.md> --no-compile   # 只看格式、不编译，快
python skills/check-solution/gate.py <你的题解.md> --no-record    # 单题 / 专题文档：跳过 6 / 9 / 10 / 11 / 18 项
# 换过仓库位置 / 复制出去用了：加 --repo <仓库根>；找不到仓库时脚本会打印三种解法
```

**看结果**：「结论：全部通过」+ 退出码 `0` = 过闸；「★有问题，改完再交付★」+ 退出码 `1` = 没过，每条带行号 + 原句，照改重跑。
`[不适用]` 不是通过：没装 g++（管编译）/ Node+katex（管渲染），或被开关跳过；逐项修法与规范细节见同目录 `SKILL.md`（全文在仓库 `knowledge/`），判定口径见 `python tools/check_solution.py --list`。

**整包质检**（含 `manifest.json` 的目录或 zip）：用导入器的 dry 模式 `python tools/import_solution.py <包>`
（只校验 + 出报告、不动盘，顺带对包内每份 md 跑同一套 18 项闸门；在仓库根跑）。

需要 Python 3.9+（**只用标准库**，零 pip 依赖）；g++ 与 Node+katex 可选，缺了只影响对应项。
另一个入口 = GitHub Action（挂到任意仓库 CI，push 即跑，规则与 skill 同源）：[../../docs/格式闸Action.md](../../docs/格式闸Action.md)。
