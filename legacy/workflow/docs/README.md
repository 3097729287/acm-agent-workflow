# TB 训练工作台 · 0.5.0

Windows 10/11 64 位安装包见 [GitHub Releases](https://github.com/3097729287/acm-agent-workflow/releases)。下载 `TB-Setup-0.5.0-win64.exe` 并运行。安装包包含 Python、C++ 工具链、题库、规范讲义和离线 WebView2 安装组件，无需先安装编程环境。便携 ZIP 也可整包解压使用。

安装时可选择导入此电脑原 TB 的训练、提交、草稿和配置。升级保留个人数据库、身份与现有题库；卸载保留个人记录。全新安装的个人训练为空，公共题库不计入个人题数。

## 训练与阅读

- **我的训练**：仅列主动加入或实际提交的题，同题计一次；可选全部、单题练习或某场模拟赛。取消训练保留历史和代码。
- **题库 / 比赛**：按题名、平台、真实比赛时间、知识点和难度选题。难度说明区分 Codeforces 官方分与其它平台的估算值；联网同步也会更新旧题评级。
- **模拟赛**：综合训练、专项训练、随机单题；可选平台、知识点、题数、时长、难度范围，以及排除已通过题和仅限本地审核题。试卷预览与比赛中隐藏考点，开始后关闭题解和旧代码，结束后在同页复盘。
- **提交记录**：查看全部历史运行与提交、结果、代码、时间与耗时，支持加载更早记录。
- **成长与能力**：每日任务按实际通过和题目难度奖励经验，领取后不会重复奖励；查看知识缺口与下一步训练。右上角奖杯打开成就，等级统计从侧栏移到顶部。
- **活动记录**：训练热图与默认展开的日期明细。
- **从零讲**：正式概念名称、知识分类、基础定义、手算例子、理由与原题推导。377 篇完整讲义由现有题解整理，保留原公式与代码。旧目录与来源保留可核对；未有题解的公开题按可查证内容分析知识点，不把推断冒充完整题解。

侧栏知识清单支持搜索和全部展开/收起。设置分外观与导航、账号与身份、翻译 API、更新、训练与键盘；可调整字号、主题、导航上下顺序、页面名与页面组合，同组页面在一个入口内用标签切换。页面和筛选书签可修改名称。固定界面文字不可选择，题面、题解、公式、代码、输入框与 ID 可选择和复制。

## 评测、官方提交与 API

CodeMirror C++ 编辑器自动保存，单题与每场模拟赛的草稿独立。运行检查样例或自定义输入，提交执行本地评测。只有通过已审核本地测试才计“本地 AC”；公开样例通过单独统计，本地 AC 与原站官方 AC 分开。

官方提交面板在同一个主窗口中保留网站完整区域，支持 C++17/20/23 等可用编译器和网站显示的编译器版本。使用正常原站登录与表单；代码需要更高标准时选择兼容项，无法可靠识别则停止自动提交。结果以原站可靠回执为准。模拟赛中不能提交对应题到官方。

翻译支持 DeepSeek、火山方舟与自定义 OpenAI 兼容服务。自定义填写 **Base URL、API Key、模型 ID**；只发送公开题面，保留代码、数学及样例。密钥用 Windows DPAPI 保存在当前用户本机，不回显；更换接口不会误用旧接口密钥。实际翻译成功后才标记验证成功，失败保留原文。

四平台公开账号无需平台密码。CF 官方资料与 AtCoder 官方评级/AtCoder Problems 公开通过统计分别注明来源；原站未公开的数据保持未知。更新通知只在右上角铃铛展示，设置保留同步控制，不重复展示通知列表。

## 身份与排行榜

每份新个人数据库首次运行生成唯一 UUID，可设置昵称，显示为昵称 + ID。默认发布包不含共享身份或私人令牌。排行榜统计客户端报告的首次已审核本地通过题数，提供每日、每周和总榜；重复题与样例通过不计入，尚不提供防作弊认证。

共享服务尚需部署。可在“账号与身份”填写统一 HTTPS 服务地址；源码中的 [Cloudflare Worker + D1 服务](server/leaderboard/README.md) 可部署后供全部安装用户使用，客户端仅同步题目摘要、时间与难度，不上传代码。当前安装包未内置已上线的云服务。

## 常用键位

| 按键 | 操作 |
| --- | --- |
| Ctrl+1 … 9 | 原固定页面快捷入口，重排导航后仍保留 |
| Ctrl+0 / Ctrl+,；Ctrl+B；Ctrl+K | 设置；收起侧栏；命令面板 |
| Tab / Shift+Tab；Enter / Space | 移动焦点；激活 |
| F6 / Shift+F6 | 在导航、知识清单、主区、代码、结果间切换 |
| F / Ctrl+F；F5 | 搜索（编辑器内搜索代码）；刷新 |
| 列表 ↑↓ / J K；Enter；U；S；Delete | 选题；练习；题解；收藏；取消训练 |
| 知识清单 ↑↓ / →← / Home / End / Enter | 移动、展开收起、筛选 |
| Ctrl+Enter；Ctrl+R；Ctrl+S；Ctrl+Shift+Enter | 本地提交；运行；保存；官方提交 |
| 编辑器 Tab / Shift+Tab；Ctrl+Tab | 缩进 / 取消缩进；移出编辑区 |
| Alt+1 / Alt+2 / Alt+0；比赛中 1 … 9 | 题面 / 代码 / 双栏；切题 |
| 官方面板 Alt+S / Alt+B | 提交到官方 / 返回 TB |
| 活动热图 ↑↓←→ / Enter；?；Esc | 查看日期；键位帮助；关闭或返回 |

## 从源码运行与构建

源代码位于 `tools/tb_web`；其 `common/` 保留所需共享模块版本，与旧 Tk 图形端独立。安装 Python 3.13、Node.js 和 C++ 工具链后：

```powershell
python -m pip install -r tools/tb_web/requirements.txt
cd tools/tb_web
npm ci
npm run build
python launch.py --check
python launch.py
```

根目录 `config.json` 为本地配置，不入库；`data_root` 指向含 `题解/TB.md` 的资源根，可使用已安装版的文件夹。题库仅作为只读资源，个人记录在根目录 `state/`。

完整安装包构建使用 `build_release.py` 四步命令。`--stage` 是全新构建目录；`--compiler-source` 指向包含 `ucrt64/bin/g++.exe` 的完整工具链；`--data-root` 指向归档根；`--dictionary` 指向标准知识词典。`installer` 还需要 Inno Setup 6.7.3 的 `ISCC.exe` 及微软官方 x64 Evergreen 离线 WebView2 安装器。可用 `--leaderboard-endpoint` 预置已部署的共享地址。所有步骤从隔离副本构建，不打包 state/cache、平台账号或 API 密钥。

```powershell
python build_release.py prepare --stage BUILD --compiler-source COMPILER
python build_release.py build --stage BUILD
python build_release.py assemble --stage BUILD --data-root DATA --dictionary DICTIONARY
python build_release.py installer --stage BUILD --inno ISCC.exe --webview2 WebView2-offline-x64.exe
```

自测：`python -m unittest test_v5_services test_v5_root test_v5_knowledge test_migration`、`node tests/v5_ui.mjs`；服务端自测见部署文档。桌面发行还使用临时安装和真实 C++ 评测检查，测试不触碰原个人数据库。
