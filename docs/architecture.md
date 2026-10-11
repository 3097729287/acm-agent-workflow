# TB 架构

## 边界

`frontend/` 只负责界面、编辑器与交互，通过 JSON HTTP API 调用服务；不导入 Python 或读取归档文件。`backend/` 管理题库、个人记录、公开数据、翻译和本地评测，可以只启动 API。`desktop/` 创建 WebView2 工作台窗口，并通过随包的浏览器扩展连接用户日常浏览器中的原站会话。`server/leaderboard/` 是可独立部署的共享服务。

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

单题工作台的“运行样例”调用本地运行接口，“提交”进入 `BrowserBridge` 后台队列，不调用系统浏览器启动器。一次启用随包的 Edge/Chrome 扩展后，扩展从回环接口读取已由用户发起的任务，在已运行浏览器的现有窗口内创建不激活的专用标签，使用原站登录会话处理请求。没有浏览器窗口时不创建窗口。仅用户明确点击“连接浏览器”或“在浏览器查看”才打开原站或连接页。登录或验证码保留原站流程，TB 不创建应用内登录页，不导出账号 Cookie、密码或 CSRF 令牌。扩展目录为程序目录下 `browser-extension`，由 `scripts/build_browser_extension.py` 生成。

每次原站提交冻结题目和代码；进行中的同题提交拒绝重复请求。每个会话绑定独立后台标签，切换题目不停止回执读取；终态持久化为 `scope=official`，成功后仅关闭扩展自己创建的标签。提交命令最多派发一次，不因轮询、扩展恢复或超时自动重发。发出请求只进入“等待原站受理”；收到原站提交编号后才进入“评测中”。45 秒仍没有受理编号时提示正在核对，继续查询并接受迟到的可靠回执，最长 15 分钟；应用界面也继续轮询。登录完成不自动提交，需回 TB 点击提交。模拟赛保留受比赛隔离规则保护的“赛内提交”。

原站适配器由同一份 `official_page.js` 与语言、牛客、洛谷脚本打包生成，扩展不下载可执行代码。牛客普通旧版编辑器直接 POST 官网使用的 `/nccommon/submit_cd`，再按返回的 submissionId 查询 `/nccommon/status`，兼容顶层和 data 两种响应结构。新版编辑器保留原站提交流程，通过 document_start 观察器兼容提前缓存的 fetch/XHR 和 Victorinox 回执。洛谷从 `lentille-context` 读取本题、用户和允许语言，从原站配置读取语言与提交路由，携带页面 CSRF 令牌 POST `/fe/api/problem/submit/{pid}`，按 rid 查询 `/record/{rid}`；不依赖代码编辑器是否挂载。接口拒绝、验证码、未知网络结果分别处理，不重试 POST。提交编号、题目、代码、账号和评测元数据必须匹配，令牌只留在原站页面。CF、AtCoder 在后台使用原站表单与 CSRF，从本账号提交记录或 CF 官方查询 API 读取新结果，使用提交前快照拒绝旧记录；无法取得快照时不发送代码。四站没有统一的公开代码提交 API，不将网页内部接口称为公共开放 API。

`/api/browser/register` 与 `/api/browser/queue` 要求固定扩展 ID 和严格匹配的扩展 Origin；注册只授予读取用户已创建任务的后台能力，不能创建提交或访问通用应用接口。队列在锁内将每个任务分配给单一浏览器配置。`/api/browser/exchange` 继续要求每次提交独立的随机令牌、扩展 ID 与匹配来源。任务令牌存入扩展的 storage.session，不发送给原站，不是应用的 X-TB-Token。每次派发代码前重新检查模拟赛锁，页面跳转离开本平台则拒绝处理。前端状态响应不含代码和令牌。已有 AC 字号、提示音和结果持久化行为保留。

排行榜默认服务为 `https://tb-leaderboard.fsxxxg.workers.dev`。身份由个人数据库生成，初始连接异步注册；界面在同步完成后刷新并区分“已连接但没有通过记录”和请求错误。测试用 `TB_OFFLINE=1` 或本地服务，避免生成测试用户。协议和部署见共享服务目录。
