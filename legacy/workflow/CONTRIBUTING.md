# 贡献指南（题解共享库）

给想投稿一场题解的人。三条路径任挑一条——走同一个导入器、同一套校验，署名照留；你本地跑的、CI 跑的、
维护者合并时跑的，是同一条命令。路线总览见 [README 的路线 C](README.md#路线-c投稿与开发)。

## 三条路径

| 路径 | 怎么传 | 谁跑校验 |
|---|---|---|
| A：会 git | fork → 包放进 `contributions\` → 提 PR | CI 自动跑，不过关的包在 PR 阶段就红 |
| B：不会 git | zip 当附件发到 [Issues](https://github.com/3097729287/acm-agent-workflow/issues) | 维护者收到后本地跑同一条命令 |
| C：最省事 | 加维护者 QQ **3660535264**（备注「题解投稿」）直传 zip；不会导出就发题解 md + 代码，维护者替你打包 | 维护者也本地跑一遍 |

## 第 1 步：导出题解包

```bash
python tools/export_solution.py Round163        # 整场 → 牛客周赛Round163.zip
python tools/export_solution.py Round163-G      # 或只导出 G 一题
-o 输出.zip        # 指定输出位置（缺省 = 当前目录）
--contributor 名字 # 署名（缺省取 git config user.name）
```

导出器自动做三件事：**过滤耗材**（`_work\` / `__pycache__` / `.exe` / `.png` / `.bak` 不进包）、**别名规范化**（非标准知识点名换成词典标准名）、**写 manifest.json**（字段抄自算法记录 md 头部，单一事实来源）。手写包也收：只要有 `manifest.json` 和整场题解 md 就行。
包结构、manifest 字段（`format` / `format_version` / `contest` / `round` / `contributor` / `problems[]`）与分级口径，见 [knowledge/10-工具链.md](knowledge/10-工具链.md#题解包export_solution--import_solution) 的「题解包」节。

## 第 2 步：提交前自己跑一遍

```bash
python tools/check_contributions.py --pack 你的包.zip
```

| 退出码 | 意思 | 怎么办 |
|---|---|---|
| 0 | 合格 | 往下走 |
| 1 | 有硬伤 | 报告里逐项写了行号 / 原因，改完重打 |
| 2 | 读不了 | 多半不是 zip、或者缺 `manifest.json` |

打回级硬伤：manifest 字段缺 / 拼错（`difficulty` 要写成 `CF 900` 这样）、题解 md 没过 18 项格式闸（`python tools/check_solution.py <md>` 能看逐项行号）、目标位置已有同一题（防覆盖）、`url` 末尾字母与 `letter` 对不上。
**不会被打回的**：知识点 / 文件夹名不在词典里——照收，只列进「待登记清单」，维护者合并时收编；算法记录不带——生成「精简记录」（头部齐、正文标注「未附」）；四档验证没跑——实测记录节如实写「未验证」就行。

## 第 3 步：交出去

```bash
# A 路径：fork 之后
git clone 你的 fork && cd acm-agent-workflow && cp 你的包.zip contributions/
git checkout -b 贡献-Round163 && git add contributions/你的包.zip && git commit -m "contributions: 牛客周赛 Round163（署名 你的ID）" && git push origin 贡献-Round163
# 推完在 GitHub 上开 PR
```

## 合并之后会发生什么

维护者导入：图形端菜单「题解包 → 导入题解包…」，或 `python tools/import_solution.py <包> --root 题库 --mem 题库/知识库 --apply`。

自动串齿轮，一步不少：复制文件（题解区 + 算法库）→ 补索引反查表与 `06` 对照表 → 写题解指针 → `index_sync` 生成索引场次小节 → 追加状态表行 →
`fill_knowledge` 刷知识点列 → `archive_check` 对账——**退出码 0 才算收工**。`contributions\` 里的包随后清掉（只是投递箱）；署名留在 `题库\` 的索引里。

贡献即同意内容按 MIT 发布（与本仓库一致）；仓库页按场次列贡献者，想展示的 ID / 昵称欢迎在 PR 描述里补一句。报 bug 或改 `tools\` 脚本也欢迎——直接开 Issues / 提 PR，改完把相关闸门跑一遍（CI 会再跑一遍）。
