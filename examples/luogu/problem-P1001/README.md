# 洛谷单题抓取样例：`problem/P1001`

整场（`/contest/<id>`）之外的第二条输入形态：**单题 URL** 走同一条流水线。

- **原 URL**：<https://www.luogu.com.cn/problem/P1001>（A+B Problem）
- 抓取时间：2026-10-03

```bash
python tools/fetch_problem.py "https://www.luogu.com.cn/problem/P1001" \
       --out examples/luogu/problem-P1001 --delay 3
```

| 路径 | 是什么 |
|---|---|
| `raw/P1001.json` | 题面页**原始返回** |
| `题面/P1001.txt` | 拼好的题面 + 官方样例 |
| `samples.py` | 官方样例常量表 |

**单题模式的文件名用题号当标签**（`P1001`）——比赛字母列这时不存在，硬编 `A` 会骗人；
要别的标签加 `--letter A`（例如把单题并进某个 `RoundN\_work\` 时）。
