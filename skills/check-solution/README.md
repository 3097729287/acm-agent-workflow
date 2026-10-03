# check-solution：题解格式闸（Claude Code skill）

对你写的题解 md 跑一遍 **17 项格式检查**（LaTeX 配对与完整度、公式真渲染、代码块真编译、节结构白名单、
目录表、表格竖线、编码行尾、实测记录…），每条问题都带**行号 + 原句**。不需要先懂这个项目。

## 1. 装

```bash
git clone https://github.com/3097729287/acm-agent-workflow             # 还没有仓库的话
mkdir -p ~/.claude/skills && cp -r acm-agent-workflow/skills/check-solution ~/.claude/skills/
# Windows 等价：xcopy /E /I skills\check-solution %USERPROFILE%\.claude\skills\check-solution
```

只想给某一个项目用，就复制到那个项目的 `.claude/skills/` 下。已经开着的 Claude Code 会话里打
`/reload-skills` 拾起它（还看不到就重开会话）。

## 2. 用

在 Claude Code 里说一句就行：

> 对 `<你的题解.md>` 跑一遍题解质检

不想经过 agent，也可以直接跑（在克隆下来的仓库里）：

```bash
python skills/check-solution/gate.py <你的题解.md>            # 完整 17 项
python skills/check-solution/gate.py <你的题解.md> --no-compile   # 只看格式、不编译，快
```

单题题解 / 专题长文（不是「整场题解」那种带目录表和多道题的）加 `--no-record`，跳过整场专有的那几项。
换过仓库位置或复制出去用了，加 `--repo <仓库根>`；脚本找不到仓库时会自己打印三种解法。

## 3. 看结果

末行「**结论：全部通过**」且退出码 `0` = 过闸；「**★有问题，改完再交付★**」且退出码 `1` = 没过，
上面的每一条都指着行号，照着改完再跑一遍。`[不适用]` 不是通过——那几项是**没装工具**（g++ 管代码编译、
Node+katex 管公式渲染）或者**被开关跳过**了。

---

需要 Python 3.9+（只用标准库）；g++ 和 Node+katex 可选，缺了只影响对应的那一两项。
17 项各自的判定口径与修法见同目录 `SKILL.md`，细节见仓库 `knowledge/` 与 `tools/check_solution.py --list`。
