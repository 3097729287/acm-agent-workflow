# demo —— 两场示例数据

这是默认数据根，也是一个最小完整示例：给 clone 下来想先看真实数据、想直接跑一遍闸门的人；仓库总览见 [../README.md](../README.md)。

- **牛客周赛 Round 163 的 B~G**（该场题解本身覆盖 B~G 六题）：完整一场，六级台阶、各种验证写法都有。
- **牛客周赛 Round 161 的 C~E**（该场题解覆盖 A~F，示例只取三题）：迷你第二场，演示**跨场次台账**——同一算法文件夹进第二场的记录后，《已讲过概念清单》的「首次出现取最早那场、讲掉的概念划掉」在这里有真实落法。

| 目录 | 里面是什么 |
|---|---|
| `题解\牛客周赛\Round163\` | 一场自包含的题解文件夹：题解 md + 每题代码 + 配图 / 对拍脚本 |
| `题解\牛客周赛\Round161\` | 迷你场：C / D / E 三题的题解 md + 代码 + 配图脚本 |
| `算法\` | 9 份题目记录（按主算法分文件夹）+ 3 份 `题解指针.md` |
| `索引\` | 全量索引 `题解算法索引.md` + `题目记录模板.md` |
| `题解\题目状态.md` | 状态跟踪表（图形端：`python tools\status_gui.py`） |

验证驱动的分布（两种写法都保留在示例里）：

- Round163 B = 框架写法 `B-G\B\verify_b.py`（配 `samples.py` + `b_brute.cpp`）；第 6 步 `python tools\md_full.py <md> B --dir <目录>` 认这种命名；C 的 `专题\` 里有对拍 / 画图脚本；
- Round163 F = 自包含脚本 `B-G\F\verify_all.py`，暴力对拍写在脚本里、不依赖框架；
- Round161 C / D / E = 框架写法 `A-F\<字母>\verify_<字母>.py`，三题齐全，演示多题场次落盘；
- **Round163 D / E / G 没有验证驱动**，只留代码与配图脚本——第 6 步会明确报「没找到 verify 脚本」，而不是假装跑过。

直接可跑（仓库根下；`archive_check` 退出码 0 = 归档四处（记录 / 索引 / 知识库《归档》/《已讲过概念清单》）对账通过；验证驱动需要 g++）：

    python tools\archive_check.py Round163
    python tools\archive_check.py Round161
    python demo\题解\牛客周赛\Round163\B-G\B\verify_b.py
    python demo\题解\牛客周赛\Round161\A-F\C\verify_c.py
