# 贡献指南（题解共享库）

谢谢你愿意把自己的题解放进来。这里的规矩只有一条：**一切以机器闸门为准**——
你本地跑过、CI 跑过、维护者合并时再跑一次，三道都是同一条命令，不存在「看人下菜」。

## 两条路径，挑一条

| | 路径 A：会 git | 路径 B：不会 git（或不想折腾） |
|---|---|---|
| 怎么传 | fork → 把包放进 `contributions\` → 提 PR | 把包当附件发到 [Issues](https://github.com/3097729287/acm-agent-workflow/issues) |
| 谁跑校验 | CI 自动跑（PR 里每个包都校验，不通过变红） | 维护者收到后本地跑同一条命令 |
| 你的收益 | PR 记录 + 署名进 manifest | 署名进 manifest |

两条路最终**走同一个导入器、同一套校验**——「合并」永远是维护者按一次键的事。

## 第 1 步：把你这场题解打包

包里装什么、manifest 每个字段什么含义，见设计文档第二节（`manifest.json` 十一行、人可读可手写）。
最小可用的一条命令是现成的导出器：

```bash
python tools/export_solution.py Round163        # 整场 → 牛客周赛Round163.zip
python tools/export_solution.py Round163-G      # 或只导出 G 一题
-o 输出.zip        # 指定输出位置（缺省 = 当前目录）
--contributor 名字 # 署名（缺省取 git config user.name）
```

导出器会自动做三件事，你不用管：**过滤耗材**（`_work\` / `__pycache__` / `.exe` / `.png` / `.bak`
不进包）、**别名规范化**（记录 md 里的非标准知识点名换成词典标准名）、**写 manifest**
（题面各字段抄自算法库记录 md 头部——单一事实来源）。

手写包也收：只要目录里有 `manifest.json` 和 `题解\` 那棵树，格式对就行。

## 第 2 步：提交前自己跑一遍

```bash
python tools/check_contributions.py --pack 你的包.zip
```

| 退出码 | 意思 | 怎么办 |
|---|---|---|
| 0 | 合格 | 往下走 |
| 1 | 有硬伤 | 报告里逐项写了行号 / 原因，改完重打 |
| 2 | 读不了 | 多半不是 zip、或者缺 `manifest.json` |

常见硬伤（都是**打回**级）：

- manifest 字段缺 / 拼错（`difficulty` 要写成 `CF 900` 这样）；
- 题解 md 没过 17 项格式闸（`python tools/check_solution.py <md>` 能看逐项行号）；
- 目标位置已经有同一题（防覆盖）；
- `url` 不是这道题的牛客链接（末尾字母要和 `letter` 对得上）。

**不会被打回的**（放心）：知识点 / 文件夹名不在词典里——照收，只在报告里列进「待登记清单」，
维护者合并时收编；**算法记录可以不写全文**——缺了会生成「精简记录」（头部齐、正文标注
「未附」，见设计文档 2.3）；**四档验证记录也可以不附**——题解 md 的实测记录节会按现有口径
写「未附验证记录」。

## 第 3 步：交出去

**路径 A**：

```bash
# fork 之后
git clone 你的 fork && cd acm-agent-workflow
cp 你的包.zip contributions/
git checkout -b 贡献-Round163
git add contributions/你的包.zip
git commit -m "contributions: 牛客周赛 Round163（署名 你的ID）"
git push origin 贡献-Round163
# 然后在 GitHub 上开 PR
```

PR 里 CI 会自动跑 `python tools/check_contributions.py`（跑在 Ubuntu / Windows × Python 3.13 上），
**不过关的包在 PR 阶段就红**，不会流到维护者手里。

**路径 B**：到 Issues 里说清楚是哪一场、附上 zip，维护者会把它放进 `contributions\` 跑同一条命令。

## 合并之后会发生什么

维护者按一次键（图形端菜单「题解包 → 导入题解包…」或命令行 `import_solution.py <包> --root 题库 --apply`）：

1. 文件落进 `题库\`（题解区 + 算法库）；
2. 索引反查表、题解指针、状态表行、06 对照表自动补上；
3. 最后跑 `archive_check` 对账——**退出码 0 才算收工**；
4. `contributions\` 里的包被清掉（那只是投递箱），你在 manifest 里的署名保留在 `题库\` 的索引里。

想在本机看合并后的样子：`python tools/status_gui.py --file 题库/题解/题目状态.md`。

## 许可与署名

- **贡献即同意内容按 MIT 发布**（与本仓库一致）——你有权分享这些题解，就按这条捐；
- 每题署名写在 manifest 的 `contributor` 字段里，导入后跟着索引一起保留；
- 仓库页按场次列贡献者（欢迎你自己在 PR 描述里补一句想展示的 ID / 昵称）。

## 不想打包？还有更轻的两种

- **只报一个坏例子**：题解格式哪里卡住了、哪条命令报错，直接开 Issue——这类反馈和题解一样值钱；
- **只改工具**：`tools\` 下的脚本都收 PR，改完请自己跑一遍相关闸门（CI 会再跑一遍）。
