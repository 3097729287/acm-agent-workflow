# -*- coding: utf-8 -*-
"""
vizgrid —— 终端字符画引擎
==========================
讲数据结构 / 算法过程时，各题的 `<题>_visual.py` 导入本模块，只写"画什么"，
不重写绘图代码。

用法（放在自己脚本的开头）：

    import os, sys
    _p = os.environ.get("AGENT_CP_TOOLS")
    if not _p:                       # 向上找到含 tools/toolutil.py 的目录
        _p = os.path.dirname(os.path.abspath(__file__))
        while not os.path.isfile(os.path.join(_p, "tools", "toolutil.py")):
            _q = os.path.dirname(_p)
            if _q == _p:
                raise SystemExit("没找到仓库 tools/：请设置 AGENT_CP_TOOLS 环境变量")
            _p = _q
        _p = os.path.join(_p, "tools")
    sys.path.insert(0, _p)
    from vizgrid import Grid, banner, render_tree, table, hr

本模块把下面 6 条踩出来的规则固化进了代码，调 API 就自动遵守：

  1. 终端字符是"高瘦"的（约 1 宽 × 2 高）→ Grid 默认 ys = xs / 2，
     这样 x 方向和 y 方向的比例才对，画出来不扁。
  2. 画线要**逐格步进**：每步只走一格行或一格列，否则两个字符会堆进同一格，
     屏幕上看起来像 `//`。→ Grid.seg() 已按此实现，别自己按比例采样。
  3. 网格里的**空行是图的一部分**：没有点的行 rstrip() 之后就是空行，
     往 markdown 里嵌时**不能"遇到空行就结束"**，要按 `(ymax-ymin)*ys+1`
     整段取。→ Grid.text() 返回的就是整段，直接用它，别自己拼。
  4. 用 **Unicode 制表符**（━ ┃ ┆ · ─ └ ├ │），不是 ASCII 画。
     文件一律 UTF-8。
  5. 每个脚本旁放一个 `run.cmd`（纯 ASCII + CRLF）双击可跑；
     有些环境**没有 `py` 这个命令**，脚本里和 run.cmd 里都写 `python`。
  6. **对齐宽度坑**：`─ └ ├ → ★ · │` 这些在 Unicode 里是 **Ambiguous(A)**
     宽度，中文引号「」是 Wide(W)。本引擎按"Ambiguous 算 1 格"排版，
     这与历史脚本（trie_visual.py / cross_visual.py）实测的效果一致。
     如果哪天换了字体、框线看起来错位了，把 AMBIGUOUS_WIDE 改成 True 再跑。
     **含中文的表格列必须用 pad() 补位，不能用 str.ljust()**——
     ljust 数的是字符个数，中文一个字符占两格，会错位。
"""

import unicodedata

# 框线等 Ambiguous 字符是否按 2 格算。默认 False（= 历史脚本的实测效果）。
AMBIGUOUS_WIDE = False

# 常用的线框字符，统一从这儿取
H_LINE = "─"
V_LINE = "│"
TEE = "├"
ELBOW = "└"
ARROW = "→"
DOT = "·"
STAR = "★"
CROSS_PT = "+"


# ------------------------------------------------------------------ 宽度处理
def dwidth(s):
    """字符串在终端里占的格数（中文 2 格，ASCII 1 格）。"""
    n = 0
    for ch in s:
        ea = unicodedata.east_asian_width(ch)
        if ea in ("W", "F"):
            n += 2
        elif ea == "A" and AMBIGUOUS_WIDE:
            n += 2
        elif unicodedata.combining(ch):
            n += 0
        else:
            n += 1
    return n


def pad(s, width, align="<"):
    """按终端格数补位（不是按字符个数）。align: '<' 左对齐 / '>' 右对齐 / '^' 居中。"""
    gap = width - dwidth(s)
    if gap <= 0:
        return s
    if align == ">":
        return " " * gap + s
    if align == "^":
        left = gap // 2
        return " " * left + s + " " * (gap - left)
    return s + " " * gap


# ------------------------------------------------------------------ 排版小件
def hr(char=H_LINE, n=70):
    print(char * n)


def banner(title, char="=", n=70):
    """一节的开头。风格基准里 part1/part2/part3 每部分都用它收口。"""
    print()
    print(char * n)
    print(title)
    print(char * n)


def part(n, total, title):
    """带序号的 banner：part(1, 3, "叉积怎么算")"""
    banner("第 %d/%d 部分 · %s" % (n, total, title), char="=")


def note(text, indent=2):
    """讲解文字（不是图），统一缩进。"""
    for ln in text.split("\n"):
        print(" " * indent + ln if ln.strip() else "")


def table(headers, rows, indent=2, aligns=None):
    """
    打印一张对齐的表。中文列宽用 dwidth 算，不会错位。
    aligns: 每个列的 '<' / '>' / '^'，默认全左对齐。
    """
    cols = len(headers)
    aligns = aligns or ["<"] * cols
    w = [dwidth(str(h)) for h in headers]
    srows = [[str(c) for c in r] for r in rows]
    for r in srows:
        for i in range(min(cols, len(r))):
            w[i] = max(w[i], dwidth(r[i]))
    out = []
    out.append(" " * indent + "  ".join(pad(str(headers[i]), w[i], "^")
                                        for i in range(cols)).rstrip())
    out.append(" " * indent + "  ".join(H_LINE * w[i] for i in range(cols)))
    for r in srows:
        out.append(" " * indent + "  ".join(pad(r[i], w[i], aligns[i])
                                            for i in range(min(cols, len(r)))).rstrip())
    text = "\n".join(out)
    print(text)
    return text


# ------------------------------------------------------------------ 平面网格
class Grid:
    """字符画平面。x 每 1 单位占 xs 列，y 每 1 单位占 ys 行。

    ys 默认取 xs 的一半 —— 终端字符高瘦（约 1 宽 × 2 高），
    这样画出来的图形不会被压扁。稀疏图用 xs=4, ys=2；密集网格用 xs=2, ys=1。
    """

    def __init__(self, xmin, xmax, ymin, ymax, xs=4, ys=2):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.xs, self.ys = xs, ys
        self.w = (xmax - xmin) * xs + 1
        self.h = (ymax - ymin) * ys + 1
        self.g = [[" "] * self.w for _ in range(self.h)]

    def rc(self, x, y):
        """数学坐标 (x, y) -> 画布行列 (row, col)。y 轴向上，所以要翻过来。"""
        return (int(round((self.ymax - y) * self.ys)),
                int(round((x - self.xmin) * self.xs)))

    def put(self, x, y, ch):
        r, c = self.rc(x, y)
        if 0 <= r < self.h and 0 <= c < self.w:
            self.g[r][c] = ch
        return self

    def seg(self, x1, y1, x2, y2, ch):
        """逐格步进画线段：每步只走一格（行或列）。

        按比例采样会把两个字符堆进同一格，屏幕上看起来像 `//`——这是画线
        必须逐格走的原因。
        """
        r1, c1 = self.rc(x1, y1)
        r2, c2 = self.rc(x2, y2)
        steps = max(abs(r2 - r1), abs(c2 - c1), 1)
        for k in range(steps + 1):
            t = k / steps
            r = int(round(r1 + (r2 - r1) * t))
            c = int(round(c1 + (c2 - c1) * t))
            if 0 <= r < self.h and 0 <= c < self.w:
                self.g[r][c] = ch
        return self

    def axes(self, dot=DOT, origin=CROSS_PT, arrow=">"):
        """画坐标轴：x 轴取 y=0，y 轴取 x=0。"""
        for x in range(self.xmin, self.xmax + 1):
            self.put(x, 0, dot)
        for y in range(self.ymin, self.ymax + 1):
            self.put(0, y, dot)
        self.put(0, 0, origin)
        self.put(self.xmax, 0, arrow)
        return self

    def text(self, indent="      ", trim_tail=True):
        """把画布整段取出来，返回字符串，可直接贴进 markdown。

        **网格内部的空行一律保留**——空行是图的一部分，往 markdown 里嵌时
        不能"遇到空行就结束"。只有最底下多出来的空行会被去掉（trim_tail=False
        可以连它们一起留下，比如要展示一块固定边界的区域）。
        空行不打缩进，免得往 md 里塞一堆行尾空格。
        """
        out = []
        for row in self.g:
            s = "".join(row).rstrip()
            out.append(indent + s if s else "")
        if trim_tail:
            while out and not out[-1].strip():
                out.pop()
        return "\n".join(out)

    def show(self, indent="      ", trim_tail=True):
        t = self.text(indent, trim_tail)
        print(t)
        return t


# ------------------------------------------------------------------ 树的渲染
def render_tree(children_of, label_of, root=0, root_label="根", mark=()):
    """
    把树画成字符画。**迭代版遍历**（递归遇到深链会爆栈，见《算法实现踩坑集》）。

    children_of(v) -> [(边的字符, 子结点), ...]，顺序即从左到右的显示顺序
    label_of(v)    -> 结点右边那段文字
    mark           -> 需要标 ★ 的结点集合

    返回行列表，每行形如：
        ├─ b ──→  v=2 「ab」id=2 剩1
    """
    mark = set(mark)
    # 缩进单位跟着线框符的实际宽度推：`└─ ` 占 3 格（Ambiguous 算 1）或 5 格
    # （算 2），再留 1 格让子结点落在父结点那条边字符的右边。写死 4 的话，
    # AMBIGUOUS_WIDE 一翻转就整体错位——那这个开关就形同虚设了。
    UNIT = dwidth(ELBOW + H_LINE + " ") + 1
    BLANK = " " * UNIT
    PIPE = V_LINE + " " * (UNIT - dwidth(V_LINE))
    out = []
    # 栈元素：(结点, 深度, 进来的那条边的字符, 我是不是最小的孩子, 祖先们的"最小"标记)
    stack = [(root, 0, "", True, ())]
    while stack:
        v, depth, ec, is_last, anc = stack.pop()
        if depth == 0:
            out.append("  {%s}" % root_label)
        else:
            prefix = "".join(BLANK if flag else PIPE for flag in anc)
            arrow = ELBOW + H_LINE if is_last else TEE + H_LINE
            right = (STAR + " " if v in mark else "  ") + label_of(v)
            out.append("  " + prefix + arrow + " " + (ec or "?") + " " + H_LINE * 2
                       + ARROW + " " + right)
        kids = list(children_of(v))
        for i in range(len(kids) - 1, -1, -1):
            c, u = kids[i]
            child_anc = () if depth == 0 else anc + (is_last,)
            stack.append((u, depth + 1, c, i == len(kids) - 1, child_anc))
    return out


def show_tree(children_of, label_of, root=0, root_label="根", mark=()):
    lines = render_tree(children_of, label_of, root, root_label, mark)
    print("\n".join(lines))
    return lines


# ------------------------------------------------------------------ 数组的行
def render_array(name, values, idx_name="i", start=0, label=None):
    """把一维数组打成两行：下标行 + 值行。讲解"数组怎么跟着变"用。

        v[]        0    1    2    3
        ch[v][]    0    1    0    0

    label 传了就再加一行表头（如 "ch[v]：结点 v 的字符 x 儿子是谁"）。
    """
    cells = ["%d" % v for v in values]
    w = max(5, max((dwidth(c) for c in cells), default=1) + 1)
    namew = max(9, dwidth(name + "[]") + 1, dwidth(idx_name + "[]") + 1)
    idx = "  " + pad(idx_name + "[]", namew) + "".join(pad(str(start + j), w, ">")
                                                      for j in range(len(cells)))
    row = "  " + pad(name + "[]", namew) + "".join(pad(c, w, ">") for c in cells)
    out = [idx, row]
    if label:
        out = [label] + out
    return out
