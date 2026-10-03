# 题库（真实题解数据根）

这里是**发布用的数据根**——收集大家贡献的真场题解，结构和 `demo\` 完全一样：

```
题库\
├── 题解\牛客周赛\RoundNNN\RoundNNN题解.md   ← 整场题解（每题目录在它旁边）
├── 算法\<算法名>\牛客周赛RoundNNN-X-*.md     ← 算法库记录（五节模板）
└── 索引\题解算法索引.md                      ← 全量索引（反查表 + 场次小节）
```

`题解\题目状态.md`（补题状态表）、`索引\题目记录模板.md` 已随骨架放好，`索引\题解算法索引.md` 是空索引。

## 怎么用

**只看图 / 管自己的题**（同学动线）：

```bash
python install.py --new-data <你自己的目录>   # 建自己的数据根
python install.py --data-root <你自己的目录>  # 让 config.json 指向它
python tools/status_gui.py                    # 打开图形端；菜单「题解包 → 导入题解包…」
```

**把包导进这里**（维护者动线，本仓库自己的数据根）：

```bash
python tools/import_solution.py <包.zip> --root 题库        # dry：先看报告
python tools/import_solution.py <包.zip> --root 题库 --apply # 确认后落盘
python tools/archive_check.py RoundNNN --root 题库 --status 题库/题解/题目状态.md  # 退出码 0 = 收工
```

图形端同理：`status_gui.py --file 题库/题解/题目状态.md` 打开，菜单「题解包 → 导入题解包…」选包，
报告里点「应用到数据根」。

## 为什么现在是空的

空目录 = **还没合并过任何外部贡献**。题解由贡献者按《[CONTRIBUTING.md](../CONTRIBUTING.md)》
打包投递，维护者 review 后导入——**导入器会给每一处落盘留下机器可查的痕迹**
（反查表、题解指针、状态表行、`archive_check` 退出码 0），不是手工往文件夹里丢文件。

`题解\牛客周赛\.gitkeep` 和 `算法\.gitkeep` 只是让空目录能进 git，导入第一个包之后它们可以删。

## 注意

- 这个目录是**数据根**，不是仓库代码的一部分：里面的题解归贡献者（按 MIT 发布，署名在 manifest 里）；
- 跑工具时 `--root` 记得指到 `题库`（或者 `install.py --data-root 题库` 之后省掉 `--root`），
  否则默认动的还是自带示例 `demo\`；
- 导入会写文件 / 索引 / 状态表 / 台账四处，写前自动备份（备份落在 `config.json` 的 `backup_root`）。
