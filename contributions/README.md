# contributions（贡献区）

**把你的题解包放进这个目录，然后提 PR。** 这是贡献路径 A 的落点——PR 里 CI 会自动把
每个包跑一遍校验（`python tools/check_contributions.py`，退出码 0 才算过），不合格的包
到不了维护者手里。

**这个目录平时是空的**（这份 README 就是存根）：包被 review、导入 `题库\` 之后，维护者会把
贡献文件从这里清掉——它只是「投递箱」，不是存档处。

## 怎么放

```
contributions\
├── 牛客周赛Round163.zip     ← 单个 zip（推荐：导出器现打的就是这个形态）
└── 或者解压后的目录：
    └── 牛客周赛Round163\    ← 目录里必须有 manifest.json 和 题解\ 算法\ 两棵树
        ├── manifest.json
        ├── 题解\牛客周赛\Round163\...
        └── 算法\...
```

**怎么导出**（先把这场题解在自己机器上归档好）：

```bash
python tools/export_solution.py Round163        # 整场 → 牛客周赛Round163.zip
python tools/export_solution.py Round163-G      # 或单题 → 牛客周赛Round163-G.zip
```

## 提交前先自己跑一遍

```bash
python tools/check_contributions.py --pack 你的包.zip   # 退出码 0 = 没问题
```

想连自检（好包绿 / 坏包红）一起看，就直接跑 `python tools/check_contributions.py`。
两类结果的意思：

| 退出码 | 意思 | 怎么办 |
|---|---|---|
| 0 | 包合格 | 提 PR |
| 1 | 包有硬伤（manifest 缺字段 / 题解 md 没过 17 项格式闸 / 与数据根冲突…） | 报告里有逐项行号，改完重打 |
| 2 | 读不了（不是 zip / 没有 manifest.json） | 检查是不是传错了文件 |

**未登记的知识点 / 文件夹不算问题**——照收，只在报告里列进「待登记清单」，由维护者合并时定夺。

完整规则（包格式、署名、MIT 许可、PR 流程）见仓库根目录的 [CONTRIBUTING.md](../CONTRIBUTING.md)。
