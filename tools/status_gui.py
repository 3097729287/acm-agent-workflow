# -*- coding: utf-8 -*-
r"""status_gui.py —— 题目状态跟踪窗口 v15（tkinter，纯标准库）

用法：
    pythonw status_gui.py                     # 打开窗口（默认读 <数据根>/题解/题目状态.md）
    python  status_gui.py --file 别的.md      # 换一份状态表
    python  status_gui.py --selftest          # 自测：不开窗口、只用自造的 fixture（不碰真 md）
    python  status_gui.py --smoke             # 窗口冒烟：建窗口 + 走一遍交互，不 mainloop()

界面（v2 表结构；v9：窗口第一行 = 搜索 + 统计 + 消息）：
    表头 = | 场次 | 题号 | 题名 | 知识点 | 难度 | 状态 | 日期 |
    只能改「状态」「日期」两格，其余格一律只读；改状态时日期自动写今天。

键盘（全键盘可操作；按 ? 弹一览）：
    总表页  ↑↓ 移动 ｜ PgUp / PgDn 翻页（一个功能只留一个键）
            回车 → 行内浮层（6 个带序号的状态 `1. 未做`…：↑↓ 选 ｜ 1~6 数字直选 ｜ 回车确认 ｜ Esc 取消）；双击同
            S = 换排序字段（场次 → 难度 → 日期 循环）｜ R = 反转升 / 降；点表头同效
            换排序（点表头 / S / R）后选中行**钉在原行号**（v4：原来第 x 行就一直是第 x 行，
            行里的题换成别的；越界贴最后一行）；搜索才「跟题」（按 场次 + 题号）
            改完状态（回车确认 / 数字直选）选中行自动下移一行；浮层按 Esc 取消则不移动
            选中行直接按 1~6 = 改状态（不开浮层），v12 起；焦点在搜索框时数字照常打进输入框
    Tab / Shift+Tab 在「主页面 / 搜索」两站之间轮换（v14；下拉面板里各行都算「搜索」站，其余控件 takefocus 全关）
    ← / → 在一整条横排上左右走：总表 → 1 待重写 → 2 待补题 → 3 复习 → 4 抽检，两头绕回（v6）
    / 搜索 ｜ 搜索框里 ↓ 展开筛选下拉（再按 ↓ 进「知识点」）、↑ 收起（v14）
    搜索框里 Enter = 跳回总表看结果（v5：搜索词保留；v14 起 ↓ 改作展开下拉）
    Esc 逐层退回（v14）：框里有字先清空 → 上退一行 → 收起面板 → 回主页面
    搜索（v10；v12 起含难度）：忽略空格 + 多词都要命中（查 场次 + 题名 + 知识点 + 难度，大小写不敏感）
    F5 从磁盘重读 ｜ F11 全屏开关（再按一次退出；任何焦点都生效）（v11）
    ? 快捷键一览（v7：页签栏已整条隐藏，切页只走 ← / →）
    Alt+Enter 打开这题的资料（算法库记录 → 场题解）｜ Shift+Enter 打开原题（牛客题目页，v12）
    Ctrl+Z 撤销上一步改动（可连撤，本窗口内）（v6 追加；v12 起多步）
    看板页  ↑↓ 移动 ｜ 回车（或双击）弹同一个浮层改状态（v6：数字键 1~4 切段已删；v12：数字键改挂树上 = 直接改状态）

v5：
    搜索框里 Enter / ↓ = 跳回总表看结果（搜索词保留，选中按「跟题」）。主窗口不再挂常驻快捷键
    提示——快捷键只由 `?` 一览说明（v3 的「底部留一句 按 ? 看快捷键」作废）。状态浮层带
    序号（`1. 未做` …，数字键与序号一一对应；v10 起 6 项 = `1. 未做` … `6. 巩固`），浮层底部
    那行「数字直选 ｜ Enter 确认 ｜ Esc 取消」提示也已删。切页键由 Tab / Shift+Tab 改成 ← / →（两页来回绕；焦点在搜索框里时
    不抢，浮层 / 一览打开时不响应；切完焦点落到目标页表格）——v3 的「Tab 仍切页」作废。
    （v7 起页签栏整条不画，见下。）
    （v6 起「两页来回绕」也作废：改走 5 格横排，Tab 回来了但不是切页、是焦点轮换 —— 见下。
      v9 起状态筛选删除，轮换只剩「主页面 ⇄ 搜索框」两站。）

v6：
    导航改成一整条横排：← / → 在「总表 → 1 待重写 → 2 待补题 → 3 复习 → 4 抽检」5 格上左右走，
    两头绕回（总表按 → 进第 1 段、总表按 ← 进第 4 段；第 1 段按 ← 回总表、第 4 段按 → 回总表）。
    换到某段时：强调色 / 清单 / 选中行贴回本段上次那行（没记过 / 那行没了就贴第 1 行）/ 焦点
    落到该页清单，一并到位；进「今天要做的」
    不记上次在哪段（往前 = 第 1 段、往后 = 第 4 段；**v10 起每段各自记住上次选中的行**，
    切回来还停在那一行 —— 见下）。看板页的 1~4 数字键切段删除（**浮层里的数字直选照旧**，
    那是另一回事）。Tab / Shift+Tab 改成**焦点轮换**（v6 当时三站：主页面 →
    状态筛选 → 搜索框 → 主页面，Shift+Tab 反向；**v9 起状态筛选删除，改两站：主页面 ⇄ 搜索框**）；
    页签 / 段卡片等其余控件 takefocus 全关，焦点各有可见指示（选中行换色、输入框边框变强调色，
    走 style 的 focus 状态）。v5 的防冲突全保留：焦点在搜索框里时 ← / → 让位（光标照旧、不换格），
    浮层 / `?` 一览打开时都不响应。

v6 追加：
    Alt+Enter 打开选中这题的资料 —— 顺序：① glob 找算法库记录（`算法/**/牛客周赛Round<号>-<字母>-*.md`，
    别拼路径：文件夹按主知识点分，复合名不一定等于文件夹名）；② 那一场的题解 md
    （`题解/牛客周赛/Round<号>/Round<号>题解.md`）；③ 都没有 → 「打不开：没找到这题的资料」。
    场次不是「牛客周赛 Round N」形式 → 「打不开：这场还没接」。打开动作走 self._opener
    （默认 os.startfile；测试里换成假函数，绝不真开文件）。绑定挂两棵树上 —— 树自己的回车会先吃掉
    Alt+Enter（实测），只挂 root 收不到。Ctrl+Z 撤销上一步状态改动（v6 只记一步；v12 起改成撤销栈、可连撤多步，见下）：
    走正常写回（重读 → 按 场次+题号 定位 → 只替换 状态/日期 两格 → 备份 → 复读校验）把旧值写回去，
    选中行回到那题，底部提示 3 秒消失；没有可撤的 → 「没有可撤销的改动」，文件一个字不动。

v7（2026-10-03）：
    ① 界面上所有「提示型 / 信息型」括号全去掉：搜索标签 = `搜索`；看板第 2 段卡片标题 = `待补题`；
      计数行改成分隔符形式（不带括号）；底部反馈行那几句也一并去括号。`?` 一览（KEY_TABLE）里的
      括号是键位限定词，照旧保留。（当时的「空结果占位 = `无匹配` / `无`」与底行那句
      「已读入 … ｜ 共 N 题」**v9 起都删了**：占位两处不留、消息也不再写「已读入」。）
    ② **页签栏整条隐藏**（不是删页）：`_init_style` 把 `TNotebook.Tab` 的布局清空 —— 页签高度
      来自这个元素的布局，清空后标签区不画、不占高度，客户端区贴顶（实测 48px → 2px）。
      注意：`TNotebook` 自己的布局本来就只含 `Notebook.client`，改它没有效果（实测 48px 不动）。
      两个页与 `nb.select()` / `nb.index()` 的语义**原样保留** —— 切页、`_nav_arrow`、自测 /
      冒烟全靠它；只是鼠标没得点页签了。
    ③ 看板页顶上那行键盘提示（`← / → 换段 ｜ ↑↓ 移动 ｜ 回车 / 双击 = 改状态浮层`）整条删掉。
    ④ 状态筛选那个只读下拉框：字**居中**（`justify="center"`）；只读态不再用 clam 的灰底 ——
      只读态画的是样式的 `background`（原来继承 `.` 的 C_BG），现在 `Nav.TCombobox` 的
      `background` 也设成 C_PANEL 并进 map；聚焦仍是淡蓝底 C_ACCENT_LIGHT + 强调色边框（不丢）。
      （**v9 起状态筛选整块删除**，这条连同 `Nav.TCombobox` 样式一并作废。）

v8（2026-10-03）：
    ① 输入法守卫（`ImeGuard`）：中文输入法开着时，焦点在总表 / 看板清单上按 S / R / `/` / `?` /
      数字键（浮层里的状态直选），输入法候选窗会跳出来把按键吃掉 —— Windows 给**每个窗口**默认都关联了输入法上下文
      （可编辑控件 Tk 自己会管，非输入控件没人摘）。现在窗口建好后把主窗口里所有控件（含主窗口
      自己）的 HWND 都用 `ImmAssociateContext(hwnd, 0)` 摘一遍、各自存下旧上下文；**只有搜索框**
      拿到焦点时还原（搜索框 HWND + 主窗口 HWND），从搜索框离开（Esc / Enter / ↓ / Tab / 点表格）
      立刻再摘 —— 打完中文回表格再按快捷键不会再弹输入法。浮层 / `?` 一览是独立 Toplevel（自己的
      HWND，实测它们的 <FocusIn> 不会冒到 root 上），建的时候同样摘、并把兜底挂到它们自己身上。
      只在 `sys.platform == "win32"` 做；其余平台 / 拿不到 imm32 / 任何 API 异常一律静默降级成
      no-op，窗口行为与 v7 完全一致。**没用 ImmDisableIME**（那是一刀切、搜索框也没法打中文），
      搜索框的键盘行为一个字没改。

v9（2026-10-03）：
    ① 顶部重排：窗口第一行（左 → 右）= `搜索` 标签 + 搜索框（宽度 26 → **13**，贴左上角）+
      题目统计行 + **消息（最右端，side="right"；启动时为空）**。原先的两行页头（大标题
      `题目状态跟踪表`、路径行 `%s ｜ 今天 %s`）与窗口最底下那条消息行整条删掉（窗口标题栏的
      名字保留）。消息文案缩短：`已保存：<场次> <题号> → <状态>` / `已撤销：<场次> <题号> →
      <状态>` / `没有变化，未写盘`；不再显示备份文件名与日期（磁盘上的写盘与备份照旧），
      也不再写「已读入 …」（改状态 / 撤销后出现，3 秒自动消失照旧）。
    ② 状态筛选整块删除（不是隐藏）：`状态筛选` 标签 / 只读下拉框 / `var_filter` / `F` 键 /
      `Esc` 的筛选分支 / `_in_text_widget` 里对下拉的判断 / `Nav.TCombobox` 样式全删。
      Tab 焦点轮换从三站变两站：主页面 ⇄ 搜索框（Shift+Tab 反向）。
    ③ 计数行末段改口径：`%d天内做对：N 题`（默认 7 天），N = 日期在最近 N 天内**且** 状态 ∈
      {独立AC, 复现AC}（**不含「巩固」**）；前半段 `共 X 题 ｜ 未做 Y ｜ …`（6 个状态）照旧。
      （v9 当时行首还多一段 `搜出 M 题 ｜` —— **v10 起整段删掉**，计数行固定不变。）
    ④ 两处空占位（总表 `无匹配` / 看板 `无`）删除：搜不到 / 空段就是空白；PLACEHOLDER 整套
      机制（常量、插入逻辑）一并删掉，空表上 ↑↓ / Enter / PgUp / PgDn 不抛异常。

v10（2026-10-03）：
    ① **搜索规则重做**（`visible_rows`）：查询按空白切词（半角 / 全角空格都算），**每个词都要
      命中**才显示；比对前把「场次 + 题名 + 知识点 + 难度」拼起来、去掉所有空白、转小写 —— 于是
      「牛客周赛Round」与「牛客周赛 Round」命中集合完全相同，跨列组合（如「牛客 构造」）也
      能中；大小写不敏感照旧。搜不到 → 空表（v9 行为不变，不插占位）。
    ② **计数行删掉行首那段 `搜出 M 题 ｜`**：计数行固定是
      `共 X 题 ｜ <6 个状态计数> ｜ N天内做对：M 题`，搜索时也不再变。
    ③ **状态 8 个 → 6 个**（跟着 tools/status_report.py 走：「卡住」「只读过」已删，现在是
      未做 / 不会 / 待重写 / 复现AC / 独立AC / 巩固）：浮层 8 项 → 6 项、数字直选 1~8 → 1~6
      （7 / 8 不再有效）；自测 fixture 换成 12 行 6 状态全覆盖；**历史值容错** —— 真表里若还留着
      「卡住」这类旧值：统计 / 看板四段 / 浮层一律不炸，浮层对不在 6 项内的当前值**不预选**
      （按 `1` 仍能直接写「未做」），`set_status` 对非法状态**直接拒绝**（不写盘、不备份）。
    ④ **看板四段各自记住上次选中的行**（`self._seg_sel`，存 iid）：用户在清单里移动 / 点选
      （挂 `<TreeviewSelect>`）、切段前、改状态下移后都记；`refresh_today` 重建后把本段记住的
      那行贴回去，那行不在了（比如刚被改状态踢出这一段）就贴回第一行 —— 都不报错。

v11（2026-10-03）：
    F11 = 全屏开关（浏览器同款：按一次进全屏、再按一次退出）。bind_all 挂 —— 总表 / 看板 /
    搜索框里都生效，状态浮层 / `?` 一览打开时也生效；不动已有 Esc 语义、不动输入法守卫。
    **不记全屏状态**（不写配置，重启按窗口态起）。**不污染已保存的窗口几何**：进入全屏前把
    当时的窗口态 geometry 记进 `self.last_windowed_geometry`，全屏中关窗存的就是这一份
    （不是整屏尺寸）；退出全屏后把缓存同步成当前（恢复出来的）geometry；窗口态下拖大拖小
    关窗照旧存当前值。`?` 一览加一行 F11。

v12（2026-10-03）：
    ① **选中行直接按 `1`~`6` 改状态**（不开浮层）：总表 / 看板的树控件上各挂一套数字键
      （**不挂 root** —— 焦点在搜索框里时数字照常打进输入框）；浮层 / `?` 一览开着
      （`_busy()`）不响应，浮层自己的数字直选照旧；空表 / 没选中 → 静默 break。动作 =
      `set_status`：写盘、日期取今天、提示、自动下移、记进撤销栈，全按老规矩。
    ② **Ctrl+Z 连撤多步**：v6 的 `_last_change`（只一步）扩成撤销栈 `self._undo_stack`
      （容量 UNDO_MAX = 50，只在内存、不跨重启）；`set_status` 真写盘才入栈，`_undo` 弹一个
      还原一个、弹掉不压回；栈空 → 「没有可撤销的改动」、文件一个字不动。`_last_change`
      留着 = 栈顶那份（v6 / v11 老断言的读法不变）。
    ③ **Shift+Enter 打开原题**（牛客题目页）：解析链**只读**（不改文件、不产生备份）——
      场次 `牛客周赛 Round N` → 读 `题解/牛客周赛/RoundN/RoundN题解.md` 里的
      `ac.nowcoder.com/acm/contest/<cid>` → 拼 `https://ac.nowcoder.com/acm/contest/<cid>/<题号>`
      （= fetch_problem.py 的单题页形态）。解析（`parse_problem_url`，返回 URL 或 None + 原因）
      与打开（`_do_open_url`，走可打桩的 `self._opener`）分成两层 —— 自测只断言解析结果，
      **绝不真开浏览器**。失败提示跟 Alt+Enter 同风格：「打不开：没找到这场比赛的原题链接」/
      「打不开：这场还没接」。
    ④ **搜索加难度**：`visible_rows` 的拼串多接一节 难度 —— `1800` / `CF1800` / `cf 1800`
      等价，大小写 / 空格规则照旧（忽略空格 + 多词都要命中）。

v13（2026-10-03 批次 C）：
    ① **筛选区**（窗口第二行，在「搜索 + 统计 + 消息」那一行下面）= `筛选` 标签 +
      知识点框 + 难度框 + 6 个状态小按钮（可多选）+ `清空` + 最右端 `筛出 N 题`。
      三个条件 AND、**只作用于总表**（跟搜索一个口径，不影响看板）；日期 / 题名不参与。
      **匹配逻辑一律走 `status_report.filter_rows`**（拆词走 `SR.split_terms` /
      `SR.difficulty_specs`），本文件不另写一套规则 —— 命令行
      `python tools/status_report.py --todo --knowledge DP` 与 GUI 同条件必然同一份结果
      （冒烟 (zz) 拿子进程真跑命令行比过命中集合）。
      · 知识点 = 任一词在知识点列里出现即命中（子串、忽略空白大小写：`区间dp` ≡ `区间 DP`）；
        多个词用逗号分隔、取并集（`DP,动态规划` —— 不查词典、不做同义扩展）；
      · 状态 = ∈ 选中的那几个（一个都没选 = 不按状态筛）；
      · 难度 = CF 数字，`1500` / `1200-1600` / `<=1400` / `>=1800`；认不出的写法
        **一条都不匹配**并在 `筛出 N 题` 后面点名（跟命令行的 `★` 同一口径）。
      筛选开着时右端显示 `筛出 N 题`（N = 当前可见行数 = 筛选 ∧ 搜索的交集）；清空后
      这行字消失 —— v10 删掉的常驻「搜出 M 题」不复活。
    ② **端点**：两个筛选框里 Enter = 带条件跳回总表（跟搜索框同风格）；Esc 逐层退回
      （v14 改；原「清这一格 + 回表格」作废 —— 翻成了 v14 那张逐层退回表）。
    ③ **Tab 轮换变 5 站**（v13）：主页面 → 搜索 → 知识点 → 难度 → 状态组（整组算一站，
      Shift+Tab 反向）—— v9 / v6 的两站口径作废。输入法守卫的 keep 名单同步收进两个
      新输入框（v8 规则不变：在表 / 清单上按键不弹输入法）。（v14 起这 5 站又并回 2 站。）
    （v9 删的是「状态筛选下拉框」那一套；v13 不是把它搬回来：没有下拉、没有 `F` 键，
      也没有新的状态取值 —— 是输入框 + 多选按钮 + 与命令行共用一份匹配实现。
      v14 起筛选整体收进搜索框下面的下拉面板。）
v13（2026-10-03 批次 B）：
    **题解包三个文件级入口**（菜单栏「题解包」；只动菜单 / 入口区，不碰搜索筛选区）：
      ① 导入题解包…：选 zip / 已解压的目录 → 后台跑 `import_solution` dry（不写盘）→
         弹报告窗口；校验全过（退出码 0）才出现「应用到数据根」按钮，按了才真 `--apply`
         （落盘后自动刷新本窗口的表格）。
      ② 导出题解包…：选场次（状态表里「牛客周赛 Round N」形式）+ 可选题号 → 生成
         题解包 zip（默认存桌面）。
      ③ 一键校验…：同 ① 的 dry，但只出报告、不给落盘按钮。
      任务跑在后台线程（界面不卡；同一时刻只允许一个包任务）。执行走**进程内调用**
      （不是子进程）—— PyInstaller 打的 exe（frozen）里没有解释器可用，两种环境
      统一这条路径（子齿轮由 `toolutil.run_sibling` 在 frozen 下同样进程内化）。
      无窗口命令行版（CI / 自动化）：`--pack-import <包> [--apply]` /
      `--pack-check <包>` / `--pack-export Round163[-G] [-o 出.zip] [--log 日志]`。

v14（2026-10-03）：
    **搜索 + 筛选合并成一个「下拉」**：v13 的第二行筛选区整行删除，内容并进搜索框下面的
    下拉面板（行序 = 搜索 / 知识点 / 难度 / 状态；展开时面板占位、**表格整体下移**，收起恢复）。
    ① 「状态」不再是 6 个小按钮，改成**多选清单**（`lb_status`：`1. 未做`…`6. 巩固` 六行，
       跟状态浮层同一个选项框结构）—— ↑↓ 移光标、空格 / Enter / 1~6 勾选 / 取消，
       勾选 = 强调色底（多选并集，再与知识点 / 难度 / 搜索取交集）。
    ② 匹配逻辑一个字没换：仍是 `filter_state()` → `status_report.filter_rows`
       （`status_on` / `var_know` / `var_diff` 属性名照旧，命令行同条件必同一结果）。
       「筛出 N 题」挪进面板底部；**面板收起时同一行字挂到窗口第一行右端**（`var_hits_min`）
       —— 筛选开着却不给提示的状态不许出现。
    ③ 键位：搜索框 ↓ = 展开（第一下只展开、焦点留在框里能接着打字；再按 ↓ 才进「知识点」）、
       ↑ = 收起；面板里 ↑↓ 逐行走（搜索 → 知识点 → 难度 → 状态）、Esc 逐层退回
       （框里有字先清空 → 上退一行 → 状态 → 难度 → 搜索框 → 收面板 → 回主页面）；
       离开搜索站（Tab 走 / Enter 跳回总表）自动收面板，条件一个字不动。
    ④ Tab 轮换：v13 五站 → v14 两站（主页面 ⇄ 搜索）；面板里任意一行都按「搜索」站算。

v15（2026-10-03）：
    **只动观感，键位与匹配逻辑一个字没改**（用户点名：输入框整洁一点、搜索框长一点）：
    ① 搜索框宽 13 → **26**（约两倍，能看全「Round 163 E」这类词；固定宽，不随窗口伸缩）。
    ② 四行标签统一 3 个字宽（`搜　索` / `知识点` / `难　度` / `状　态`，两字的中间插一个
       全角空格）—— 搜索框与面板里两个输入框、状态清单的**左缘排成一条竖线**。
    ③ 输入框格式：`Nav.TEntry` 统一 **padding=(7, 5)**（字不贴边、三个框一样高）。
    ④ **灰字占位提示**（`_add_placeholder`）：框空着且没焦点时显示浅灰提示语
       （搜索「场次 / 题名 / 知识点 / 难度」、知识点「如 DP、二分」、难度「如 1700-1900」），
       聚焦或打字即隐。提示是**浮在输入框上的 Label**，不写进 textvariable —— 不参与匹配。
    ⑤ 面板底部「清空」按钮**删除**（v15 末用户点名「去掉清空选项」；底排只留「筛出 N 题」，
       要清条件走 Esc 逐层退回）；第一行元素间距调匀。

v16（2026-10-03，观感版）：用户从三方案里选「只换观感、不动布局」，另点名「能合并的
    按钮弄到同一行」——**题解包三弹窗只动观感 + 两处按钮合排**（键位、匹配逻辑、其余
    控件位置一律未动）：
    ① 新增 ttk 样式 `Accent.TButton`（强调色底 + 白字；禁用自动变浅灰）—— 选包窗
       「开始」、导出窗「开始导出」、报告窗「应用到数据根」用它。
    ② 报告窗状态行跑完按结果着色：成功绿 `C_OK` / 失败红 `C_ERR`（跑着仍是强调色）。
    ③ 选包窗路径框加灰字占位「包路径」（`register=False`，弹窗临时框不进 `_ph_syncs`）；
       空路径时「开始」禁用（原来点了静默没反应）。
    ④ 按钮合排：选包窗**四个按钮并成一行**（「选 zip…」「选目录…」靠左、「取消」「开始」
       靠右，不再单占底排 —— 用户二次看图点名）；导出窗「另存为…」从单独一行 →
       挪到输出框同一行右端。

记住上次（v4）：
    关窗时把 窗口大小 + 位置 + 排序字段 + 升/降序 存成脚本同目录的 `status_gui.config.json`
    （纯 LF、UTF-8、键用小写英文）；下次打开照上次来，文件没有 / 读不动 / 值不对就回默认。
    **--selftest / --smoke 一律不碰这个文件**（StatusGui(config_path=None) 即关闭配置读写）。
    消息提示 3 秒后自动消失（TOAST_MS），不再一直挂着；v9 起它在窗口顶部那一行的最右端。
    （v11：全屏中关窗存的是「进全屏前」的窗口态 geometry —— 不存整屏尺寸，也不存 1x1。）

职责边界（与 v1 同）：
  * 解析 / 状态集合 / 队列阈值 **import 自**同目录的 `status_report.py`；场次的排序键
    （比赛名 → 场次号，v6 追加 6）走 `toolutil.parse_contest`，认不出的场次排最后；
    本文件自己只定两样：v2 的 7 列表头、v3 起沿用的可排序三列 SORTABLE
    （tools 同步后自动改走 SR.parse_table）。
  * 写回只改目标行的「状态」「日期」单元格，**其余行逐字节不变**；纯 LF、无 BOM。
  * 写前备份复用同目录 `toolutil.py` 的 `backup_to_repo`，原目录不留 .bak。
"""

import argparse
import ctypes
import datetime
import glob
import hashlib
import io
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import traceback

sys.dont_write_bytecode = True          # 只读地 import 工具目录：绝不往那儿写 __pycache__

import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont, messagebox


def _load_tool(name):
    """按脚本同目录 import（从任何工作目录启动都能找到兄弟模块）。"""
    tools = os.path.dirname(os.path.abspath(__file__))
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return __import__(name)


SR = _load_tool("status_report")        # 解析器与规则常量的唯一出处
toolutil = _load_tool("toolutil")       # 备份实现

DEFAULT_FILE = SR.DEFAULT_FILE
STATES = list(SR.STATES)                # v10：未做 / 不会 / 待重写 / 复现AC / 独立AC / 巩固（6 个，自动跟随 status_report）

# v2 表头：备注列删除，知识点列插在 题名 与 难度 之间。
NEW_HEADER = ["场次", "题号", "题名", "知识点", "难度", "状态", "日期"]
_SR_HEADER = list(getattr(SR, "HEADER", []))
SR_SYNCED = (_SR_HEADER == NEW_HEADER)  # tools/status_report.py 是否已同步到新表头
HEADER = list(NEW_HEADER)

SORTABLE = ("场次", "难度", "日期")              # 可排序的三列（v3 起取消「知识点」）
KEY_TABLE = """\
Tab / Shift+Tab    焦点轮换：主页面 ⇄ 搜索（面板里各行都算「搜索」站；Shift+Tab 反向）
← / →              横着走：总表 → 1 待重写 → 2 待补题 → 3 复习 → 4 抽检，两头绕回
/                  跳到搜索框
Esc                逐层退回：框里有字先清空 → 上退一行 → 收起面板 → 回主页面
↑ ↓                移动选中行
PgUp / PgDn        翻页
1 ~ 6              选中行直接改状态（不开浮层）
Enter              状态浮层：↑↓ 选 · 1~6 直选 · Enter 确认 · Esc 取消
Alt+Enter          打开这题的资料（算法库记录 → 场题解）
Shift+Enter        打开原题（先重做、别偷看题解）
Ctrl+Z             撤销上一步改动（可连撤，本窗口内）
S / R              换排序字段 / 反转升降序（总表页）
F5                 从磁盘重读
F11                全屏开关（再按一次退出）
?                  快捷键一览
下拉面板           搜索框 ↓ 展开 / ↑ 收起：知识点 · 难度 框 + 状态多选，只筛总表
面板里 ↓ / ↑       知识点 → 难度 → 状态 逐行走 ｜ 状态列表：空格 / Enter / 1~6 勾选 · Esc 退一层"""                   # 与 说明.md 的键位表一字不差（v14：17 行；v13 的「筛选区 / 状态按钮上」两行并进面板两行，裸 F 那行随 v9 筛选删除，F5 / F11 不算；v15：观感改 + 删掉「清空 = 全清」尾句——按钮同版删除）
TODAY_COLS = ["场次", "题号", "题名", "知识点", "难度", "日期"]
EDITABLE = ("状态", "日期")                      # 唯一允许改的两格
CELL_STATE = HEADER.index("状态")
CELL_DATE = HEADER.index("日期")
REVIEW_DAYS = 7                                 # 对应 status_report.py 的 --days 默认值（D+7 复习）
DONE_STATES = ("独立AC", "复现AC")              # v9「做对」= 这两个状态（「巩固」不算）
# v9：PLACEHOLDER（`无匹配` / `无` 占位行）整套删除 —— 空表就是空表。
# 自测 / 冒烟的备份镜像目录：夹具是临时的，别把 .bak 混进真 md 的备份目录
TEST_BACKUP_ROOT = os.path.join(tempfile.gettempdir(), "status_gui_test_backups")
CONFIG_NAME = "status_gui.config.json"          # 「记住上次」的配置文件（= 脚本同目录）
TOAST_MS = 3000                                 # 底部保存提示 3 秒后自动消失
UNDO_MAX = 50                                   # v12：Ctrl+Z 撤销栈容量（多步；只在内存、不跨重启）
DATA_ROOT = toolutil.DATA_ROOT                      # v6 追加：资料查找的根（算法库记录 / 场题解），测试里可换沙箱


# ================================================================ 题解包（v13）
# 三入口（菜单「导入 / 导出 / 一键校验」）的纯逻辑都在这一节 —— 不开窗口、不碰磁盘，
# selftest 直接断言；真正的执行在 StatusGui 的方法与 pack_cli()（无窗口命令行入口）里。
PACK_MENU_LABEL = "题解包"
PACK_IMPORT_LABEL = "导入题解包…"
PACK_EXPORT_LABEL = "导出题解包…"
PACK_CHECK_LABEL = "一键校验…"


def pack_import_argv(pack, root, apply_=False):
    """「导入题解包」→ import_solution.main 的参数列表（dry 或 --apply）。"""
    argv = [pack]
    if apply_:
        argv.append("--apply")
    argv += ["--root", root]
    return argv


def pack_export_argv(target, out, root):
    """「导出题解包」→ export_solution.main 的参数列表；out 为空 = 用工具的默认命名。"""
    argv = [target]
    if out:
        argv += ["-o", out]
    argv += ["--root", root]
    return argv


def pack_verdict(rc, applied):
    """导入跑完的（退出码, 是否 --apply）→（还能不能「应用到数据根」, 状态行文案）。"""
    if rc == 0:
        if applied:
            return False, "导入完成 —— 文件 / 索引 / 状态表 / 台账四处都对上了"
        return True, "校验通过 —— 可以应用到数据根"
    if rc == 1:
        return False, "包里有不合格项（看上面的「问题」清单），改完再来"
    return False, "包不可读或参数不对（看上面的报错）"


def pack_round_choices(rows):
    """状态表行 → 可导出的场次列表（「牛客周赛 Round N」形式，按场次号降序）。

    export_solution 目前只认牛客周赛（别的比赛等通用化批次），筛选口径跟它一致。
    """
    seen, out = set(), []
    for r in rows:
        s = r.get("场次", "")
        name, _n = toolutil.parse_contest(s)
        if name == "牛客周赛" and s not in seen:
            seen.add(s)
            out.append(s)
    out.sort(key=round_num, reverse=True)
    return out


# 统一配色：浅底 + 一个强调色
C_BG = "#f4f6fb"
C_PANEL = "#ffffff"
C_ACCENT = "#2f6fed"
C_ACCENT_DARK = "#1b4bb8"
C_ACCENT_LIGHT = "#dbe7ff"
C_ZEBRA = "#eef2f8"
C_TEXT = "#1f2430"
C_MUTED = "#667085"
C_LINE = "#b9c3d6"          # v6：输入控件的常态边框（聚焦时换成强调色 C_ACCENT）
C_SELECT_OFF = "#c9d4e6"    # v6：失焦时选中行的底色（聚焦时是 C_ACCENT —— 一眼看出焦点在哪）
C_PLACEHOLDER = "#9aa6ba"   # v15：空输入框里的灰字占位提示（比 C_MUTED 再浅一档）
LABEL_PAD = "　"            # v15：全角空格 —— 两字标签插一个 = 三字宽，四行控件的左缘才能对齐
C_OK = "#1a7f37"            # v16：报告窗跑完的成功状态行（绿）
C_ERR = "#c0392b"           # v16：报告窗跑完的失败状态行（红）

# 场次号：优先用 tools 侧导出的正则；tools 正在做「多平台场次键」重构、这个常量可能还没回来，
# 兜底用本地的同款正则（= 改造前的 SR.ROUND_RE：取场次文本里第一串数字），别让 GUI 因 tools 改版打不开。
ROUND_RE = getattr(SR, "ROUND_RE", None) or re.compile(r"(\d+)")
CF_RE = re.compile(r"(\d+)")


# ================================================================ 文本读写
def read_text(path):
    """整文件读成 str；newline="" 关掉换行翻译，字节原样进来。"""
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path, text):
    """整文件写回：UTF-8 无 BOM、不翻译换行（因此写出去就是纯 LF）。"""
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def assert_plain(path):
    """写后自检：纯 LF、无 BOM。"""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError("文件带 BOM：%s" % path)
    if b"\r" in raw:
        raise RuntimeError("文件不是纯 LF（出现 CR）：%s" % path)


# ================================================================ 配置（记住上次）
DEFAULT_CFG = {"geometry": "", "sort_col": "场次", "sort_desc": False}


def config_path_default():
    """「记住上次」的配置文件 = 脚本同目录的 status_gui.config.json。

    frozen（exe）下脚本在一个**一次性临时解包目录**里 —— 写那儿等于每次开窗都丢；
    跟着 exe 走（`toolutil.REPO_ROOT` 在 frozen 下就是 exe 所在目录）。
    """
    d = (toolutil.REPO_ROOT if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(d, CONFIG_NAME)


def _geometry_ok(g, sw=None, sh=None):
    """`1200x800+100+80` 这种 geometry 值认不认。

    sw / sh 不给 = 只查格式（读配置时）；给了屏幕尺寸 = 连「窗口得有一块留在屏幕里」一起查，
    跑出屏幕（拔了副屏、换了分辨率）就当没有，回默认居中（v4 派发要求）。
    """
    m = re.match(r"^(\d{3,5})x(\d{3,5})\+(-?\d+)\+(-?\d+)$", g or "")
    if not m:
        return False
    if sw is None or sh is None:
        return True
    w, h, x, y = (int(v) for v in m.groups())
    return x >= -w + 120 and y >= 0 and x <= sw - 120 and y <= sh - 80


def load_config(path):
    """读上次的 窗口大小位置 / 排序字段 / 升降序。

    文件没有 / 读不动 / 不是 JSON / 值不对 —— 一律回默认，**不抛错、不崩**（v4 派发要求）。
    """
    cfg = dict(DEFAULT_CFG)
    if not path:
        return cfg
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return cfg
    if not isinstance(data, dict):
        return cfg
    g = data.get("geometry")
    if isinstance(g, str) and _geometry_ok(g):
        cfg["geometry"] = g
    if data.get("sort_col") in SORTABLE:
        cfg["sort_col"] = data["sort_col"]
    if isinstance(data.get("sort_desc"), bool):
        cfg["sort_desc"] = data["sort_desc"]
    return cfg


def save_config(path, cfg):
    """关窗时存一次：纯 LF、UTF-8 无 BOM、键用小写英文；写不动就返回 False（不抛）。"""
    if not path:
        return False
    data = {"geometry": cfg.get("geometry") or "",
            "sort_col": cfg.get("sort_col") if cfg.get("sort_col") in SORTABLE else "场次",
            "sort_desc": bool(cfg.get("sort_desc", False))}
    txt = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    except OSError:
        return False
    return True


# ================================================================ 表格行
def row_segments(line):
    """表格行 → (segments, cells)。

    segments = 每格「两竖线之间」的 [起, 止) 区间（用于原地替换）；
    cells    = 去掉首尾空白、还原 \\| 之后的单元格文本。不是表格行返回 (None, None)。
    """
    if not line.lstrip().startswith("|"):
        return None, None
    pipes, i, n = [], 0, len(line)
    while i < n:
        if line[i] == "\\" and i + 1 < n and line[i + 1] == "|":
            i += 2
            continue
        if line[i] == "|":
            pipes.append(i)
        i += 1
    if len(pipes) < 2:
        return None, None
    segs, cells = [], []
    for k in range(len(pipes) - 1):
        a, b = pipes[k] + 1, pipes[k + 1]
        segs.append((a, b))
        cells.append(line[a:b].strip().replace("\\|", "|"))
    return segs, cells


def render_row(cells):
    """按本表的排版风格拼一行（每格两侧各一个空格，空格格写两个空格 —— 与真表
    `| 未做 |  |` 的既定形态一致；v6.1 修复前这里写单空格，会让「空日期格」与
    replace_cells 的写回形态对不上）。"""
    return "|" + "|".join((" " + c + " ") if c else "  " for c in cells) + "|"


def replace_cells(line, changes):
    """只替换 changes = {列名: 新值} 指定的单元格；该行其余字节原样保留。"""
    segs, cells = row_segments(line)
    if segs is None or len(segs) != len(HEADER):
        raise ValueError("不是状态表数据行：%r" % line)
    edits = []
    for name, val in changes.items():
        if name not in HEADER:
            raise ValueError("没有这一列：%s" % name)
        text = (val or "").replace("|", "\\|")          # 半角竖线要转义，别把表格切断
        a, b = segs[HEADER.index(name)]
        edits.append((a, b, (" " + text + " ") if text else "  "))
    for a, b, seg in sorted(edits, key=lambda e: e[0], reverse=True):
        line = line[:a] + seg + line[b:]
    return line


def _header_row(lines):
    """找表头行下标：整行切分结果必须**精确等于** v2 的 7 列。找不到返回 None。"""
    for i, ln in enumerate(lines):
        if SR.split_cells(ln) == HEADER:
            return i
    return None


def locate_row(lines, key):
    """按（场次, 题号）在原文里定位唯一数据行，返回 0 基行下标。

    扫描范围与 status_report.parse_table 一致（表头 + 分隔线之后、到主表结束为止）。
    命中 0 行或 >1 行都报错——宁可拒绝写，也不改错行。
    """
    start = _header_row(lines)
    if start is None:
        raise ValueError("没找到表头「| %s |」" % " | ".join(HEADER))
    hits = []
    for i in range(start + 2, len(lines)):
        cells = SR.split_cells(lines[i])
        if not cells or len(cells) != len(HEADER):
            break                                       # 主表结束
        if set("".join(cells)) <= set("-: "):
            continue
        if cells[0] == key[0] and cells[1] == key[1]:
            hits.append(i)
    if len(hits) != 1:
        raise ValueError("定位到 %d 行（应恰好 1 行）：%s %s" % (len(hits), key[0], key[1]))
    return hits[0]


def _parse_table_local(path):
    """status_report.parse_table 的等价实现，只把表头常量换成 v2 的 7 列。

    tools/status_report.py 的 HEADER 同步成新表头后本函数不再被走到（见 parse_rows）。
    """
    text = read_text(path)
    lines = text.split("\n")
    start = _header_row(lines)
    if start is None:
        raise SystemExit("★ 没找到表头「| %s |」：%s" % (" | ".join(HEADER), path))
    rows = []
    for ln in lines[start + 2:]:          # +2：表头下面紧跟一行分隔线
        c = SR.split_cells(ln)
        if not c:
            break                          # 主表结束（后面是别的段落）
        if len(c) != len(HEADER):
            break
        if set("".join(c)) <= set("-: "):
            continue
        r = dict(zip(HEADER, c))
        r["_i"] = len(rows)
        rows.append(r)
    return rows


def parse_rows(path):
    """读状态表：优先用 status_report.parse_table，没同步时用等价兜底。"""
    if SR_SYNCED:
        return SR.parse_table(path)
    return _parse_table_local(path)


def _check_changes(changes):
    """只许改两格；状态必须是 6 个合法值之一，日期必须是空或 YYYY-MM-DD。"""
    for name in changes:
        if name not in EDITABLE:
            raise ValueError("只许改 %s，不收：%s" % (" / ".join(EDITABLE), name))
    if "状态" in changes and changes["状态"] not in STATES:
        raise ValueError("状态「%s」不在 6 个合法值里" % changes["状态"])
    if changes.get("日期") and SR.parse_date(changes["日期"]) is None:
        raise ValueError("日期「%s」不是 YYYY-MM-DD" % changes["日期"])


# ================================================================ 写回
def backup_file(path, src_root=None):
    """备份规则的唯一实现（toolutil.backup_to_repo）；返回 .bak 路径。"""
    return toolutil.backup_to_repo(path, src_root)


def save_changes(path, key, changes, backup_src_root=None):
    """写回：重读文件 → 定位唯一目标行 → 只替换「状态 / 日期」→ 备份 → 落盘 → 复读校验。

    返回 (备份路径, 旧文本, 新文本)；两格都没变时返回 (None, 原文本, 原文本)（不写盘、不备份）。
    """
    _check_changes(changes)
    old = read_text(path)
    old_lines = old.split("\n")
    i = locate_row(old_lines, key)
    new_line = replace_cells(old_lines[i], changes)
    if new_line == old_lines[i]:
        return None, old, old
    new_lines = list(old_lines)
    new_lines[i] = new_line
    diff = [k for k in range(len(old_lines)) if old_lines[k] != new_lines[k]]
    if diff != [i]:
        raise RuntimeError("内部错误：应当只改第 %d 行，实际改了 %r" % (i, diff))
    new = "\n".join(new_lines)
    bak = backup_file(path, backup_src_root)
    write_text(path, new)
    if read_text(path) != new:
        raise RuntimeError("写后复读不一致：%s" % path)
    assert_plain(path)
    return bak, old, new


# ================================================================ 统计、队列、排序
def annotate(rows, today):
    """补 _date / _ago（口径同 status_report.build）。"""
    for r in rows:
        d = SR.parse_date(r["日期"]) if r["日期"] else None
        r["_date"] = d
        r["_ago"] = (today - d).days if d else None
    return rows


def state_counts(rows):
    return {s: sum(1 for r in rows if r["状态"] == s) for s in STATES}


def done_count(rows):
    """最近 N 天做对的题数（v9 口径）：窗口 = SR.RECENT_DAYS 天（默认 7）。

    「做对」= 状态 ∈ DONE_STATES（独立AC / 复现AC）——**「巩固」不算**，超期（_ago >= N）
    与没日期的（_ago is None）也都不算。
    """
    return sum(1 for r in rows if r["状态"] in DONE_STATES
               and r["_ago"] is not None and 0 <= r["_ago"] < SR.RECENT_DAYS)


def round_num(s):
    m = ROUND_RE.search(s or "")
    return int(m.group(1)) if m else 10 ** 9


def contest_key(s):
    """场次文本 → (比赛名, 号)；认不出给 (None, None)（照工具链 parse_contest 的口径，不猜）。

    v6 追加 6：正常路径走 `toolutil.parse_contest`（「牛客周赛 Round 161」与
    「Codeforces Round 161」是两场比赛，只按裸号排会互相插队）；只有 toolutil 加载失败 /
    没有这个函数时，才退到本地旧口径（裸号，比赛名给空串）—— 别让 GUI 因工具链改版打不开。
    """
    fn = getattr(toolutil, "parse_contest", None)
    if fn is not None:
        try:
            name, num = fn(s)
            return (name, num)
        except Exception:
            pass
    if ROUND_RE is not None:
        m = ROUND_RE.search(s or "")
        if m:
            return ("", int(m.group(1)))
    return (None, None)


def contest_num(s):
    """场次排序键：认得出 → (0, 比赛名, 号)（比赛名先分组、组内按号）；认不出 → (1, "", 0) 排最后。

    用 0 / 1 前缀打头，是为了让「认不出」与「认得出」在同一位置上可比（None 与 str / int 不可比）。
    """
    name, num = contest_key(s)
    if name is None:
        return (1, "", 0)
    return (0, name, num if num is not None else 10 ** 9)


def cf_num(s):
    """难度列按「CF 后面的数字」比大小；非 CF / 空的排最后。"""
    m = CF_RE.search(s or "")
    return int(m.group(1)) if m else 10 ** 9


def _row_order_key(r):
    """并列时的稳定次序（打底：比赛名 → 场次号 → 题号 → 原行序）。

    v6 追加 6：场次键改用工具链的 `toolutil.parse_contest`（见 contest_key / contest_num）——
    不同比赛各归各的组、不互相插队，认不出的场次（如「洛谷月赛 Round 5」）排最后；
    toolutil 加载失败时 contest_key 自会退到本地旧口径，GUI 照常能开。
    """
    return contest_num(r["场次"]) + (r["题号"], r["_i"])


def sort_rows(rows, col, desc):
    """排序：主键按 col（升 / 降），并列时永远按 比赛名→场次号→题号 升序（_row_order_key）。

    日期列的空值**永远排最后**（升序降序都一样）；场次列认不出的（非「比赛名 Round 号」
    形式）也排最后；场次键 v6 追加 6 起走 toolutil.parse_contest（不同比赛不互相插队）。
    """
    items = list(rows)
    items.sort(key=_row_order_key)              # 打底：比赛名 → 场次号 → 题号（并列时的稳定次序）
    if col == "日期":
        dated = [r for r in items if r["_date"]]
        undated = [r for r in items if not r["_date"]]
        dated.sort(key=lambda r: r["_date"], reverse=desc)
        return dated + undated
    if col == "场次":
        key = lambda r: contest_num(r["场次"])
    elif col == "难度":
        key = lambda r: cf_num(r["难度"])
    elif col == "知识点":
        key = lambda r: (r["知识点"] == "", r["知识点"])
    else:
        return items
    items.sort(key=key, reverse=desc)
    return items


def segment_specs():
    """看板四段：名字 + 判据（阈值与状态集合全部取 status_report 的常量）。"""
    return [
        ("待重写", "① 待重写"),
        ("待补题", "② 待补题"),
        ("D+%d 复习" % REVIEW_DAYS, "③ D+%d 复习" % REVIEW_DAYS),
        ("D+%d 抽检" % SR.KEEP_DAYS, "④ D+%d 抽检" % SR.KEEP_DAYS),
    ]


def segment_rows(rows, idx):
    """第 idx 段（0~3）的题目清单；规则与 status_report.build 的 ①–④ 完全一致。

    「未做」不进任何一段（照 status_report.py 的规则；v10 起状态收成 6 个，四段只认
    待重写 / 不会 / 独立AC+复现AC / 巩固）。
    """
    if idx == 0:
        return sorted([r for r in rows if r["状态"] == SR.TODO_HARD], key=_row_order_key)
    if idx == 1:
        return sorted([r for r in rows if r["状态"] in SR.TODO_FILL], key=_row_order_key)
    if idx == 2:
        return sorted([r for r in rows if r["状态"] in SR.REVIEW
                       and r["_ago"] is not None and r["_ago"] >= REVIEW_DAYS],
                      key=lambda r: -r["_ago"])
    return sorted([r for r in rows if r["状态"] == SR.KEEP
                   and r["_ago"] is not None and r["_ago"] >= SR.KEEP_DAYS],
                  key=lambda r: -r["_ago"])


# ================================================================ 自测 fixture
FIXTURE_ROWS = [
    ("牛客周赛 Round 200", "A", "签到一", "模拟", "CF 800", "巩固", "2026-08-01"),
    ("牛客周赛 Round 199", "C", "小红的密码锁", "字符串 ｜ 哈希、双指针", "CF 1400", "独立AC", "2026-09-20"),
    ("牛客周赛 Round 205", "B", "数组重排", "贪心", "CF 1100", "未做", ""),
    ("牛客周赛 Round 188", "D", "树上路径", "树链剖分 ｜ 线段树、LCA", "CF 1900", "待重写", "2026-09-30"),
    ("牛客周赛 Round 210", "E", "区间DP", "动态规划 ｜ 前缀和", "CF 1700", "待重写", "2026-09-25"),
    ("牛客周赛 Round 197", "A", "求最大", "模拟", "CF 800", "未做", ""),
    ("牛客周赛 Round 201", "F", "构造难题", "构造", "CF 2100", "不会", "2026-08-15"),
    ("牛客周赛 Round 202", "B", "双指针", "双指针", "CF 1200", "复现AC", "2026-09-28"),
    ("牛客周赛 Round 203", "D", "树形DP", "动态规划 ｜ 树形DP", "CF 1800", "巩固", "2026-08-20"),
    ("牛客周赛 Round 204", "C", "并查集", "并查集", "CF 1500", "独立AC", "2026-10-01"),
    ("牛客周赛 Round 207", "B", "贪心题", "贪心 ｜ 排序", "CF 1300", "复现AC", "2026-09-29"),
    ("牛客周赛 Round 208", "E", "期望DP", "概率与期望 ｜ 动态规划", "CF 2000", "不会", "2026-08-30"),
]


def fixture_text():
    """造一份自测用状态表：新表头 + 12 行（6 个状态各 2 行、含空日期 / 带 ｜ 的知识点 / 场次乱序）。"""
    lines = ["# 题目状态（status_gui 自测 fixture，可整份重建）", "",
             "| " + " | ".join(HEADER) + " |",
             "|" + "|".join(["---"] * len(HEADER)) + "|"]
    for c in FIXTURE_ROWS:
        lines.append(render_row(list(c)))
    lines += ["", "## 表后说明（不是表格行，用来验证解析器在表尾停住）",
              "- 日期 = 最后一次状态变更日；空日期表示还没变过状态。"]
    return "\n".join(lines) + "\n"


def write_fixture(path):
    write_text(path, fixture_text())
    return path


def control_fixture_text():
    """按 tools/status_report.py **当前**的表头造一份对照 fixture。

    只在「它的 HEADER 还没同步到 v2」时用来验证子进程调用链本身可用；
    同步之后这个函数不会再被走到（selftest 里走的是严格断言那一支）。
    """
    hdr = _SR_HEADER or ["场次", "题号", "题名", "难度", "状态", "日期", "备注"]
    lines = ["# 对照件（表头跟 tools 现在的一致）", "",
             "| " + " | ".join(hdr) + " |",
             "|" + "|".join(["---"] * len(hdr)) + "|"]
    for c in FIXTURE_ROWS:
        vals = []
        for h in hdr:
            vals.append("" if h in ("知识点", "备注") else c[HEADER.index(h)])
        lines.append(render_row(vals))
    return "\n".join(lines + [""]) + "\n"


# ================================================================ 输入法守卫（v8）
class ImeGuard(object):
    """v8：Windows 输入法守卫 —— 只留搜索框收中文，别的地方一律把输入法摘掉。

    症状（用户原话「现在中文输入法按快捷键会直接跳出输入法」）：中文输入法开着时，焦点在
    总表 / 看板清单上按 S / R / F / `/` / `?` / 数字键（浮层里的状态直选），输入法候选窗会跳出来把按键吃掉 ——
    Windows 给**每个窗口**默认都关联了输入法上下文（可编辑控件 Tk 自己会管，非输入控件没人摘）。

    机制：ImmAssociateContext(hwnd, 0) 摘掉、ImmAssociateContext(hwnd, imc) 还原（imc = 摘掉时
    返回的旧上下文，各自存好）；每个 HWND 各摘自己那一份、互不影响（2026-10-03 实测）。
    窗口建好后把主窗口里所有控件的 HWND 都摘一遍；之后靠 <FocusIn> 兜底（挂 root + 各 Toplevel
    —— 实测独立窗口的 <FocusIn> 不会冒到 root 上）：拿到焦点的是搜索框 → 还原 搜索框 + 主窗口，
    是别的控件 → 把它的 HWND 摘掉（没见过的 HWND 也照摘）。

    只在 sys.platform == "win32" 做；其余平台 / 拿不到 imm32 / 任何 API 异常 —— 全部静默降级成
    no-op（available = False 时所有方法直接返回），窗口行为与 v7 完全一致。
    """

    def __init__(self, root, keep=()):
        self.root = root
        self.keep = tuple(w for w in keep if w is not None)  # 允许收中文的控件（搜索框）
        self.available = False   # 「可用」标志：置假 = 整条守卫 no-op（冒烟 (gg) 用它验降级路径）
        self.default_ctx = None  # 摘之前主窗口的上下文（= 线程默认；系统没有输入法环境时是 None）
        self._imm = None
        self._saved = {}         # hwnd(int) -> 摘掉时存下的旧上下文（attach 用它还原）
        try:
            if sys.platform != "win32":
                return
            imm = ctypes.windll.imm32
            # 64 位下必须设 argtypes / restype = c_void_p（默认 c_int 有截断 HWND 的风险 —— 实测口径）
            imm.ImmGetContext.restype = ctypes.c_void_p
            imm.ImmGetContext.argtypes = [ctypes.c_void_p]
            imm.ImmAssociateContext.restype = ctypes.c_void_p
            imm.ImmAssociateContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            self._imm = imm
            self.available = True
        except Exception:
            self._imm = None
            self.available = False

    # ---------------------------------------------------------- 对外
    def install(self):
        """窗口建好后调用一次：先取默认上下文、把主窗口全部控件摘一遍，再挂 <FocusIn>。"""
        if not self.available:
            return
        try:
            self.default_ctx = self._ctx(self.root)
            self.detach_tree(self.root)
            self.watch(self.root)
        except Exception:
            pass

    def watch(self, win):
        """给这个窗口（root / 各 Toplevel）挂 <FocusIn> 兜底；独立窗口的事件不会冒到 root 上。"""
        if not self.available:
            return
        try:
            win.bind("<FocusIn>", self.on_focus_in, add="+")
        except Exception:
            pass

    def on_focus_in(self, event=None):
        """焦点变了：搜索框拿到焦点 → 还原输入法；别的控件 → 摘掉它（搜索框也一并摘）。"""
        if not self.available:
            return
        try:
            w = event.widget if event is not None else None
            target = w if w in self.keep else None
            if target is None:                   # 顶层 / 别的窗口的 FocusIn：以 Tk 当前焦点为准兜底
                try:
                    f = self.root.focus_get()
                except Exception:
                    f = None
                target = f if f in self.keep else None
            if target is not None:
                for k in self.keep:
                    self.attach(k)
                # 主窗口 HWND 也还原：键盘焦点在顶层 / 子窗口两种口径下都能打中文
                self.attach(self.root)
            else:
                self.detach(w)               # 没见过的 HWND 也照摘
                for k in self.keep:
                    self.detach(k)           # 离开搜索框立刻摘：回表格再按快捷键不再弹输入法
                self.detach(self.root)
        except Exception:
            pass

    def detach_tree(self, win):
        """win 子树里每个控件都摘一遍（含 win 自己）。"""
        if not self.available:
            return
        try:
            self.detach(win)
            for c in win.winfo_children():
                self.detach_tree(c)
        except Exception:
            pass

    # ---------------------------------------------------------- 内部（都吞异常）
    def _hwnd(self, widget):
        """控件 → HWND（int）；拿不到（None / 已销毁）给 None。"""
        try:
            return int(widget.winfo_id()) if widget is not None else None
        except Exception:
            return None

    def _ctx(self, widget):
        """这个控件当前的输入法上下文；没挂 / 不可用 → None。"""
        if not self.available:
            return None
        h = self._hwnd(widget)
        if h is None:
            return None
        try:
            return self._imm.ImmGetContext(ctypes.c_void_p(h))
        except Exception:
            return None

    def detach(self, widget):
        """摘掉这个控件的输入法（旧上下文存起来供 attach 还原）；任何异常都吞掉。"""
        if not self.available:
            return
        h = self._hwnd(widget)
        if h is None:
            return
        try:
            old = self._imm.ImmAssociateContext(ctypes.c_void_p(h), None)
            if h not in self._saved:         # 已经摘过别再存：别把真正的旧上下文冲成 None
                self._saved[h] = old
        except Exception:
            pass

    def attach(self, widget):
        """还原这个控件的输入法（用摘掉时存的旧上下文）；没存过 / 不可用就不动。"""
        if not self.available:
            return
        h = self._hwnd(widget)
        if h is None or h not in self._saved:
            return
        try:
            old = self._saved.pop(h)
            self._imm.ImmAssociateContext(ctypes.c_void_p(h), old)
        except Exception:
            pass


# ================================================================ 窗口
class StatusGui(object):
    def __init__(self, root, path, quiet=False, config_path=None):
        """config_path = 「记住上次」的配置文件路径；None = 不读也不写
        （--selftest / --smoke 走 None，绝不碰脚本同目录的 status_gui.config.json）。"""
        self.root = root
        self.path = path
        self.quiet = quiet                  # 冒烟/自测里不弹 messagebox
        self.backup_src_root = None         # 备份镜像目录的「来源目录」；None = 表自己所在目录
        self.config_path = config_path
        self.cfg = load_config(config_path)  # v4：窗口大小位置 + 排序字段 / 升降序
        self._msg_after = None               # 保存提示「3 秒后清空」的回调 id
        self.rows = []
        self.popup = None
        self.popup_lb = None
        self.popup_row = None
        self.popup_tree = None
        self.help_win = None                 # `?` 快捷键一览浮层
        self.help_prev = None                # 关掉一览后把焦点还给谁
        self.help_lbl = None                 # 一览里那张键位表（自测要核内容）
        self.sort_col = self.cfg["sort_col"]  # 默认：场次升序 → 题号升序；有配置就照上次
        self.sort_desc = self.cfg["sort_desc"]
        self.seg_idx = 0
        self._seg_sel = [None] * 4           # v10：看板四段各自记住上次选中的行（存 iid = str(_i)）
        self._seg_rebuild = False            # v10：refresh_today 重建清单的中间态（期间不动记忆）
        self.data_root = DATA_ROOT           # v6 追加：Alt+Enter 找资料的根（测试里换成沙箱）
        self._opener = getattr(os, "startfile", None)   # v6 追加：打开动作（测试里换假函数，绝不真开文件）
        self._undo_stack = []                # v12：Ctrl+Z 撤销栈（多步；只在内存、不跨重启）
        self._last_change = None             # v6~v11：只记一步 → v12 起 = 栈顶那份（栈空即 None）
        self.last_windowed_geometry = None   # v11：进全屏前记下的窗口态 geometry（全屏中关窗存这份）
        self._pack_job = None                # v13：正在跑的题解包后台任务（同时只许一个）
        self._ph_syncs = []                  # v15：三个占位提示的同步函数（程序改空 var 后手动喊一声）

        root.title("题目状态跟踪表")
        root.geometry("1320x800")
        root.minsize(1000, 620)
        root.configure(bg=C_BG)
        self.fam = self._pick_family()
        self._init_style()

        self._make_menu()                   # v13：菜单栏（题解包：导入 / 导出 / 一键校验）
        self._make_head()                   # v9：第一行 = 搜索 + 统计 + 消息（页头两行 / 底部行都删了）
        self._make_dropdown()               # v14：搜索框下的筛选下拉（原 v13 第二行筛选区整行并进来；默认收起）

        self.nb = ttk.Notebook(root, takefocus=0)   # v6：页签不进 Tab 轮换（鼠标点不受影响）
        self.nb.pack(fill="both", expand=True, padx=12, pady=(2, 4))
        self.tab_all = tk.Frame(self.nb, bg=C_BG)
        self.tab_today = tk.Frame(self.nb, bg=C_BG)
        self.nb.add(self.tab_all, text="总表")
        self.nb.add(self.tab_today, text="今天要做的")
        self._make_all_tab()
        self._make_today_tab()

        # v14：Tab / Shift+Tab = 两站焦点轮换（主页面 ⇄ 搜索；下拉面板里各行都算「搜索」站，见 _rotate_focus）
        root.bind("<Tab>", lambda e: self._rotate_focus(1))
        root.bind("<Shift-Tab>", lambda e: self._rotate_focus(-1))
        # v6 追加：Ctrl+Z 撤销挂 root —— 任何焦点下都生效（Entry 没有自己的 Ctrl+Z，不会打架）。
        # Alt+Enter 不挂 root：树自己的回车会先吃掉它（实测），得挂两棵树上（见两个 _make_*_tab）。
        root.bind("<Control-z>", self._undo)
        # v6：← / → 在一整条横排上走（总表 + 4 段 = 5 格，两头绕回；命中搜索框时让位）
        root.bind("<Left>", lambda e: self._nav_arrow(-1))
        root.bind("<Right>", lambda e: self._nav_arrow(1))
        root.bind("<F5>", self._on_reload_key)
        # v3 快捷键都挂在 root（子控件里按会冒泡上来；键位表见 KEY_TABLE / `?` 浮层）
        # v9：`F`（跳筛选）已随状态筛选整块删除 —— 不再绑任何东西。
        root.bind("<Key-slash>", self._on_focus_search)
        root.bind("<Key-s>", self._sort_next_key)
        root.bind("<Key-r>", self._sort_toggle_key)
        root.bind("<Key-question>", self._on_help_key)
        # v11：F11 全屏开关 —— 挂 bind_all（不在 root 上单绑）：总表 / 看板 / 搜索框，以及状态浮层 /
        # `?` 一览（都是独立 Toplevel）打开时，按 F11 都切换；处理函数 return "break"。
        root.bind_all("<F11>", self._on_f11_key)
        geom = self.cfg["geometry"]
        if geom and _geometry_ok(geom, root.winfo_screenwidth(), root.winfo_screenheight()):
            root.geometry(geom)             # v4：上次的窗口大小 / 位置（跑出屏幕就回默认）
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.reload()
        self.tree.focus_set()
        # v8：输入法守卫 —— 只留搜索框收中文，其余（总表 / 清单 / 浮层 / 一览…）一律摘掉输入法；
        # win32 之外 / 拿不到 imm32 / 任何异常都静默降级，窗口行为与 v7 完全一致（见 ImeGuard）。
        # v13：筛选区那两个输入框也收中文（keep 名单跟着 _in_text_widget 一起扩）。
        self.ime = ImeGuard(root, keep=(self.ent_search, self.ent_know, self.ent_diff))
        self.ime.install()

    # ------------------------------------------------------------ 配置 / 关窗
    def on_close(self):
        """关窗：先把 窗口大小 + 位置 + 排序 存下来（配置关闭时只关窗），再销毁。

        v11：全屏中关窗存的是「进全屏前」的窗口态 geometry（last_windowed_geometry）——
        别把整屏尺寸（或 1x1）留在配置里；窗口态下关窗照旧存当前 geometry。
        """
        if self._msg_after is not None:
            try:
                self.root.after_cancel(self._msg_after)
            except tk.TclError:
                pass
            self._msg_after = None
        if self.config_path:
            geom = self.root.geometry()
            if self._is_fullscreen() and self.last_windowed_geometry:
                geom = self.last_windowed_geometry            # v11：全屏中关窗 → 存进全屏前的窗口态
            save_config(self.config_path, {"geometry": geom,
                                           "sort_col": self.sort_col,
                                           "sort_desc": self.sort_desc})
        self.root.destroy()

    # ------------------------------------------------------------ 全屏（v11）
    def _is_fullscreen(self):
        """现在在全屏吗？`wm attributes -fullscreen` 的返回值随平台 / Tk 版本是 int 或 str
        （实测 = int 0/1）—— 一律归一成 bool；拿不到就当没全屏。"""
        try:
            v = self.root.attributes("-fullscreen")
        except tk.TclError:
            return False
        try:
            return bool(int(v))
        except (TypeError, ValueError):
            return str(v).strip().lower() in ("1", "true", "yes")

    def toggle_fullscreen(self):
        """F11：全屏 ⇄ 窗口态（浏览器同款，再按一次退出）。

        v11：进入前把当时的窗口态 geometry 记进 last_windowed_geometry（全屏中关窗存这份）；
        退出全屏后同步成当前（= 系统恢复出来的）geometry —— 窗口态下拖动改过大小，关窗仍存当前值。
        """
        if self._is_fullscreen():
            try:
                self.root.attributes("-fullscreen", False)
            except tk.TclError:
                return
            self.last_windowed_geometry = self.root.geometry()  # 退出 = 回到窗口态，同步缓存
        else:
            self.last_windowed_geometry = self.root.geometry()  # 记在进入前（此刻还是窗口态）
            try:
                self.root.attributes("-fullscreen", True)
            except tk.TclError:
                pass

    def _on_f11_key(self, event=None):
        """F11 按键处理：切换全屏；return "break"（挂在 bind_all 上，任何焦点都走这里）。"""
        self.toggle_fullscreen()
        return "break"

    # ------------------------------------------------------------ 外观
    def _pick_family(self):
        try:
            fams = set(tkfont.families(self.root))
        except tk.TclError:
            return "TkDefaultFont"
        for c in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "Segoe UI", "DejaVu Sans"):
            if c in fams:
                return c
        return "TkDefaultFont"

    def _init_style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")               # clam 才认下面的配色；vista 会吃掉一部分
        except tk.TclError:
            pass
        st.configure(".", background=C_BG, foreground=C_TEXT, font=(self.fam, 13))
        st.configure("TNotebook", background=C_BG, borderwidth=0)
        # v7：页签栏整条隐藏。页签高度来自「TNotebook.Tab」这个元素的布局（TNotebook 自己的布局
        # 本来就只含 Notebook.client，改它没用 —— 实测 delta 仍 48px），把 Tab 的布局清空后
        # 标签区不画、不占高度（实测 48px → 2px），客户端区贴顶。nb.select() / nb.index() 照旧。
        st.layout("TNotebook.Tab", [])
        st.configure("TNotebook.Tab", font=(self.fam, 13, "bold"), padding=(20, 9))
        # 选中只换颜色（v3：clam 默认会给选中页签加大 padding，显式压平成同一个值，尺寸不变）
        st.map("TNotebook.Tab",
               background=[("selected", C_PANEL), ("!selected", C_BG)],
               foreground=[("selected", C_ACCENT_DARK), ("!selected", C_MUTED)],
               padding=[("selected", (20, 9)), ("!selected", (20, 9))],
               font=[("selected", (self.fam, 13, "bold")),
                     ("!selected", (self.fam, 13, "bold"))])
        st.configure("Status.Treeview", background=C_PANEL, fieldbackground=C_PANEL,
                     foreground=C_TEXT, font=(self.fam, 13), rowheight=34, borderwidth=0)
        st.configure("Status.Treeview.Heading", font=(self.fam, 13, "bold"),
                     background=C_ACCENT_LIGHT, foreground=C_ACCENT_DARK, padding=(6, 9),
                     relief="flat")
        st.map("Status.Treeview.Heading", background=[("active", C_ACCENT_LIGHT)])
        # v6：选中行在「有焦点 / 没焦点」下两套颜色 —— 这就是表格 / 清单的焦点指示
        # （focus 状态由 ttk 自己维护：控件拿到键盘焦点时是真状态，探针实测 8.6.18 成立）
        st.map("Status.Treeview",
               background=[("selected", "focus", C_ACCENT),
                           ("selected", "!focus", C_SELECT_OFF)],
               foreground=[("selected", "focus", "#ffffff"),
                           ("selected", "!focus", C_TEXT)])
        # v6 / v9：唯一的输入控件（搜索框）焦点指示 = 强调色边框 + 淡蓝底（没焦点时灰边框 + 白底）
        # v15：统一内边距（7, 5）—— 字不贴边、三个输入框一样高（占位提示的 x 偏移也照这个来）
        st.configure("Nav.TEntry", fieldbackground=C_PANEL, bordercolor=C_LINE,
                     lightcolor=C_LINE, darkcolor=C_LINE, padding=(7, 5))
        st.map("Nav.TEntry",
               bordercolor=[("focus", C_ACCENT)], lightcolor=[("focus", C_ACCENT)],
               darkcolor=[("focus", C_ACCENT)],
               fieldbackground=[("focus", C_ACCENT_LIGHT)])
        # v16：弹窗主按钮（「开始 / 开始导出 / 应用到数据根」）—— 强调色底 + 白字，
        # 禁用时整颗变浅灰（选包窗空路径时「开始」禁用靠它）
        st.configure("Accent.TButton", background=C_ACCENT, foreground="#ffffff",
                     font=(self.fam, 13, "bold"), padding=(14, 6),
                     relief="flat", borderwidth=0,
                     bordercolor=C_ACCENT, lightcolor=C_ACCENT, darkcolor=C_ACCENT)
        st.map("Accent.TButton",
               background=[("disabled", C_SELECT_OFF), ("pressed", C_ACCENT_DARK),
                           ("active", C_ACCENT_DARK)],
               foreground=[("disabled", C_MUTED)],
               bordercolor=[("disabled", C_SELECT_OFF)],
               lightcolor=[("disabled", C_SELECT_OFF), ("pressed", C_ACCENT_DARK),
                           ("active", C_ACCENT_DARK)],
               darkcolor=[("disabled", C_SELECT_OFF), ("pressed", C_ACCENT_DARK),
                          ("active", C_ACCENT_DARK)])
        # v9：`Nav.TCombobox`（状态筛选下拉的样式，v7 加的）随筛选整块删除 —— 窗口里没有下拉框了。

    def _make_head(self):
        """v9：窗口第一行（左 → 右）= 搜索标签 + 搜索框 + 统计行 + 消息（最右端）。

        原来的两行页头（大标题 `题目状态跟踪表`、路径行 `%s ｜ 今天 %s`）与窗口最底下那条
        消息行都删了；窗口标题栏（root.title）保留。消息启动时为空（不再写「已读入 …」），
        改状态 / 撤销时出现、3 秒自动消失。
        """
        head = tk.Frame(self.root, bg=C_BG)
        head.pack(fill="x", padx=16, pady=(10, 2))
        self.lbl_search = tk.Label(head, text="搜" + LABEL_PAD + "索", bg=C_BG, fg=C_TEXT,
                                   font=(self.fam, 13))       # v7：去掉「（场次 / 题名 / 知识点）」；v15：插全角空格 = 三字宽（与面板三行标签对齐）
        self.lbl_search.pack(side="left")
        self.var_search = tk.StringVar(value="")
        self.ent_search = ttk.Entry(head, textvariable=self.var_search, width=26,
                                    font=(self.fam, 13),
                                    style="Nav.TEntry")         # v6：聚焦时边框 / 底色变强调；v15：宽 13 → 26
        self.ent_search.pack(side="left", padx=(6, 16))
        self.ent_search.bind("<KeyRelease>", lambda e: self.refresh_view())
        self.ent_search.bind("<Return>", self._jump_to_table)   # v5：Enter 跳回总表（搜索词保留）
        self.ent_search.bind("<Down>", self._dropdown_open)     # v14：↓ 展开筛选下拉（第一下只展开）
        self.ent_search.bind("<Up>", self._dropdown_hide)       # v14：↑ 收起（没展开时什么也不做）
        self.ent_search.bind("<Escape>", self._esc_search)      # v14：逐层退回（见 _esc_search）
        self._add_placeholder(self.ent_search, "场次 / 题名 / 知识点 / 难度")   # v15：空框灰字提示

        self.var_count = tk.StringVar(value="")
        self.lbl_count = tk.Label(head, textvariable=self.var_count, bg=C_BG, fg=C_TEXT,
                                  font=(self.fam, 12), anchor="w")
        self.lbl_count.pack(side="left")                        # v9：统计行并进第一行

        self.var_msg = tk.StringVar(value="")
        self.lbl_msg = tk.Label(head, textvariable=self.var_msg, bg=C_BG, fg=C_MUTED,
                                font=(self.fam, 11), anchor="e")
        self.lbl_msg.pack(side="right")                         # v9：消息挪到这一行最右端

        self.var_hits_min = tk.StringVar(value="")
        self.lbl_hits_min = tk.Label(head, textvariable=self.var_hits_min, bg=C_BG, fg=C_ACCENT_DARK,
                                     font=(self.fam, 11), anchor="e")
        self.lbl_hits_min.pack(side="right", padx=(0, 16))      # v14：面板收起时「筛出 N 题」挂这儿（v15：与消息之间留 16px）
        # v5 那条常驻快捷键提示（「按 ? 看快捷键」…）早已删；v9 把计数行并进这一行、
        # 消息挪到最右端（原底部行删除），并删掉状态筛选（下拉框 + F 键）。

    # ------------------------------------------------------------ 筛选下拉（v14）
    def _make_dropdown(self):
        """v14：搜索框下面的**下拉面板**（原 v13 第二行筛选区整行并进来）。

        行序 = 知识点 / 难度 / 状态（面板上面那行「搜索」就是窗口第一行的搜索框）；
        搜索框里按 ↓ 展开、↑ 收起；展开时面板占位、表格整体下移（收起即恢复）。
        匹配逻辑一个字没换：`filter_state()` → `status_report.filter_rows`，
        命令行 status_report.py 与 GUI 同条件必同一结果（冒烟 (zz) 拿子进程比过）。
        「筛出 N 题」在面板底部；面板收起时同一行字挂到窗口第一行右端（var_hits_min）。

        焦点：两个输入框 + 状态列表都进「搜索」这一站（Tab 环只有主页面 ⇄ 搜索两站，
        `_rotate_focus` 里把面板各行都算「搜索」）；面板内部用 ↑↓ 逐行走、Esc 逐层退回
        （见 `_dropdown_open` / `_esc_search` 那一族）。控件一律 takefocus=0 ——
        窗口里 Tab 只由 root 那处处理。
        """
        dlg = tk.Frame(self.root, bg=C_BG)
        self.dlg = dlg
        self.dlg_open = False
        self.status_cursor = 0                      # 状态列表里的光标行（0 起；勾选态不用 Listbox 自带 selection）
        f13 = (self.fam, 13)

        row = tk.Frame(dlg, bg=C_BG)
        row.pack(fill="x", pady=(2, 0))
        tk.Label(row, text="知识点", bg=C_BG, fg=C_TEXT, font=f13).pack(side="left", padx=(0, 6))
        self.var_know = tk.StringVar(value="")
        self.ent_know = ttk.Entry(row, textvariable=self.var_know, width=16, font=f13,
                                  style="Nav.TEntry", takefocus=0)
        self.ent_know.pack(side="left")
        self._add_placeholder(self.ent_know, "如 DP、二分")      # v15：空框灰字提示

        row = tk.Frame(dlg, bg=C_BG)
        row.pack(fill="x", pady=(2, 0))
        tk.Label(row, text="难" + LABEL_PAD + "度", bg=C_BG, fg=C_TEXT, font=f13).pack(side="left", padx=(0, 6))   # v15：插全角空格 = 与「知识点」同宽
        self.var_diff = tk.StringVar(value="")
        self.ent_diff = ttk.Entry(row, textvariable=self.var_diff, width=16, font=f13,
                                  style="Nav.TEntry", takefocus=0)
        self.ent_diff.pack(side="left")
        self._add_placeholder(self.ent_diff, "如 1700-1900")     # v15：空框灰字提示

        row = tk.Frame(dlg, bg=C_BG)
        row.pack(fill="x", pady=(2, 0))
        tk.Label(row, text="状" + LABEL_PAD + "态", bg=C_BG, fg=C_TEXT, font=f13).pack(side="left", padx=(0, 6), anchor="n")   # v15：插全角空格 = 与「知识点」同宽；padx 与另两行统一（左缘对齐见冒烟 (hh2)）
        self.status_on = set()                      # 勾选中的状态（空 = 不按状态筛）
        self.lb_status = tk.Listbox(row, height=len(STATES), width=13, font=f13,
                                    activestyle="none", selectmode="multiple", exportselection=False,
                                    takefocus=0, highlightthickness=1,
                                    highlightbackground=C_LINE, highlightcolor=C_ACCENT,
                                    bd=0, bg=C_PANEL, fg=C_TEXT)
        self.lb_status.pack(side="left")            # v15：去掉 (6,0) 的左侧 padding —— 与两个输入框同一条左缘（对齐账见冒烟 (hh2)）
        for i, st in enumerate(STATES):
            self.lb_status.insert("end", "%d. %s" % (i + 1, st))   # 序号跟状态浮层一致（`1. 未做` …）
        lb = self.lb_status
        lb.bind("<Up>", lambda e: self._status_move(-1))
        lb.bind("<Down>", lambda e: self._status_move(1))
        lb.bind("<space>", lambda e: self._status_toggle_cur())
        lb.bind("<Return>", lambda e: self._status_toggle_cur())
        lb.bind("<KP_Enter>", lambda e: self._status_toggle_cur())
        for k in range(len(STATES)):
            lb.bind("<Key-%d>" % (k + 1), lambda e, i=k: self._toggle_status_index(i))
            lb.bind("<KP_%d>" % (k + 1), lambda e, i=k: self._toggle_status_index(i))
        lb.bind("<Escape>", self._esc_from_status)
        lb.bind("<Button-1>", self._status_click)
        lb.bind("<FocusIn>", lambda e: self._paint_chips())
        lb.bind("<FocusOut>", lambda e: self._paint_chips())

        row = tk.Frame(dlg, bg=C_BG)
        row.pack(fill="x", pady=(6, 4))                          # v15：面板底排留白调匀
        # v15 末（用户点名「去掉清空选项」）：底排的「清空」按钮删除 —— 这行只留「筛出 N 题」。
        # 要清条件走 Esc 逐层退回（框里有字先清这一格）；`_clear_filters` 保留给测试夹具调用。
        self.var_hits = tk.StringVar(value="")
        self.lbl_hits = tk.Label(row, textvariable=self.var_hits, bg=C_BG, fg=C_ACCENT_DARK,
                                 font=(self.fam, 11), anchor="e")
        self.lbl_hits.pack(side="right")            # 只在筛选开着时才有字

        # 面板里按行上下走（↑↓）；Enter 跟搜索框同风格 = 带条件跳回总表；Esc 逐层退回
        for ent, var in ((self.ent_know, self.var_know), (self.ent_diff, self.var_diff)):
            ent.bind("<KeyRelease>", lambda e: self.refresh_view())
            ent.bind("<Return>", self._jump_to_table)
            ent.bind("<KP_Enter>", self._jump_to_table)
            ent.bind("<Escape>", lambda e, v=var: self._esc_row(v))
        self.ent_know.bind("<Up>", lambda e: self._focus_to(self.ent_search))
        self.ent_know.bind("<Down>", lambda e: self._focus_to(self.ent_diff))
        self.ent_diff.bind("<Up>", lambda e: self._focus_to(self.ent_know))
        self.ent_diff.bind("<Down>", lambda e: self._focus_to(self.lb_status))
        self._paint_chips()

    # ------------------------------------------------------------ 占位提示（v15）
    def _add_placeholder(self, ent, text, register=True):
        """空框且没焦点时浮一句浅灰提示语；聚焦 / 有字就隐。

        提示是**浮在输入框上的 Label**（`place` 在框内），不写进 textvariable ——
        `ent.get()` 仍是空串，匹配逻辑 / 命令行看不到它，不参与搜索。
        x=8 是给 Nav.TEntry 的 padding(7,5) + 1px 边框留的位置。
        register=False = 弹窗里的临时输入框（v16）：不进 `_ph_syncs`，窗销毁后
        主窗的「程序性清空 → 重同步」不会再碰它。
        """
        lbl = tk.Label(ent, text=text, bg=C_PANEL, fg=C_PLACEHOLDER,
                       font=(self.fam, 13), takefocus=0)

        def click(_e):
            ent.focus_set()                  # 点提示 = 点框（提示别把鼠标吃掉）
            return "break"

        def sync(_e=None):
            if ent.get() or ent.focus_get() is ent:
                lbl.place_forget()
            else:
                lbl.place(x=8, rely=0.5, anchor="w")

        lbl.bind("<Button-1>", click)
        ent.bind("<FocusIn>", sync, add="+")
        ent.bind("<FocusOut>", sync, add="+")
        ent.bind("<KeyRelease>", sync, add="+")     # 打字 / 删空都走这条
        if register:                                # v16：弹窗临时框不登记
            self._ph_syncs.append(sync)
        sync()

    def _dropdown_open(self, event=None):
        """搜索框里按 ↓：展开面板（第一下只展开、焦点留在搜索框，还能接着打字）；
        已经展开时再按 ↓ = 进「知识点」行。"""
        if not self.dlg_open:
            self.dlg.pack(fill="x", padx=16, pady=(0, 2), before=self.nb)
            self.dlg_open = True
            self._paint_chips()
            self._refresh_hits_labels()
            return "break"
        self.ent_know.focus_set()
        return "break"

    def _dropdown_hide(self, event=None):
        """收起面板（搜索框 ↑ / Esc 到底 / 离开搜索站都走这条）；筛选条件一个字不动。"""
        if self.dlg_open:
            self.dlg.pack_forget()
            self.dlg_open = False
            self._refresh_hits_labels()
        return "break"

    def _focus_to(self, w):
        """面板里 ↑↓ 逐行走：把焦点挪到相邻那一行。"""
        w.focus_set()
        return "break"

    def filter_state(self):
        """筛选（v14：搜索框下的下拉面板）当前状态 → (kwargs, raw_diff, bad)。

        kwargs 直接喂 `status_report.filter_rows`（两端唯一实现）；raw_diff = 难度框拆出的
        原文词表（原样显示用）；bad = 认不出的难度写法（这些一条都不匹配，要跟命令行的
        `★` 一样点名）。
        """
        know = [t for x in (self.var_know.get(),) for t in SR.split_terms(x)]
        raw = SR.split_terms(self.var_diff.get())
        specs, bad = SR.difficulty_specs(raw)
        return ({"knowledge": know,
                 "statuses": [s for s in STATES if s in self.status_on],
                 "difficulty": specs}, raw, bad)

    def _filter_on(self):
        """筛选有没有开着（任意一项非空就算；写法认不出的难度也算开着）。"""
        kw, _raw, _bad = self.filter_state()
        return bool(kw["knowledge"] or kw["statuses"] or kw["difficulty"])

    def _toggle_status(self, st):
        """勾选 / 取消一个状态（列表里点 / 空格 / Enter / 1~6 都走这条）。回 "break"：
        空格键别让 Listbox 类绑定再触发一次。"""
        self.status_on.symmetric_difference_update({st})
        self._paint_chips()
        self.refresh_view()
        return "break"

    def _toggle_status_index(self, i):
        """状态列表里按 1~6：勾选 / 取消第 i+1 项（越界忽略）；光标跟到那行。"""
        if not (0 <= i < len(STATES)):
            return "break"
        self.status_cursor = i
        return self._toggle_status(STATES[i])

    def _status_toggle_cur(self):
        """状态列表里空格 / Enter：勾选 / 取消光标那一行。"""
        return self._toggle_status(STATES[self.status_cursor])

    def _status_move(self, delta):
        """状态列表里 ↑↓：移动光标行（不改勾选）；到顶再 ↑ = 退回上一行（难度框）。"""
        i = self.status_cursor + delta
        if i < 0:
            self.ent_diff.focus_set()
            return "break"
        self.status_cursor = min(i, len(STATES) - 1)
        self._paint_chips()
        self.lb_status.see(self.status_cursor)
        return "break"

    def _status_click(self, event):
        """鼠标点状态列表：点哪行就把光标 + 勾选落到那行（选中态全走 itemconfig，不用 selection）。"""
        lb = self.lb_status
        i = lb.nearest(event.y)
        if 0 <= i < len(STATES):
            self.status_cursor = i
            lb.focus_set()
            self._toggle_status(STATES[i])
        return "break"

    def _paint_chips(self):
        """重画状态列表：勾选 = 强调色底白字；光标行（焦点在列表里时）再加一档底色。"""
        lb = self.lb_status
        focused = self._focus_widget() is lb
        lb.selection_clear(0, "end")                # 勾选态不用 Listbox 自带 selection，全部走 itemconfig
        for i, st in enumerate(STATES):
            on = st in self.status_on
            cur = focused and i == self.status_cursor
            if on:
                bg, fg = (C_ACCENT_DARK if cur else C_ACCENT), "#ffffff"
            else:
                bg, fg = (C_ACCENT_LIGHT if cur else C_PANEL), (C_ACCENT_DARK if cur else C_TEXT)
            lb.itemconfig(i, background=bg, foreground=fg)

    def _clear_filters(self):
        """清空筛选（两个框 + 全部勾选）——回到「不筛」，总表恢复全量。

        v15 末：面板底部的「清空」按钮已删（用户点名），这里保留给测试夹具与程序化调用。"""
        self.var_know.set("")
        self.var_diff.set("")
        self.status_on.clear()
        self._paint_chips()
        for sync in self._ph_syncs:      # v15：程序改空 var 不触发 KeyRelease，手动同步占位提示
            sync()
        self.refresh_view()
        return "break"

    def _esc_row(self, var, event=None):
        """知识点 / 难度框里 Esc：这一格有字先清掉（人留在本行）；已经空了 → 上退一行。"""
        if var.get():
            var.set("")
            for sync in self._ph_syncs:      # v15：程序改空 var 不触发 KeyRelease，手动同步占位提示
                sync()
            self.refresh_view()
            return "break"
        (self.ent_search if var is self.var_know else self.ent_know).focus_set()
        return "break"

    def _esc_from_status(self, event=None):
        """状态列表里 Esc：退回上一层（难度框）——勾选不动。"""
        self.ent_diff.focus_set()
        return "break"

    def _refresh_hits_labels(self):
        """「筛出 N 题」两处挂点：面板底部一处；面板收起时同一行字挂到窗口第一行右端。"""
        self.var_hits_min.set("" if self.dlg_open else self.var_hits.get())

    def update_hits(self, n):
        """`筛出 N 题`：只在筛选开着时有字（N = 当前总表可见行数 = 筛选 ∧ 搜索的交集）。

        面板展开时在面板底部；收起时挂到窗口第一行右端（v14）—— 筛选开着却没有任何
        提示的窗口状态不许出现。清空就消失（v10 删掉的常驻「搜出 M 题」不复活）。
        写法认不出的难度在这里点名（跟命令行的 `★` 同一口径）。
        """
        if not self._filter_on():
            self.var_hits.set("")
            self.var_hits_min.set("")
            return
        s = "筛出 %d 题" % n
        _kw, _raw, bad = self.filter_state()
        if bad:
            s += "（难度写法不认：%s）" % "、".join(bad)
        self.var_hits.set(s)
        self._refresh_hits_labels()

    # ------------------------------------------------------------ 总表页
    def _make_all_tab(self):
        mid = tk.Frame(self.tab_all, bg=C_BG)
        mid.pack(fill="both", expand=True, padx=2, pady=(6, 8))
        self.tree = ttk.Treeview(mid, columns=HEADER, show="headings", selectmode="browse",
                                 style="Status.Treeview")
        weights = {"场次": .15, "题号": .05, "题名": .23, "知识点": .28,
                   "难度": .08, "状态": .11, "日期": .10}
        anchors = {"题号": "center", "难度": "center", "状态": "center", "日期": "center"}
        for h in HEADER:
            if h in SORTABLE:
                self.tree.heading(h, text=h, command=lambda c=h: self.on_sort(c))
            else:
                self.tree.heading(h, text=h)
            self.tree.column(h, width=max(40, int(1200 * weights[h])), minwidth=40,
                             anchor=anchors.get(h, "w"), stretch=False)
        self.tree.tag_configure("odd", background=C_PANEL)
        self.tree.tag_configure("even", background=C_ZEBRA)
        self.tree.tag_configure("today", foreground=C_ACCENT_DARK)
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview,
                            takefocus=0)                 # v6：滚动条不进 Tab 轮换
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tree_weights = weights
        self.tree.bind("<Configure>", self._on_tree_configure)
        self.tree.bind("<Return>", self._on_open_key)
        self.tree.bind("<KP_Enter>", self._on_open_key)
        self.tree.bind("<Alt-Return>", self._open_material)     # v6 追加：Alt+Enter 打开资料（比 <Return> 更具体，先命中）
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Prior>", lambda e: self._move_sel(self.tree, "pgup"))
        self.tree.bind("<Next>", lambda e: self._move_sel(self.tree, "pgdn"))
        # v12：选中行直接按 1~6 改状态（不开浮层）—— 绑树上：焦点在搜索框里时数字照常打字。
        for k in range(len(STATES)):
            self.tree.bind("<Key-%d>" % (k + 1), lambda e, i=k: self._on_digit_key(i, self.tree))
            self.tree.bind("<KP_%d>" % (k + 1), lambda e, i=k: self._on_digit_key(i, self.tree))
        self.tree.bind("<Shift-Return>", self._on_problem_key)   # v12：Shift+Enter 开原题（比 <Return> 更具体）

    # ------------------------------------------------------------ 看板页
    def _make_today_tab(self):
        self.today_cards = tk.Frame(self.tab_today, bg=C_BG)
        self.today_cards.pack(fill="x", padx=6, pady=(12, 6))
        self.card_num, self.card_cap, self.card_box = [], [], []
        specs = segment_specs()
        for i, (cap, _) in enumerate(specs):
            card = tk.Frame(self.today_cards, bg=C_PANEL, highlightthickness=2,
                            highlightbackground=C_PANEL, cursor="hand2", takefocus=0)
            card.pack(side="left", fill="both", expand=True, padx=8)
            num = tk.Label(card, text="0", bg=C_PANEL, fg=C_ACCENT,
                           font=(self.fam, 32, "bold"), takefocus=0)
            num.pack(pady=(12, 0))
            lbl = tk.Label(card, text="%d. %s" % (i + 1, cap), bg=C_PANEL, fg=C_TEXT,
                           font=(self.fam, 12), takefocus=0)
            lbl.pack(pady=(2, 12))
            for w in (card, num, lbl):
                w.bind("<Button-1>", lambda e, k=i: self.show_segment(k))
            self.card_box.append(card)
            self.card_num.append(num)
            self.card_cap.append(lbl)

        # v7：原来这行页内键盘提示（← / → 换段 ｜ ↑↓ 移动 ｜ 回车 / 双击 = 改状态浮层）按用户要求
        # 整条删掉 —— 看板页不再挂任何提示行（快捷键说明只有 `?` 一览一处）。
        mid = tk.Frame(self.tab_today, bg=C_BG)
        mid.pack(fill="both", expand=True, padx=2, pady=(4, 8))
        w2 = {"场次": .18, "题号": .06, "题名": .26, "知识点": .30, "难度": .08, "日期": .12}
        self.today_tree = ttk.Treeview(mid, columns=TODAY_COLS, show="headings",
                                       selectmode="browse", style="Status.Treeview")
        anchors = {"题号": "center", "难度": "center", "日期": "center"}
        for h in TODAY_COLS:
            self.today_tree.heading(h, text=h)
            self.today_tree.column(h, width=int(1200 * w2[h]), minwidth=40,
                                   anchor=anchors.get(h, "w"), stretch=False)
        self.today_tree.tag_configure("odd", background=C_PANEL)
        self.today_tree.tag_configure("even", background=C_ZEBRA)
        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.today_tree.yview,
                            takefocus=0)                 # v6：滚动条不进 Tab 轮换
        self.today_tree.configure(yscrollcommand=vsb.set)
        self.today_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._today_weights = w2
        self.today_tree.bind("<Configure>",
                             lambda e: self._on_tree_configure(e, self.today_tree,
                                                               self._today_weights))
        self.today_tree.bind("<Return>", self._on_open_key)
        self.today_tree.bind("<KP_Enter>", self._on_open_key)
        self.today_tree.bind("<Alt-Return>", self._open_material)   # v6 追加：Alt+Enter 打开资料
        self.today_tree.bind("<Double-1>", self._on_double)
        self.today_tree.bind("<Prior>", lambda e: self._move_sel(self.today_tree, "pgup"))
        self.today_tree.bind("<Next>", lambda e: self._move_sel(self.today_tree, "pgdn"))
        # v12：数字键 / Shift+Enter 看板同样生效（绑树上，理由同总表）
        for k in range(len(STATES)):
            self.today_tree.bind("<Key-%d>" % (k + 1), lambda e, i=k: self._on_digit_key(i, self.today_tree))
            self.today_tree.bind("<KP_%d>" % (k + 1), lambda e, i=k: self._on_digit_key(i, self.today_tree))
        self.today_tree.bind("<Shift-Return>", self._on_problem_key)
        # v10：选中行变了（键盘移动 / 鼠标点选 / 程序改选）就记进本段 —— 切段回来还停这一行
        self.today_tree.bind("<<TreeviewSelect>>", self._on_today_select)
        # v6：原来这里挂着数字键 1~4 切段，已删（段改由 ← / → 走横排；浮层里的数字直选不受影响）

    # ------------------------------------------------------------ 列宽铺满
    def _on_tree_configure(self, event=None, tree=None, weights=None):
        """窗口 / 表格变宽变窄时按权重等比重排列宽（知识点列最宽）。"""
        tree = tree or (event.widget if event else self.tree)
        total = tree.winfo_width() - 4
        if total < 300:
            return
        for h, frac in (weights or self._tree_weights).items():
            tree.column(h, width=max(40, int(total * frac)))

    # ------------------------------------------------------------ 读盘 / 重绘
    def reload(self, note=None, clear_after=None):
        """从磁盘重读（别处改过也能看到），再重绘两个页面。

        v9：不再写「已读入 …」——note 不给（启动 / F5）就一个字不加，消息行保持原样；
        读表失败照样报（弹窗 + 消息行）。
        """
        keep = self.selected_key()
        try:
            self.rows = parse_rows(self.path)
        except SystemExit as e:
            self.rows = []
            note = "读表失败：%s" % e
            self._error("读表失败", str(e))
        except (OSError, ValueError) as e:
            self.rows = []
            note = "读表失败：%s" % e
            self._error("读表失败", str(e))
        annotate(self.rows, datetime.date.today())
        self.refresh_view(keep=keep)
        self.refresh_today()
        if note is not None:
            self.set_msg(note, clear_after=clear_after)

    # ------------------------------------------------------------ 消息行（第一行最右端）
    def set_msg(self, text, clear_after=None):
        """消息行那行字（v9：在第一行最右端；原底部行）。clear_after（毫秒）给了就定时清空
        （v4：保存提示 3 秒后自动消失）。"""
        if self._msg_after is not None:
            try:
                self.root.after_cancel(self._msg_after)
            except tk.TclError:
                pass
            self._msg_after = None
        self.var_msg.set(text or "")
        if clear_after:
            self._msg_after = self.root.after(clear_after, self._clear_msg)

    def _clear_msg(self):
        """定时器到点：清空提示行（冒烟里直接调它，不用真等 3 秒）。"""
        self._msg_after = None
        self.var_msg.set("")

    def visible_rows(self):
        """总表当前该显示的行 = **筛选（v13 起；v14 移进搜索框下的下拉面板）∧ 搜索（v10 规则）**。

        筛选走 `status_report.filter_rows` —— 命令行 `--knowledge / --status / --todo /
        --difficulty` 与 GUI 共用同一份实现（两端同条件必然同一份结果，冒烟 (zz) 真跑 CLI 比过）。
        v10 搜索规则照旧 = **忽略空格 + 多词都要命中**：查询按空白切词（半角 / 全角空格都算），
        每个词都要命中才显示；比对前把「场次 + 题名 + 知识点 + 难度」拼起来、去掉所有空白、转小写
        （v12：拼串加了 难度 —— 搜 `1800` / `CF1800` / `cf 1800` 等价）
        —— 所以「牛客周赛Round」与「牛客周赛 Round」命中集合完全相同，跨列组合（「牛客 构造」）
        也能中，大小写不敏感。
        """
        kw, _raw, _bad = self.filter_state()
        out = SR.filter_rows(self.rows, **kw)
        words = self.var_search.get().split()
        if words:
            keep = []
            for r in out:
                hay = re.sub(r"\s+", "", r["场次"] + r["题名"] + r["知识点"] + r["难度"]).lower()   # v12：加难度
                if all(w.lower() in hay for w in words):
                    keep.append(r)
            out = keep
        return sort_rows(out, self.sort_col, self.sort_desc)

    def _head_text(self, col):
        if col == self.sort_col:
            return col + (" ▼" if self.sort_desc else " ▲")
        return col

    def refresh_view(self, keep=None, keep_index=None):
        """重画总表。

        - keep_index 给了（v4：点表头 / S / R 换排序）→ 选中**原行号**：原来第 x 行就选第 x 行
          （行里的题换成别的），越界贴最后一行。
        - 否则（搜索 / 换表 / 改状态）→ **跟题**：按「场次 + 题号」保住选中，
          该题被搜掉时兜底贴回第一行；一行都没有就不选（v9：不再插占位行）。
        """
        if keep_index is None:
            keep = keep or self.selected_key()
        tree = self.tree
        for iid in tree.get_children():
            tree.delete(iid)
        rows = self.visible_rows()
        today = datetime.date.today().isoformat()
        for k, r in enumerate(rows):
            tags = ["even" if k % 2 else "odd"]
            if r["日期"] == today:
                tags.append("today")
            tree.insert("", "end", iid=str(r["_i"]), values=[r[h] for h in HEADER], tags=tags)
        for h in HEADER:
            tree.heading(h, text=self._head_text(h))
        self.update_count()
        self.update_hits(len(rows))         # v13：筛选的「筛出 N 题」（v14：面板底部 / 收起时第一行右端）
        if keep_index is not None:
            self._select_index(tree, keep_index)
        elif keep:
            self.select_key(keep, focus=False)
        first = tree.get_children()
        if not tree.selection() and first:          # 选中的题被搜掉 / 换表 → 贴回第一行
            tree.selection_set(first[0])
            tree.focus(first[0])
            tree.see(first[0])

    def update_count(self):
        """计数行（v10 口径）：`共 X 题 ｜ 未做 Y ｜ …（6 个状态）｜ N天内做对：M 题`。

        M = 日期在最近 N 天内且状态 ∈ {独立AC, 复现AC}（不含「巩固」）；v10 起这行固定
        按全量算 —— 原来行首那段 `搜出 M 题 ｜` 已删，搜不搜都是同一行字。
        """
        c = state_counts(self.rows)
        s = "共 %d 题" % len(self.rows)
        s += " ｜ " + " ｜ ".join("%s %d" % (k, c[k]) for k in STATES)
        s += " ｜ %d天内做对：%d 题" % (SR.RECENT_DAYS, done_count(self.rows))
        self.var_count.set(s)

    def refresh_today(self):
        """重画看板：四段数字 + 当前段清单。

        v10：重建后把**本段上次选中的行**（`self._seg_sel`）贴回去；那一行不在了
        （比如刚被改状态踢出这一段）就贴回第一行；一段都没有就留空 —— 都不报错。
        """
        counts = [len(segment_rows(self.rows, i)) for i in range(4)]
        for i, n in enumerate(counts):
            self.card_num[i].configure(text=str(n))
        for i in range(4):
            sel = (i == self.seg_idx)
            bg = C_ACCENT if sel else C_PANEL                 # 当前段用强调色标出
            self.card_box[i].configure(bg=bg,
                                       highlightbackground=C_ACCENT_DARK if sel else C_PANEL)
            self.card_num[i].configure(bg=bg, fg="#ffffff" if sel else C_ACCENT)
            self.card_cap[i].configure(bg=bg, fg="#ffffff" if sel else C_TEXT)

        seg = self.seg_idx % 4
        remember = self._seg_sel[seg]               # 重建前先拿住记忆（删行时的选中事件不许冲掉它）
        tree = self.today_tree
        self._seg_rebuild = True
        try:
            for iid in tree.get_children():
                tree.delete(iid)
            rows = segment_rows(self.rows, self.seg_idx)
            for k, r in enumerate(rows):
                tree.insert("", "end", iid=str(r["_i"]),
                            values=[r[h] for h in TODAY_COLS],
                            tags=["even" if k % 2 else "odd"])
            iids = list(tree.get_children())
            if iids:                                # v9：空段就留空，不再插「无」占位行
                pick = remember if remember in iids else iids[0]
                tree.selection_set(pick)
                tree.focus(pick)
                tree.see(pick)
                self._seg_sel[seg] = pick
        finally:
            self._seg_rebuild = False

    def show_segment(self, idx):
        self._remember_today_sel()              # v10：切走前先把本段当前选中行记下来
        self.seg_idx = idx % 4
        self.refresh_today()
        self.today_tree.focus_set()
        return "break"

    def _remember_today_sel(self):
        """v10：把看板清单「当前段」的选中行记进 `self._seg_sel`（重建中间态不记，空清单不记）。

        键盘移动 / 鼠标点选都靠挂在 today_tree 上的 `<<TreeviewSelect>>` 走到这里；切段前、
        改状态下移后再各调一次兜底 —— 记忆里存的是 iid（= `str(r["_i"])`）。
        """
        if self._seg_rebuild:
            return
        tree = self.today_tree
        sel = list(tree.selection())
        iid = sel[0] if sel else tree.focus()
        if iid and iid in tree.get_children():
            self._seg_sel[self.seg_idx % 4] = iid

    def _on_today_select(self, event=None):
        """v10：清单选中变了（键盘 / 鼠标 / 程序改选）→ 记下当前段选中行。"""
        self._remember_today_sel()

    # ------------------------------------------------------------ 选中 / 键盘
    def row_by_iid(self, iid):
        if not iid:
            return None
        try:
            return self.rows[int(iid)]
        except (ValueError, IndexError):
            return None

    def tree_row(self, tree):
        sel = list(tree.selection())
        if not sel:
            cur = tree.focus()
            sel = [cur] if cur else []
        return self.row_by_iid(sel[0]) if sel else None

    def _active_tree(self):
        return self.today_tree if self.nb.index(self.nb.select()) == 1 else self.tree

    def selected_key(self):
        r = self.tree_row(self._active_tree())
        return (r["场次"], r["题号"]) if r else None

    def select_key(self, key, focus=True):
        for tree in (self.tree, self.today_tree):     # 两页都选上：在看板改完也能接着改
            for iid in tree.get_children():
                r = self.row_by_iid(iid)
                if r and (r["场次"], r["题号"]) == key:
                    tree.selection_set(iid)
                    tree.focus(iid)
                    tree.see(iid)
                    break
        if focus:
            self._active_tree().focus_set()

    def _index_of(self, tree):
        """当前选中行在 tree 可见列表里的行号（0 起）；没选中 / 列表空 → None。"""
        iids = list(tree.get_children())
        sel = list(tree.selection())
        iid = sel[0] if sel else tree.focus()
        return iids.index(iid) if iid in iids else None

    def _select_index(self, tree, idx):
        """选中 tree 里第 idx 行（0 起）：v4 的「换排序钉行号」「改完状态下移一行」都走这条。
        越界贴最后一行；列表空就不动（v9：空表不许报错）。"""
        iids = list(tree.get_children())
        if idx is None or not iids:
            return False
        iid = iids[max(0, min(int(idx), len(iids) - 1))]
        tree.selection_set(iid)
        tree.focus(iid)
        tree.see(iid)
        return True

    def _move_sel(self, tree, kind):
        iids = list(tree.get_children())
        if not iids:                                # v9：空表上 ↑↓ / 翻页不报错
            return "break"
        sel = list(tree.selection())
        idx = iids.index(sel[0]) if sel and sel[0] in iids else 0
        if kind == "pgup":
            idx = max(0, idx - 12)
        elif kind == "pgdn":
            idx = min(len(iids) - 1, idx + 12)
        tree.selection_set(iids[idx])
        tree.focus(iids[idx])
        tree.see(iids[idx])
        tree.focus_set()
        return "break"

    def _nav_arrow(self, delta, event=None):
        """v6：← / → 在一整条横排上左右走（替代 v5 的两页来回绕）。

        横排 5 格：[总表] [1 待重写] [2 待补题] [3 复习] [4 抽检]，两头绕回：
          * 总表按 → 进第 1 段；总表按 ← 进第 4 段；
          * 第 1 段按 ← 回总表；第 4 段按 → 回总表；其余按方向挪一段。
        进段时 show_segment 会把强调色 / 清单 / 选中行（v10：本段上次那行，没记过就是第 1 行）/
        焦点一并弄好；进「今天要做的」不记上次在哪段（往前第 1 段、往后第 4 段）。

        防冲突（v5 的规则原样保留；v14 起让位对象 = 三个输入框 + 状态列表…）：
          * 焦点在搜索框 / 知识点框 / 难度框里时**不抢** —— return None（不 break），那儿的
            ← / → 归 Entry 自己挪光标；
          * 焦点在面板的状态列表上时也不抢（列表里 ↑↓ 走、空格 / Enter / 1~6 勾选）；
          * 状态浮层 / `?` 一览打开时不响应（_busy）；
          * 表格 / 清单里 ← / → 没有别的用途，直接绑。
        """
        if self._busy() or self._in_text_widget() or self._focus_widget() is self.lb_status:
            return None
        self._remember_today_sel()          # v10：切走前先把本段当前选中行记下来
        if self.nb.index(self.nb.select()) == 0:
            cell = 0
        else:
            cell = 1 + (self.seg_idx % 4)
        if cell == 0:
            cell = 1 if delta > 0 else 4         # 从总表出发：→ 第 1 段 / ← 第 4 段
        elif (cell == 1 and delta < 0) or (cell == 4 and delta > 0):
            cell = 0                             # 第 1 段 ← 回总表 / 第 4 段 → 回总表
        else:
            cell += delta
        if cell == 0:
            self.nb.select(0)
            self._active_tree().focus_set()
        else:
            self.nb.select(1)
            self.show_segment(cell - 1)          # 强调色 / 清单 / 选中行 / 焦点都在这里面
        return "break"

    def _focus_ring(self):
        """v14：Tab 轮换的一圈（2 站）= 当前页表格 / 搜索框。

        「主页面」= 当前页的表格 / 清单（总表页→总表树、看板页→看板清单）；下拉面板里的
        各行（知识点 / 难度 / 状态列表）**都算「搜索」这一站**（面板内部用 ↑↓ 走）。
        v13 的五站口径作废。
        """
        return [self._active_tree(), self.ent_search]

    def _rotate_focus(self, delta, event=None):
        """Tab / Shift+Tab：在 `_focus_ring()` 那一圈上正 / 反向轮换（v6 三站 → v9 两站 → v13 五站 → v14 又并回两站）。

        焦点在面板任意一行上都按「搜索」站算；在主页面 ⇄ 搜索之间走时**自动收起 / 保持面板**
        （离开搜索站收面板、条件不动）。跑去别处（理论上不该有）时贴回第一站。
        浮层 / 一览开着时不响应。Tab 的默认遍历不会跑：这个 root 级处理 return "break"
        （v2~v4 的 Tab 切页就是靠它压住的）；窗口里 Tab 只有这一处。
        """
        if self._busy():
            return None
        ring = self._focus_ring()
        cur = self._focus_widget()
        if cur is self.ent_search or (self.dlg_open and cur in (self.ent_know, self.ent_diff, self.lb_status)):
            i = ring.index(self.ent_search)          # 面板里各行都算「搜索」站
        elif cur in ring:
            i = ring.index(cur)
        else:
            ring[0].focus_set()
            return "break"
        nxt = ring[(i + delta) % len(ring)]
        if nxt is self._active_tree():
            self._dropdown_hide()                    # 离开搜索站：收面板，条件不动
        nxt.focus_set()
        return "break"

    def _open_material(self, event=None):
        """v6 追加：Alt+Enter 打开选中这题的资料（算法库记录 → 场题解 → 都没有就在消息处提示）。

        顺序（任务书）：① 算法库记录 `算法/**/牛客周赛Round<号>-<字母>-*.md` —— **用 glob 找**，
        库里文件夹按主知识点分，复合知识点名不一定等于文件夹名，不能拼路径；② 那一场的题解 md
        `题解/牛客周赛/Round<号>/Round<号>题解.md`；③ 都没有 → 「打不开：没找到这题的资料」。
        场次不是「牛客周赛 Round N」形式 → 「打不开：这场还没接」。打开走 self._opener
        （默认 os.startfile；测试里换成假函数 —— 绝不真开文件）。浮层 / 一览开着时不响应。
        """
        if self._busy() or self._in_text_widget():
            return None
        row = self.tree_row(self._active_tree())
        if not row:
            return "break"
        m = re.match(r"^牛客周赛\s*Round\s*(\d+)$", row["场次"])
        if not m:
            self.set_msg("打不开：这场还没接", clear_after=TOAST_MS)
            return "break"
        n, letter = int(m.group(1)), row["题号"]
        pat = os.path.join(self.data_root, "算法", "**", "牛客周赛Round%d-%s-*.md" % (n, letter))
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            self._do_open(hits[0])
            return "break"
        sol = os.path.join(self.data_root, "题解", "牛客周赛",
                           "Round%d" % n, "Round%d题解.md" % n)
        if os.path.isfile(sol):
            self._do_open(sol)
            return "break"
        self.set_msg("打不开：没找到这题的资料", clear_after=TOAST_MS)
        return "break"

    def _do_open(self, path):
        """真正去「打开」这一下 —— 单独一层好换：测试里把 self._opener 换成假函数就永远不开文件。"""
        path = path.replace("\\", "/")       # Windows glob 会混出反斜杠，统一成正斜杠
        if self._opener is not None:
            self._opener(path)

    def parse_problem_url(self, row):
        """v12：Shift+Enter 的解析链（**只读**：不改任何文件、不产生备份）。

        场次 `牛客周赛 Round <n>` → 读 `题解/牛客周赛/Round<n>/Round<n>题解.md`（就是本 GUI
        Alt+Enter 打开的那份场题解），取里面 `ac.nowcoder.com/acm/contest/<cid>` 的 cid →
        拼 `https://ac.nowcoder.com/acm/contest/<cid>/<题号>`（= fetch_problem.py 的单题页形态）。
        返回 (url, None)；失败 (None, 原因)：「这场还没接」（场次不认）/
        「没找到这场比赛的原题链接」（题解文件不在 / 里面没有链接行）。
        """
        m = re.match(r"^牛客周赛\s*Round\s*(\d+)$", row["场次"])
        if not m:
            return None, "这场还没接"
        n = int(m.group(1))
        sol = os.path.join(self.data_root, "题解", "牛客周赛",
                           "Round%d" % n, "Round%d题解.md" % n)
        try:
            with io.open(sol, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return None, "没找到这场比赛的原题链接"
        m2 = re.search(r"ac\.nowcoder\.com/acm/contest/(\d+)", text)
        if not m2:
            return None, "没找到这场比赛的原题链接"
        return "https://ac.nowcoder.com/acm/contest/%s/%s" % (m2.group(1), row["题号"]), None

    def _do_open_url(self, url):
        """v12：真正「打开」这一下 —— 单独一层（和 _do_open 同套路）好换：测试里把
        self._opener 换成假函数，就绝不真开浏览器。"""
        if self._opener is not None:
            self._opener(url)

    def _on_problem_key(self, event=None):
        """v12：Shift+Enter 打开选中这题的原题（牛客题目页）。总表 / 看板都挂。

        解析只读（parse_problem_url）；打开走 _do_open_url（测试可打桩，绝不真开浏览器）。
        失败 → 右上角消息（跟 Alt+Enter 同风格）；浮层 / 一览开着时不响应。
        """
        if self._busy() or self._in_text_widget():
            return None
        row = self.tree_row(self._active_tree())
        if not row:
            return "break"
        url, why = self.parse_problem_url(row)
        if url is None:
            self.set_msg("打不开：%s" % why, clear_after=TOAST_MS)
            return "break"
        self._do_open_url(url)
        return "break"

    def _on_reload_key(self, event=None):
        self.reload()
        return "break"

    # ------------------------------------------------------------ 键盘进搜索
    def _focus_widget(self):
        try:
            return self.root.focus_get()
        except (KeyError, tk.TclError):
            return None

    def _in_text_widget(self):
        """焦点是不是在「要收普通字符」的控件里（v14：搜索框 + 下拉面板的两个输入框）——那时快捷键让位。"""
        return self._focus_widget() in (self.ent_search, self.ent_know, self.ent_diff)

    def _busy(self):
        return self.popup is not None or self.help_win is not None

    def focus_search(self):
        self.ent_search.focus_set()
        self.ent_search.selection_range(0, "end")   # 全选已打的内容，直接重打
        return "break"

    def _on_focus_search(self, event=None):
        if self._busy() or self._in_text_widget():
            return None                             # 已在输入框里：让 / 当普通字符打进去
        return self.focus_search()

    def _esc_search(self, event=None):
        """搜索框里 Esc（v14 起逐层退回，不再一把清空 + 回表格）：

        有字 → 先清空（留在搜索框）；空 → 面板开着就先收起；面板也收着 → 回主页面表格。
        """
        if self.var_search.get():
            self.var_search.set("")
            self.refresh_view()
            return "break"
        if self.dlg_open:
            return self._dropdown_hide()
        self._active_tree().focus_set()
        return "break"

    def _jump_to_table(self, event=None):
        """v5：搜索框 / 面板里 Enter —— 带着搜索词跳回总表看结果（v14 起 ↓ 改作展开下拉）。

        搜索词与筛选条件一律保留；离开搜索站自动收起面板（条件不动）。选中行按「跟题」
        规矩：当前那道题还在结果里就保它，被搜掉 / 搜不到就贴回第一行，并滚到可见。
        焦点在别的页（看板页）上时先切回总表页。
        """
        self._dropdown_hide()
        keep = self.selected_key()
        if self.nb.index(self.nb.select()) != 0:
            self.nb.select(0)
        self.refresh_view(keep=keep)
        tree = self.tree
        sel = list(tree.selection())
        if sel:
            tree.see(sel[0])
        tree.focus_set()
        return "break"

    # ------------------------------------------------------------ 排序
    def _apply_sort(self, col=None, desc=None):
        """col=None 不改字段、desc=None 不改方向。

        v4：换排序后选中行**钉在原行号**（点表头 / S / R 都走这条）—— 原来第 x 行就还是第 x 行，
        行里的题换成别的；越界贴最后一行。「跟着那道题走」自 v4 起作废（搜索仍跟题；v9 筛选删掉）。
        """
        keep_idx = self._index_of(self.tree)
        if col is not None:
            self.sort_col = col
        if desc is not None:
            self.sort_desc = bool(desc)
        self.refresh_view(keep_index=keep_idx)
        self.tree.focus_set()

    def on_sort(self, col):
        """点表头：首点升序，再点降序。"""
        if col not in SORTABLE:
            return
        self._apply_sort(col, (not self.sort_desc) if col == self.sort_col else False)

    def _sort_next_key(self, event=None):
        """S：场次 → 难度 → 日期 → 场次 循环（切字段一律回到升序）。"""
        if self._busy() or self._in_text_widget():
            return None
        if self.nb.index(self.nb.select()) != 0:
            self.nb.select(0)                       # 排序只对总表页有意义，先把页切过去
        i = SORTABLE.index(self.sort_col) if self.sort_col in SORTABLE else -1
        self._apply_sort(SORTABLE[(i + 1) % len(SORTABLE)], False)
        return "break"

    def _sort_toggle_key(self, event=None):
        """R：反转升 / 降。"""
        if self._busy() or self._in_text_widget():
            return None
        if self.nb.index(self.nb.select()) != 0:
            self.nb.select(0)
        self._apply_sort(None, not self.sort_desc)
        return "break"

    # ------------------------------------------------------------ `?` 快捷键一览
    def _mono_family(self):
        try:
            fams = set(tkfont.families(self.root))
        except tk.TclError:
            return "Courier New"
        for c in ("Consolas", "Courier New", "Lucida Console"):
            if c in fams:
                return c
        return "TkFixedFont"

    def _on_help_key(self, event=None):
        if self.popup is not None:
            return "break"
        self.toggle_help()
        return "break"

    def toggle_help(self):
        if self.help_win is not None:
            self.close_help()
        else:
            self.open_help()

    def open_help(self):
        prev = self._focus_widget()
        win = tk.Toplevel(self.root)
        win.title("快捷键一览")
        # v8：一览是独立 Toplevel（自己的 HWND，它的 <FocusIn> 不会冒到 root 上）——
        # 建好就把输入法摘掉，并把兜底挂到它自己身上。
        self.ime.detach_tree(win)
        self.ime.watch(win)
        win.configure(bg=C_BG)
        win.transient(self.root)
        panel = tk.Frame(win, bg=C_PANEL, highlightthickness=1,
                         highlightbackground=C_ACCENT_LIGHT)
        panel.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(panel, text="快捷键一览", bg=C_PANEL, fg=C_ACCENT_DARK,
                 font=(self.fam, 16, "bold")).pack(pady=(10, 8))
        lbl = tk.Label(panel, text=KEY_TABLE, bg=C_PANEL, fg=C_TEXT, justify="left",
                       anchor="w", font=(self._mono_family(), 12))
        lbl.pack(padx=18, pady=(0, 10))
        tk.Label(panel, text="Esc / ? 关闭", bg=C_PANEL, fg=C_MUTED,
                 font=(self.fam, 11)).pack(pady=(0, 10))
        win.bind("<Escape>", lambda e: self.close_help())
        win.bind("<Key-question>", lambda e: self.close_help())
        win.bind("<Return>", lambda e: self.close_help())
        win.bind("<KP_Enter>", lambda e: self.close_help())
        win.protocol("WM_DELETE_WINDOW", self.close_help)
        win.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - win.winfo_reqheight()) // 3)
        win.geometry("+%d+%d" % (max(0, x), max(0, y)))
        try:
            win.grab_set()
        except tk.TclError:
            pass
        win.focus_force()
        self.help_win, self.help_prev, self.help_lbl = win, prev, lbl

    def close_help(self):
        win, prev = self.help_win, self.help_prev
        self.help_win, self.help_prev, self.help_lbl = None, None, None
        if win is not None:
            try:
                win.grab_release()
            except tk.TclError:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass
        if prev is not None:
            try:
                prev.focus_set()
            except tk.TclError:
                pass
        return "break"

    # ------------------------------------------------------------ 行内浮层
    def _on_open_key(self, event=None):
        tree = event.widget if event else self._active_tree()
        row = self.tree_row(tree)
        if row:
            self.open_status_popup(row, tree)
        return "break"

    def _on_double(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            return "break"
        tree.selection_set(iid)
        tree.focus(iid)
        row = self.row_by_iid(iid)
        if row:
            self.open_status_popup(row, tree)
        return "break"

    def open_status_popup(self, row, tree):
        """在该行旁边弹 6 个带序号的状态（`1. 未做`…`6. 巩固`）：↑↓ 选、回车确认、Esc 取消。

        v5：每项前缀 = 序号；数字键 1~6 与序号一一对应（按下即确认第 N 项）；
        底部那行「数字直选 ｜ Enter 确认 ｜ Esc 取消」提示已删（`?` 一览是唯一说明处）。
        v10：当前值不在 6 项内（真表里历史遗留的旧值）→ **不预选**（curselection 为空），
        但数字直选照旧好使（按 1 直接写「未做」）。
        """
        self.close_popup()
        if row is None:
            return
        cur = row["状态"] if row["状态"] in STATES else None
        try:
            box = tree.bbox(str(row["_i"]))
        except tk.TclError:
            box = ""
        if box:
            x = tree.winfo_rootx() + box[0] + box[2] + 6
            y = tree.winfo_rooty() + box[1]
        else:
            x = tree.winfo_rootx() + 120
            y = tree.winfo_rooty() + 60
        pop = tk.Toplevel(self.root)
        pop.wm_overrideredirect(True)
        pop.configure(bg=C_ACCENT)
        lb = tk.Listbox(pop, height=len(STATES), width=13, font=(self.fam, 13),
                        activestyle="none", selectmode="browse", exportselection=False,
                        highlightthickness=0, bd=0, bg=C_PANEL, fg=C_TEXT,
                        selectbackground=C_ACCENT, selectforeground="#ffffff")
        lb.pack(padx=2, pady=2)
        for i, s in enumerate(STATES):
            lb.insert("end", "%d. %s" % (i + 1, s))   # v5：每项带序号（数字键 1~6 与之一一对应）
            if s == cur:
                lb.itemconfig(i, background=C_ACCENT_LIGHT, foreground=C_ACCENT_DARK)
        if cur is not None:                         # v10：历史旧值不在 6 项里 → 不预选（按 1 仍能写「未做」）
            idx = STATES.index(cur)
            lb.selection_clear(0, "end")
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
        for k in range(len(STATES)):                # v3：数字直选 1~6（按下即确认第 N 个状态）
            lb.bind("<Key-%d>" % (k + 1), lambda e, i=k: self._popup_pick(i))
            lb.bind("<KP_%d>" % (k + 1), lambda e, i=k: self._popup_pick(i))
        lb.bind("<Up>", lambda e: self._popup_move(-1))
        lb.bind("<Down>", lambda e: self._popup_move(1))
        lb.bind("<Return>", lambda e: self._popup_confirm())
        lb.bind("<KP_Enter>", lambda e: self._popup_confirm())
        lb.bind("<Escape>", lambda e: self._popup_cancel())
        lb.bind("<Double-1>", lambda e: self._popup_confirm())
        # v5：原来这里有底部一行「数字直选 ｜ Enter 确认 ｜ Esc 取消」提示，按用户要求删掉——
        # 加了序号后它也没用了；快捷键说明以 `?` 一览为唯一处。
        pop.bind("<Button-1>", self._popup_click)   # grab 会把浮层外的点击送到浮层这儿
        # v8：浮层也是独立 Toplevel —— 摘掉它（含列表框）的输入法，兜底挂到它自己身上
        self.ime.detach_tree(pop)
        self.ime.watch(pop)

        pop.update_idletasks()
        pw, ph = pop.winfo_reqwidth(), pop.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = max(0, min(x, sw - pw - 6))
        y = max(0, min(y, sh - ph - 6))
        pop.geometry("+%d+%d" % (x, y))
        pop.deiconify()
        try:
            pop.grab_set()
        except tk.TclError:
            pass
        lb.focus_force()
        self.popup, self.popup_lb, self.popup_row, self.popup_tree = pop, lb, row, tree

    def _popup_click(self, event):
        """点浮层内部（列表框）不动；点浮层外（被本地 grab 重定向过来）＝取消。"""
        w = event.widget
        if w is not None:
            try:
                if w is self.popup_lb or w.winfo_toplevel() is self.popup:
                    return None
            except tk.TclError:
                return None
        return self._popup_cancel()

    def _popup_pick(self, i):
        """浮层里按 1~6：直接确认第 i+1 个状态（越界忽略）。"""
        lb = self.popup_lb
        if lb is None or not (0 <= i < lb.size()):
            return "break"
        lb.selection_clear(0, "end")
        lb.selection_set(i)
        lb.activate(i)
        lb.see(i)
        return self._popup_confirm()

    def _popup_move(self, delta):
        lb = self.popup_lb
        if lb is None:
            return "break"
        sel = lb.curselection()
        i = (sel[0] if sel else 0) + delta
        i = max(0, min(lb.size() - 1, i))
        lb.selection_clear(0, "end")
        lb.selection_set(i)
        lb.activate(i)
        lb.see(i)
        return "break"

    def _popup_confirm(self):
        lb, row, tree = self.popup_lb, self.popup_row, self.popup_tree
        sel = lb.curselection() if lb else ()
        state = STATES[sel[0]] if sel else None
        self.close_popup()
        if state and row:
            self.set_status(row, state, tree)
        return "break"

    def _popup_cancel(self):
        self.close_popup()
        return "break"

    def close_popup(self):
        pop = self.popup
        self.popup = self.popup_lb = self.popup_row = self.popup_tree = None
        if pop is not None:
            try:
                pop.grab_release()
            except tk.TclError:
                pass
            try:
                pop.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------ 数字直改 / 打开原题（v12）
    def _on_digit_key(self, i, tree, event=None):
        """v12：树上按 1~6 = 直接用第 i+1 个状态改选中行（= 浮层里按那个数字，但不开浮层）。

        绑在两棵树上、**不绑 root** —— 焦点在搜索框里时数字要照常打进输入框。浮层 / `?` 一览
        开着（`_busy()`）不响应（浮层的数字直选自己走，别双触发）；空表 / 没选中 → 静默 break。
        写盘 / 日期取今天 / 提示 / 自动下移 / 入撤销栈全交给 set_status，一个规矩。
        """
        if self._busy():
            return "break"
        row = self.tree_row(tree)
        if not row:
            return "break"
        if 0 <= i < len(STATES):
            self.set_status(row, STATES[i], tree)
        return "break"

    # ------------------------------------------------------------ 写动作
    def set_status(self, row, state, tree=None):
        """把一行的状态改成 state、日期改成今天，写回 md 并整表刷新。

        v4：改完选中行自动**下移一行**（总表 / 看板一个规矩，已经是最后一行就不动）；
        底部保存提示 3 秒后自动消失。Esc 取消不走这里，所以取消不会移动。
        v10：state 不在 6 个合法值里（旧值「卡住」「只读过」等）→ 直接拒绝，文件一个字不动。
        """
        if state not in STATES:              # v10：非法状态拒绝（浮层不会送来；直接调也要拦）
            self.set_msg("写入失败：%s 不是合法状态" % state, clear_after=TOAST_MS)
            return
        key = (row["场次"], row["题号"])
        tree = tree or self._active_tree()
        idx = self._index_of(tree)          # 改之前那一行在第几行（下移的基准）
        today = datetime.date.today().isoformat()
        old_status, old_date = row["状态"], row["日期"]     # v6 追加：Ctrl+Z 要记下旧值
        try:
            bak, _, _ = save_changes(self.path, key, {"状态": state, "日期": today},
                                     backup_src_root=self.backup_src_root)
        except Exception as e:
            self._error("写入失败", "%s\n\n%s %s" % (e, key[0], key[1]))
            self.set_msg("写入失败：%s" % e)
            return
        if bak is None:
            note = "没有变化，未写盘"
        else:
            # v6 追加：真写盘了才记；v12：改记撤销栈（栈顶 = 最近一步，_last_change 同步成栈顶）
            ch = {"round": key[0], "letter": key[1],
                  "old_status": old_status, "old_date": old_date,
                  "new_status": state, "new_date": today}
            self._undo_stack.append(ch)
            if len(self._undo_stack) > UNDO_MAX:     # 容量外的最老那步丢掉
                del self._undo_stack[0]
            self._last_change = ch
            note = "已保存：%s %s → %s" % (key[0], key[1], state)   # v9：短文案（备份 / 日期不上屏）
        self.reload(note=note, clear_after=TOAST_MS)
        if idx is not None:                  # 下移一行；末尾（idx+1 越界）就留在原地
            self._select_index(tree, idx + 1)
        self._remember_today_sel()           # v10：看板里改完自动下移产生的新选中也要记

    def _undo(self, event=None):
        """v6 追加 / v12 扩成多步：Ctrl+Z 撤销上一步状态改动（可连撤，本窗口内有效，不跨重启）。

        栈里的每一步走正常写回流程：重读 → 按 场次+题号 定位 → 只替换 状态/日期 两格 → 备份
        → 复读校验（就是把旧状态 / 旧日期再写一遍，save_changes 原样复用）—— 还原成功才把
        那步弹出（弹掉不压回）。选中行回到那题，底部提示 3 秒消失；栈空 → 只提示，文件一个字
        不动。任何焦点下都生效（挂 root；Entry 没有自己的 Ctrl+Z，不会打架）。
        """
        if self._busy():
            return None
        if not self._undo_stack:
            self.set_msg("没有可撤销的改动", clear_after=TOAST_MS)
            return "break"
        ch = self._undo_stack[-1]
        key = (ch["round"], ch["letter"])
        try:
            bak, _, _ = save_changes(self.path, key,
                                     {"状态": ch["old_status"], "日期": ch["old_date"]},
                                     backup_src_root=self.backup_src_root)
        except Exception as e:
            self._error("撤销失败", "%s\n\n%s %s" % (e, key[0], key[1]))
            self.set_msg("撤销失败：%s" % e)
            return "break"
        self._undo_stack.pop()               # v12：这一步还原成功 → 弹掉（弹掉不压回）
        self._last_change = self._undo_stack[-1] if self._undo_stack else None
        if bak is None:
            note = "没有变化，未写盘"
        else:
            note = "已撤销：%s %s → %s" % (key[0], key[1], ch["old_status"])   # v9：短文案
        self.reload(note=note, clear_after=TOAST_MS)
        self._select_problem(key)
        return "break"

    def _select_problem(self, key):
        """v6 追加：把选中行拉回（场次, 题号）那一题 —— 当前页有就留在当前页，没有就回总表看。"""
        cur = self._active_tree()
        here = False
        for iid in cur.get_children():
            r = self.row_by_iid(iid)
            if r and (r["场次"], r["题号"]) == key:
                here = True
                break
        if not here and cur is not self.tree:
            self.nb.select(0)
        self.select_key(key, focus=True)

    # ------------------------------------------------------------ 题解包（v13）
    def _make_menu(self):
        """菜单栏：`题解包` → 导入题解包… / 导出题解包… / ── / 一键校验…（v13 三入口）。

        入口只在这里出现（不占快捷键 —— 键位表 KEY_TABLE 与说明 md 逐字同步，别动那两处）。
        """
        menubar = tk.Menu(self.root, tearoff=0)   # tearoff=0：菜单栏里别混进一条「撕下」项
        m = tk.Menu(menubar, tearoff=0)
        m.add_command(label=PACK_IMPORT_LABEL, command=lambda: self.pack_flow("import"))
        m.add_command(label=PACK_EXPORT_LABEL, command=self.pack_export_dialog)
        m.add_separator()
        m.add_command(label=PACK_CHECK_LABEL, command=lambda: self.pack_flow("check"))
        menubar.add_cascade(label=PACK_MENU_LABEL, menu=m)
        self.root.config(menu=menubar)

    def pack_flow(self, mode):
        """「导入题解包…」/「一键校验…」：选包 → 后台 dry → 报告窗。

        import 模式报告窗多一个「应用到数据根」按钮（dry 通过才亮）；check 模式只出报告。
        """
        if self._pack_job is not None:
            self.set_msg("已有题解包任务在跑，等它结束", clear_after=TOAST_MS)
            return
        pack = self._ask_pack_path()
        if not pack:
            return
        title = PACK_IMPORT_LABEL.rstrip("…") if mode == "import" else PACK_CHECK_LABEL.rstrip("…")
        win, text, status, btn = self._open_pack_report(
            title, "包：%s" % pack, allow_apply=(mode == "import"))
        self._pack_report_append(text, "正在校验 %s ……\n" % pack)
        self._start_pack_job(kind="import", pack=pack,
                             argv=pack_import_argv(pack, self.data_root, False),
                             win=win, text=text, status=status, btn=btn)

    def _ask_pack_path(self):
        """选包对话框（zip 或解压后的目录二选一）。返回路径；取消 = None。

        v16：一行四按钮布局（用户二次看图点名）—— 路径框带灰字占位；
        「选 zip…」「选目录…」与「取消」「开始」**并成一行**（选择在左、
        取消 / 开始在右，不再单占底排）；主按钮「开始」用 Accent 样式、
        空路径时禁用（原来点了静默没反应）。
        """
        win = tk.Toplevel(self.root)
        win.title("选择题解包")
        win.configure(bg=C_BG)
        win.transient(self.root)
        win.resizable(False, False)
        var = tk.StringVar()
        body = tk.Frame(win, bg=C_BG)
        body.pack(fill="both", expand=True, padx=16, pady=(14, 14))
        tk.Label(body, text="题解包（.zip 或解压后的目录）：", bg=C_BG, fg=C_TEXT,
                 font=(self.fam, 13)).grid(row=0, column=0, columnspan=3, sticky="w")
        ent = ttk.Entry(body, textvariable=var, width=48, font=(self.fam, 13))
        ent.grid(row=1, column=0, columnspan=3, sticky="we", pady=(6, 0))
        self._add_placeholder(ent, "包路径", register=False)   # v16：弹窗临时框不登记

        def pick(kind):
            if kind == "zip":
                p = filedialog.askopenfilename(parent=win, title="选择题解包（zip）",
                                               filetypes=[("题解包", "*.zip"), ("全部文件", "*.*")])
            else:
                p = filedialog.askdirectory(parent=win, title="选择题解包（目录）")
            if p:
                var.set(os.path.normpath(p))

        # v16：四个按钮一行 —— 选包按钮靠左，取消 / 开始在右（原来「选择一行 + 底排一行」）
        row = tk.Frame(body, bg=C_BG)
        row.grid(row=2, column=0, columnspan=3, sticky="we", pady=(10, 0))
        ttk.Button(row, text="选 zip…", command=lambda: pick("zip")).pack(side="left")
        ttk.Button(row, text="选目录…", command=lambda: pick("dir")).pack(side="left", padx=(8, 0))
        tk.Frame(row, bg=C_BG, width=32, height=1).pack(side="left", fill="x", expand=True)
        out = {"path": None}

        def ok(*_e):
            p = var.get().strip().strip('"')
            if not p:
                return
            out["path"] = os.path.normpath(p)
            win.destroy()

        btn_ok = ttk.Button(row, text="开始", style="Accent.TButton", command=ok)
        btn_ok.pack(side="right")
        ttk.Button(row, text="取消", command=win.destroy).pack(side="right", padx=(0, 8))

        def sync_ok(*_e):                           # v16：空路径 → 主按钮禁用
            btn_ok.config(state=("normal" if var.get().strip() else "disabled"))
        var.trace_add("write", sync_ok)
        sync_ok()

        ent.bind("<Return>", ok)
        win.bind("<Escape>", lambda _e: win.destroy())
        self._center_on_root(win)
        ent.focus_set()
        win.grab_set()
        win.wait_window()
        return out["path"]

    def pack_export_dialog(self):
        """「导出题解包…」：选场次（可选题号 = 单题包）→ 输出 zip → 后台导出，报告进报告窗。

        v16（只动观感 + 按钮合排）：主按钮「开始导出」用 Accent 样式；「另存为…」
        从单独一行挪到输出框同一行右端（用户点名「能合并的按钮弄到同一行」）。
        """
        if self._pack_job is not None:
            self.set_msg("已有题解包任务在跑，等它结束", clear_after=TOAST_MS)
            return
        rounds = pack_round_choices(self.rows)
        if not rounds:
            self._error("导出题解包", "状态表里没有「牛客周赛 Round N」形式的场次。")
            return
        win = tk.Toplevel(self.root)
        win.title(PACK_EXPORT_LABEL.rstrip("…"))
        win.configure(bg=C_BG)
        win.transient(self.root)
        win.resizable(False, False)
        body = tk.Frame(win, bg=C_BG)
        body.pack(fill="both", expand=True, padx=16, pady=(14, 4))
        tk.Label(body, text="场次", bg=C_BG, fg=C_TEXT, font=(self.fam, 13)).grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(body, values=rounds, state="readonly", width=24, font=(self.fam, 13))
        cb.set(rounds[0])
        cb.grid(row=0, column=1, sticky="w", padx=(8, 16))
        tk.Label(body, text="题号（空 = 整场）", bg=C_BG, fg=C_TEXT,
                 font=(self.fam, 13)).grid(row=0, column=2, sticky="w")
        ent_letter = ttk.Entry(body, width=6, font=(self.fam, 13))
        ent_letter.grid(row=0, column=3, sticky="w", padx=(8, 0))
        tk.Label(body, text="输出 zip", bg=C_BG, fg=C_TEXT,
                 font=(self.fam, 13)).grid(row=1, column=0, sticky="w", pady=(10, 0))
        var_out = tk.StringVar()
        ent_out = ttk.Entry(body, textvariable=var_out, width=44, font=(self.fam, 13))
        ent_out.grid(row=1, column=1, columnspan=2, sticky="we", padx=(8, 8), pady=(10, 0))

        def default_out(*_e):
            name, n = toolutil.parse_contest(cb.get())
            if not name or not n:
                return
            letter = ent_letter.get().strip().upper()
            var_out.set(os.path.join(os.path.expanduser("~"), "Desktop",
                                     "%sRound%d%s.zip" % (name, n, ("-" + letter) if letter else "")))

        def save_as():
            p = filedialog.asksaveasfilename(parent=win, title="题解包另存为",
                                             defaultextension=".zip",
                                             initialfile=os.path.basename(var_out.get() or "pack.zip"),
                                             filetypes=[("题解包", "*.zip")])
            if p:
                var_out.set(os.path.normpath(p))

        ttk.Button(body, text="另存为…", command=save_as).grid(
            row=1, column=3, sticky="w", pady=(10, 0))   # v16：与输出框同一行（原来单独一行）
        cb.bind("<<ComboboxSelected>>", default_out)
        ent_letter.bind("<KeyRelease>", default_out)

        def go(*_e):
            name, n = toolutil.parse_contest(cb.get())
            if not name or not n:
                messagebox.showerror("导出题解包", "认不出场次「%s」" % cb.get(), parent=win)
                return
            letter = ent_letter.get().strip().upper()
            if letter and not re.match(r"^[A-Z]$", letter):
                messagebox.showerror("导出题解包", "题号要写单个字母（A~Z），或留空导整场", parent=win)
                return
            target = "Round%d%s" % (n, ("-" + letter) if letter else "")
            out = var_out.get().strip().strip('"')
            if not out:
                messagebox.showerror("导出题解包", "给输出 zip 挑个位置（`另存为…`）", parent=win)
                return
            win.destroy()
            w2, text, status, btn = self._open_pack_report(
                PACK_EXPORT_LABEL.rstrip("…"), "导出 %s → %s" % (target, out), allow_apply=False)
            self._pack_report_append(text, "正在导出 %s ……\n" % target)
            self._start_pack_job(kind="export", pack=None,
                                 argv=pack_export_argv(target, out, self.data_root),
                                 win=w2, text=text, status=status, btn=btn)

        btns = tk.Frame(win, bg=C_BG)
        btns.pack(fill="x", padx=16, pady=(8, 14))
        ttk.Button(btns, text="开始导出", style="Accent.TButton", command=go).pack(side="right")
        ttk.Button(btns, text="取消", command=win.destroy).pack(side="right", padx=(0, 8))
        ent_out.bind("<Return>", go)
        win.bind("<Escape>", lambda _e: win.destroy())
        self._center_on_root(win)
        default_out()
        cb.focus_set()
        win.grab_set()
        win.wait_window()

    def _open_pack_report(self, title, subtitle, allow_apply):
        """报告窗：只读文本框 + 状态行 +（导入时）「应用到数据根」。

        返回 (win, text, status, btn)；btn 在 allow_apply=False 时没 pack（调用方仍可拿到）。
        """
        win = tk.Toplevel(self.root)
        win.title("题解包 —— %s" % title)
        win.configure(bg=C_BG)
        win.geometry("860x560")
        top = tk.Frame(win, bg=C_BG)
        top.pack(fill="x", padx=14, pady=(12, 0))
        tk.Label(top, text=subtitle, bg=C_BG, fg=C_MUTED, font=(self.fam, 12),
                 anchor="w", justify="left").pack(fill="x")
        body = tk.Frame(win, bg=C_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(8, 0))
        text = tk.Text(body, wrap="none", font=("Consolas", 10), bg=C_PANEL, fg=C_TEXT,
                       relief="solid", borderwidth=1)
        sb = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.configure(state="disabled")
        status = tk.Label(win, text="跑着呢……", bg=C_BG, fg=C_ACCENT_DARK, anchor="w",
                          font=(self.fam, 13, "bold"))
        status.pack(fill="x", padx=14, pady=(8, 0))
        btns = tk.Frame(win, bg=C_BG)
        btns.pack(fill="x", padx=14, pady=(6, 12))
        tk.Button(btns, text="关闭", command=win.destroy).pack(side="right")
        btn = None
        if allow_apply:
            btn = ttk.Button(btns, text="应用到数据根", style="Accent.TButton", state="disabled")
            btn.pack(side="right", padx=(0, 8))      # v16：主按钮样式（禁用时自动变浅灰）
        self._center_on_root(win)
        return win, text, status, btn

    def _pack_report_append(self, text, chunk):
        """往报告窗追加一段（只读 Text：临时放开 → 追加 → 收回 → 滚到底）。"""
        try:
            text.configure(state="normal")
            text.insert("end", chunk)
            text.configure(state="disabled")
            text.see("end")
        except tk.TclError:
            pass                                  # 报告窗被关了：任务照跑

    def _start_pack_job(self, kind, pack, argv, win, text, status, btn, applied=False):
        """后台线程跑 import / export 的 main()：stdout 实时贴进报告窗（同时只跑一个）。"""
        q = queue.Queue()
        self._pack_job = {"win": win, "kind": kind, "pack": pack, "queue": q, "applied": applied}

        def worker():
            old = (sys.stdout, sys.stderr)

            class _QW:                             # stdout → 队列（报告窗实时刷）
                def write(self, s):
                    if s:
                        q.put(("out", s))
                    return len(s)

                def flush(self):
                    pass

                def reconfigure(self, **kw):       # 子脚本模块顶层会调（见 pack_cli 的同款注释）
                    return None
            sys.stdout = sys.stderr = _QW()
            rc = 1
            try:
                mod = _load_tool("export_solution" if kind == "export" else "import_solution")
                try:
                    rc = mod.main(list(argv))
                except SystemExit as e:
                    rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            except Exception:
                traceback.print_exc()
                rc = 1
            finally:
                sys.stdout, sys.stderr = old
            q.put(("done", rc))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        self._poll_pack_job(win, text, status, btn)

    def _poll_pack_job(self, win, text, status, btn):
        """每 150ms 把后台任务的输出贴出来；跑完按（退出码, 是否 --apply）落状态行。

        报告窗被关掉也不打断任务（改轮 root）——跑完一样清 _pack_job、该 reload 就 reload。
        """
        job = self._pack_job
        if job is None:
            return
        rc = None
        try:
            while True:
                kind, payload = job["queue"].get_nowait()
                if kind == "out":
                    self._pack_report_append(text, payload)
                else:
                    rc = payload
        except queue.Empty:
            pass
        if rc is None:
            try:
                if win.winfo_exists():
                    win.after(150, lambda: self._poll_pack_job(win, text, status, btn))
                    return
            except tk.TclError:
                pass
            self.root.after(150, lambda: self._poll_pack_job(win, text, status, btn))
            return
        self._pack_job = None
        pack, applied, job_kind = job["pack"], job["applied"], job["kind"]
        if job_kind == "export":
            can_apply = False
            verdict = ("导出完成 —— 包在上面写的路径（清单见上）" if rc == 0
                       else "导出失败（退出码 %d，看上面的报错）" % rc)
        else:
            can_apply, verdict = pack_verdict(rc, applied)
        try:
            status.config(text=verdict, fg=(C_OK if rc == 0 else C_ERR))   # v16：成功绿 / 失败红
        except tk.TclError:
            pass
        if can_apply and btn is not None:
            try:
                btn.config(state="normal",
                           command=lambda: self._pack_apply(pack, win, text, status, btn))
            except tk.TclError:
                pass
        if job_kind == "import" and applied and rc == 0:
            self.reload(note="已导入题解包", clear_after=TOAST_MS)

    def _pack_apply(self, pack, win, text, status, btn):
        """「应用到数据根」：同一个包带 --apply 再跑一遍（这一步才真写盘）。"""
        if self._pack_job is not None:
            self.set_msg("已有题解包任务在跑，等它结束", clear_after=TOAST_MS)
            return
        parent = win if getattr(win, "winfo_exists", lambda: False)() else self.root
        if not messagebox.askyesno(
                "导入题解包",
                "把 %s 导进数据根？\n\n会写文件 / 索引 / 状态表 / 台账（写前自动备份）。"
                % os.path.basename(pack), parent=parent):
            return
        try:
            btn.config(state="disabled")
        except tk.TclError:
            pass
        self._pack_report_append(text, "\n" + "─" * 62 + "\n── 应用（--apply）──\n")
        self._start_pack_job(kind="import", pack=pack,
                             argv=pack_import_argv(pack, self.data_root, True),
                             win=win, text=text, status=status, btn=btn, applied=True)

    def _center_on_root(self, win):
        """把对话框 / 报告窗摆到主窗口中间（偏上一点）。"""
        try:
            win.update_idletasks()
            w, h = win.winfo_width(), win.winfo_height()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 3
            win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        except tk.TclError:
            pass

    def _error(self, title, text):
        if not self.quiet:
            try:
                messagebox.showerror(title, text)
            except tk.TclError:
                pass


# ================================================================ 自测
def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _mirror_dir(src_dir):
    """源目录 → 备份镜像目录（口径与 toolutil.backup_to_repo 的镜像规则一致）。"""
    d = os.path.abspath(src_dir)
    mirror = d.replace(":", "").replace("\\", "_").replace("/", "_")
    return os.path.join(toolutil.BACKUP_ROOT, mirror)


def _count_bak(d):
    if not os.path.isdir(d):
        return 0
    return len([n for n in os.listdir(d) if n.endswith(".bak")])


def _run_report(md, extra=()):
    """跨工具一致性：把 status_report.py 当子进程跑一遍，返回 (退出码, 输出文本)。

    extra 会加在 --file 后（v13：拿命令行的筛选模式跟 GUI 比命中集合，真跑子进程）。
    """
    p = subprocess.run([sys.executable, SR.__file__, "--file", md] + list(extra),
                       capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def selftest():
    print("=== status_gui --selftest（v4：全程只用自造的 fixture，不碰真 md）===")
    cfg_state0 = _cfg_state(config_path_default())   # v4：自测也不许碰脚本同目录的配置文件
    tmpdir = tempfile.mkdtemp(prefix="status_gui_selftest_")
    tmp = write_fixture(os.path.join(tmpdir, "fixture.md"))
    orig_bytes = open(tmp, "rb").read()
    orig_text = read_text(tmp)
    orig_lines = orig_text.split("\n")
    src_root = TEST_BACKUP_ROOT                      # 夹具的 .bak 只进测试镜像目录
    bak_dir = _mirror_dir(src_root)
    n0 = _count_bak(bak_dir)
    print("[0] fixture = %s ｜ %d 字节 ｜ sha256(前) = %s"
          % (tmp, len(orig_bytes), _sha256(tmp)[:16]))
    print("    备份目录 = %s（现有 .bak %d 份；夹具的 .bak 只落这里，不碰真 md 的备份目录）"
          % (bak_dir, n0))
    print("    tools/status_report.py 的表头已同步到 v2 = %s" % SR_SYNCED)

    rows = annotate(parse_rows(tmp), datetime.date.today())
    states = set(r["状态"] for r in rows)
    rounds = [round_num(r["场次"]) for r in rows]
    assert len(rows) == len(FIXTURE_ROWS), len(rows)
    assert states == set(STATES), states
    assert any(r["日期"] == "" for r in rows), "fixture 要有空日期"
    assert any("｜" in r["知识点"] for r in rows), "fixture 要有带全角竖线的知识点"
    assert rounds != sorted(rounds), "fixture 的场次要是乱序的"
    print("[1] 解析：共 %d 题 ｜ %s" % (
        len(rows), " ｜ ".join("%s %d" % (s, c) for s, c in state_counts(rows).items() if c)))
    print("    6 个状态全覆盖 ✓ ｜ 有空日期 ✓ ｜ 有「｜」知识点 ✓ ｜ 场次乱序 ✓")
    assert list(SORTABLE) == ["场次", "难度", "日期"], SORTABLE
    print("    排序键（v4）= " + " / ".join(SORTABLE) + "（知识点不可排）✓")

    for i in range(4):
        print("    看板第 %d 段（%s）：%d 题" % (i + 1, segment_specs()[i][0],
                                                len(segment_rows(rows, i))))

    row = next(r for r in rows if r["日期"] == "" and r["状态"] != "待重写")
    key = (row["场次"], row["题号"])
    old = (row["状态"], row["日期"])
    idx = locate_row(orig_lines, key)
    today = datetime.date.today().isoformat()
    print("[2] 选中：%s %s（原状态 %s / 日期 %r），在第 %d 行"
          % (key[0], key[1], old[0], old[1], idx + 1))

    # 写回边界：不存在的题 / 不许改的列 → 必须拒绝，且不产生备份
    for bad_key, bad_ch in ((("不存在 Round 1", "Z"), {"状态": "未做"}),
                            (key, {"知识点": "不许改"}), (key, {"状态": "没有这个状态"})):
        try:
            save_changes(tmp, bad_key, bad_ch, backup_src_root=src_root)
            raise AssertionError("应当拒绝：%r %r" % (bad_key, bad_ch))
        except ValueError:
            pass
    assert _count_bak(bak_dir) == n0, "被拒绝的写不该产生备份"
    print("[3] 拒绝越界写（不存在的题 / 改知识点 / 非法状态）✓，未产生备份 ✓")

    bak1, _, _ = save_changes(tmp, key, {"状态": "待重写", "日期": today}, backup_src_root=src_root)
    print("[4] save_changes：状态 → 待重写，日期 → %s；备份 = %s" % (today, os.path.basename(bak1)))
    got = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == key)
    assert got["状态"] == "待重写" and got["日期"] == today, got
    print("    (a) 该行状态 / 日期写对了 ✓")

    new_lines = read_text(tmp).split("\n")
    diff = [k for k in range(len(orig_lines)) if orig_lines[k] != new_lines[k]]
    assert len(new_lines) == len(orig_lines) and diff == [idx], diff
    c0 = row_segments(orig_lines[idx])[1]
    c1 = row_segments(new_lines[idx])[1]
    for k, name in enumerate(HEADER):
        if name in EDITABLE:
            continue
        assert c1[k] == c0[k], (name, c0[k], c1[k])
    assert c1[CELL_STATE] == "待重写" and c1[CELL_DATE] == today, c1
    assert new_lines[idx] == render_row(c1), "目标行排版被改了"
    print("    (b) 其余行逐字节不变（唯一改动 = 第 %d 行）、该行其余格与排版原样 ✓" % (idx + 1))

    raw = open(tmp, "rb").read()
    crlf, cr = raw.count(b"\r\n"), raw.count(b"\r")
    assert crlf == 0 and cr == 0 and not raw.startswith(b"\xef\xbb\xbf"), (crlf, cr)
    print("    (c) 纯 LF（CRLF=%d、CR=%d）、无 BOM ✓" % (crlf, cr))

    n1 = _count_bak(bak_dir)
    assert n1 == n0 + 1, (n0, n1)
    print("    (d) 备份目录 .bak：%d → %d ✓" % (n0, n1))

    code, out = _run_report(tmp)
    n_hard = len(segment_rows(parse_rows(tmp), 0))
    if code == 0:
        sec1 = next((ln.rstrip() for ln in out.splitlines() if ln.startswith("① ")), "")
        assert sec1.endswith("：%d 题" % n_hard), sec1
        print("    (f) 跨工具：status_report.py --file <fixture> 退出码 0，%s ✓" % sec1)
    else:
        assert not SR_SYNCED, "表头已同步却读不了 fixture（退出码 %d）\n%s" % (code, out)
        ctrl = os.path.join(tmpdir, "control_fixture.md")
        write_text(ctrl, control_fixture_text())
        print("    (f) ★ 跨工具闸门暂缓：tools/status_report.py 的表头还没同步到 v2"
              "（现在是 %s），读不了 v2 fixture（退出码 %d）" % (" | ".join(_SR_HEADER), code))
        print("        主会话把它的 HEADER 同步成新表头后，重跑本条即通过；"
              "本次先验证子进程调用链本身可用：", end=" ")
        code2, _ = _run_report(ctrl)
        assert code2 == 0, "连「与 tools 同表头」的对照件都跑不通（退出码 %d）" % code2
        print("同表头对照件退出码 %d ✓" % code2)

    bak2, _, _ = save_changes(tmp, key, {"状态": old[0], "日期": old[1]}, backup_src_root=src_root)
    assert open(tmp, "rb").read() == orig_bytes, "改回后与原件不逐字节相同"
    print("    (e) 改回去：整份与原件逐字节相同 ✓；备份 %d → %d" % (n1, _count_bak(bak_dir)))

    code3, _ = _run_report(tmp)
    if SR_SYNCED:
        assert code3 == 0, "改回后 status_report --file 退出码 %d" % code3
        print("    (g) 改回后 status_report.py --file <fixture> 退出码 0 ✓")
    else:
        print("    (g) 改回后仍受「tools 未同步」影响（退出码 %d），同上待同步后重跑" % code3)

    assert _count_bak(bak_dir) == n0 + 2, _count_bak(bak_dir)
    assert _cfg_state(config_path_default()) == cfg_state0, \
        "--selftest 碰了脚本同目录的 %s（v4 要求一律不碰）" % CONFIG_NAME
    print("    (h) 脚本同目录的 %s 全程没被碰过 ✓" % CONFIG_NAME)
    print("[5] fixture 收尾：sha256 = %s（与改回后一致）｜ 临时目录保留在 %s"
          % (_sha256(tmp)[:16], tmpdir))

    # --- v13：[6] 题解包三入口的纯逻辑（argv 拼法 / 退出码文案 / 可导出场次）——
    # 不开窗口、不碰磁盘；真正的执行（后台线程 / 进程内调用）由 --smoke 与 CLI 闸门覆盖。
    assert pack_import_argv(r"X:\包.zip", r"X:\root") == [r"X:\包.zip", "--root", r"X:\root"]
    assert pack_import_argv("a.zip", "r", True) == ["a.zip", "--apply", "--root", "r"]
    assert pack_export_argv("Round163", "", "R") == ["Round163", "--root", "R"]
    assert pack_export_argv("Round163-G", "o.zip", "R") == ["Round163-G", "-o", "o.zip", "--root", "R"]
    can_after, msg_after = pack_verdict(0, True)
    can_dry, msg_dry = pack_verdict(0, False)
    assert (can_after, can_dry) == (False, True)
    assert "导入完成" in msg_after and "校验通过" in msg_dry
    assert not pack_verdict(1, False)[0] and "不合格" in pack_verdict(1, False)[1]
    assert not pack_verdict(2, False)[0] and "不可读" in pack_verdict(2, False)[1]
    rr = pack_round_choices(rows)
    want_rr = sorted({r["场次"] for r in rows}, key=round_num, reverse=True)
    assert rr == want_rr == [("牛客周赛 Round %d" % n) for n in
                             (210, 208, 207, 205, 204, 203, 202, 201, 200, 199, 197, 188)], rr
    assert pack_round_choices([{"场次": "Codeforces Round 1000"}, {"场次": "Round 161"},
                               {"场次": "AtCoder ABC 380"}, {"场次": "牛客周赛 Round 210"},
                               {"场次": "牛客周赛 Round 210"}]) == ["牛客周赛 Round 210"], \
        "只认「牛客周赛 Round N」形式（跟 export_solution 同口径）、同场次去重"
    print("[6] 题解包纯逻辑：dry / --apply 两套 argv；退出码 0/1/2 三种文案；"
          "可导出场次 = 12 场按场次号降序（非牛客 / 认不出的场次不收）✓")
    print("ALL OK")
    return 0


def _first_row_cell(gui, col):
    iid = gui.tree.get_children()[0]
    return gui.tree.item(iid, "values")[HEADER.index(col)]


def _cfg_state(path):
    """配置文件的身份（在不在 / 多大 / 啥时候改的）—— 冒烟前后比一次，证明它没被碰过。"""
    try:
        st = os.stat(path)
        return (True, st.st_size, st.st_mtime_ns)
    except OSError:
        return (False, 0, 0)


def smoke():
    """窗口冒烟：建窗口 + 走一遍排序 / 切段 / 浮层改状态，不 mainloop()（不动真 md）。"""
    print("=== status_gui --smoke（构造窗口、不开 mainloop）===")
    tmpdir = tempfile.mkdtemp(prefix="status_gui_smoke_")
    tmp = write_fixture(os.path.join(tmpdir, "fixture.md"))
    script_cfg = config_path_default()
    cfg_state0 = _cfg_state(script_cfg)         # 冒烟全程不许碰脚本同目录的配置文件
    root = tk.Tk()
    gui = StatusGui(root, tmp, quiet=True, config_path=None)
    gui.backup_src_root = TEST_BACKUP_ROOT      # 夹具的 .bak 只进测试镜像目录
    root.update_idletasks()

    def _walk(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Toplevel):       # ? 一览 / 状态浮层都是独立 Toplevel，不算主窗口
                continue
            yield c
            for d in _walk(c):
                yield d

    print("窗口标题：", root.title())
    print("总表行数：", len(gui.tree.get_children()))
    print("计数行  ：", gui.var_count.get())
    seg_n = [len(segment_rows(gui.rows, i)) for i in range(4)]
    print("看板 4 段数字：", [gui.card_num[i].cget("text") for i in range(4)],
          "（算出来 = %r）" % (seg_n,))
    assert [gui.card_num[i].cget("text") for i in range(4)] == [str(n) for n in seg_n]

    # --- v9 闸门 (hh)：顶部第一行 = 搜索标签 + 搜索框（v15 起宽 26）+ 统计 + 消息（这一行最右端）
    head = gui.ent_search.master
    assert gui.lbl_search.master is head and gui.lbl_count.master is head \
        and gui.lbl_msg.master is head and gui.lbl_hits_min.master is head, \
        "搜索 / 统计 / 消息 / 筛出计数（v14）该在同一个父容器（第一行）里"
    assert gui.lbl_search.cget("text") == "搜" + LABEL_PAD + "索", gui.lbl_search.cget("text")
    assert int(gui.ent_search.cget("width")) == 26, \
        "搜索框宽度该是 26（v15 从 13 翻倍）：%r" % gui.ent_search.cget("width")
    assert str(gui.lbl_msg.pack_info()["side"]) == "right", gui.lbl_msg.pack_info()
    heads = [str(w.cget("text")) for w in _walk(root) if w.winfo_class() == "Label"]
    assert "题目状态跟踪表" not in heads, "页头大标题还留在窗口里"
    assert not any("今天" in t for t in heads), "路径行（… ｜ 今天 …）还留在窗口里：%r" % heads
    assert gui.var_msg.get() == "", "启动时消息该是空的（不再写「已读入 …」）：%r" % gui.var_msg.get()
    print("(hh) 第一行 = 搜索标签 + 搜索框（宽 %s）+ 统计 + 消息（side=right，同一父容器）；"
          "无大标题 / 无路径行 ✓；(ll) 启动消息为空（无「已读入 …」）✓" % gui.ent_search.cget("width"))

    # --- v15 闸门 (hh2)：四个标签同宽 + 三行控件左缘一条线 + 框内留白 + 灰字占位提示
    gui._dropdown_open()                     # 先展开面板 —— 面板里的控件映射了才有真几何
    root.update()
    labels4 = (gui.lbl_search, gui.ent_know.master.winfo_children()[0],
               gui.ent_diff.master.winfo_children()[0], gui.lb_status.master.winfo_children()[0])
    widths = [w.winfo_reqwidth() for w in labels4]
    assert len(set(widths)) == 1, "四个标签该一样宽（三字宽）：%r" % (widths,)
    xs = [w.winfo_rootx() for w in (gui.ent_search, gui.ent_know, gui.ent_diff, gui.lb_status)]
    assert len(set(xs)) == 1, "搜索框与面板三行控件的左缘该排成一条线：%r（标签 rootx=%r）" % (
        xs, [w.winfo_rootx() for w in labels4])
    pad = ttk.Style(root).lookup("Nav.TEntry", "padding")
    assert str(pad) in ("(7, 5)", "7 5", ("7", "5")), "Nav.TEntry 该有统一内边距 (7,5)：%r" % (pad,)
    phs = [w for w in _walk(root) if w.winfo_class() == "Label"
           and str(w.cget("fg")) == C_PLACEHOLDER]
    assert len(phs) == 3, "三个输入框该各有一个灰字占位提示：%r" % ([w.cget("text") for w in phs],)
    assert gui.var_search.get() == "" and not gui.ent_search.get(), "占位提示不许写进搜索框的值"
    assert gui.ent_search.winfo_children() and any(
        w.place_info() for w in gui.ent_search.winfo_children()), "搜索框空着时该显示占位提示"
    gui.ent_search.focus_set()
    root.update()
    assert not any(w.place_info() for w in gui.ent_search.winfo_children()), \
        "聚焦后占位提示该隐掉"
    gui.tree.focus_set()
    root.update()
    assert any(w.place_info() for w in gui.ent_search.winfo_children()), \
        "失焦且空着时占位提示该回来"
    assert not hasattr(gui, "btn_clear"), "v15 末：「清空」按钮该已删除（用户点名「去掉清空选项」）"
    gui._dropdown_hide()                     # 收起面板，后面的闸门按「默认收起」继续
    root.update()
    print("(hh2) v15 观感：四标签同宽（%dpx）、搜索框 26、三行控件左缘一条线、Nav.TEntry padding=%s、"
          "三个灰字占位提示（聚焦隐 / 失焦回、不写进 var）、面板「清空」按钮已删 ✓" % (widths[0], pad))

    # --- v9 闸门 (ii)：那个「状态筛选**下拉框**」整块没了 —— 窗口里没有下拉框控件、没有
    #     var_filter / cmb_filter、F 不绑东西（v14 的下拉面板 = Entry + Listbox，不是把它搬回来）

    combos = [w for w in [root] + list(_walk(root)) if w.winfo_class() == "TCombobox"]
    assert combos == [], "窗口里还有下拉框：%r" % (combos,)
    assert not hasattr(gui, "var_filter") and not hasattr(gui, "cmb_filter"), \
        "var_filter / cmb_filter 属性还在"
    assert root.bind("<Key-f>") == "", "F 还绑着东西：%r" % root.bind("<Key-f>")
    gui.tree.focus_set()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="f")
    root.update()
    assert root.focus_get() is gui.tree, "按 F 不该有任何反应（焦点被抢到 %r）" % root.focus_get()
    print("(ii) 下拉框式筛选没了：窗口里 0 个 TCombobox；var_filter / cmb_filter 不存在；"
          "F 未绑定（按下去什么也不发生）✓（v14 的筛选 = 搜索框下的下拉面板：Entry + Listbox，见 (zz)）")

    # --- v3 闸门 (a)：排序键只留 场次 / 难度 / 日期（知识点不可排）
    assert list(SORTABLE) == ["场次", "难度", "日期"], SORTABLE
    assert gui.tree.heading("知识点", "command") == "", "「知识点」不该再接排序命令"
    gui.sort_col, gui.sort_desc = "场次", False
    gui.refresh_view()
    seen = []
    for _ in range(3):                       # S 循环：场次 → 难度 → 日期 → 场次
        gui._sort_next_key()
        seen.append(gui.sort_col)
    assert seen == ["难度", "日期", "场次"], seen
    assert gui.sort_desc is False, "S 换字段后应回到升序"
    print("(a) 排序键循环：场次 → %s（知识点不在列）✓" % " → ".join(seen))

    # --- v4 闸门 (b)：点表头 / S / R 换排序后，选中行**钉在原行号**（v4 翻盘：不再跟题走）
    def _sel_key():
        r = gui.tree_row(gui.tree)
        return (r["场次"], r["题号"]) if r else None

    def _sel_row():
        iid = gui.tree.focus()
        return gui.tree.index(iid) if iid else None

    gui.sort_col, gui.sort_desc = "场次", False
    gui.refresh_view()
    ids = list(gui.tree.get_children())
    pick = len(ids) // 2
    gui.tree.selection_set(ids[pick])
    gui.tree.focus(ids[pick])
    gui.tree.see(ids[pick])
    key0, row0 = _sel_key(), _sel_row()
    changed = []
    for step, call in (("S", gui._sort_next_key), ("R", gui._sort_toggle_key)):
        call()
        assert _sel_row() == row0, \
            "%s 换排序后行号应原样不动（v4 钉行号）：第 %s 行 → 第 %s 行" % (step, row0, _sel_row())
        assert gui.tree.focus() == gui.tree.selection()[0], "selection 与 focus 都要跟上"
        changed.append(_sel_key() != key0)
    gui.on_sort("日期")                                   # 点表头同效
    assert _sel_row() == row0, "点表头换排序后行号应原样不动：第 %s 行" % (_sel_row(),)
    assert gui.tree.focus() == gui.tree.selection()[0], "selection 与 focus 都要跟上"
    changed.append(_sel_key() != key0)
    assert any(changed), "换了三次排序、行里的题一次都没变 —— 这条断言等于白测"
    print("(b) 换排序钉在原行号：第 %d 行从头到尾没动（S / R / 点表头各一次）；"
          "行里的题 %s %s → %s %s ✓"
          % (row0, key0[0], key0[1], _sel_key()[0], _sel_key()[1]))

    other = {"场次": "日期", "难度": "场次", "日期": "难度"}
    for col in SORTABLE:                     # 点一下升序、再点一下降序（每个可排序键各一遍）
        gui.sort_col, gui.sort_desc = other[col], False   # 先让「当前排序列」不是它
        gui.refresh_view()
        gui.on_sort(col)
        up, first_up = gui.tree.heading(col)["text"], _first_row_cell(gui, col)
        gui.on_sort(col)
        down, first_dn = gui.tree.heading(col)["text"], _first_row_cell(gui, col)
        assert up.endswith("▲") and down.endswith("▼"), (col, up, down)
        print("排序 %s：升「%s」首行=%s ｜ 降「%s」首行=%s" % (col, up, first_up, down, first_dn))
    dates = [c for c in map(lambda i: gui.tree.item(i, "values")[HEADER.index("日期")],
                            gui.tree.get_children())]
    assert dates == sorted([d for d in dates if d], reverse=True) + [""] * dates.count(""), \
        "日期降序时空日期应排最后：%r" % (dates,)
    gui.sort_col, gui.sort_desc = "场次", False      # 回到默认：场次升序 → 题号升序
    gui.refresh_view()

    ids = list(gui.tree.get_children())
    gui.tree.selection_set(ids[0])
    gui.tree.focus(ids[0])
    gui._move_sel(gui.tree, "pgdn")
    assert _sel_row() == min(12, len(ids) - 1), _sel_row()
    gui._move_sel(gui.tree, "pgup")
    assert _sel_row() == 0, _sel_row()
    print("PgUp / PgDn 翻页 ✓（Home / End 已删）")

    # --- v3 闸门 (g)：两棵树都不再有 Home / End 绑定（一个功能只留一个键）
    for t, name in ((gui.tree, "总表"), (gui.today_tree, "看板")):
        assert t.bind("<Home>") == "" and t.bind("<End>") == "", \
            "%s树上还有 Home / End 绑定" % name
    print("(g) 无 <Home> / <End> 绑定 ✓")

    # --- v5 闸门 (k)：主窗口不再挂常驻快捷键提示（快捷键只由 ? 一览说明）
    hot = [str(w.cget("text")) for w in _walk(root)
           if w.winfo_class() == "Label"
           and ("看快捷键" in str(w.cget("text")) or "F5 重读" in str(w.cget("text")))]
    assert hot == [], "主窗口还有常驻快捷键提示：%r" % hot
    tvs = [str(w.cget("textvariable")) for w in _walk(root)
           if w.winfo_class() == "Label" and str(w.cget("textvariable"))]
    assert str(gui.var_count) in tvs, "计数行被误删了"
    assert str(gui.var_msg) in tvs, "消息提示行（v9 在第一行最右端）被误删了"
    print("(k) 主窗口无常驻快捷键提示行（只在 ? 一览里）；计数行 / 消息提示行仍在 ✓")

    # --- v7 闸门 (z)：页签栏整条隐藏 —— 客户端区贴顶 + nb.select() 语义照旧
    #     （改之前这个差 = 48px = 页签高度；负向探针见交付说明。）
    root.update()
    tab_gap = gui.tab_all.winfo_rooty() - gui.nb.winfo_rooty()
    assert tab_gap <= 4, \
        "Notebook 标签区还在：客户端区距 nb 顶 %d px（页签高度约 48px）" % tab_gap
    gui.nb.select(0)
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0 and gui.tab_all.winfo_ismapped() \
        and not gui.tab_today.winfo_ismapped(), "nb.select(0) 后可见的该是总表页"
    gui.nb.select(1)
    root.update()
    assert gui.nb.index(gui.nb.select()) == 1 and gui.tab_today.winfo_ismapped() \
        and not gui.tab_all.winfo_ismapped(), "nb.select(1) 后可见的该是看板页"
    gui.nb.select(0)
    root.update()
    print("(z) 页签栏整条隐藏：客户端区距 nb 顶 %d px（≤4；改前 48px = 页签高度）；"
          "nb.select(0)/select(1) 照旧切页（可见的是对应 frame）✓" % tab_gap)

    # --- v7 闸门 (aa)：界面上没有「提示括号」（主窗口 Label / Entry 的文案 + 两棵树的单元格）
    BANNED = ("（场次", "（卡住", "（筛选显示", "（无匹配", "（无）", "← / → 换段")
    seen_txt = []
    for w in _walk(root):                        # Toplevel（? 一览 / 浮层）不在 _walk 里
        try:
            if w.winfo_class() == "Label":
                seen_txt.append(str(w.cget("text")))
            tv = str(w.cget("textvariable"))
        except tk.TclError:
            tv = ""
        if tv:                                   # textvariable 的那几个（计数行 / 消息行）要按「值」查
            try:
                seen_txt.append(str(root.getvar(tv)))
            except tk.TclError:
                pass
    for tr in (gui.tree, gui.today_tree):
        for iid in tr.get_children():
            seen_txt.extend(str(v) for v in tr.item(iid, "values"))
    hit = sorted(set(s for s in seen_txt for b in BANNED if b in s))
    assert hit == [], "界面上还有提示括号：%r" % hit
    print("(aa) 界面上没有提示括号：扫了 %d 段文案（Label / 计数行 / 消息行 / 两棵树的单元格），"
          "%d 个禁用子串 %s 一个都没命中 ✓" % (len(seen_txt), len(BANNED), "/".join(BANNED)))

    # --- v7 闸门 (bb)：看板第 2 段卡片标题 / 搜索标签的文案定死（v15：标签插了全角空格）
    cap2 = gui.card_cap[1].cget("text")
    sea = gui.lbl_search.cget("text")
    assert cap2 == "2. 待补题", cap2
    assert sea == "搜" + LABEL_PAD + "索", sea
    print("(bb) 看板第 2 段卡片标题 = %r；搜索标签 = %r ✓" % (cap2, sea))

    # --- v7 闸门 (cc) 已随「状态筛选」整块删除（下拉框没了，样式断言无处可测）——
    #     替代断言 = (ii)：窗口里遍历不到 TCombobox / 没有 var_filter / cmb_filter / F 键。

    # --- v8 闸门 (dd)~(ff)：输入法守卫 —— 只有搜索框收中文，别处一律摘掉
    #     断言里查 ImmGetContext 一律走 ctypes.windll.imm32；判「有没有挂」用 is None（不跟 0/False 比）。
    root.update()
    imm_ok = False
    try:
        _imm = ctypes.windll.imm32
        _imm.ImmGetContext.restype = ctypes.c_void_p
        _imm.ImmGetContext.argtypes = [ctypes.c_void_p]
        imm_ok = True
    except Exception as e:
        print("(dd)~(ff) ★ 跳过：拿不到 imm32（%s）" % e)

    def _hctx(w):
        return _imm.ImmGetContext(ctypes.c_void_p(w.winfo_id()))

    if not imm_ok:
        print("(dd)~(ff) ★ 跳过：拿不到 imm32 —— 不假装通过")
    else:
        # 「跳不跳」要独立量一次：新造一个没被守卫碰过的控件，它的上下文 = 线程默认；
        # 只有它也是 None（系统根本没有输入法环境）才允许跳过 —— 「守卫自己没跑」不在此列。
        probe_w = tk.Frame(root)
        probe_w.update_idletasks()
        default_seen = _hctx(probe_w)
        probe_w.destroy()
        if default_seen is None:
            print("(dd)~(ff) ★ 跳过：系统没有输入法上下文（新控件 ImmGetContext 也是 None）"
                  "—— 不假装通过")
        else:
            assert gui.ime.available, "imm32 拿得到、守卫就该是可用的"
            assert gui.ime.default_ctx is not None, "守卫没在窗口建好时取到默认上下文（install 没跑？）"
            assert _hctx(gui.tree) is None, "总表树的输入法没摘掉：%r" % (_hctx(gui.tree),)
            assert _hctx(gui.today_tree) is None, "看板清单的输入法没摘掉：%r" % (_hctx(gui.today_tree),)
            print("(dd) 建好窗口后输入法已摘：总表树 / 看板清单 ImmGetContext 都是 None ✓")
            gui.ent_search.focus_set()
            root.update()
            assert _hctx(gui.ent_search) is not None, "搜索框里中文要能打（ImmGetContext 不该是 None）"
            print("(ee) 焦点进搜索框：搜索框 ImmGetContext=%r（非 None，中文打得出来）✓"
                  % (_hctx(gui.ent_search),))
            gui.tree.focus_set()
            root.update()
            assert _hctx(gui.ent_search) is None, "离开搜索框后输入法该立刻摘掉"
            print("(ff) 焦点回总表树：搜索框 ImmGetContext=None（离开就摘）✓")

    # --- v8 闸门 (gg)：守卫不可用时（非 Windows / 拿不到 imm32）整条路是 no-op，不许抛异常
    g8 = gui.ime
    was_avail, was_imm = g8.available, g8._imm
    ctx8 = _hctx(gui.ent_search) if imm_ok else None
    calls8 = []

    class _Spy8(object):                 # 假 imm32：被碰到就记一笔（不可用时一个都不该来）
        def ImmGetContext(self, *a):
            calls8.append("ImmGetContext")
            return None

        def ImmAssociateContext(self, *a):
            calls8.append("ImmAssociateContext")
            return None

    g8.available = False                 # 临时置假：模拟「非 Windows / 拿不到 imm32」
    g8._imm = _Spy8()
    for w in (gui.tree, gui.today_tree, gui.ent_search, root, None):
        g8.detach(w)                     # 一律 no-op，不许抛异常
        g8.attach(w)
    g8.on_focus_in()
    g8.detach_tree(root)
    g8.watch(root)
    g8.install()
    g8.available, g8._imm = was_avail, was_imm       # 还原：后面还要真用
    assert calls8 == [], "不可用时不该碰 imm32（%d 次：%r）" % (len(calls8), calls8)
    assert gui.tree.winfo_exists() and gui.ent_search.winfo_exists(), "窗口该照常可用"
    gui.refresh_view()
    assert gui.tree.get_children(), "窗口照常可用（重绘后总表里有行）"
    if imm_ok:
        assert _hctx(gui.ent_search) == ctx8, "不可用时不许动输入法状态（no-op）"
    print("(gg) 守卫置假：attach / detach / on_focus_in / detach_tree / watch / install 全不抛异常、"
          "一次都没碰到 imm32，输入法状态没动、窗口照常可用 ✓")

    # --- v3 闸门 (c)(d)：/ 搜索、Esc 回表格（键盘进得去）；v9：F 那半边随筛选删除
    gui.nb.select(0)
    gui.tree.focus_set()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="slash")
    root.update()
    assert root.focus_get() is gui.ent_search, root.focus_get()
    print("(c) 按 / ：焦点进搜索框 ✓")
    gui.ent_search.event_generate("<KeyPress>", keysym="f")     # 搜索框里 F 是普通字符
    root.update()
    assert root.focus_get() is gui.ent_search, "搜索框里打 F 不该被抢走"
    gui.var_search.set("双指针")
    gui.ent_search.event_generate("<Escape>")                   # v14 起逐层退回：有字先清空（人留在框里）
    root.update()
    assert gui.var_search.get() == "", gui.var_search.get()
    assert root.focus_get() is gui.ent_search, root.focus_get()
    gui.ent_search.event_generate("<Escape>")                   # 再按一次（空框、面板收着）才回表格
    root.update()
    assert root.focus_get() is gui.tree, root.focus_get()
    print("(d) 搜索框 Esc 逐层退回（v14）：有字先清空、再按一次才回表格 ✓")
    n_focus_before = root.focus_get()
    gui.tree.event_generate("<KeyPress>", keysym="f")           # v9：F 不再跳任何地方
    root.update()
    assert root.focus_get() is n_focus_before, "按 F 不该跳焦点（现在是 %r）" % root.focus_get()
    print("(c) 按 F ：不再跳筛选（绑定已删，什么也不发生）✓")
    # --- v6 闸门 (q)：← / → 走 5 格横排（总表 → 1 待重写 → 2 待补题 → 3 复习 → 4 抽检），两头绕回
    gui.nb.select(0)
    gui.show_segment(2)                     # 先把「上次停在哪段」搅乱：进段不该记忆
    gui.nb.select(0)
    gui.tree.focus_set()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 1 and gui.seg_idx == 0, \
        "总表按 → 应进「今天要做的」第 1 段（不记忆上次停在哪段）"
    assert root.focus_get() is gui.today_tree, "进段后焦点要落到该页清单上"
    assert gui.card_box[0].cget("bg") == C_ACCENT, "当前段强调色要同步"
    # v10：进段恢复的是本段记忆 —— 此刻记忆 = 第 1 行（本段此前没动过选中）；记忆行为的总测在 (rr)
    assert gui.today_tree.focus() != "" and gui._index_of(gui.today_tree) == 0, \
        "进段后选中行要落到本段（v10：上次那行；本场还没动过 = 第 1 行）"
    gui.today_tree.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.seg_idx == 1, "第 1 段按 → 应到第 2 段"
    gui.today_tree.event_generate("<KeyPress>", keysym="Left")
    root.update()
    assert gui.seg_idx == 0, "第 2 段按 ← 应回第 1 段"
    gui.today_tree.event_generate("<KeyPress>", keysym="Left")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0, "第 1 段按 ← 应回总表"
    assert root.focus_get() is gui.tree, "回总表后焦点在总表树"
    gui.tree.event_generate("<KeyPress>", keysym="Left")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 1 and gui.seg_idx == 3, "总表按 ← 应进第 4 段"
    gui.today_tree.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0, "第 4 段按 → 应回总表"
    # 浮层开着时 ← / → 不响应（v5 的规则原样保留）
    iid_t = gui.tree.get_children()[0]
    gui.tree.selection_set(iid_t)
    gui.tree.focus(iid_t)
    gui.open_status_popup(gui.row_by_iid(iid_t), gui.tree)
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0 and gui.seg_idx == 3, \
        "浮层开着时 ← / → 不该动（页与段都不动）"
    assert gui._nav_arrow(1) is None, "浮层开着时导航处理要「不响应」"
    assert gui.nb.index(gui.nb.select()) == 0, "浮层开着时不该动（直接调用也不行）"
    gui._popup_cancel()
    root.update()
    print("(q) ← / → 走 5 格（总表 →1→2→3→4→ 总表，两头绕回）：进段时强调色 / 清单 / "
          "选中行（v10：本段记忆，没记过 = 第 1 行）/ 焦点都到位、不记上次哪段；浮层开着时不响应 ✓")

    # --- (o) 焦点在搜索框里时 ← / → 不切页，控件行为照旧（v9：筛选半边删除）
    gui.nb.select(0)
    gui.var_search.set("abc")
    gui.refresh_view()
    # 焦点前置用 focus_force：浮层（Toplevel）关掉后 Tk 的显示焦点是空，
    # 非强制的 focus_set 要等系统把主窗口激活才生效（无人值守/别的窗口占前台时会推迟），
    # 合成按键就送不到控件上 —— 强制设置让这段自测与「窗口有没有被激活」无关（断言不变）
    gui.ent_search.focus_force()
    gui.ent_search.icursor("end")
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="Left")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0, "搜索框里按 ← 不该切页"
    assert gui.ent_search.index("insert") == 2, "搜索框里 ← 应照常挪光标（3 → 2）"
    assert gui.var_search.get() == "abc", "搜索框内容不该被动"
    gui.ent_search.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 0, "搜索框里按 → 不该切页"
    assert gui.ent_search.index("insert") == 3, "搜索框里 → 应照常挪光标（2 → 3）"
    # v6：看板页上（焦点在搜索框里）← / → 同样只做控件自己的事，不换格
    gui.nb.select(1)
    gui.show_segment(2)
    root.update()
    gui.ent_search.focus_force()        # 同上：浮层关掉之后非强制 focus_set 会被推迟
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="Left")
    gui.ent_search.event_generate("<KeyPress>", keysym="Right")
    root.update()
    assert gui.nb.index(gui.nb.select()) == 1 and gui.seg_idx == 2, \
        "看板页上焦点在搜索框时 ← / → 不该换格"
    print("(o) 搜索框里 ← / → 不换格、光标照常（3→2→3）、内容没动（看板页同样）✓")
    gui.var_search.set("")
    gui.refresh_view()
    gui.nb.select(0)
    gui.tree.focus_set()
    root.update()

    # --- v6 闸门 (r)：看板页数字键不切段（浮层里 1~6 直选照旧）
    #     v12 口径更新：数字键仍不切段，但已改挂到两棵树上做「直接改状态」——root 上依然一个
    #     数字键都不许有；「无选中」时按数字静默：不切段、文件一个字不动。
    for k in range(1, 5):
        assert root.bind("<Key-%d>" % k) == "" and root.bind("<KP_%d>" % k) == "", \
            "root 上还挂着数字键 %d（v12 起数字键只许挂树上）" % k
    gui.nb.select(1)
    gui.show_segment(1)
    root.update()
    sel_r = gui.today_tree.selection()
    if sel_r:
        gui.today_tree.selection_remove(*sel_r)
    gui.today_tree.focus("")            # v12：tree_row 无选中时会拿 focus 当当前行 —— 真「无选中」两样都清
    root.update()
    bytes_r0 = open(tmp, "rb").read()
    for k in (1, 2, 3, 4):
        gui.today_tree.event_generate("<KeyPress>", keysym=str(k))
        root.update()
        assert gui.seg_idx == 1, "看板页按 %d 不该再切段（段只认 ← / →）" % k
    assert open(tmp, "rb").read() == bytes_r0, "没选中行时按数字不许改任何东西（v12）"
    print("(r) 看板页数字键不切段（v12 起 = 直接改状态；root 上没有数字键；无选中按数字文件不动）")
    # 浮层里数字键照旧：按「待重写」的序号 = 直选那个状态（别把浮层的数字直选一起删了）
    gui.nb.select(0)
    want3 = "待重写"                             # v10：按状态名取，不依赖顺序下标
    key3 = STATES.index(want3) + 1
    iid = next(x for x in gui.tree.get_children()
               if gui.row_by_iid(x)["状态"] != want3)
    gui.tree.selection_set(iid)
    gui.tree.focus(iid)
    row3 = gui.row_by_iid(iid)
    gui.open_status_popup(row3, gui.tree)
    assert gui.popup is not None, "浮层没弹出来"
    root.update()
    assert gui.popup_lb.winfo_viewable(), "浮层应已可见"
    gui.popup_lb.event_generate("<KeyPress>", keysym=str(key3))
    root.update()
    assert gui.popup is None, "数字直选后浮层应关闭"
    got = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row3["场次"], row3["题号"]))
    assert got["状态"] == want3 and row3["状态"] != want3, (row3["状态"], got["状态"])
    print("(r) 浮层里按 %d → 直接写入第 %d 个状态「%s」（浮层数字直选没被误删）✓"
          % (key3, key3, want3))

    # --- v9 闸门 (jj)：Tab / Shift+Tab 焦点轮换（v14：两站 —— 主页面 ⇄ 搜索；
    #     下拉面板里的行（知识点 / 难度 / 状态）都按「搜索」这一站算）
    assert root.bind("<Tab>") != "" and root.bind("<Shift-Tab>") != "", \
        "root 上要挂 Tab / Shift-Tab 焦点轮换"
    gui.nb.select(0)
    gui.tree.focus_force()                   # 合成按键 / 反复查 focus_get 前先 focus_force：
    root.update()                            # 窗口没拿到 OS 焦点时 focus_get() 会给 None（v10 踩过）
    gui._dropdown_hide()
    root.update()
    ring = [gui.ent_search, gui.tree]
    seq = []
    for _ in range(2 * len(ring)):            # 绕两圈：每圈 2 站
        w = root.focus_get()
        assert w is not None, "轮换过程中焦点不能丢"
        w.event_generate("<KeyPress>", keysym="Tab")
        root.update()
        seq.append(root.focus_get())
    assert seq == ring * 2, "Tab 轮换序列不对：%r" % ([str(x) for x in seq],)
    gui.tree.focus_force()
    root.update()
    seq2 = []
    for _ in range(len(ring)):                # Shift+Tab 反向：树 → 搜索框 → 树
        root.focus_get().event_generate("<KeyPress>", keysym="Tab", state=0x1)
        root.update()
        seq2.append(root.focus_get())
    assert seq2 == [gui.ent_search, gui.tree], "Shift+Tab 反向轮换不对：%r" % ([str(x) for x in seq2],)
    # 面板里任意一行都算「搜索」站：从面板按 Tab（或 Shift+Tab）都回主页面，并自动收面板
    gui.ent_search.focus_force()
    root.update()
    gui._dropdown_open()
    root.update()
    assert gui.dlg_open and gui.dlg.winfo_ismapped(), "展开后面板该占位显示"
    gui.ent_know.focus_force()
    root.update()
    gui.ent_know.event_generate("<KeyPress>", keysym="Tab")
    root.update()
    assert root.focus_get() is gui.tree, "从面板里按 Tab 该跳到主页面"
    assert not gui.dlg_open, "离开搜索站该把面板收起"
    gui.ent_search.focus_force()
    root.update()
    gui._dropdown_open()
    root.update()
    gui.lb_status.focus_force()
    root.update()
    gui.lb_status.event_generate("<KeyPress>", keysym="Tab", state=0x1)
    root.update()
    assert root.focus_get() is gui.tree and not gui.dlg_open, \
        "从状态列表按 Shift+Tab 也该回主页面并收起面板（两站环里两个方向同一条路）"
    # 页签 / 段卡片等「中间控件」都不进轮换：takefocus 关掉；Tab 处理只在 root 一处
    for w, name in ((gui.nb, "Notebook"), (gui.card_box[0], "段卡片"),
                    (gui.card_num[0], "卡片数字"), (gui.card_cap[0], "卡片标题")):
        assert str(w.cget("takefocus")) in ("0", "False", "false"), \
            "%s 的 takefocus 没关：%r" % (name, w.cget("takefocus"))
    for w, name in ((gui.tree, "总表树"), (gui.today_tree, "看板树"),
                    (gui.ent_search, "搜索框"),
                    (gui.ent_know, "知识点框"), (gui.ent_diff, "难度框"),
                    (gui.lb_status, "状态列表"), (gui.dlg, "下拉面板"),
                    (gui.nb, "Notebook"), (gui.tab_all, "总表页"),
                    (gui.tab_today, "看板页"), (gui.today_cards, "看板卡片区")):
        assert w.bind("<Tab>") == "" and w.bind("<Shift-Tab>") == "", \
            "%s 上也挂了 Tab 绑定（应该只在 root 一处处理）" % name
    assert root.bind_all("<Tab>") == "" and root.bind_all("<Shift-Tab>") == "", \
        "bind_all 上还有 Tab 处理"
    print("(jj) Tab 两站轮换（v14）：主页面 ⇄ 搜索，正反两圈都只停这两站；面板里任意一行都按"
          "「搜索」站算（Tab / Shift+Tab 都回主页面并收面板）；页签 / 段卡片 takefocus 全关、"
          "Tab 处理只在 root ✓")

    # --- v6 闸门 (t)：两个焦点各有可见指示（选中行换色 / 输入框边框 + 底色换强调色）
    st = ttk.Style(root)
    bg_on = st.lookup("Status.Treeview", "background", ("selected", "focus"))
    bg_off = st.lookup("Status.Treeview", "background", ("selected", "!focus"))
    fg_on = st.lookup("Status.Treeview", "foreground", ("selected", "focus"))
    fg_off = st.lookup("Status.Treeview", "foreground", ("selected", "!focus"))
    assert bg_on == C_ACCENT and bg_off == C_SELECT_OFF and bg_on != bg_off, (bg_on, bg_off)
    assert fg_on != fg_off, (fg_on, fg_off)
    en_b = dict((s, st.lookup("Nav.TEntry", "bordercolor", s)) for s in (("focus",), ("!focus",)))
    en_g = dict((s, st.lookup("Nav.TEntry", "fieldbackground", s)) for s in (("focus",), ("!focus",)))
    assert en_b[("focus",)] == C_ACCENT and en_b[("focus",)] != en_b[("!focus",)], en_b
    assert en_g[("focus",)] != en_g[("!focus",)], en_g
    gui.tree.focus_set()
    root.update()
    assert gui.tree.instate(["focus"]), "总表聚焦时 ttk 要有 focus 状态（样式才切得动）"
    gui.ent_search.focus_set()
    root.update()
    assert gui.ent_search.instate(["focus"]) and not gui.tree.instate(["focus"])
    print("(t) 焦点可见：选中行 %s（有焦点）/ %s（没焦点）；搜索框边框 %s + 底色变化；"
          "两个控件都真挂得上 focus 状态 ✓" % (bg_on, bg_off, en_b[("focus",)]))

    for i in range(4):
        gui.show_segment(i)
        n = len(gui.today_tree.get_children())
        assert n == len(segment_rows(gui.rows, i)), (i, n)
        assert gui.card_box[i].cget("bg") == C_ACCENT, "当前段要用强调色标出"
        print("切段 %d：%s ｜ 清单 %d 行" % (i + 1, segment_specs()[i][0], n))
    gui.show_segment(0)
    assert gui.today_tree.focus() != "", "切段后清单要有选中行"

    # 看板页也回车弹浮层
    gui.nb.select(1)

    class _Ev(object):
        widget = None

    ev = _Ev()
    ev.widget = gui.today_tree
    iid = gui.today_tree.get_children()[0]
    gui.today_tree.selection_set(iid)
    gui.today_tree.focus(iid)
    gui._on_open_key(ev)                            # 等价于在看板清单里按回车
    assert gui.popup is not None, "看板页回车也要弹浮层"
    gui._popup_cancel()
    gui.nb.select(0)

    iid = gui.tree.get_children()[0]
    gui.tree.selection_set(iid)
    gui.tree.focus(iid)
    row = gui.row_by_iid(iid)
    print("浮层目标：%s %s（原状态 %s）" % (row["场次"], row["题号"], row["状态"]))
    gui.open_status_popup(row, gui.tree)
    assert gui.popup is not None and gui.popup_lb.size() == len(STATES)
    raw = [gui.popup_lb.get(i) for i in range(gui.popup_lb.size())]
    texts = [re.sub(r"^\d+\.\s*", "", t) for t in raw]
    assert texts == STATES, texts
    assert gui.popup_lb.curselection() == (STATES.index(row["状态"]),), "浮层应默认选在当前状态"
    want_no = ["%d. " % (k + 1) for k in range(len(STATES))]     # v5 闸门 (l)
    assert all(t.startswith(w) for t, w in zip(raw, want_no)), raw
    bad = [str(w.cget("text")) for w in _walk(gui.popup)          # v5 闸门 (m)
           if w.winfo_class() == "Label"
           and ("直选" in str(w.cget("text")) or "Enter 确认" in str(w.cget("text")))]
    assert bad == [], "浮层里还有提示行：%r" % bad
    print("浮层：%d 项带序号、顺序 = %s，当前状态高亮选中（首项 = %r）"
          % (gui.popup_lb.size(), " / ".join(texts), raw[0]))
    print("(l) 浮层 6 项依次以 1. ~ 6. 开头（数字键与序号一一对应）✓")
    print("(m) 浮层里没有「直选 / Enter 确认」提示行（只剩 6 个编号选项）✓")
    gui._popup_move(1)
    sel = gui.popup_lb.curselection()[0]
    want = STATES[sel]
    gui._popup_confirm()
    assert gui.popup is None, "确认后浮层应关闭"
    got = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row["场次"], row["题号"]))
    assert got["状态"] == want, (got["状态"], want)
    assert got["日期"] == datetime.date.today().isoformat(), got["日期"]
    print("回车确认后：%s ｜ %s → %s，日期 %s（写入 fixture）✓"
          % (got["题号"], row["状态"], got["状态"], got["日期"]))

    gui.open_status_popup(next(r for r in gui.rows if r["题号"] == row["题号"]), gui.tree)
    assert gui.popup_lb.curselection()[0] == STATES.index(want), "浮层应把当前状态选上"
    before_idx = gui._index_of(gui.tree)
    gui._popup_cancel()
    assert gui.popup is None, "Esc 取消后浮层应关闭"
    assert gui._index_of(gui.tree) == before_idx, "Esc 取消不该动选中行"
    print("Esc 取消：浮层关闭、文件未改、选中行没动 ✓")

    # --- v4 闸门 (d)：改完状态选中行自动下移一行（最后一行则不动）+ 闸门 (f) 保存提示 3 秒清空
    gui.nb.select(0)
    gui.sort_col, gui.sort_desc = "场次", False
    gui.var_search.set("")
    gui.refresh_view()
    ids = list(gui.tree.get_children())
    at = 3                                          # 取中间一行，上下都有人
    gui.tree.selection_set(ids[at])
    gui.tree.focus(ids[at])
    up_row, down_row = gui.row_by_iid(ids[at]), gui.row_by_iid(ids[at + 1])
    gui.open_status_popup(up_row, gui.tree)
    gui.popup_lb.selection_clear(0, "end")
    gui.popup_lb.selection_set(0)                   # 选个和原状态不同的，确保真写盘
    assert STATES[0] != up_row["状态"], "这条要换个状态才有意义"
    gui._popup_confirm()
    assert gui._index_of(gui.tree) == at + 1, \
        "改完状态应自动下移一行：第 %s 行 → 第 %s 行" % (at, gui._index_of(gui.tree))
    now = gui.row_by_iid(gui.tree.focus())
    assert (now["场次"], now["题号"]) == (down_row["场次"], down_row["题号"]), \
        "下移后应停在原来它下面那一行（%s）" % down_row["题号"]
    print("(d) 改完状态下移一行：第 %d 行改完 → 选中第 %d 行（%s → %s）✓"
          % (at, gui._index_of(gui.tree), up_row["题号"], now["题号"]))

    # --- v4 闸门 (f) + v9 闸门 (ll)：保存消息 = 短文案（无备份名 / 日期），3 秒后自动清空
    want_msg = "已保存：%s %s → %s" % (up_row["场次"], up_row["题号"], STATES[0])
    assert gui.var_msg.get() == want_msg, gui.var_msg.get()
    assert ".bak" not in gui.var_msg.get() \
        and datetime.date.today().isoformat() not in gui.var_msg.get(), \
        "消息里不该出现备份文件名 / 日期：%r" % gui.var_msg.get()
    assert TOAST_MS == 3000, TOAST_MS
    assert gui._msg_after is not None, "保存后应注册「3 秒后清空」的 after 回调"
    assert root.tk.call("after", "info", gui._msg_after), "回调要真的挂在 Tk 的 after 表里"
    gui._clear_msg()                                # 等价于 3 秒到点
    assert gui.var_msg.get() == "" and gui._msg_after is None, gui.var_msg.get()
    print("(ll) 消息：改状态后 = %r（无 .bak / 日期）；(f) 3 秒后自动清空（after 回调已注册 %d ms）✓"
          % (want_msg, TOAST_MS))

    ids = list(gui.tree.get_children())
    last = len(ids) - 1
    gui.tree.selection_set(ids[last])
    gui.tree.focus(ids[last])
    last_row = gui.row_by_iid(ids[last])
    gui.open_status_popup(last_row, gui.tree)
    pick = 0 if STATES.index(last_row["状态"]) != 0 else 1
    gui.popup_lb.selection_clear(0, "end")
    gui.popup_lb.selection_set(pick)
    gui._popup_confirm()
    assert gui._index_of(gui.tree) == last, "最后一行改完应留在最后一行不动"
    print("(d) 最后一行改完仍停在最后一行（不动）✓")

    # 看板页同样：段落里改状态也下移一行（v10：段里只剩「不会」这一种状态，就重选「不会」——
    # 只有日期变（仍是真写盘），行不会被踢出这一段，下移才测得出）
    gui.nb.select(1)
    gui.show_segment(1)
    cap = segment_specs()[1][0]
    tr_ids = list(gui.today_tree.get_children())
    assert len(tr_ids) >= 2, "「待补题」段至少要有两行才测得出下移"
    gui.today_tree.selection_set(tr_ids[0])
    gui.today_tree.focus(tr_ids[0])
    r0 = gui.row_by_iid(tr_ids[0])
    gui.open_status_popup(r0, gui.today_tree)
    assert r0["状态"] == "不会", "第 2 段里只该有「不会」：%r" % (r0["状态"],)
    pick = STATES.index("不会")                      # 重选同一个状态：只改日期，仍留在本段
    gui.popup_lb.selection_clear(0, "end")
    gui.popup_lb.selection_set(pick)
    gui._popup_confirm()
    assert gui._index_of(gui.today_tree) == 1, \
        "看板页改完也应下移一行：第 %s 行" % (gui._index_of(gui.today_tree),)
    print("(d) 看板页同样下移一行：%s 段第 0 行改完 → 选中第 1 行 ✓" % cap)
    gui.nb.select(0)

    # --- v3 闸门 (e)：浮层里按数字键 = 直接选中对应状态并写入（v10：按状态名取序号）
    iid = gui.tree.get_children()[1]
    gui.tree.selection_set(iid)
    gui.tree.focus(iid)
    row4 = gui.row_by_iid(iid)
    want4 = "复现AC"                                  # v10：按状态名取，不依赖顺序下标
    key4 = STATES.index(want4) + 1
    assert row4["状态"] != want4, "这条要换个状态才有意义：%r" % (row4["状态"],)
    gui.open_status_popup(row4, gui.tree)
    assert gui.popup is not None, "浮层没弹出来"
    root.update()                                     # 等浮层真画出来，按键才送得到
    assert gui.popup_lb.winfo_viewable(), "浮层应已可见"
    gui.popup_lb.event_generate("<KeyPress>", keysym=str(key4))
    root.update()
    assert gui.popup is None, "数字直选后浮层应关闭"
    got = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row4["场次"], row4["题号"]))
    assert got["状态"] == want4, (got["状态"], want4)
    assert got["日期"] == datetime.date.today().isoformat(), got["日期"]
    print("(e) 浮层里按 %d → 直接写入「%s」+ 日期今天 ✓" % (key4, want4))

    # --- v3 闸门 (f)：页签选中只换色、不改尺寸
    # 注：ttk.Notebook.bbox 在某些 Tk 版本恒返回 (0,0,0,0)（实测），所以用两条真能照出问题的量：
    #   ① 决定标签尺寸的样式项 padding / font 在「选中 / 未选中」两态必须相同
    #      —— clam 默认 padding 是「选中 6 4 6 2 / 未选中 6 2 6 2」，选中时会高 2px（v2 就是这个）
    #   ② 页面 reqwidth 前后一致（派发里点名的口径）
    st = ttk.Style(root)
    probe_root = tk.Tk()                          # 独立解释器：干净 clam，没被本程序的 map 影响
    probe_root.withdraw()
    st_probe = ttk.Style(probe_root)
    st_probe.theme_use("clam")
    probe_sel = st_probe.lookup("TNotebook.Tab", "padding", ("selected",))
    probe_un = st_probe.lookup("TNotebook.Tab", "padding", ("!selected",))
    probe_root.destroy()
    assert probe_sel != probe_un, \
        "探针失效：clam 默认本应让选中的页签更大，照不出来这条检查就没意义（两态都是 %s）" % (probe_sel,)
    for opt in ("padding", "font"):
        a = st.lookup("TNotebook.Tab", opt, ("selected",))
        b = st.lookup("TNotebook.Tab", opt, ("!selected",))
        assert a == b, ("选中页签的 %s 变了" % opt, a, b)
    tabs = gui.nb.tabs()
    gui.nb.select(tabs[0])
    root.update()
    w0 = [root.nametowidget(t).winfo_reqwidth() for t in tabs]
    gui.nb.select(tabs[1])
    root.update()
    w1 = [root.nametowidget(t).winfo_reqwidth() for t in tabs]
    assert w0 == w1, (w0, w1)
    print("(f) 页签选中不改尺寸：padding/font 两态一致（clam 默认两态差 %r，已被压平）；"
          "页面 reqwidth %s ✓" % (probe_sel, w0))

    # --- v3：? 弹快捷键一览（内容 = 键位表原文），Esc 关闭
    gui.nb.select(0)
    gui.tree.focus_force()          # 合成按键前必须 focus_force：窗口没拿到 OS 焦点时
    root.update()                   # focus_set 是空操作，event_generate 送不到（v10 老坑）
    gui.tree.event_generate("<KeyPress>", keysym="question")
    root.update()
    assert gui.help_win is not None, "? 应弹出快捷键一览"
    assert gui.help_lbl.cget("text") == KEY_TABLE, "一览内容应与键位表一字不差"
    ks = KEY_TABLE.splitlines()
    assert not any(re.match(r"^F(\s|/|$)", ln) for ln in ks), \
        "键位表里还有裸 F 那行（v9 删过；F5 / F11 不算）：%r" % ks
    assert any(ln.startswith("F11") and "全屏" in ln for ln in ks), \
        "键位表里该有 F11 全屏那行（v11）：%r" % ks
    assert any(ln.startswith("1 ~ 6") and "直接改状态" in ln for ln in ks), \
        "键位表里该有 1~6 直接改状态那行（v12）：%r" % ks
    assert any(ln.startswith("Shift+Enter") and "原题" in ln for ln in ks), \
        "键位表里该有 Shift+Enter 打开原题那行（v12）：%r" % ks
    assert any(ln.startswith("Ctrl+Z") and "可连撤" in ln for ln in ks), \
        "键位表里 Ctrl+Z 那行该写出「可连撤」（v12）：%r" % ks
    # v14：搜索框下多了筛选下拉面板（用户点名就叫「下拉」）——键位表里禁的是 v9 删掉的
    # 那种只读「下拉框」控件字样（窗口里 0 个 TCombobox，见 (ii)）；v14 新行必须有。
    assert "下拉框" not in KEY_TABLE, "键位表里还有「下拉框」控件字样（v9 删的不是这个）"
    assert any(ln.startswith("下拉面板") and "只筛总表" in ln for ln in ks), \
        "键位表里该有下拉面板那行（v14）：%r" % ks
    assert any(ln.startswith("面板里 ↓ / ↑") and "勾选" in ln for ln in ks), \
        "键位表里该有面板内行走那行（v14）：%r" % ks
    assert any(ln.startswith("Tab / Shift+Tab") and "主页面" in ln and "搜索" in ln for ln in ks), \
        "键位表里 Tab 那行该写出两站（v14）：%r" % ks
    print("? 快捷键一览：%d 行键位表原文；Esc 关闭" % len(ks))
    gui.help_win.event_generate("<Escape>")
    root.update()
    assert gui.help_win is None, "Esc 应关掉一览"
    assert root.focus_get() is gui.tree, "关掉一览后焦点应回到表格"
    print("(kk) 一览与 KEY_TABLE 一字不差：%d 行、无裸 F 行（F5 / F11 不算）、"
          "有 F11 全屏行、有下拉面板两行（v14）、无「下拉框」控件字样 ✓" % len(ks))
    print("Esc 关闭一览、焦点回表格 ✓")

    # --- v4 闸门 (c)：搜索**跟题**（选中的题还在结果里 → 仍选它；被搜掉 → 回第一行）（v9：筛选半边删除）
    gui.sort_col, gui.sort_desc = "场次", False
    gui.var_search.set("")
    gui.refresh_view()
    hits = [x for x in gui.tree.get_children()
            if "双指针" in gui.row_by_iid(x)["知识点"]
            or "双指针" in gui.row_by_iid(x)["题名"]]
    assert len(hits) >= 2, "fixture 里「双指针」应至少命中两行，这条才测得动"
    gui.tree.selection_set(hits[1])               # 挑第 2 条命中：保得住才算真跟题
    gui.tree.focus(hits[1])
    srow = gui.row_by_iid(hits[1])
    gui.var_search.set("双指针")
    gui.refresh_view()
    got = gui.row_by_iid(gui.tree.focus())
    assert got is not None and (got["场次"], got["题号"]) == (srow["场次"], srow["题号"]), \
        "搜索后选中的题还在结果里，就该继续选它（现在是 %s）" % (got and got["题号"],)
    assert gui._index_of(gui.tree) == 1, "它应落在结果第 1 行（真跟题，不是被贴回第 0 行）"
    print("(c) 搜索跟题：搜「双指针」后仍选中原来那条（第 1 行）✓")

    gui.var_search.set("")
    gui.refresh_view()
    other_iid = next(x for x in gui.tree.get_children()
                     if "双指针" not in gui.row_by_iid(x)["知识点"]
                     and "双指针" not in gui.row_by_iid(x)["题名"])
    gui.tree.selection_set(other_iid)             # 先选一道搜「双指针」搜不到的题
    gui.tree.focus(other_iid)
    gui.tree.see(other_iid)
    gui.var_search.set("双指针")
    gui.refresh_view()
    assert gui.tree.focus() == gui.tree.get_children()[0], \
        "原来选中的题被搜掉后，选中应贴回第一行（focus 也在第一行）"
    print("(c) 搜索搜掉选中行：「双指针」结果里没有它 → 贴回第一行（focus 也在第一行）✓")
    gui.var_search.set("")
    gui.refresh_view()

    # --- v5 闸门 (i)：搜索框里 Enter 跳回总表（搜索词保留、结果不丢、选中跟题；v14 起 ↓ 改作展开下拉）
    gui.var_search.set("")
    gui.refresh_view()
    hits = [x for x in gui.tree.get_children()
            if "双指针" in gui.row_by_iid(x)["知识点"]
            or "双指针" in gui.row_by_iid(x)["题名"]]
    assert len(hits) >= 2, "fixture 里「双指针」应至少命中两行，这条才测得动"
    gui.tree.selection_set(hits[1])
    gui.tree.focus(hits[1])
    srow = gui.row_by_iid(hits[1])
    gui.var_search.set("双指针")
    gui.refresh_view()
    want_rows = len(gui.tree.get_children())
    gui.ent_search.focus_set()
    root.update()
    assert root.focus_get() is gui.ent_search, root.focus_get()
    gui.ent_search.event_generate("<KeyPress>", keysym="Return")
    root.update()
    assert root.focus_get() is gui.tree, root.focus_get()
    assert gui.var_search.get() == "双指针", "Enter 跳转不该动搜索词"
    assert len(gui.tree.get_children()) == want_rows, "Enter 跳转不该改搜索出的结果"
    got = gui.row_by_iid(gui.tree.focus())
    assert got is not None and (got["场次"], got["题号"]) == (srow["场次"], srow["题号"]), \
        "跳回总表后该保住的还是原来那道题（现在是 %s）" % (got and got["题号"],)
    gui.ent_search.focus_set()
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="Down")   # v14：↓ = 展开筛选下拉（不再跳转）
    root.update()
    assert gui.dlg_open and root.focus_get() is gui.ent_search, \
        "v14 起搜索框 ↓ = 展开下拉（焦点留在搜索框、能接着打字）"
    gui._dropdown_hide()
    root.update()
    assert not gui.dlg_open
    gui.nb.select(1)                                             # 看板页上跳转也先切回总表
    gui._jump_to_table()
    assert gui.nb.index(gui.nb.select()) == 0, "看板页上跳转要先切回总表页"
    print("(i) 搜索框里 Enter 跳回总表：焦点在表格、搜索词没清、结果仍是搜出来的、"
          "选中跟题（看板页上先切回总表）；v14：↓ 改作展开筛选下拉 ✓")
    gui.var_search.set("")
    gui.refresh_view()

    # --- v5 闸门 (j) 已随「状态筛选」整块删除（没有筛选下拉了，Enter 跳转只剩搜索框那一半，
    #     由上面的 (i) 覆盖）。

    # 搜索打「知识点」与空结果：v9 起搜不到就是空表（不再有「无匹配」占位行）
    gui.var_search.set("双指针")
    gui.refresh_view()
    want = len([r for r in gui.rows if "双指针" in r["知识点"] or "双指针" in r["题名"]])
    assert len(gui.tree.get_children()) == want, (want, gui.tree.get_children())
    print("搜索「双指针」（打 知识点）= %d 行 ✓" % want)
    gui.var_search.set("zzz-没有这个")
    gui.refresh_view()
    assert gui.tree.get_children() == (), "搜不到就是空表：%r" % (gui.tree.get_children(),)
    assert gui.tree.selection() == (), "空表不该有选中行"
    assert "搜出" not in gui.var_count.get(), gui.var_count.get()   # v10：前缀整段删掉
    assert gui.var_count.get().startswith("共 %d 题" % len(gui.rows)), gui.var_count.get()
    # 空表上 ↑↓ / Enter 不许抛异常：回调里的异常 Tk 会吞，挂钩子先把它接住
    errs = []
    keep_hook = root.report_callback_exception
    root.report_callback_exception = lambda *a: errs.append(a)
    try:
        gui.tree.focus_set()
        root.update()
        for ksym in ("Up", "Down", "Return"):
            gui.tree.event_generate("<KeyPress>", keysym=ksym)
            root.update()
        assert errs == [], "空表上按 ↑↓ / Enter 抛异常了：%r" % (errs,)
    finally:
        root.report_callback_exception = keep_hook
    gui._move_sel(gui.tree, "up")                 # 直接调（同步抛就是这条挂）
    gui._move_sel(gui.tree, "down")
    ev0 = _Ev()
    ev0.widget = gui.tree
    gui._on_open_key(ev0)
    assert gui.popup is None, "空表上回车不该弹浮层"
    print("(nn) 搜索搜不到：总表就是空的（无「无匹配」占位行、无选中行），"
          "空表上 ↑↓ / Enter 不抛异常、回车不弹窗 ✓")
    gui.var_search.set("")
    gui.refresh_view()

    empty = os.path.join(tmpdir, "empty.md")
    write_text(empty, "\n".join(["# 空表 fixture（只有 未做）", "",
                                 "| " + " | ".join(HEADER) + " |",
                                 "|" + "|".join(["---"] * len(HEADER)) + "|",
                                 render_row(["牛客周赛 Round 1", "A", "占位题", "模拟",
                                             "CF 800", "未做", ""]),
                                 ""]) + "\n")
    gui.path = empty
    gui.reload()
    errs2 = []
    keep_hook2 = root.report_callback_exception
    root.report_callback_exception = lambda *a: errs2.append(a)
    try:
        for i in range(4):
            gui.show_segment(i)
            assert gui.today_tree.get_children() == (), gui.today_tree.get_children()
            for ksym in ("Up", "Down", "Return"):
                gui.today_tree.event_generate("<KeyPress>", keysym=ksym)
                root.update()
        assert errs2 == [], "空段清单上按 ↑↓ / Enter 抛异常了：%r" % (errs2,)
    finally:
        root.report_callback_exception = keep_hook2
    gui.show_segment(0)
    gui._move_sel(gui.today_tree, "up")
    gui._move_sel(gui.today_tree, "down")
    ev1 = _Ev()
    ev1.widget = gui.today_tree
    gui._on_open_key(ev1)
    assert gui.popup is None, "空段清单上回车不该弹浮层"
    print("(nn) 四段全空时清单就是空的（无「无」占位行、每段都没有选中行），"
          "空清单上 ↑↓ / Enter 不抛异常 ✓（未做不进看板）")
    gui.path = tmp
    gui.reload()
    assert gui.tree_row(gui.tree) is not None
    print("重读后总表行数：", len(gui.tree.get_children()))

    # --- v9 闸门 (mm)：计数口径 —— 「7天内做对：N 题」只数 独立AC / 复现AC 且日期在 7 天内
    mm = os.path.join(tmpdir, "count7.md")
    t0 = datetime.date.today()
    mm_rows = [("牛客周赛 Round 301", "A", "计数今天", "模拟", "CF 800", "独立AC",
                t0.isoformat()),
               ("牛客周赛 Round 301", "B", "计数三天前", "模拟", "CF 800", "复现AC",
                (t0 - datetime.timedelta(days=3)).isoformat()),
               ("牛客周赛 Round 301", "C", "计数昨天巩固", "模拟", "CF 800", "巩固",
                (t0 - datetime.timedelta(days=1)).isoformat()),
               ("牛客周赛 Round 301", "D", "计数十天前", "模拟", "CF 800", "独立AC",
                (t0 - datetime.timedelta(days=10)).isoformat())]
    write_text(mm, "\n".join(["# 计数口径 fixture（四行：今天 / 3 天前 / 昨天 / 10 天前）", "",
                              "| " + " | ".join(HEADER) + " |",
                              "|" + "|".join(["---"] * len(HEADER)) + "|"]
                             + [render_row(list(c)) for c in mm_rows] + [""]) + "\n")
    gui.path = mm
    gui.var_search.set("")
    gui.reload()
    line_mm = gui.var_count.get()
    assert line_mm.endswith("7天内做对：2 题"), line_mm
    assert line_mm.startswith("共 4 题"), line_mm      # 全量那半段仍是 6 个状态全列
    print("(mm) 计数口径：独立AC 今天 / 复现AC 3 天前 / 巩固 昨天 / 独立AC 10 天前 → "
          "计数行以「7天内做对：2 题」结尾（巩固与超期都不算）✓")
    gui.path = tmp
    gui.reload()

    # --- v6 追加 (v)：Alt+Enter 打开这题的资料（算法库记录 → 场题解 → 都没有提示；绝不真开文件）
    assert gui.tree.bind("<Alt-Return>") != "" and gui.today_tree.bind("<Alt-Return>") != "", \
        "Alt+Enter 要挂在两棵树上（只挂 root 会被树自己的回车吃掉 —— 实测）"
    sand = os.path.join(tmpdir, "资料沙箱")
    rec188 = os.path.join(sand, "算法", "树链剖分", "牛客周赛Round188-D-树上路径.md")
    sol188 = os.path.join(sand, "题解", "牛客周赛", "Round188", "Round188题解.md")
    sol199 = os.path.join(sand, "题解", "牛客周赛", "Round199", "Round199题解.md")
    rec208 = os.path.join(sand, "算法", "动态规划", "牛客周赛Round208-E-期望DP.md")
    for p in (rec188, sol188, sol199, rec208):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        write_text(p, "# 占位（冒烟只关心路径）\n")
    opened = []
    gui.data_root = sand                        # 查找根换到沙箱（测试绝不碰真数据根）
    gui._opener = opened.append                 # 假打开器：只记调用，不真开文件
    spawn = {"n": 0}
    real_sf = getattr(os, "startfile", None)

    def _spy_startfile(path, _c=spawn):
        _c["n"] += 1                            # 万一哪条路绕过注入直接调 os.startfile，就在这儿现形

    if real_sf is not None:
        os.startfile = _spy_startfile

    def _pick_row(tree, round_txt, letter):
        for iid in tree.get_children():
            r = gui.row_by_iid(iid)
            if r and r["场次"] == round_txt and r["题号"] == letter:
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)
                return r
        raise AssertionError("fixture 里没有 %s %s" % (round_txt, letter))

    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    gui.tree.focus_force()          # 合成按键前一律 focus_force（见 (jj) 注释）
    root.update()
    _pick_row(gui.tree, "牛客周赛 Round 188", "D")
    gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x20000)    # = Alt+Enter（实测这个 state 口径能命中）
    root.update()
    assert gui.popup is None, "Alt+Enter 不该弹状态浮层（树自己的回车别抢）"
    assert len(opened) == 1 and os.path.normpath(opened[-1]) == os.path.normpath(rec188), \
        "有记录时该开算法库记录（同轮还有场题解也先走记录）：%r" % (opened,)
    _pick_row(gui.tree, "牛客周赛 Round 199", "C")
    gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x20000)
    root.update()
    assert len(opened) == 2 and os.path.normpath(opened[-1]) == os.path.normpath(sol199), \
        "没有记录、只有场题解时该开 Round199题解.md：%r" % (opened,)
    n_open = len(opened)
    _pick_row(gui.tree, "牛客周赛 Round 210", "E")
    gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x20000)
    root.update()
    assert len(opened) == n_open, "「都没有」时不该调 opener"
    assert gui.var_msg.get() == "打不开：没找到这题的资料", gui.var_msg.get()
    assert gui._msg_after is not None, "「打不开」提示也要走 3 秒消失那套"
    # 看板页同样生效（待补题段里的 Round 208 E 有记录）
    gui.nb.select(1)
    gui.show_segment(1)
    root.update()
    _pick_row(gui.today_tree, "牛客周赛 Round 208", "E")
    gui.today_tree.focus_force()
    root.update()
    gui.today_tree.event_generate("<KeyPress>", keysym="Return", state=0x20000)
    root.update()
    assert len(opened) == n_open + 1 and os.path.normpath(opened[-1]) == os.path.normpath(rec208), \
        "看板页 Alt+Enter 同样能开资料：%r" % (opened,)
    assert gui.popup is None, "看板页 Alt+Enter 也不该弹浮层"
    # 场次不是「牛客周赛 Round N」形式 → 「打不开：这场还没接」
    gui.nb.select(0)
    row_o = _pick_row(gui.tree, "牛客周赛 Round 200", "A")
    saved_round = row_o["场次"]
    row_o["场次"] = "洛谷月赛 Round 5"
    gui.tree.focus_force()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x20000)
    root.update()
    row_o["场次"] = saved_round
    assert len(opened) == n_open + 1 and gui.var_msg.get() == "打不开：这场还没接", gui.var_msg.get()
    if real_sf is not None:
        os.startfile = real_sf
    assert spawn["n"] == 0, "测试里真调了 os.startfile %d 次（注入没兜住）" % spawn["n"]
    print("(v) Alt+Enter 打开资料：记录优先（188D）→ 只有场题解走题解（199C）→ 都没有 / "
          "这场还没接 都给提示；看板页同样生效；全程没碰真 os.startfile ✓")

    # --- v6 追加 (w)：Ctrl+Z 撤销上一步改动（只一步；逐字节还原 + 撤销也走备份）
    assert root.bind("<Control-z>") != "", "root 上要挂 Ctrl+Z"
    # v12：撤销栈改多步 —— 这一段（和 (y)）测的是「从栈空开始撤一步」的老口径：
    # 先把前面测试攒下的栈清掉（口径没放松：改一步 → 撤一步 → 撤完再看「只一步」的读法）。
    gui._undo_stack.clear()
    gui._last_change = None
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    ids = list(gui.tree.get_children())
    gui.tree.selection_set(ids[2])
    gui.tree.focus(ids[2])
    r_u = gui.row_by_iid(ids[2])
    old_state, old_date = r_u["状态"], r_u["日期"]
    new_state = next(s for s in STATES if s != old_state)
    bak_dir = _mirror_dir(TEST_BACKUP_ROOT)
    n_bak = _count_bak(bak_dir)
    bytes0 = open(tmp, "rb").read()
    gui.set_status(r_u, new_state, gui.tree)          # = 浮层里选新状态并确认（走正常写回）
    assert open(tmp, "rb").read() != bytes0 and _count_bak(bak_dir) == n_bak + 1
    assert gui._last_change is not None and gui._last_change["round"] == r_u["场次"] \
        and gui._last_change["letter"] == r_u["题号"], gui._last_change
    assert (gui._last_change["old_status"], gui._last_change["old_date"]) == (old_state, old_date)
    assert (gui._last_change["new_status"], gui._last_change["new_date"]) == \
        (new_state, datetime.date.today().isoformat())
    gui.tree.focus_force()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="z", state=0x4)             # = Ctrl+Z
    root.update()
    assert open(tmp, "rb").read() == bytes0, "撤销后文件该与改前逐字节相同"
    assert _count_bak(bak_dir) == n_bak + 2, "撤销自己也要走备份"
    assert gui._last_change is None, "撤销后记录清空（只记一步）"
    got = gui.tree_row(gui.tree)
    assert got is not None and (got["场次"], got["题号"]) == (r_u["场次"], r_u["题号"]), \
        "撤销后选中行要回到那题（现在是 %r）" % (got and got["题号"],)
    assert gui.var_msg.get() == "已撤销：%s %s → %s" % (r_u["场次"], r_u["题号"], old_state), \
        gui.var_msg.get()
    assert gui._msg_after is not None, "撤销提示也要 3 秒消失那套"
    # 再按一次：没有可撤的 —— 只提示，文件一个字不动（这次从搜索框里按 = 任何焦点下都生效）
    gui.ent_search.focus_force()
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="z", state=0x4)
    root.update()
    assert gui.var_msg.get() == "没有可撤销的改动", gui.var_msg.get()
    assert open(tmp, "rb").read() == bytes0, "没有可撤时文件不许动"
    print("(w) Ctrl+Z 撤销一步：改状态 → 撤销后逐字节还原、选中回那题、撤销也走备份；"
          "再按给「没有可撤销的改动」；搜索框里按也生效 ✓")

    # --- v6.1 追加 (y)：空日期行的「改完 → Ctrl+Z」整份逐字节还原（含空日期格的两空格形态）
    #     （派发里叫「(v)」，但 (v) 已是 Alt+Enter 的号 —— 旧断言号一律不重排，新号顺取 y）
    gui._undo_stack.clear()                # v12：同上，从栈空开始才测得出「撤一步」
    gui._last_change = None
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    iid_y = next((x for x in gui.tree.get_children()
                  if gui.row_by_iid(x)["日期"] == ""), None)
    assert iid_y is not None, "这条要一行日期为空的数据（前面几条断言别把它写没了）"
    gui.tree.selection_set(iid_y)
    gui.tree.focus(iid_y)
    gui.tree.see(iid_y)
    r_y = gui.row_by_iid(iid_y)
    assert r_y["日期"] == "", "挑中的这行日期要是空的：%r" % (r_y,)
    new_y = "待重写" if r_y["状态"] != "待重写" else "复现AC"   # v10：只许用 6 个合法状态
    bytes_y0 = open(tmp, "rb").read()
    gui.set_status(r_y, new_y, gui.tree)              # = 浮层里选新状态并确认（走正常写回）
    mid_y = open(tmp, "rb").read()
    assert mid_y != bytes_y0, "改完文件应变了（%s %s → %s）" % (r_y["场次"], r_y["题号"], new_y)
    gui._undo()                                       # = Ctrl+Z
    back_y = open(tmp, "rb").read()
    assert len(back_y) == len(bytes_y0), (len(bytes_y0), len(back_y))
    assert back_y == bytes_y0, "空日期行撤销后该与改前逐字节相同（空日期格恢复两空格形态）"
    assert gui._last_change is None, "撤销后记录清空（只记一步）"
    gui._undo()                                       # 再按一次：没有可撤的
    assert gui.var_msg.get() == "没有可撤销的改动", gui.var_msg.get()
    assert open(tmp, "rb").read() == bytes_y0, "没有可撤时文件一个字不动"
    print("(y) 空日期行 Ctrl+Z：改状态（%d → %d 字节）→ 撤销后整份逐字节还原（含空日期格的"
          "两空格形态，长度 %d = %d）；再按一次文件仍逐字节不变 ✓"
          % (len(bytes_y0), len(mid_y), len(bytes_y0), len(back_y)))

    # ---- (x) 场次排序走 toolutil.parse_contest：不同比赛各归各组、不互相插队（v6 追加 6）----
    assert getattr(toolutil, "parse_contest", None) is not None, "toolutil 里应有 parse_contest（场次新键）"
    x_rows = [
        {"场次": "牛客周赛 Round 161", "题号": "D", "_i": 0},
        {"场次": "Codeforces Round 161", "题号": "B", "_i": 1},
        {"场次": "洛谷月赛 Round 5", "题号": "A", "_i": 2},          # 认不出：该排最后
        {"场次": "牛客周赛 Round 161", "题号": "A", "_i": 3},
        {"场次": "Codeforces Round 161", "题号": "A", "_i": 4},
        {"场次": "牛客周赛 Round 99", "题号": "F", "_i": 5},
    ]
    x_seq = [(contest_key(r["场次"]), r["题号"]) for r in sort_rows(x_rows, "场次", False)]
    x_exp = [(("Codeforces", 161), "A"), (("Codeforces", 161), "B"),
             (("牛客周赛", 99), "F"), (("牛客周赛", 161), "A"), (("牛客周赛", 161), "D"),
             ((None, None), "A")]
    assert x_seq == x_exp, "场次排序应比赛名分组（组内按号、题号；认不出的排最后）：%r" % (x_seq,)
    print("(x) 场次排序走 toolutil.parse_contest：牛客 / Codeforces 各自成组不插队、组内按 "
          "Round 号、认不出的（洛谷月赛）排最后 ✓")

    # --- v10 闸门 (oo)：搜索规则 = 忽略空格 + 多词都要命中（场次 + 题名 + 知识点 + 难度，
    #     大小写不敏感；v12 起拼串加难度）
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()

    def _search_rows(q):
        gui.var_search.set(q)
        gui.refresh_view()
        return [gui.row_by_iid(x) for x in gui.tree.get_children()]

    def _keys(rs):
        return set((r["场次"], r["题号"]) for r in rs)

    all_rows = _search_rows("")                        # 空查询 = 全量
    hit_wc = _search_rows("牛客周赛")
    hit_round = _search_rows("Round")
    hit_nospace = _search_rows("牛客周赛Round")
    hit_space = _search_rows("牛客周赛 Round")
    hit_fullspace = _search_rows("牛客周赛　Round")   # 全角空格也算分隔
    hit_zzz = _search_rows("zzz")
    assert hit_wc and hit_round, \
        "「牛客周赛」「Round」都该有命中：%d / %d" % (len(hit_wc), len(hit_round))
    assert _keys(hit_nospace) == _keys(hit_space) and hit_nospace, \
        "「牛客周赛Round」与「牛客周赛 Round」命中集合要完全相同且非空"
    assert _keys(hit_fullspace) == _keys(hit_space), "全角空格也该算分隔"
    assert _keys(hit_nospace) == _keys(hit_wc) == _keys(hit_round) == _keys(all_rows), \
        "本 fixture 每行场次都有「牛客周赛 Round」：几种查询都该命中全部 %d 行" % len(all_rows)
    hit_cross = _search_rows("牛客 构造")              # 跨列：场次含「牛客」+ 题名/知识点含「构造」
    assert _keys(hit_cross) == set([("牛客周赛 Round 201", "F")]), _keys(hit_cross)
    hit_r199 = _search_rows("Round199")                # 数字也要粘得住
    hit_r199s = _search_rows("Round 199")
    assert _keys(hit_r199) == _keys(hit_r199s) and len(hit_r199) == 1, _keys(hit_r199)
    assert hit_zzz == [], "搜不到的词就该是空表（v9 行为不变）：%r" % (hit_zzz,)
    gui.var_search.set("")
    gui.refresh_view()
    print("(oo) 搜索：忽略空格 + 多词都要命中 —— 「牛客周赛Round」≡「牛客周赛 Round」≡全角空格版，"
          "三种查询都命中全部 %d 行；跨列「牛客 构造」只中 Round201F；「Round199」≡「Round 199」"
          "（1 行）；「zzz」= 空表 ✓" % len(all_rows))

    # --- v10 闸门 (pp)：计数行不再带「搜出 M 题 ｜」前缀，搜不搜都是同一行
    gui.var_search.set("")
    gui.refresh_view()
    line_all = gui.var_count.get()
    gui.var_search.set("Round 199")
    gui.refresh_view()
    line_one = gui.var_count.get()
    assert "搜出" not in line_all and "搜出" not in line_one, (line_all, line_one)
    assert line_one == line_all, "计数行固定按全量算，搜索时也不许变：%r → %r" % (line_all, line_one)
    assert line_all.startswith("共 %d 题" % len(gui.rows)), line_all
    assert line_all.count(" ｜ ") == len(STATES) + 1 \
        and line_all.endswith("%d天内做对：%d 题" % (SR.RECENT_DAYS, done_count(gui.rows))), line_all
    gui.var_search.set("")
    gui.refresh_view()
    print("(pp) 计数行没有「搜出 M 题」：搜前搜后一字不差 = %r（共 X 题 ｜ 6 个状态 ｜ N天内做对）✓"
          % line_all)

    # --- v10 闸门 (qq)：状态恰 6 个（卡住 / 只读过 已删）；浮层 6 项、数字键 1~6 好使、7/8 无效
    assert len(STATES) == 6, STATES
    assert STATES == ["未做", "不会", "待重写", "复现AC", "独立AC", "巩固"], STATES
    assert "卡住" not in STATES and "只读过" not in STATES, STATES
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    qq_iid = next(x for x in gui.tree.get_children() if gui.row_by_iid(x)["状态"] != "巩固")
    gui.tree.selection_set(qq_iid)
    gui.tree.focus(qq_iid)
    qq_row = gui.row_by_iid(qq_iid)
    gui.open_status_popup(qq_row, gui.tree)
    root.update()
    assert gui.popup_lb.size() == 6, gui.popup_lb.size()
    texts6 = [gui.popup_lb.get(i) for i in range(6)]
    assert texts6 == ["1. 未做", "2. 不会", "3. 待重写", "4. 复现AC", "5. 独立AC", "6. 巩固"], texts6
    for k in range(1, 7):
        assert gui.popup_lb.bind("<Key-%d>" % k) != "" and gui.popup_lb.bind("<KP_%d>" % k) != "", \
            "数字键 %d 该绑着直选" % k
    for k in (7, 8):
        assert gui.popup_lb.bind("<Key-%d>" % k) == "", "数字键 %d 不该再绑（状态只有 6 个）" % k
    bytes_q0 = open(tmp, "rb").read()
    n_q0 = _count_bak(_mirror_dir(TEST_BACKUP_ROOT))
    gui.popup_lb.event_generate("<KeyPress>", keysym="7")      # 负向：7 / 8 按了什么都不许发生
    root.update()
    assert gui.popup is not None, "按 7 不该写盘（浮层还该开着）"
    gui.popup_lb.event_generate("<KeyPress>", keysym="8")
    root.update()
    assert gui.popup is not None, "按 8 不该写盘（浮层还该开着）"
    assert open(tmp, "rb").read() == bytes_q0 \
        and _count_bak(_mirror_dir(TEST_BACKUP_ROOT)) == n_q0, "按 7 / 8 不许改文件、不许产生备份"
    gui.popup_lb.event_generate("<KeyPress>", keysym="6")
    root.update()
    assert gui.popup is None, "按 6 该写「巩固」并关掉浮层"
    got = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (qq_row["场次"], qq_row["题号"]))
    assert got["状态"] == "巩固", (got["状态"],)
    print("(qq) 状态恰 6 个（卡住 / 只读过 不在）；浮层 %r；键 1~6 已绑、7/8 未绑且按了不改任何东西；"
          "按 6 直接写入「巩固」✓" % (texts6,))

    # --- v10 闸门 (rr)：看板四段各自记住上次选中的行（左右切段回来不重置）
    assert gui.today_tree.bind("<<TreeviewSelect>>") != "", "要挂 <<TreeviewSelect>> 统一记录选中"
    seg_mem = os.path.join(tmpdir, "seg_mem.md")
    sm_rows = [("牛客周赛 Round 501", "A", "重写一", "模拟", "CF 800", "待重写", "2026-09-10"),
               ("牛客周赛 Round 502", "B", "重写二", "模拟", "CF 800", "待重写", "2026-09-11"),
               ("牛客周赛 Round 503", "C", "重写三", "模拟", "CF 800", "待重写", "2026-09-12"),
               ("牛客周赛 Round 504", "D", "补题一", "模拟", "CF 800", "不会", "2026-09-13"),
               ("牛客周赛 Round 505", "E", "补题二", "模拟", "CF 800", "不会", "2026-09-14")]
    write_text(seg_mem, "\n".join(["# 看板记忆 fixture（段1 三行 / 段2 两行）", "",
                                   "| " + " | ".join(HEADER) + " |",
                                   "|" + "|".join(["---"] * len(HEADER)) + "|"]
                                  + [render_row(list(c)) for c in sm_rows] + [""]) + "\n")
    gui.path = seg_mem
    gui.var_search.set("")
    gui.reload()
    gui._seg_sel = [None] * 4
    gui.show_segment(0)
    ids0 = list(gui.today_tree.get_children())
    assert len(ids0) == 3, len(ids0)
    gui.today_tree.selection_set(ids0[2])              # 段1 选第 3 行
    gui.today_tree.focus(ids0[2])
    root.update()
    assert gui._seg_sel[0] == ids0[2], "选中该记进段 1：%r" % (gui._seg_sel,)
    gui.show_segment(1)                                # 切到段 2
    ids1 = list(gui.today_tree.get_children())
    assert len(ids1) == 2, len(ids1)
    gui.today_tree.selection_set(ids1[1])              # 段2 选第 2 行
    gui.today_tree.focus(ids1[1])
    root.update()
    gui.show_segment(0)                                # 切回段 1
    assert gui.today_tree.focus() == ids0[2] and gui._index_of(gui.today_tree) == 2, \
        "切回段 1 该还停在第 3 行（现在第 %s 行）" % (gui._index_of(gui.today_tree),)
    gui.show_segment(1)                                # 段 2 也各自记
    assert gui.today_tree.focus() == ids1[1] and gui._index_of(gui.today_tree) == 1, \
        "切回段 2 该还停在第 2 行（现在第 %s 行）" % (gui._index_of(gui.today_tree),)
    gui.show_segment(0)
    assert gui.today_tree.focus() == ids0[2], "两段来回切两次也不许重置"
    # 被记住的那行改状态踢出这一段 → 贴回第一行、不报错
    # （走「改文件 + F5 重读」而不是 set_status：后者自带 v9 的「选中自动下移」，
    #   会把回落的选中再挪走一行，照不出「贴回第一行」这条）
    kicked = gui.row_by_iid(ids0[2])
    save_changes(seg_mem, (kicked["场次"], kicked["题号"]),
                 {"状态": "不会", "日期": datetime.date.today().isoformat()},
                 backup_src_root=TEST_BACKUP_ROOT)
    gui.reload()
    assert gui.today_tree.focus() == gui.today_tree.get_children()[0] \
        and gui._index_of(gui.today_tree) == 0, \
        "记住的那行被踢出该段 → 该贴回第一行（现在 %r）" % (gui.today_tree.focus(),)
    gui.show_segment(1)
    gui.show_segment(0)
    assert gui._index_of(gui.today_tree) == 0, "回落之后继续切段也不许报错 / 不许乱跳"
    gui.path = tmp
    gui.reload()
    gui._seg_sel = [None] * 4
    print("(rr) 看板记忆：段1 第 3 行 → 切段2 → 切回仍在第 3 行；段2 独立记住第 2 行；"
          "被记住的行踢出该段 → 贴回第一行、不抛 ✓")

    # --- v10 闸门 (ss)：历史值容错（真表里可能还留着旧值「卡住」/「只读过」）
    bad_row = {"场次": "牛客周赛 Round 601", "题号": "A", "题名": "历史值行",
               "知识点": "模拟", "难度": "CF 800", "状态": "卡住", "日期": "2026-09-01",
               "_i": 0, "_date": datetime.date(2026, 9, 1),
               "_ago": (datetime.date.today() - datetime.date(2026, 9, 1)).days}
    sc_bad = state_counts([bad_row])                   # ① 统计只数 6 个状态，卡住不入账
    assert set(sc_bad) == set(STATES) and sum(sc_bad.values()) == 0, sc_bad
    assert done_count([bad_row]) == 0
    for i in range(4):                                 # ② 看板四段：不许抛
        assert segment_rows([bad_row], i) == [], i
    keep_rows = gui.rows
    gui.rows = [bad_row]
    gui.update_count()                                 # ③ 计数行：不抛、6 个状态照列
    line_bad = gui.var_count.get()
    assert line_bad.startswith("共 1 题") and "搜出" not in line_bad, line_bad
    gui.rows = keep_rows
    # ④ 浮层：当前值不在 6 项内 → 不预选（curselection 为空），按 1 仍能写成「未做」
    legacy = os.path.join(tmpdir, "legacy_state.md")
    write_text(legacy, "\n".join(["# 历史值 fixture（旧值 卡住 + 一行正常）", "",
                                  "| " + " | ".join(HEADER) + " |",
                                  "|" + "|".join(["---"] * len(HEADER)) + "|",
                                  render_row(["牛客周赛 Round 601", "A", "历史值行", "模拟",
                                              "CF 800", "卡住", "2026-09-01"]),
                                  render_row(["牛客周赛 Round 602", "B", "正常行", "模拟",
                                              "CF 800", "未做", ""]),
                                  ""]) + "\n")
    gui.path = legacy
    gui.var_search.set("")
    gui.reload()
    row_bad = next(r for r in gui.rows if r["状态"] == "卡住")
    assert gui.var_count.get().startswith("共 2 题"), gui.var_count.get()
    gui.tree.selection_set(str(row_bad["_i"]))
    gui.tree.focus(str(row_bad["_i"]))
    gui.open_status_popup(row_bad, gui.tree)
    root.update()
    assert gui.popup_lb.curselection() == (), \
        "当前值不在 6 项里 → 浮层不预选：%r" % (gui.popup_lb.curselection(),)
    gui.popup_lb.event_generate("<KeyPress>", keysym="1")
    root.update()
    assert gui.popup is None, "按 1 该直接写入并关掉浮层"
    got = next(r for r in parse_rows(legacy) if r["题号"] == "A")
    assert got["状态"] == "未做" and got["日期"] == datetime.date.today().isoformat(), got
    # ⑤ set_status：直接调「卡住」「只读过」必须拒绝，文件一个字不动、不产生备份
    n_ss0 = _count_bak(_mirror_dir(TEST_BACKUP_ROOT))
    bytes_ss0 = open(legacy, "rb").read()
    for bad_state in ("卡住", "只读过"):
        gui.set_status(row_bad, bad_state, gui.tree)
        assert gui.var_msg.get() == "写入失败：%s 不是合法状态" % bad_state, gui.var_msg.get()
    assert open(legacy, "rb").read() == bytes_ss0, "非法状态不许写盘"
    assert _count_bak(_mirror_dir(TEST_BACKUP_ROOT)) == n_ss0, "非法状态不许产生备份"
    gui.path = tmp
    gui.reload()
    gui._seg_sel = [None] * 4
    print("(ss) 历史值容错：「卡住」行 dict 走 统计 / 计数行 / 看板四段都不抛；浮层对旧值不预选"
          "（curselection 空）但按 1 写成「未做」；set_status 拒绝「卡住」「只读过」（不写盘、不备份）✓")

    # --- v4 闸门 (e)：配置往返（临时的 status_gui.config.json）+ 坏文件 / 屏幕外不崩
    cfg1 = os.path.join(tmpdir, "status_gui.config.json")
    want_cfg = {"geometry": "1234x789+11+22", "sort_col": "日期", "sort_desc": True}
    assert save_config(cfg1, want_cfg) is True
    assert load_config(cfg1) == want_cfg, load_config(cfg1)
    raw = open(cfg1, "rb").read()
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), "配置文件也要纯 LF / 无 BOM"
    assert b'"sort_col"' in raw and b'"sort_desc"' in raw, "键要小写英文：%r" % raw
    print("(e) 配置往返：存 → 读回一致（geometry / sort_col / sort_desc）✓")

    with open(cfg1, "wb") as f:
        f.write(b"{ not json at all")
    assert load_config(cfg1) == dict(DEFAULT_CFG), "坏配置应回默认"
    os.remove(cfg1)
    assert load_config(cfg1) == dict(DEFAULT_CFG), "缺文件应回默认"
    assert load_config(None) == dict(DEFAULT_CFG), "不给路径（--selftest / --smoke）也要有个默认值"
    assert _geometry_ok("1200x800+100+80", 1920, 1080), "屏幕里该认"
    assert not _geometry_ok("1200x800+99999+99999", 1920, 1080), "跑到屏幕外的不该认"
    assert not _geometry_ok("随便写的", 1920, 1080), "格式不对的不该认"
    print("(e) 坏文件 / 缺文件 / 屏幕外 geometry：一律回默认、不崩 ✓")

    cfg2 = os.path.join(tmpdir, "cfg_roundtrip.json")
    save_config(cfg2, {"geometry": "1200x700+30+40", "sort_col": "难度", "sort_desc": True})
    root2 = tk.Tk()
    gui2 = StatusGui(root2, tmp, quiet=True, config_path=cfg2)   # 打开就照上次的排序 / 大小
    root2.update_idletasks()
    assert (gui2.sort_col, gui2.sort_desc) == ("难度", True), (gui2.sort_col, gui2.sort_desc)
    assert gui2.tree.heading("难度")["text"].endswith("▼"), gui2.tree.heading("难度")["text"]
    assert root2.geometry().startswith("1200x700"), root2.geometry()
    gui2.sort_col, gui2.sort_desc = "日期", False
    gui2.on_close()                                  # = 点右上角关闭：存配置 + 销毁
    back = load_config(cfg2)
    assert back["sort_col"] == "日期" and back["sort_desc"] is False, back
    assert back["geometry"].startswith("1200x700"), back
    print("(e) 过一遍窗口对象：打开照上次的排序 / 大小，关窗把新值存回 ✓")

    # --- v11 闸门 (tt1)~(tt5)：F11 全屏开关（bind_all 挂；全屏中关窗不污染配置 geometry）
    #     合成按键前一律 focus_force（v10 老坑：窗口没被激活时非强制的 focus_set 会推迟，
    #     合成按键送不到控件上）—— 这里让每段自测与「窗口有没有被激活」无关。
    assert root.bind_all("<F11>") != "", "F11 该挂在 bind_all 上（任何焦点都生效）"
    gui.tree.focus_force()
    root.update()
    assert not gui._is_fullscreen(), "初始该是窗口态（非全屏）"
    gui.tree.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 1, \
        "总表焦点下按 F11 该进全屏：%r" % (root.attributes("-fullscreen"),)
    assert gui._is_fullscreen() and gui.last_windowed_geometry is not None, \
        "进全屏前该记下窗口态 geometry"
    gui.tree.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 0, \
        "再按一次该退出全屏（浏览器同款，不是单向）：%r" % (root.attributes("-fullscreen"),)
    print("(tt1) 初始非全屏；总表焦点 F11 → -fullscreen=1 → 再按 → 0（bind_all 已挂、进入前记下窗口态）✓")

    gui.ent_search.focus_force()
    root.update()
    gui.ent_search.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 1, "搜索框焦点下按 F11 也要进全屏"
    assert root.focus_get() is gui.ent_search, "F11 不该抢走搜索框焦点（现在 %r）" % (root.focus_get(),)
    gui.ent_search.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 0, "搜索框焦点下再按 F11 也要退出全屏"
    print("(tt2) 焦点在搜索框（focus_force）：F11 照样切换，焦点没被抢走 ✓")

    iid_t = gui.tree.get_children()[0]
    gui.tree.selection_set(iid_t)
    gui.tree.focus(iid_t)
    gui.open_status_popup(gui.row_by_iid(iid_t), gui.tree)
    root.update()
    assert gui.popup is not None
    gui.popup_lb.focus_force()
    root.update()
    gui.popup_lb.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 1 and gui.popup is not None, \
        "状态浮层开着时 F11 也要切换（浮层不许被吃掉按键 / 不许被关掉）"
    gui.popup_lb.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 0 and gui.popup is not None, \
        "状态浮层开着时再按 F11 也要退出全屏"
    gui._popup_cancel()
    assert gui.popup is None
    gui.open_help()
    root.update()
    assert gui.help_win is not None
    gui.help_lbl.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 1 and gui.help_win is not None, \
        "`?` 一览开着时 F11 也要切换（一览不许被关掉）"
    gui.help_lbl.event_generate("<F11>")
    root.update()
    assert int(root.attributes("-fullscreen")) == 0 and gui.help_win is not None, \
        "`?` 一览开着时再按 F11 也要退出全屏"
    gui.close_help()
    root.update()
    print("(tt3) 状态浮层 / `?` 一览打开时 F11 照样切换（两个 Toplevel 都没被 F11 影响）✓")

    root.geometry("1000x700+40+40")
    root.update()
    assert root.geometry() == "1000x700+40+40", root.geometry()
    gui.tree.focus_force()
    root.update()
    gui.tree.event_generate("<F11>")
    root.update()
    fs_geom = root.geometry()
    assert fs_geom != "1000x700+40+40", "全屏下 geometry 该变成整屏：%r" % (fs_geom,)
    gui.tree.event_generate("<F11>")
    root.update()
    assert root.geometry() == "1000x700+40+40", \
        "退出全屏该回到进入前的窗口态（现在 %r）" % (root.geometry(),)
    print("(tt4) 几何往返：1000x700+40+40 → F11 开（%s）→ F11 关 → 回到 1000x700+40+40 ✓" % fs_geom)

    # 全屏下关窗：临时 config_path（别碰脚本同目录）；存回的必须是「进全屏前」的窗口态
    cfg_fs = os.path.join(tmpdir, "cfg_v11_fullscreen.json")
    assert save_config(cfg_fs, {"geometry": "1000x700+40+40",
                                "sort_col": "场次", "sort_desc": False})
    root3 = tk.Tk()
    gui3 = StatusGui(root3, tmp, quiet=True, config_path=cfg_fs)
    root3.update()
    win_geom3 = root3.geometry()
    assert win_geom3 == "1000x700+40+40", win_geom3
    assert not gui3._is_fullscreen()
    sw3, sh3 = root3.winfo_screenwidth(), root3.winfo_screenheight()
    gui3.tree.focus_force()
    root3.update()
    gui3.tree.event_generate("<F11>")
    root3.update()
    assert int(root3.attributes("-fullscreen")) == 1
    fs_geom3 = root3.geometry()                 # 全屏态 geometry = 整屏
    assert fs_geom3 != win_geom3
    gui3.on_close()                             # 全屏下关窗（= 点右上角）
    back3 = load_config(cfg_fs)
    assert back3["geometry"] == win_geom3, \
        "全屏下关窗该存「进全屏前」的窗口态：存成 %r（进屏前 %r）" % (back3["geometry"], win_geom3)
    assert back3["geometry"] != fs_geom3, "全屏下关窗不许把整屏 geometry 存进配置"
    assert back3["geometry"] != "1x1+0+0" and _geometry_ok(back3["geometry"]), back3["geometry"]
    assert back3["geometry"].split("+")[0] != "%dx%d" % (sw3, sh3), \
        "存的不该是整屏尺寸 %dx%d" % (sw3, sh3)
    print("(tt5) 全屏下关窗：配置存回 %r = 进全屏前的窗口态（整屏是 %r、非 1x1）✓"
          % (back3["geometry"], fs_geom3))

    # 窗口态关窗对照：拖大拖小后的当前 geometry 照旧存当前值
    cfg_win = os.path.join(tmpdir, "cfg_v11_windowed.json")
    root4 = tk.Tk()
    gui4 = StatusGui(root4, tmp, quiet=True, config_path=cfg_win)
    root4.update()
    root4.geometry("1120x680+70+80")            # = 窗口态下拖动改大小后的当前 geometry
    root4.update()
    now4 = root4.geometry()
    assert now4 == "1120x680+70+80", now4
    gui4.on_close()
    back4 = load_config(cfg_win)
    assert back4["geometry"] == now4, (back4["geometry"], now4)
    print("(tt5) 窗口态关窗对照：存的就是当时 geometry（%r），全屏那条没影响这条 ✓" % (now4,))

    # --- v12 闸门 (uu)：选中行直接按 1~6 改状态（绑树上不绑 root；不开浮层；浮层开着不双写）
    for k in range(1, 7):
        assert gui.tree.bind("<Key-%d>" % k) != "" and gui.tree.bind("<KP_%d>" % k) != "", \
            "总表树上该挂数字键 %d（v12 直改状态）" % k
        assert gui.today_tree.bind("<Key-%d>" % k) != "" and gui.today_tree.bind("<KP_%d>" % k) != "", \
            "看板树上该挂数字键 %d（v12 直改状态）" % k
    for k in (7, 8):
        assert gui.tree.bind("<Key-%d>" % k) == "" and gui.today_tree.bind("<Key-%d>" % k) == "", \
            "数字键 %d 不该绑（v10 起状态只有 6 个）" % k
    gui.sort_col, gui.sort_desc = "场次", False      # 钉住顺序，下面才按行号算「下移一行」
    gui.var_search.set("")
    gui.nb.select(0)
    gui.refresh_view()
    bak_dir_u = _mirror_dir(TEST_BACKUP_ROOT)
    today_u = datetime.date.today().isoformat()
    # ① 总表：挑一行状态 != 待重写，按 3 → 待重写（写盘 + 日期今天 + 提示一条 + 自动下移一行）
    iid_u = next(x for x in gui.tree.get_children() if gui.row_by_iid(x)["状态"] != "待重写")
    gui.tree.selection_set(iid_u)
    gui.tree.focus(iid_u)
    gui.tree.see(iid_u)
    row_u = gui.row_by_iid(iid_u)
    idx_u = gui.tree.index(iid_u)
    n_u0 = _count_bak(bak_dir_u)
    gui.tree.focus_force()
    root.update()
    gui.tree.event_generate("<KeyPress>", keysym="3")
    root.update()
    got_u = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row_u["场次"], row_u["题号"]))
    assert (got_u["状态"], got_u["日期"]) == ("待重写", today_u), (got_u["状态"], got_u["日期"])
    assert _count_bak(bak_dir_u) == n_u0 + 1, "数字直改也要走备份（+1）"
    assert gui.var_msg.get() == "已保存：%s %s → 待重写" % (row_u["场次"], row_u["题号"]), \
        "提示该只出一条：%r" % gui.var_msg.get()
    kids_u = list(gui.tree.get_children())
    nxt_u = kids_u[min(idx_u + 1, len(kids_u) - 1)]
    cur_after = gui.tree_row(gui.tree)
    nxt_row = gui.row_by_iid(nxt_u)
    assert cur_after is not None and (cur_after["场次"], cur_after["题号"]) == \
        (nxt_row["场次"], nxt_row["题号"]), "数字直改后选中行应自动下移一行（现在是 %r）" % (cur_after,)
    assert gui._undo_stack and gui._undo_stack[-1]["round"] == row_u["场次"], "数字直改也要入撤销栈"
    # ② 看板：哪段非空就在哪段挑第一行，按 1 → 未做
    seg_b = next(i for i in range(4) if segment_rows(gui.rows, i))
    gui.nb.select(1)
    gui.show_segment(seg_b)
    root.update()
    iid_b = gui.today_tree.get_children()[0]
    gui.today_tree.selection_set(iid_b)
    gui.today_tree.focus(iid_b)
    row_b = gui.row_by_iid(iid_b)
    n_b0 = _count_bak(bak_dir_u)
    gui.today_tree.focus_force()
    root.update()
    gui.today_tree.event_generate("<KeyPress>", keysym="1")
    root.update()
    got_b = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row_b["场次"], row_b["题号"]))
    assert (got_b["状态"], got_b["日期"]) == ("未做", today_u), (got_b["状态"], got_b["日期"])
    assert _count_bak(bak_dir_u) == n_b0 + 1
    assert gui.var_msg.get() == "已保存：%s %s → 未做" % (row_b["场次"], row_b["题号"]), gui.var_msg.get()
    # ③ 焦点在搜索框时按 3：数字打进输入框，状态一个字没变
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    gui.ent_search.focus_force()
    gui.ent_search.icursor("end")
    root.update()
    n_c0 = _count_bak(bak_dir_u)
    bytes_c0 = open(tmp, "rb").read()
    gui.ent_search.event_generate("<KeyPress>", keysym="3")
    root.update()
    assert gui.var_search.get().endswith("3"), "搜索框里按 3 该照常打字：%r" % gui.var_search.get()
    assert open(tmp, "rb").read() == bytes_c0 and _count_bak(bak_dir_u) == n_c0, \
        "焦点在搜索框时按数字不许改状态"
    gui.var_search.set("")
    gui.refresh_view()
    # ④ 浮层开着按 3：只改一次（盘一遍、消息一条 —— 树上的绑定不许双触发）
    iid_p = next(x for x in gui.tree.get_children() if gui.row_by_iid(x)["状态"] != "待重写")
    gui.tree.selection_set(iid_p)
    gui.tree.focus(iid_p)
    row_p = gui.row_by_iid(iid_p)
    gui.open_status_popup(row_p, gui.tree)
    root.update()
    assert gui.popup is not None, "浮层没弹出来"
    n_p0 = _count_bak(bak_dir_u)
    bytes_p0 = open(tmp, "rb").read()
    gui.popup_lb.focus_force()
    root.update()
    gui.popup_lb.event_generate("<KeyPress>", keysym="3")
    root.update()
    assert gui.popup is None, "浮层里按 3 该直选「待重写」并关掉浮层"
    assert _count_bak(bak_dir_u) == n_p0 + 1, \
        "浮层开着按数字只许写一遍盘（差 %d 遍）" % (_count_bak(bak_dir_u) - n_p0)
    assert open(tmp, "rb").read() != bytes_p0
    assert gui.var_msg.get() == "已保存：%s %s → 待重写" % (row_p["场次"], row_p["题号"]), \
        "消息只该有一条：%r" % gui.var_msg.get()
    got_p = next(r for r in parse_rows(tmp) if (r["场次"], r["题号"]) == (row_p["场次"], row_p["题号"]))
    assert got_p["状态"] == "待重写"
    # ⑤ 空表上按数字：没得改，静默不抛、文件 / 备份都不动
    gui.tree.focus_force()
    gui.var_search.set("zzz-没有这一行")
    gui.refresh_view()
    root.update()
    n_e0 = _count_bak(bak_dir_u)
    assert gui.tree.get_children() == (), "这条要空表才测得动（没搜出任何行）"
    gui.tree.event_generate("<KeyPress>", keysym="3")
    root.update()
    assert _count_bak(bak_dir_u) == n_e0, "空表按数字不许写盘"
    gui.var_search.set("")
    gui.refresh_view()
    root.update()
    print("(uu) 数字直改：总表按 3 → 待重写 / 日期今天 / 自动下移 / 提示一条 / 入栈；看板按 1 同样；"
          "焦点在搜索框按 3 只打字不改状态；浮层开着按 3 只写一遍盘；空表按数字静默 ✓")

    # --- v12 闸门 (vv)：Ctrl+Z 连撤多步（栈）：连改 3 行 → 撤 3 次逐字节还原 → 再撤给提示
    gui._undo_stack.clear()                          # 隔离：本条自己造三步
    gui._last_change = None
    gui.nb.select(0)
    gui.var_search.set("")
    gui.refresh_view()
    ids_v = list(gui.tree.get_children())[:3]
    picks = []
    for iid in ids_v:
        r = gui.row_by_iid(iid)
        target = "待重写" if r["状态"] != "待重写" else "未做"
        picks.append((r["场次"], r["题号"], r["状态"], r["日期"], target))
    bytes_v0 = open(tmp, "rb").read()
    n_v0 = _count_bak(bak_dir_u)
    for rd, lt, old_s, old_d, target in picks:
        r = next(x for x in gui.rows if (x["场次"], x["题号"]) == (rd, lt))
        gui.set_status(r, target, gui.tree)
    assert len(gui._undo_stack) == 3, "三笔改动该三步都入栈：%d" % len(gui._undo_stack)
    assert open(tmp, "rb").read() != bytes_v0
    for rd, lt, old_s, old_d, target in picks:
        got_v = next(x for x in parse_rows(tmp) if (x["场次"], x["题号"]) == (rd, lt))
        assert got_v["状态"] == target, (rd, lt, got_v["状态"], target)
    gui.tree.focus_force()
    root.update()
    for _ in range(3):
        gui.tree.event_generate("<KeyPress>", keysym="z", state=0x4)   # = Ctrl+Z
        root.update()
    assert gui._undo_stack == [] and gui._last_change is None, (gui._undo_stack, gui._last_change)
    assert open(tmp, "rb").read() == bytes_v0, "连撤三步后该逐字节回到原样"
    for rd, lt, old_s, old_d, target in picks:
        got_v = next(x for x in parse_rows(tmp) if (x["场次"], x["题号"]) == (rd, lt))
        assert (got_v["状态"], got_v["日期"]) == (old_s, old_d), (rd, lt, got_v["状态"], got_v["日期"])
    assert _count_bak(bak_dir_u) == n_v0 + 3 + 3, \
        "三改 + 三撤各走一次备份（差 %d）" % (_count_bak(bak_dir_u) - n_v0)
    assert gui.var_msg.get() == "已撤销：%s %s → %s" % (picks[0][0], picks[0][1], picks[0][2]), \
        gui.var_msg.get()
    n_v1 = _count_bak(bak_dir_u)
    bytes_v1 = open(tmp, "rb").read()
    gui.tree.event_generate("<KeyPress>", keysym="z", state=0x4)       # 第 4 次：栈空
    root.update()
    assert gui.var_msg.get() == "没有可撤销的改动", gui.var_msg.get()
    assert open(tmp, "rb").read() == bytes_v1 and _count_bak(bak_dir_u) == n_v1, \
        "栈空时按 Ctrl+Z 文件一个字不动、也不备份"
    print("(vv) Ctrl+Z 连撤：连改 3 行 → 撤 3 次逐字节还原（栈空、日期也回原位）；"
          "第 4 次提示「没有可撤销的改动」且不写盘 ✓")

    # --- v12 闸门 (ww)：Shift+Enter 打开原题（解析链只读；opener 打桩 —— 绝不真开浏览器）
    assert gui.tree.bind("<Shift-Return>") != "" and gui.today_tree.bind("<Shift-Return>") != "", \
        "Shift+Enter 该挂两棵树上（和 Alt+Enter 同规矩）"
    real_sf2 = getattr(os, "startfile", None)
    if real_sf2 is not None:                        # 再把真开文件的闸门关上（(v) 末尾放回来了）
        os.startfile = _spy_startfile
    try:
        gui.data_root = sand
        sol163 = os.path.join(sand, "题解", "牛客周赛", "Round163", "Round163题解.md")
        os.makedirs(os.path.dirname(sol163), exist_ok=True)
        write_text(sol163, "# Round163 题解（冒烟占位）\n\n"
                           "> 比赛主页：<https://ac.nowcoder.com/acm/contest/140737>\n")
        url_w, why_w = gui.parse_problem_url({"场次": "牛客周赛 Round 163", "题号": "E"})
        assert (url_w, why_w) == ("https://ac.nowcoder.com/acm/contest/140737/E", None), (url_w, why_w)
        # 经按键走一遍（总表）：把选中行的两格临时改成 Round 163 / E，Shift+Enter → opener 收到 URL
        gui.nb.select(0)
        gui.var_search.set("")
        gui.refresh_view()
        row_w = _pick_row(gui.tree, "牛客周赛 Round 205", "B")
        saved_w = (row_w["场次"], row_w["题号"])
        opened_before = len(opened)
        row_w["场次"], row_w["题号"] = "牛客周赛 Round 163", "E"
        gui.tree.focus_force()
        root.update()
        gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x1)     # = Shift+Enter（实测 state=0x1）
        root.update()
        row_w["场次"], row_w["题号"] = saved_w
        assert gui.popup is None, "Shift+Enter 不该弹状态浮层"
        assert opened[opened_before:] == [url_w], \
            "Shift+Enter 该把拼好的原题 URL 交给 opener：%r" % (opened[opened_before:],)
        # 题解目录换到不存在的路径 → None + 原因、不抛
        gui.data_root = os.path.join(tmpdir, "没有这个资料根")
        url_w2, why_w2 = gui.parse_problem_url({"场次": "牛客周赛 Round 163", "题号": "E"})
        assert (url_w2, why_w2) == (None, "没找到这场比赛的原题链接"), (url_w2, why_w2)
        # 题解文件在、但里面没有主页链接 → 同一条原因
        sol164 = os.path.join(sand, "题解", "牛客周赛", "Round164", "Round164题解.md")
        os.makedirs(os.path.dirname(sol164), exist_ok=True)
        write_text(sol164, "# Round164 题解（冒烟占位：故意没有主页链接）\n")
        gui.data_root = sand
        url_w3, why_w3 = gui.parse_problem_url({"场次": "牛客周赛 Round 164", "题号": "A"})
        assert (url_w3, why_w3) == (None, "没找到这场比赛的原题链接"), (url_w3, why_w3)
        # 场次不是牛客周赛 → 「这场还没接」；经按键走一遍，提示同风格
        url_w4, why_w4 = gui.parse_problem_url({"场次": "洛谷月赛 Round 5", "题号": "A"})
        assert (url_w4, why_w4) == (None, "这场还没接"), (url_w4, why_w4)
        row_w5 = _pick_row(gui.tree, "牛客周赛 Round 205", "B")
        saved_w5 = row_w5["场次"]
        row_w5["场次"] = "洛谷月赛 Round 5"
        gui.tree.focus_force()
        root.update()
        gui.tree.event_generate("<KeyPress>", keysym="Return", state=0x1)
        root.update()
        row_w5["场次"] = saved_w5
        assert gui.var_msg.get() == "打不开：这场还没接", gui.var_msg.get()
        # 看板页同样生效：切到看板、选一行、行内两格临时改掉、Shift+Enter
        gui.nb.select(1)
        seg_w = next(i for i in range(4) if segment_rows(gui.rows, i))
        gui.show_segment(seg_w)
        root.update()
        iid_w6 = gui.today_tree.get_children()[0]
        gui.today_tree.selection_set(iid_w6)
        gui.today_tree.focus(iid_w6)
        row_w6 = gui.row_by_iid(iid_w6)
        saved_w6 = (row_w6["场次"], row_w6["题号"])
        row_w6["场次"], row_w6["题号"] = "牛客周赛 Round 163", "E"
        opened_w6 = len(opened)
        gui.today_tree.focus_force()
        root.update()
        gui.today_tree.event_generate("<KeyPress>", keysym="Return", state=0x1)
        root.update()
        row_w6["场次"], row_w6["题号"] = saved_w6
        assert opened[opened_w6:] == [url_w], "看板页 Shift+Enter 同样能开原题：%r" % (opened[opened_w6:],)
    finally:
        if real_sf2 is not None:
            os.startfile = real_sf2
    assert spawn["n"] == 0, "v12 打开原题测试里真调了 os.startfile %d 次（注入没兜住）" % spawn["n"]
    print("(ww) Shift+Enter 打开原题：Round 163/E → 140737/E（打桩 opener）总表 / 看板都生效；"
          "题解不在 / 没链接 →「没找到这场比赛的原题链接」；洛谷月赛 →「这场还没接」；全程没真开浏览器 ✓")

    # --- v12 闸门 (xx)：搜索含难度（1800 / CF1800 / cf 1800 等价；粘写 / 拆写、大小写照旧）
    gui.nb.select(0)
    def _hit_keys(q):
        gui.var_search.set(q)
        gui.refresh_view()
        return set((gui.row_by_iid(x)["场次"], gui.row_by_iid(x)["题号"])
                   for x in gui.tree.get_children())
    k203 = ("牛客周赛 Round 203", "D")            # fixture 里唯一的 CF 1800
    k188 = ("牛客周赛 Round 188", "D")            # fixture 里唯一的 CF 1900
    k200a, k197a = ("牛客周赛 Round 200", "A"), ("牛客周赛 Round 197", "A")   # 两个 CF 800
    h_plain = _hit_keys("1800")
    h_glued = _hit_keys("CF1800")
    h_space = _hit_keys("cf 1800")
    assert h_plain and h_plain == h_glued == h_space == {k203}, \
        (sorted(h_plain), sorted(h_glued), sorted(h_space))
    # 真实难度：粘写 / 拆写 / 大小写三种写法命中集合相同（非空）——这就是「忽略空格」的口径
    h1900g = _hit_keys("CF1900")
    h1900s = _hit_keys("CF 1900")
    assert h1900g == h1900s == {k188}, (h1900g, h1900s)
    # 不存在的难度 CF 900：粘写 = 整串「cf900」查无此值 → 空；拆写 = 词「cf」+ 词「900」都要命中，
    # 而 v10 规则是**子串**命中（1900 里含 900）→ 命中 188D。这是既定语义，不是 v12 的漏转
    #（任务书举例「CF 900 ≡ CF900」按实测改成下面两条）。
    assert _hit_keys("CF900") == set()
    assert _hit_keys("CF 900") == _hit_keys("1900") == {k188}
    # CF 800：粘写恰好两行（「cf1800」不含「cf800」）；拆写多中 203D（子串 800 ⊂ 1800）
    assert _hit_keys("cf800") == {k200a, k197a}
    assert _hit_keys("CF 800") == {k200a, k197a, k203}
    gui.var_search.set("")
    gui.refresh_view()
    print("(xx) 搜索含难度：「1800 / CF1800 / cf 1800」命中集合同 = CF 1800 那行；"
          "「CF1900」≡「CF 1900」= 188D；「CF900」空而「CF 900」子串命中 188D（v10 子串口径）；"
          "「cf800」= 两行 CF 800 ✓")

    # --- v13 闸门 (zz)：筛选（v14 起并进搜索框下的下拉面板）—— 多条件组合
    #     （知识点 / 状态 / 难度）只筛总表，且与命令行是**同一份实现**
    #     （拿子进程真跑 status_report.py 的筛选模式比命中集合）
    # 前面的闸门改过夹具的状态并真写了盘（uu / vv）→ 先重造一份干净夹具再往下断言，
    # 否则「某状态有几行」这种硬编码期望会随前面闸门的副作用漂移。
    write_fixture(tmp)
    gui.reload()
    gui.nb.select(0)
    gui.var_search.set("")
    gui._clear_filters()
    root.update()
    assert len(gui.tree.get_children()) == len(FIXTURE_ROWS), "清空筛选后该是全量 12 行"

    def _showing():
        return set((gui.row_by_iid(x)["场次"], gui.row_by_iid(x)["题号"])
                   for x in gui.tree.get_children())

    def _set(know="", diff="", sts=()):
        gui.var_know.set(know)
        gui.var_diff.set(diff)
        gui.status_on.clear()
        gui.status_on.update(sts)
        gui._paint_chips()
        gui.refresh_view()
        root.update()

    def _cli_keys(out):
        """命令行筛选输出 → {(场次, 题号)}：命中行以 4 空格起头，场次列后跟 2+ 空格。"""
        ks = set()
        for ln in out.splitlines():
            m = re.match(r"^ {4}(牛客周赛 Round \d+) {2,}(\S+) ", ln)
            if m:
                ks.add((m.group(1), m.group(2)))
        return ks

    k203 = ("牛客周赛 Round 203", "D")     # 树形DP / 动态规划 ｜ 树形DP / CF 1800 / 巩固
    k210 = ("牛客周赛 Round 210", "E")     # 区间DP / 动态规划 ｜ 前缀和 / CF 1700 / 待重写
    k208 = ("牛客周赛 Round 208", "E")     # 期望DP / 概率与期望 ｜ 动态规划 / CF 2000 / 不会
    k197 = ("牛客周赛 Round 197", "A")     # 模拟 / CF 800 / 未做
    k200 = ("牛客周赛 Round 200", "A")     # 模拟 / CF 800 / 巩固

    # ① 知识点：子串命中（忽略空格大小写）+ 逗号分隔取并集
    _set(know="树形DP")
    assert _showing() == {k203}, sorted(_showing())
    _set(know="树形 DP")
    assert _showing() == {k203}, "带空格的写法该命中同一行"
    # 子串口径：`DP` 只中「知识点里真写了 DP」的行（fixture 里只有 203D 的「树形DP」），
    # 写了「动态规划」的两行要另外写「动态规划」——不查词典、不替用户发明同义写法；
    # 想一次查全几种写法就逗号并列（= 并集）。
    _set(know="DP")
    assert _showing() == {k203}, sorted(_showing())
    _set(know="动态规划")
    assert _showing() == {k203, k210, k208}, sorted(_showing())
    _set(know="DP, 动态规划")
    assert _showing() == {k203, k210, k208}, "逗号分隔该是并集（两种写法一次查全）"
    assert gui.var_hits.get() == "筛出 3 题", gui.var_hits.get()

    # ② 状态按钮：多选 = 并集；再点一次 = 取消
    k188 = ("牛客周赛 Round 188", "D")     # 树链剖分 / CF 1900 / 待重写
    k201 = ("牛客周赛 Round 201", "F")     # 构造 / CF 2100 / 不会
    _set(sts=["待重写", "不会"])
    assert _showing() == {k188, k210, k201, k208}, sorted(_showing())
    gui._toggle_status("不会")
    root.update()
    assert _showing() == {k188, k210}, sorted(_showing())
    gui._toggle_status("不会")
    root.update()
    assert _showing() == {k188, k210, k201, k208}, "再点一次该把「不会」选回来"
    gui.status_on.clear()

    # ③ 难度：闭区间 / 单值 / <= / >=（多值取并集）
    _set(diff="1700-2000")
    assert _showing() == {k210, k203, k208, ("牛客周赛 Round 188", "D")}, sorted(_showing())
    _set(diff="1500")
    assert _showing() == {("牛客周赛 Round 204", "C")}, sorted(_showing())
    _set(diff="<=800")
    assert _showing() == {k200, k197}, sorted(_showing())
    _set(diff=">=2000")
    assert _showing() == {k208, ("牛客周赛 Round 201", "F")}, sorted(_showing())
    _set(diff="1200, 1500")
    assert _showing() == {("牛客周赛 Round 202", "B"), ("牛客周赛 Round 204", "C")}, sorted(_showing())

    # ④ 三条件 AND + 写法不认的难度：一条都不匹配，并在「筛出 N 题」后面点名
    _set(know="动态规划", diff=">=1700", sts=["待重写", "不会"])
    assert _showing() == {k210, k208}, sorted(_showing())
    assert gui.var_hits.get() == "筛出 2 题", gui.var_hits.get()
    _set(know="动态规划", diff="一千")
    assert _showing() == set(), "难度写法认不出 → 一条都不匹配（不是当没写）"
    assert "筛出 0 题" in gui.var_hits.get() and "难度写法不认" in gui.var_hits.get(), gui.var_hits.get()
    _set(know="动态规划")
    assert "难度写法不认" not in gui.var_hits.get()

    # ⑤ 与命令行同一份实现的硬证据：同条件真跑子进程，命中集合必须一模一样
    combos = [
        (dict(know="DP"), ["--knowledge", "DP"]),
        (dict(know="DP, 动态规划"), ["--knowledge", "DP,动态规划"]),
        (dict(know="树形 DP"), ["--knowledge", "树形 DP"]),
        (dict(sts=["待重写", "不会"]), ["--status", "待重写,不会"]),
        (dict(know="DP", sts=["未做", "不会", "待重写"]), ["--todo", "--knowledge", "DP"]),
        (dict(know="动态规划", sts=["未做", "不会", "待重写"]),
         ["--todo", "--knowledge", "动态规划"]),
        (dict(diff="1700-2000"), ["--difficulty", "1700-2000"]),
        (dict(diff="<=800", sts=["未做"]), ["--status", "未做", "--difficulty", "<=800"]),
        (dict(know="动态规划", diff=">=1700", sts=["待重写", "不会"]),
         ["--knowledge", "动态规划", "--difficulty", ">=1700", "--status", "待重写,不会"]),
        (dict(know="不存在的知识点"), ["--knowledge", "不存在的知识点"]),
        (dict(diff="一千"), ["--difficulty", "一千"]),
    ]
    for kw, argv in combos:
        _set(know=kw.get("know", ""), diff=kw.get("diff", ""), sts=kw.get("sts", ()))
        gui_keys = _showing()
        rc, out = _run_report(tmp, argv)
        assert rc == 0, "命令行 `%s` 退出码 %d：\n%s" % (" ".join(argv), rc, out)
        cli_keys = _cli_keys(out)
        assert gui_keys == cli_keys, \
            "GUI 与命令行命中集合不一致：`%s`\n  GUI=%r\n  CLI=%r" % (" ".join(argv), sorted(gui_keys), sorted(cli_keys))
        assert ("筛出 %d 题" % len(gui_keys)) in out, \
            "命令行报的条数跟命中集合对不上：%s\n%s" % (" ".join(argv), out)
    print("(zz) 筛选（v14：搜索框下的下拉面板）：知识点（子串 / 忽略空格 / 逗号并集）/ 状态多选"
          "（并集、可取消）/ 难度（区间 / 单值 / <= / >= / 多值并集）三条件 AND 都对；写法不认的"
          "难度一条不匹配且点名；**11 组条件逐组拿子进程真跑 status_report.py 比过命中集合，"
          "全部一字不差** ✓")

    # ⑥ v14 面板交互：↓ 展开 / ↑ 收起 / ↑↓ 逐行走 / Esc 逐层退回 / 清空 / 「筛出 N 题」两处挂点
    _set(know="动态规划", diff=">=1700", sts=["不会"])
    assert len(gui.tree.get_children()) == 1 and gui.var_hits.get() != ""
    gui._clear_filters()
    root.update()
    assert len(gui.tree.get_children()) == len(FIXTURE_ROWS)
    assert gui.var_hits.get() == "" and gui.var_hits_min.get() == "", \
        "清空后「筛出 N 题」两处都该消失：%r / %r" % (gui.var_hits.get(), gui.var_hits_min.get())
    # ↓：第一下只展开（焦点留在搜索框）；再一下进「知识点」；逐行 ↓ 走到状态列表
    assert not gui.dlg_open, "面板默认该是收起的"
    gui.ent_search.focus_force()
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="Down")
    root.update()
    assert gui.dlg_open and gui.dlg.winfo_ismapped() and root.focus_get() is gui.ent_search, \
        "↓ 第一下只展开面板、焦点留在搜索框（还能接着打字）"
    gui.ent_search.event_generate("<KeyPress>", keysym="Down")
    root.update()
    assert root.focus_get() is gui.ent_know, "↓ 第二下该进「知识点」"
    gui.ent_know.event_generate("<KeyPress>", keysym="Down")
    root.update()
    assert root.focus_get() is gui.ent_diff, "知识点 ↓ 该到「难度」"
    gui.ent_diff.event_generate("<KeyPress>", keysym="Down")
    root.update()
    assert root.focus_get() is gui.lb_status, "难度 ↓ 该到「状态」列表"
    # 状态列表（多选清单）：↑↓ 只移光标；空格勾选；1~6 直勾 / 再按取消
    gui.status_cursor = 0
    gui.lb_status.event_generate("<KeyPress>", keysym="Down")
    root.update()
    assert gui.status_cursor == 1 and not gui.status_on, "↑↓ 只移光标、不该动勾选"
    gui.lb_status.event_generate("<KeyPress>", keysym="space")
    root.update()
    assert gui.status_on == {STATES[1]}, gui.status_on
    assert gui.var_hits.get() == "筛出 %d 题" % len(gui.tree.get_children()), gui.var_hits.get()
    gui.lb_status.event_generate("<KeyPress>", keysym="3")
    root.update()
    assert gui.status_on == {STATES[1], STATES[2]}, gui.status_on
    gui.lb_status.event_generate("<KeyPress>", keysym="3")
    root.update()
    assert gui.status_on == {STATES[1]}, "同一项再按一次 = 取消"
    gui.lb_status.event_generate("<KeyPress>", keysym="Up")
    gui.lb_status.event_generate("<KeyPress>", keysym="Up")
    root.update()
    assert gui.status_cursor == 0
    gui.lb_status.event_generate("<KeyPress>", keysym="Up")      # 到顶再 ↑ = 退回难度框
    root.update()
    assert root.focus_get() is gui.ent_diff, "状态列表到顶再 ↑ 该退回难度框"
    gui._clear_filters()
    root.update()
    # Esc 逐层退回：框里有字先清空（人留在本行）→ 空了上退一行 → 状态 → 难度 → 搜索框 → 收面板 → 回表格
    gui.var_know.set("树形DP")
    gui.refresh_view()
    gui.ent_know.focus_force()
    root.update()
    gui.ent_know.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert gui.var_know.get() == "" and root.focus_get() is gui.ent_know, \
        "知识点框 Esc：有字先清掉、人留在本行（v14 逐层退回）"
    gui.ent_diff.focus_force()
    root.update()
    gui.ent_diff.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert root.focus_get() is gui.ent_know, "难度框空了再 Esc 该上退到知识点框"
    gui.lb_status.focus_force()
    root.update()
    gui.lb_status.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert root.focus_get() is gui.ent_diff, "状态列表 Esc 该退回难度框"
    gui.var_search.set("双指针")
    gui.refresh_view()
    gui.ent_search.focus_force()
    root.update()
    gui.ent_search.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert gui.var_search.get() == "" and root.focus_get() is gui.ent_search, "搜索框 Esc：有字先清空"
    assert gui.dlg_open, "清空搜索词不该动面板"
    gui.ent_search.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert not gui.dlg_open and root.focus_get() is gui.ent_search, "空了再 Esc 该收起面板"
    gui.ent_search.event_generate("<KeyPress>", keysym="Escape")
    root.update()
    assert root.focus_get() is gui.tree, "面板收着再 Esc 该回主页面"
    # 「筛出 N 题」两处挂点：面板收起时挂到第一行右端；展开时回面板底部（同一行字）
    gui.var_diff.set(">=1700")
    gui.refresh_view()
    root.update()
    assert gui.var_hits.get() != "" and gui.var_hits_min.get() == gui.var_hits.get(), \
        "面板收起时同一行字该挂到窗口第一行右端"
    gui._dropdown_open()
    root.update()
    assert gui.var_hits_min.get() == "" and gui.var_hits.get() != "", \
        "面板展开时只留面板底部那一处"
    # 面板里 Enter = 带条件跳回总表（搜索词 / 条件保留），离开搜索站自动收面板
    gui.var_know.set("DP")
    gui.refresh_view()
    n_before = len(gui.tree.get_children())
    gui.ent_know.focus_force()
    root.update()
    gui.ent_know.event_generate("<KeyPress>", keysym="Return")
    root.update()
    assert root.focus_get() is gui.tree and gui.var_know.get() == "DP" \
        and len(gui.tree.get_children()) == n_before, "知识点行 Enter 该带条件跳回总表"
    assert not gui.dlg_open, "跳回总表 = 离开搜索站，面板该收起"
    gui.var_know.set("")
    gui.var_diff.set("")
    gui.refresh_view()
    assert gui.var_hits.get() == "" and gui.var_hits_min.get() == "", "条件清空后计数该消失"

    # ⑦ 筛选只作用于总表：看板四段数字 / 计数行不受筛选影响（跟搜索一个口径）
    _set(know="动态规划", sts=["待重写"])
    seg = [len(segment_rows(gui.rows, i)) for i in range(4)]
    assert [gui.card_num[i].cget("text") for i in range(4)] == [str(n) for n in seg], \
        "筛选不该动看板四段数字"
    assert gui.var_count.get().startswith("共 %d 题" % len(gui.rows)), \
        "计数行该按全量算（v10 口径），不受筛选影响：%r" % gui.var_count.get()
    _set(know="动态规划")
    assert _showing() == {k203, k210, k208}, "搜索框还空着时筛选结果该回来"
    gui.var_search.set("Round 210")
    gui.refresh_view()
    assert _showing() == {k210}, "筛选 ∧ 搜索 = 交集"
    gui.var_search.set("")
    gui._clear_filters()
    root.update()
    assert len(gui.tree.get_children()) == len(FIXTURE_ROWS)
    print("⑦（同 (zz)）v14 面板：清空 / Esc 逐层退回 / 两处计数挂点 / Enter 跳回 / 看板不受影响 / "
          "筛选 ∧ 搜索取交集 ✓")

    # --- v13 闸门 (yy)：菜单「题解包」三项在（导入 / 导出 / ── / 一键校验）；报告窗能建能写；
    # 有任务在跑时三入口一律拦下（不弹选包框）。真跑导入由 CLI 闸门（--pack-check）覆盖。
    mb = gui.root.nametowidget(gui.root.cget("menu"))
    assert mb.entrycget(0, "label") == PACK_MENU_LABEL, mb.entrycget(0, "label")
    pm = mb.nametowidget(mb.entrycget(0, "menu"))
    kinds = [pm.type(i) for i in range(pm.index("end") + 1)]
    labels = [pm.entrycget(i, "label") for i in range(len(kinds)) if kinds[i] != "separator"]
    assert kinds == ["command", "command", "separator", "command"], kinds
    assert labels == [PACK_IMPORT_LABEL, PACK_EXPORT_LABEL, PACK_CHECK_LABEL], labels
    w, rep, st, btn = gui._open_pack_report("导入题解包", "包：X.zip（冒烟）", allow_apply=True)
    gui._pack_report_append(rep, "hello 报告\n")
    assert rep.get("1.0", "end").startswith("hello 报告"), rep.get("1.0", "end")
    assert str(rep.cget("state")) == "disabled" and str(btn.cget("state")) == "disabled"
    assert st.cget("text") == "跑着呢……" and gui._pack_job is None, "报告窗自己不许起任务"
    assert st.cget("fg") == C_ACCENT_DARK, "v16：状态行起步是强调色（跑着呢）"
    assert ttk.Style(gui.root).configure("Accent.TButton")["background"] == C_ACCENT, \
        "v16：Accent 主按钮样式已配置"
    w.destroy()
    w2, rep2, st2, btn2 = gui._open_pack_report("一键校验", "包：Y.zip（冒烟）", allow_apply=False)
    assert btn2 is None, "只读的报告窗（一键校验 / 导出）不给「应用到数据根」按钮"
    w2.destroy()
    gui._pack_job = {"win": None, "kind": "import", "pack": None,
                     "queue": queue.Queue(), "applied": False}
    gui.pack_flow("import")                    # 有任务在跑 → 直接拦下（正常路径要弹选包框，会阻塞）
    assert "已有题解包任务在跑" in gui.var_msg.get(), gui.var_msg.get()
    gui._pack_job = None
    print("(yy) 菜单「题解包」= %s / %s / ── / %s（分隔线一条）；报告窗只读、落盘按钮初始禁用、"
          "只读窗不给按钮；有任务在跑时三入口拦下 ✓"
          % (PACK_IMPORT_LABEL, PACK_EXPORT_LABEL, PACK_CHECK_LABEL))

    assert gui.config_path is None, "--smoke 走过的地方不许写配置"
    assert _cfg_state(script_cfg) == cfg_state0, \
        "冒烟碰了脚本同目录的 %s（v4 要求 --selftest / --smoke 一律不碰）" % script_cfg
    print("(e) 脚本同目录的 %s 全程没被碰过 ✓" % CONFIG_NAME)

    root.destroy()
    print("窗口构件 + 交互链路 OK")
    print("SMOKE OK")
    return 0


# ================================================================ 无窗口命令行版（v13）
def _attach_console():
    """windowed exe：把 stdout / stderr 接回启动它的控制台（接不上就保持 None）。

    打包成 --windowed 后 Win 不会给进程连控制台，从 cmd / bash 启动时 print 是黑洞；
    `AttachConsole(-1)` 借父进程的控制台，输出就能被 CI / 终端看到。源码环境不动。
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        ctypes.windll.kernel32.AttachConsole(-1)
    except Exception:
        pass
    for name, mode in (("stdout", "w"), ("stderr", "w")):
        cur = getattr(sys, name)
        if cur is not None:
            continue
        try:
            setattr(sys, name, open("CONOUT$", mode, encoding="utf-8", errors="replace"))
        except OSError:
            setattr(sys, name, None)


class _Tee:
    """把输出同时写到若干流（含 None / 已关的流 —— 写不进去就跳过，绝不因日志把任务弄挂）。"""

    def __init__(self, *streams):
        self.streams = list(streams)

    def write(self, s):
        for st in self.streams:
            if st is None:
                continue
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass
        return len(s) if s else 0

    def flush(self):
        for st in self.streams:
            try:
                if st is not None:
                    st.flush()
            except Exception:
                pass

    def reconfigure(self, **kw):
        """子脚本**模块顶层**会调它（`fill_knowledge.py` 就是）——这里当 no-op：
        流在打开时就定好了 utf-8，frozen 下不能因为少这一个方法把整条导入链弄挂。"""
        return None

    def __getattr__(self, name):
        """其余属性（encoding / errors / isatty / fileno…）转发给第一个真实流。"""
        for st in self.streams:
            if st is not None and hasattr(st, name):
                return getattr(st, name)
        raise AttributeError(name)


def pack_cli(args):
    """无窗口跑一个题解包任务（CI / 自动化 / exe），返回退出码。

    与菜单三入口共用同一套 argv 拼法（pack_import_argv / pack_export_argv）与同一个
    `main()`——命令行走的跟 GUI 走的是一条路。
    """
    _attach_console()
    logf = None
    logp = args.log
    if not logp and sys.stdout is None:        # windowed exe 且没接上控制台 → 落日志兜底
        logp = os.path.join(toolutil.REPO_ROOT, "TimuZhuangtai.log")
    if logp:
        logf = open(logp, "a", encoding="utf-8", errors="replace")
        logf.write("\n===== %s =====\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    old = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = _Tee(old[0], logf)
    try:
        if args.apply and not args.pack_import:
            print("★ `--apply` 只配合 `--pack-import`（`--pack-check` 是只读的）")
            return 2
        if args.pack_export:
            return _load_tool("export_solution").main(
                pack_export_argv(args.pack_export, args.out, DATA_ROOT))
        pack = args.pack_import or args.pack_check
        return _load_tool("import_solution").main(
            pack_import_argv(pack, DATA_ROOT, bool(args.apply and args.pack_import)))
    finally:
        sys.stdout, sys.stderr = old
        if logf:
            logf.close()


# ================================================================ 入口
def main(argv):
    ap = argparse.ArgumentParser(
        description="题目状态跟踪窗口 v15（tkinter）：全键盘改状态 + 搜索框下拉里的多条件筛选（知识点 / 状态 / 难度），"
                    "只改目标行的状态 / 日期；菜单「题解包」= 导入 / 导出 / 一键校验。")
    ap.add_argument("--file", default=DEFAULT_FILE, help="状态表路径（默认 %s）" % DEFAULT_FILE)
    ap.add_argument("--selftest", action="store_true",
                    help="自测：用自造 fixture 做读写校验，不开窗口、不碰真 md")
    ap.add_argument("--smoke", action="store_true",
                    help="窗口冒烟：建窗口 + 走一遍交互，不 mainloop()")
    ap.add_argument("--pack-import", metavar="包", help="无窗口：校验题解包（加 --apply 才落盘）")
    ap.add_argument("--pack-check", metavar="包", help="无窗口：只校验题解包，不落盘")
    ap.add_argument("--pack-export", metavar="Round163[-G]", help="无窗口：导出题解包")
    ap.add_argument("--apply", action="store_true", help="配合 --pack-import：真写盘（默认只校验）")
    ap.add_argument("-o", "--out", help="配合 --pack-export：输出 .zip / 目录")
    ap.add_argument("--log", help="把输出同时写进日志文件（无控制台时默认 exe 旁的 TimuZhuangtai.log）")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.smoke:
        return smoke()
    if args.pack_import or args.pack_check or args.pack_export:
        return pack_cli(args)

    root = tk.Tk()
    StatusGui(root, args.file, config_path=config_path_default())   # v4：记住上次
    root.mainloop()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
