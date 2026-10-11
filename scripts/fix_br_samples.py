# -*- coding: utf-8 -*-
"""一次性修复 v0.7.1 缓存样例里的 HTML 残留（只处理已确认的污染形态，幂等）。

背景：CF 抓取函数旧版不转 <br>，Div.3 1125 B（Did Not Go to Print）的输出样例
在应为空行处存了字面 "<br />"。本脚本按「原题 URL + 旧污染内容」精确匹配，
只修 statements.content JSON 里的 samples 与题面正文里的同段残留，不动其它行。

用法：
    python fix_br_samples.py <sqlite路径>... [--dry]
"""
import json
import re
import sqlite3
import sys
import urllib.parse

# 已确认的污染题：规范化 URL → 期望出现的旧字面片段（作为匹配指纹）
POLLUTED = {
    "codeforces.com/contest/2275/problem/B": "<br />",
}

BR_RE = re.compile(r"(?is)<br\s*/?>")


def fix_text(text):
    if not isinstance(text, str) or "<br" not in text:
        return text, False
    fixed = BR_RE.sub("\n", text)
    return fixed, fixed != text


def canonical(url):
    if not isinstance(url, str) or not url:
        return None
    p = urllib.parse.urlsplit(url.strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    m = re.fullmatch(r"/(?:contest/(\d+)/problem|problemset/problem/(\d+))/([A-Za-z0-9]+)", p.path)
    if host == "codeforces.com" and m:
        return f"codeforces.com/contest/{m[1] or m[2]}/problem/{m[3].upper()}"
    return None


def fix_content(content):
    """statements.content 是题面 JSON（含 samples 数组）。修 samples 的 in/out 与正文。"""
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        # 非 JSON：直接当文本修（保守——只有含污染指纹的行才会进到这里）
        return fix_text(content)
    if not isinstance(data, dict):
        return fix_text(content)
    changed = False
    samples = data.get("samples")
    if isinstance(samples, list):
        for case in samples:
            if not isinstance(case, dict):
                continue
            for key in ("in", "out", "input", "output"):
                fixed, hit = fix_text(case.get(key))
                if hit:
                    case[key] = fixed
                    changed = True
    # 正文 / markdown 里同段的残留
    for key in ("markdown", "statement", "content", "text"):
        if isinstance(data.get(key), str):
            fixed, hit = fix_text(data[key])
            if hit:
                data[key] = fixed
                changed = True
    if changed:
        return json.dumps(data, ensure_ascii=False), True
    return content, False


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    dry = "--dry" in argv
    paths = [a for a in argv[1:] if not a.startswith("--")]
    fixed_count = 0
    for path in paths:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        try:
            url_by_id = {}
            for row in db.execute("SELECT id, url FROM problems"):
                url_by_id[row["id"]] = row["url"]
            for stmt in db.execute("SELECT problem_id, content FROM statements"):
                key = canonical(url_by_id.get(stmt["problem_id"]))
                fingerprint = POLLUTED.get(key)
                if fingerprint is None:
                    continue
                if fingerprint not in stmt["content"]:
                    continue  # 无污染指纹，跳过（可能已修过）
                new_content, hit = fix_content(stmt["content"])
                if not hit:
                    continue
                if not dry:
                    with db:
                        db.execute("UPDATE statements SET content=? WHERE problem_id=?",
                                   (new_content, stmt["problem_id"]))
                fixed_count += 1
                print(f"{'[dry] ' if dry else ''}{path.split('/')[-1]}: fixed {stmt['problem_id']} ({key})")
        finally:
            db.close()
    print(f"done: {fixed_count} statements fixed ({'dry' if dry else 'applied'})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
