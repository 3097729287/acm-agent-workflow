# contributions（贡献投递箱）

给要提 PR 的投稿人：把你的题解包放进这个目录，然后提 PR。CI 会对每个包跑 `python tools/check_contributions.py`——
不过关的包到不了维护者手里。这个目录平时是空的：包导入 `题库\` 后会被清掉，它只是投递箱，不是存档处。

## 放什么

先把这场题解在自己机器上归档好，再导出：`python tools/export_solution.py Round163`（整场 → 牛客周赛Round163.zip）
或 `python tools/export_solution.py Round163-G`（单题）。然后放进来：

```text
contributions\
└── 牛客周赛Round163.zip   ← 单个 zip（推荐）；或解压后的目录（至少要有 manifest.json 和整场题解 md）
```

## 提交前先自己跑一遍

```bash
python tools/check_contributions.py --pack 你的包.zip   # 退出码 0 = 合格
```

| 退出码 | 意思 |
|---|---|
| 0 | 合格 |
| 1 | 有硬伤——报告带逐项行号，改完重打 |
| 2 | 读不了——不是 zip / 缺 `manifest.json` |

不带参数跑 `python tools/check_contributions.py` = 先自检（好包绿 / 坏包红）再扫整个目录；**未登记的知识点 / 文件夹名照收**，只列进「待登记清单」，由维护者合并时定夺。

完整规则（包格式、署名、MIT 许可、PR 流程、三条投稿路径）见 [CONTRIBUTING.md](../CONTRIBUTING.md)。
