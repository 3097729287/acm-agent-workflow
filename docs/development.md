# 开发、验证与构建

需要 Python 3.13、Node.js 24，评测需要支持 C++17 的 g++。API 和数据库只依赖 Python 标准库；桌面构建依赖 `backend/requirements.txt`。

```powershell
python backend/backend.py --offline --state-dir .backups/dev-state
# 独立终端
cd frontend
npm ci
npm run dev
```

Vite 默认代理 `127.0.0.1:18765`；改变后端地址时设置 `TB_API_URL`。构建后的界面可通过 `--frontend frontend/dist` 与本机服务组合；桌面入口为 `python desktop/launch.py`。API 的可选参数见 `--help`。

```powershell
python scripts/check.py
cd frontend
npm run build
npm run test:ui
npm run test:compilers
npm run test:e2e
cd ../server/leaderboard
npm test
```

检查使用临时目录和离线模式；端到端检查启动独立 API 与 Vite，并验证真实 SQLite 题解读取。浏览器默认用系统 Edge；CI 使用已安装的 Playwright Chromium。截图保存在被忽略的 `frontend/tests/screenshots/`。

## 本地更新记录

每次版本或 PR 更新，都要同步到用户指定的本地项目目录：保存对应提交的源码快照，维护版本索引，记录状态、验证结果和实际启动入口。未合并的 PR、已合并的源码、本地构建和正式发布分别标明；仅源码更新须注明尚未打包。

有新程序时，保留完整便携目录、独立启动入口及隔离验证记录。验证通过后再更新最新版快捷方式，保留上一可运行版本和个人数据；不能只推送 GitHub 而让本地目录无法查看本次更新。

## 导入公共题库

```powershell
python scripts/import_library.py --archive <包含题解目录的数据根> --output data/library.sqlite3
python scripts/library_seed.py export   # sqlite -> data/library/*.json
python scripts/check.py --library-only
```

导入只读源归档，清除分发库的个人状态，保存可移植题解、题面、图片和精确讲义关系。生成前保留原库备份；不要将个人工作数据库替换为公共库。

`data/library.sqlite3` 不进入 git，git 管理的是其文本源 `data/library/*.json`。改完题库后运行 `export` 提交文本源；clone 或打包时 `data/library.sqlite3` 缺失会自动由文本源重建（`scripts/library_seed.py build` 可手动触发）。

## Windows 安装包

先构建前端，再在新的空 staging 目录进行构建。编译器目录必须包含完整 `ucrt64` 树；与分发二进制对应的源代码、许可证和构建配方也要提供。

```powershell
python -m pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ..
python scripts/build_release.py build --stage build/0.6.0
python scripts/build_release.py assemble --stage build/0.6.0 --compiler-source <compiler目录>
python scripts/build_release.py installer --stage build/0.6.0 --inno <ISCC.exe> --webview2 <离线WebView2安装程序>
```

`TB新版.exe --package-check <报告路径>` 在隔离状态下检查内置题解和真实 C++ 评测；`--native-check` 检查实际桌面界面；`--serve-check` 启动检查服务，到同名 `.stop` 文件出现时停止。通过 `TB_STATE_DIR` 指定一次性状态，验证时设置 `TB_OFFLINE=1`。生产安装包不得包含这些测试产生的数据。

真实安装与升级检查使用独立 AppId，不修改日常安装、快捷方式或个人状态；在 `build/release-check-*` 保留报告与隔离数据。需要已有 0.5 公共安装目录以及对应的安装脚本：

```powershell
python scripts/check_release.py --stage build/0.6.0 --legacy-package <0.5公共安装目录> --legacy-iss <0.5的tb.iss> --inno <ISCC.exe> --webview2 <离线WebView2安装程序>
```

安装程序按相同 AppId 升级，只覆盖程序和公共种子库。完成后验证旧草稿、提交代码、身份、模拟赛和经验值仍在；生成 SHA256SUMS 和文件清单后再发布。
