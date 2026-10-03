# 打包图形端 exe（TimuZhuangtai.exe）

给**不想装 Python** 的同学一个双击即用的图形端（`tools/status_gui.py` 的 PyInstaller 单文件版）。
exe **不进 git**——它是构建产物：本机留一份，发布时挂到 Release 附件。

## 一条命令

用**官方 Python 3.13**（MSYS2 那个 Python 打的包跑不起来），仓库根目录下执行：

```bash
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller

python -m PyInstaller --noconfirm --clean --onefile --windowed --name TimuZhuangtai \
  --distpath ../acm-agent-workflow-exe/dist --workpath ../acm-agent-workflow-exe/build \
  --specpath ../acm-agent-workflow-exe \
  --add-data "$PWD/tools/katex_check.js;." \
  --hidden-import status_report --hidden-import toolutil --hidden-import knowledge_dict \
  --hidden-import index_sync --hidden-import archive_check --hidden-import import_solution \
  --hidden-import export_solution --hidden-import check_solution --hidden-import fill_knowledge \
  --hidden-import unify_latex --hidden-import extract_math --hidden-import unpair_ticks \
  tools/status_gui.py
```

产物 = `<distpath>/TimuZhuangtai.exe`（约 11 MB）。三个路径参数指到**仓库外**是为了不把构建垃圾
（`build\` / `.spec` / `.exe`）留在仓库里。

两个必须照抄的地方：

- **`--hidden-import` 那一串**：exe 里没有 Python 解释器，`tools\` 下的兄弟脚本
  （导入 / 导出 / 索引同步 / 状态表知识点刷新 / 归档对账 / 17 项格式闸）全靠
  `toolutil.run_sibling` **进程内 import** 调用——不写进清单就会「运行时找不到模块」；
- **`--add-data tools/katex_check.js;.`**：第 17 项 KaTeX 渲染检查要用它，放 exe 解包目录根
  （与 `check_solution.py` 找它的口径一致）。Windows 上分隔符是 `;`。

## 怎么发、怎么用

exe 放在**数据根旁边或仓库根**都行——`config.json` / `knowledge\` 这些资源是**跟着 exe 找**的：

```
acm-agent-workflow\            ← 仓库（同学 clone 下来的）
├── TimuZhuangtai.exe          ← exe 放这儿：双击 = 直接看 demo\ 的数据
├── config.json                ← 有它就用它的 data_root / backup_root
└── ...
```

```bash
# 让图形端看自己的数据根（而不是自带示例 demo\）
python install.py --data-root 题库        # 或任何自己的目录
# 然后照常双击 TimuZhuangtai.exe；菜单「题解包 → 导入题解包…」即可收包
```

## 无窗口命令行（CI / 批处理 / 排错用）

windowed exe 也能当命令行使，跟图形端走**同一套代码**（同一份 argv 拼法、同一个 `main()`）：

```bash
TimuZhuangtai.exe --pack-check  包.zip                    # 只校验（dry），退出码 0 = 合格
TimuZhuangtai.exe --pack-import 包.zip                    # 同上（菜单「导入」的第一段）
TimuZhuangtai.exe --pack-import 包.zip --apply            # 确认无误后真落盘
TimuZhuangtai.exe --pack-export Round163 -o 出.zip        # 导出（Round163-G = 单题）
TimuZhuangtai.exe --pack-check 包.zip --log 跑.log        # 输出同时写日志文件
```

退出码与脚本一致：`0` 合格 / `1` 包有硬伤 / `2` 读不了。**没有控制台时（双击 / CI 管道）**
输出落 `--log` 指定的文件，没给就落 exe 旁的 `TimuZhuangtai.log`。

## 已知边界

- **单文件 exe 首次启动要解包**（约 1~3 秒），之后每次开窗都一样——不是卡死；
- exe 里的路径口径：**「仓库根」= exe 所在目录**（`toolutil.REPO_ROOT`），所以别把 exe 扔到
  系统目录里再用——配置、知识库、demo 都会找不到；
- 第 17 项 KaTeX 渲染检查仍需要**外部的 node**（exe 不打包 node）；没有就如实跳过，不影响退出码。
