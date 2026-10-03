# 洛谷整场抓取样例：`contest/278842`

`tools/fetch_problem.py` 的**洛谷适配器**抓下来的一场**已结束**洛谷官方场，
留在这里当例子 + 离线回归 fixture（CI 里跑 `--selftest`）。

- **原 URL**：<https://www.luogu.com.cn/contest/278842>
- 场次：【LGR-310-Div.2】洛谷 9 月月赛 II &「DBOI」Round 6（2026-09-30 结束）
- 题数：**4**（与接口 `problemCount` 一致；A~D → `P17538`~`P17541`）
- 抓取时间：2026-10-03，用 `x-lentille-request: content-only`，请求间隔 3 秒

复现这一趟（一条命令；抓完再跑离线自检）：

```bash
python tools/fetch_problem.py "https://www.luogu.com.cn/contest/278842" \
       --out examples/luogu/contest-278842 --delay 3
python tools/fetch_problem.py --selftest          # 退出码 0 = 解析链没漂
```

## 装箱

| 路径 | 是什么 |
|---|---|
| `raw/_contest.json` | 比赛页**原始返回**（题名表在 `data.contest.description` 里） |
| `raw/_tags.json` | `/_lfe/tags` 原始返回（标签 id→名） |
| `raw/<字母>.json` | 每题题面页**原始返回**（正文 + 逐字样例 + 难度 + 标签） |
| `题面/<字母>.txt` | 拼好的题面（markdown 正文 + 官方样例），**格式与牛客产物一致** |
| `samples.py` | 官方样例常量表（贴进 `verify.py`，别手敲） |
| `题单.md` | 字母 / 题名 / 题号 / 难度 / 标签 + 原 URL |

## 备注

- **样例逐字**取自洛谷返回，一个字符都不动：D 题第一组输入是 `1\n6 \n1 1 2 3 3`
  —— 那个 `6` 后面的空格是原文自带的。
- 单题那条路另见 `../problem-P1001/`。
- 题面文字版权归洛谷及其出题人；这里作为**抓取样例**原样收录，只为离线回归测试。
- 已知边界（工具会挡）：未结束的比赛题目对外隐藏、重现赛描述里没有题名表。
