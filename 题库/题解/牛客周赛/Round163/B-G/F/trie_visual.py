# -*- coding: utf-8 -*-
"""
牛客周赛 Round 163 F - 小月的前缀：把 Trie 画出来
=================================================

这个脚本只干一件事：把 C++ 里那几行"抽象的数组操作"，翻译成
"树长什么样、数组长什么样"的逐步画面。

    ch[v][x] = u    -->  树上多一条从 v 出发、标着字符 x、指向 u 的边
    id[v] = i       -->  结点 v 上挂了一块牌子：编号 i 的串在这里结束
    cnt[i]          -->  这块牌子旁边的"库存还剩几个"

纯标准库，不依赖任何第三方包。直接运行：
    python trie_visual.py

若中文显示乱码（终端不是 UTF-8），改用：
    set PYTHONIOENCODING=utf-8 && python trie_visual.py
"""

import sys

# ---------------------------------------------------------------- 数据部分
# 这一节刻意和 C++ 的四个数组一一对应，名字都取一样的
#
#   ch[v][x]  结点 v 的 x 号儿子（x = 0..25 对应 'a'..'z'），0 表示没有
#   idv[v]    在结点 v 结束的字符串编号，0 表示没有
#   cnt[i]    第 i 种字符串还剩几个
#   sname[i]  第 i 种字符串本身（只是为了打印好看，算法里不需要）

ALPHA = 26
A_ORD = ord('a')


def new_trie():
    """造一棵只有根结点的空树。返回 (ch, idv, cnt, sname, meta)"""
    ch = [[0] * ALPHA]      # ch[0] 是根结点那一行，26 个 0
    idv = [0]               # idv[0] = 0，根不是任何串的结束点
    cnt = [0]               # cnt[0] 占位，字符串编号从 1 开始
    sname = [""]            # sname[0] 占位
    meta = {"insert_steps": [], "query_steps": []}
    return ch, idv, cnt, sname, meta


def insert(ch, idv, cnt, sname, meta, s, c, pid):
    """
    插入第 pid 种字符串 s（库存 c 个）。
    对应 C++ 里那个 for 循环，一步一步走，每走一步记一笔。
    """
    cnt.append(c)
    sname.append(s)
    v = 0                                   # 从根出发
    trail = []                              # 这一路走过来的每一步
    for k, cc in enumerate(s):
        x = ord(cc) - A_ORD
        # 下面这几行就是 C++ 的： if (!ch[v][x]) ch[v][x] = ++tot;  v = ch[v][x];
        if ch[v][x] == 0:                   # 这条边还不存在 --> 新建结点
            ch.append([0] * ALPHA)          # 新结点自带 26 个空儿子
            idv.append(0)                   # 新结点暂时不是谁的结束点
            new_node = len(ch) - 1
            ch[v][x] = new_node
            action = "ch[%d]['%s'] 是 0 --> 新建结点 v=%d" % (v, cc, new_node)
        else:
            new_node = ch[v][x]
            action = "ch[%d]['%s'] 已经是 %d --> 复用老结点" % (v, cc, new_node)
        trail.append({
            "k": k, "char": cc, "from": v, "to": new_node,
            "action": action, "prefix": s[:k + 1],
        })
        v = new_node
    idv[v] = pid                            # C++ 的 id[v] = i;
    meta["insert_steps"].append({"pid": pid, "s": s, "c": c, "trail": trail, "end": v})
    return v


def query(ch, idv, cnt, sname, meta, t):
    """
    查询串 t。返回 (best, log)。
    log 里逐字记录了每一步的判断，对应 C++ 查询循环的每一行。
    """
    v = 0
    best = 0
    log = []
    for k, cc in enumerate(t):
        x = ord(cc) - A_ORD
        if ch[v][x] == 0:                   # C++: if (!ch[v][x]) break;
            log.append({"k": k, "char": cc, "from": v,
                        "kind": "dead", "prefix": t[:k + 1]})
            break
        prev = v
        v = ch[v][x]
        i = idv[v]
        step = {"k": k, "char": cc, "from": prev, "to": v,
                "prefix": t[:k + 1], "end_id": i}
        if i and cnt[i] > 0:                # C++: if (id[v] && cnt[id[v]] > 0) best = id[v];
            step.update({"kind": "hit", "best": i, "cnt": cnt[i], "old_best": best})
            best = i
        elif i:
            step.update({"kind": "empty", "cnt": cnt[i]})   # 有牌子，但没货了
        else:
            step.update({"kind": "pass"})                   # 这里根本没有串结束
        log.append(step)
    done = {"kind": "done", "best": best}
    if best:
        cnt[best] -= 1                      # C++: if (best) --cnt[best];
        done["after"] = cnt[best]
    log.append(done)
    meta["query_steps"].append({"t": t, "log": log, "best": best})
    return best


# ---------------------------------------------------------------- 画图部分
def label_of(v, idv, cnt, sname, mark=()):
    """结点右边的牌子：v=几，挂着谁的牌子，还剩几个"""
    tag = "★ " if v in mark else "  "
    s = tag + "v=%d" % v
    if idv[v]:
        s += " 「%s」id=%d 剩%d" % (sname[idv[v]], idv[v], cnt[idv[v]])
    return s


def render_tree(ch, idv, cnt, sname, mark=()):
    """
    把树画成字符画。迭代版 DFS（不用递归，深链也不会爆栈）。
    mark: 需要标星号的结点集合
    每一行形如：  └──b──→   v=2 「ab」id=2 剩1
    """
    mark = set(mark)
    out = []
    # 栈元素：(结点, 深度, 进来的那条边的字符, 我是不是家里最小的孩子, 祖先的"最小"标记)
    stack = [(0, 0, "", True, ())]
    while stack:
        v, depth, ec, is_last, anc = stack.pop()
        if depth == 0:
            out.append("  {根 v=0}")
        else:
            prefix = ""
            for flag in anc:
                prefix += "    " if flag else "│   "
            arrow = "└─ " if is_last else "├─ "
            out.append("  " + prefix + arrow + ec + " ──→ " + label_of(v, idv, cnt, sname, mark))

        kids = [(c, ch[v][c]) for c in range(ALPHA) if ch[v][c]]
        for i in range(len(kids) - 1, -1, -1):
            c, u = kids[i]
            child_anc = () if depth == 0 else anc + (is_last,)
            stack.append((u, depth + 1, chr(A_ORD + c), i == len(kids) - 1, child_anc))
    return out


def render_arrays(ch, idv, cnt):
    """把 ch / idv / cnt 三个数组当前的样子打成表"""
    lines = []
    used = sorted({c for row in ch for c in range(ALPHA) if row[c]})
    if not used:
        lines.append("  （空树：ch[0] 整行都是 0）")
    else:
        lines.append("           " + "".join("%6s" % ("'" + chr(A_ORD + c) + "'") for c in used))
        for v in range(len(ch)):
            lines.append("  ch[%d]    " % v + "".join("%6d" % ch[v][c] for c in used))
    lines.append("")
    lines.append("  id[v]  : " + "  ".join("id[%d]=%d" % (v, idv[v]) for v in range(len(idv))))
    lines.append("  cnt[i] : " + "  ".join("cnt[%d]=%d" % (i, cnt[i]) for i in range(1, len(cnt))))
    return lines


def bar(title):
    return "\n" + "=" * 66 + "\n" + title + "\n" + "=" * 66


def show(ch, idv, cnt, sname, mark=()):
    for ln in render_tree(ch, idv, cnt, sname, mark):
        print(ln)
    print()
    for ln in render_arrays(ch, idv, cnt):
        print(ln)


def explain_insert(step):
    print("  插入 「%s」（编号 %d，库存 %d）：" % (step["s"], step["pid"], step["c"]))
    for tr in step["trail"]:
        print("    第 %d 个字符 '%s'：%s，停在 v=%d"
              % (tr["k"] + 1, tr["char"], tr["action"], tr["to"]))
    print("    走完了 --> 在停下的结点 v=%d 上挂编号：id[%d] = %d"
          % (step["end"], step["end"], step["pid"]))


def explain_query(log):
    for st in log:
        if st["kind"] == "done":
            if st["best"]:
                print("    走完 --> 答案 = %d，并把 cnt[%d] 减 1（%d --> %d）"
                      % (st["best"], st["best"], st["after"] + 1, st["after"]))
            else:
                print("    走完 --> 没有合法前缀，答案 = 0（不减任何库存）")
            continue
        k = st["k"] + 1
        if st["kind"] == "dead":
            print("    第 %d 个字符 '%s'：ch[%d]['%s'] = 0，这条边不存在"
                  % (k, st["char"], st["from"], st["char"]))
            print("        --> break。后面的前缀都要经过这里，更不可能存在")
        elif st["kind"] == "hit":
            print("    第 %d 个字符 '%s'：ch[%d]['%s'] = %d，走到 v=%d"
                  % (k, st["char"], st["from"], st["char"], st["to"], st["to"]))
            print("        id[%d] = %d 且 cnt[%d] = %d > 0  --> 合法！best 从 %d 改成 %d"
                  % (st["to"], st["end_id"], st["end_id"], st["cnt"], st["old_best"], st["best"]))
        elif st["kind"] == "empty":
            print("    第 %d 个字符 '%s'：ch[%d]['%s'] = %d，走到 v=%d"
                  % (k, st["char"], st["from"], st["char"], st["to"], st["to"]))
            print("        id[%d] = %d，可是 cnt[%d] = 0  --> 牌子在，货没了，跳过"
                  % (st["to"], st["end_id"], st["end_id"]))
        elif st["kind"] == "pass":
            print("    第 %d 个字符 '%s'：ch[%d]['%s'] = %d，走到 v=%d"
                  % (k, st["char"], st["from"], st["char"], st["to"], st["to"]))
            print("        id[%d] = 0  --> 这里没有串结束，跳过" % st["to"])


def demo():
    """跑一遍官方样例 1，把每一步都画出来"""
    SETUP = [(1, "a", 2), (2, "ab", 1), (3, "abc", 0)]
    QUERIES = ["abc", "abc", "ax", "a", "b"]
    EXPECT = [2, 1, 1, 0, 0]

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(bar("【起点】空树：只有光杆树根 v=0，三个数组都是空的"))
    ch, idv, cnt, sname, meta = new_trie()
    show(ch, idv, cnt, sname)

    print(bar("【建树】把 n 种字符串一个一个插进去"))
    for pid, s, c in SETUP:
        insert(ch, idv, cnt, sname, meta, s, c, pid)
        print("\n" + "-" * 66)
        print("第 %d 次插入" % pid)
        print("-" * 66)
        explain_insert(meta["insert_steps"][-1])
        print()
        show(ch, idv, cnt, sname)

    print(bar("【树建好了】一句话：牌子挂在不同的深度上"))
    print("  深度 1 的结点挂 id=1 「a」；深度 2 挂 id=2 「ab」；深度 3 挂 id=3 「abc」")
    print("  所以『是 t 的前缀的那些串』= 『沿 t 往下走会踩到的那些牌子』")
    print()
    show(ch, idv, cnt, sname)

    print(bar("【查询】对每个 t，沿 t 一个字一个字往下走，边走边看牌子"))
    got = []
    for qi, t in enumerate(QUERIES, 1):
        print("\n" + "-" * 66)
        print("第 %d 次操作：t = \"%s\"" % (qi, t))
        print("-" * 66)
        ans = query(ch, idv, cnt, sname, meta, t)
        explain_query(meta["query_steps"][-1]["log"])
        got.append(ans)
        print("  现在的树与数组：")
        show(ch, idv, cnt, sname)

    print(bar("【对答案】"))
    print("  程序输出： " + " ".join(str(x) for x in got))
    print("  样例答案： " + " ".join(str(x) for x in EXPECT))
    print("  %s" % ("一致 ✔" if got == EXPECT else "不一致 ✘"))


if __name__ == "__main__":
    demo()
