# TB 架构

## 边界

`frontend/` 只负责界面、编辑器与交互，通过 JSON HTTP API 调用服务；不导入 Python 或读取归档文件。`backend/` 管理题库、个人记录、公开数据、翻译和本地评测，可以只启动 API。`desktop/` 创建 WebView2 窗口，组合静态界面与本机 API，提供原站官方提交面板。`server/leaderboard/` 是可独立部署的共享服务。

开发入口：`python backend/backend.py --offline` 与 `frontend/npm run dev`。Vite 代理 `/api` 并保留会话令牌。若直接跨源连接，使用 `TB_FRONTEND_ORIGINS` 显式配置允许的来源，多个来源以逗号分隔；未配置时仍执行同源校验。API 只监听回环地址，写入要求 `X-TB-Token`。

## 数据与迁移

| 文件 | 内容 | 分发与升级 |
| --- | --- | --- |
| `data/library/` | 公共题目、题面、题解、讲义及精确关系（文本 JSON 源） | git 管理的可 diff 文本；首次启动或打包时重建 |
| `data/library.sqlite3` | 由文本源重建的二进制题库 | 随包分发，无个人进度；构建产物，不进入 git |
| `state/tb-library.sqlite3` | 可更新的题库工作副本、导入内容、抓取题面 | 首次合并内置库，后续按来源摘要合并；保护本地修改 |
| `state/tb-personal.sqlite3` | 训练、提交代码、草稿、模拟赛、身份、任务和经验 | 永不由安装包覆盖 |
| `state/tb-documents.sqlite3` 及缓存子目录同名数据库 | 设置、加密翻译凭据、公开 HTTP 缓存、知识分析等 JSON 形状文档 | SQLite 事务写入；旧 JSON 只迁入一次 |
| `state/backups/` | 升级、导入前的 SQLite 在线备份 | 保留已提交 WAL 内容 |

`data/library/` 下是随包题库的文本源：`meta.json`、`problems.json`、`solutions.json`、`statements.json`、`lectures.json`、`links.json`。`data/library.sqlite3` 是构建产物，不被 git 跟踪：首次启动时若缺失会由 `backend/store.py` 自动重建，`scripts/build_release.py` 打包时同样保证重建，`scripts/check.py` 校验前也会补齐。维护者用 `python scripts/library_seed.py export` 从 sqlite 导出文本源，用 `python scripts/library_seed.py build` 重建 sqlite。内容升级按文本源指纹（`bundled_sha256`）判定，与 sqlite 文件字节无关。

`TB_STATE_DIR` 可覆盖状态目录，`TB_LIBRARY_DB` 可指定工作题库，`TB_ARCHIVE_ROOT` 指定显式导入/收件箱根目录，`TB_BACKUP_DIR` 可指定个人记录备份目录。默认状态在程序目录的 `state/`；Windows 安装到当前用户可写目录。

旧 JSON 文件保留字节不变，后续读写 SQLite。Windows API Key 仍使用用户绑定的 DPAPI 加密，不进入公共题库、响应或日志。0.5 个人数据库保留原有表和数据，由训练服务进行兼容升级。`--migrate-local` 只在用户选择旧安装导入时运行，复制允许的状态和设置；在线备份支持旧进程的已提交 WAL。升级安装不会重新导入另一份身份，也不会覆盖现有目标。

公共库升级按表记录上次分发内容的摘要。只有未在本机修改的内容随新版本更新；用户导入、修改和后来抓取的题面保留。事务失败回滚，外键与完整性检查拒绝损坏内容。新库与个人记录分开，卸载保留运行后产生的状态目录。

Markdown 是正文格式与交换格式，运行时不通过路径定位题解。`scripts/import_library.py` 和收件箱处理负责显式导入旧归档；旧源文件保留。收件箱在提交前校验章节、冲突和讲义，正文与引用关系一起入库。

## 题解与讲义

题目 ID 与原站规范化 URL 索引共同定位内容。同题不同 URL 写法可共用已收录的题解、题面和讲义。基础讲解关联分为本题自己的章节和明确引用；不按共享标签扩散。正文摘要用于去掉重复的关系，保留不同的推导。前端将正文中的从零讲章节折叠，按需展开。

## 外部接口

翻译只发送公开英文题面，拆分请求时保护公式、代码、样例、数字和格式；截断或标记变化拒绝写入缓存，原文始终可读。自定义服务支持 Base URL 归一化、模型 ID 和可选密钥。连接测试真实调用用户配置的服务，产生普通翻译 API 用量。

官方适配按网站识别实际语言控件，区分编译器版本与 C++ 标准，触发正常表单事件。登录、验证码和 CSRF 保留原站流程；需要登录或没有匹配编译器时向用户报告原因。

排行榜默认服务为 `https://tb-leaderboard.fsxxxg.workers.dev`。身份由个人数据库生成，初始连接异步注册；界面在同步完成后刷新并区分“已连接但没有通过记录”和请求错误。测试用 `TB_OFFLINE=1` 或本地服务，避免生成测试用户。协议和部署见共享服务目录。
