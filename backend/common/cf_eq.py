#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cf_eq.py — CF-EQ v1.0：四站统一训练难度规格（训练规划层；Phase 1 实现）。

作用域（严格）：
  · 本模块只属于 **difficulty normalization + training selection**（训练分带）；
  · **不参与** correctness verification，也**不改变** p3-2 执行器路由：
    「谁首解」仍由 native difficulty + oracle_strength/risk 决定（sched.py route，口径 = native；
    1300 阈值来自 strong-oracle A/B，**不是** CF-EQ 尺度——两者不得混用，规格 §7）；
  · **不覆盖**任何平台的原始 difficulty：native_difficulty 原样保留（§0 / §8）。

规格版本 = CF-EQ-v1.0（冻结；修改只能通过显式 calibration revision）。

四站换算（规格 §1–§4）：
  Codeforces  官方 rating → 直用（HIGH，零二次换算）；无官方分 → 只接受调用方给的
              division+题位回退区间（LOW），**不制造伪精确数值**
  AtCoder     raw = 0.67 * kenkoooo + 650，四舍五入到最近 100，下限钳 800（MEDIUM）
  洛谷        官方难度档 1–8 → 区间 + 代表值（LOW；代表值仅供排序/粗调度）
  牛客        无固定映射；证据给区间（LOW）；机器必须用单值时取区间中点四舍五入到 100

边界不确定性（§6）：cf_eq_band 跨越 1200 / 1400 / 2200 / 2300 中任一关键边界 →
boundary_uncertain = True；跨 2300 且代表值原判 DEFERRED 时，按保守训练策略上调为
TARGET_STRETCH（跨界题进候选，不因不确定丢弃）。

实现决策（规格未逐字规定、由实现者选定，待确认后固化）：
  1. AtCoder 的 cf_eq_band = 代表值 ± 100（MEDIUM 置信下「一个取整格」的保守区间）；
  2. 牛客估值证据默认半宽 ± 300（NOWCODER_AI_HALF_WIDTH；调用方可用 --band 直接给区间覆盖）；
  3. 无任何难度证据 → training_band = NEED_DIFFICULTY（§5 八档之外，对齐管线
     BLOCKED_PENDING_DIFFICULTY 语义）；
  4. CF 无官方分不内置 div+题位拍脑袋表（规格说「可以用已有 fallback」——本机管线里没有
     现成表，故只接受调用方显式区间；要不要内置请拍板）。

用法：
  python cf_eq.py selftest                              # 机器自检（退出码 0 = 全过）
  python cf_eq.py anchors                               # §2 的 13 个参考锚点核对
  python cf_eq.py eval --platform atcoder --native 1573 # 单题换算
  python cf_eq.py eval --platform luogu --native 4      # 档位可给整数或 "4（普及+/提高）"
  python cf_eq.py eval --platform nowcoder --native 1400 [--band 1200-1600]
  python cf_eq.py eval --platform codeforces --native 800 [--json]
  python cf_eq.py sample [--json]                       # 四站真实题 8 列对照（人工 sanity check）
"""

import argparse
import json
import math
import os
import re
import sys

CF_EQ_VERSION = "CF-EQ-v1.0"

# ---------------------------------------------------------------- 枚举

PLATFORM_CF = "codeforces"
PLATFORM_ATCODER = "atcoder"
PLATFORM_LUOGU = "luogu"
PLATFORM_NOWCODER = "nowcoder"
PLATFORMS = (PLATFORM_CF, PLATFORM_ATCODER, PLATFORM_LUOGU, PLATFORM_NOWCODER)

CONF_HIGH = "HIGH"
CONF_MEDIUM = "MEDIUM"
CONF_LOW = "LOW"

# 训练分带（规格 §5，取值即规格字面量）
BAND_TRIVIAL = "TRIVIAL_CANDIDATE"          # CF-EQ < 1200（v1.0 不自动 SKIP）
BAND_SELECTIVE = "FOUNDATION_SELECTIVE"     # 1200–1399
BAND_FOUNDATION = "FOUNDATION"              # 1400–1599
BAND_CORE = "CORE"                          # 1600–1799
BAND_CORE_HIGH = "CORE_HIGH"                # 1800–1999
BAND_TARGET = "TARGET_APPROACH"             # 2000–2199
BAND_STRETCH = "TARGET_STRETCH"             # 2200–2299（选择性收录）
BAND_DEFER = "DEFERRED_ABOVE_TARGET"        # >= 2300（新默认上界；可显式 override）
BAND_NEED = "NEED_DIFFICULTY"               # 实现新增：无任何难度证据（§5 八档之外）

TRAINING_BANDS = (BAND_TRIVIAL, BAND_SELECTIVE, BAND_FOUNDATION, BAND_CORE,
                  BAND_CORE_HIGH, BAND_TARGET, BAND_STRETCH, BAND_DEFER, BAND_NEED)

# §6：关键边界（跨界的非 HIGH 题标记 BOUNDARY_UNCERTAIN）
KEY_BOUNDARIES = (1200, 1400, 2200, 2300)
DEFER_MIN = 2300
CF_EQ_FLOOR = 800

# 牛客估值证据的默认半宽（实现决策 2；调用方可用 --band 覆盖）
NOWCODER_AI_HALF_WIDTH = 300

# 洛谷官方档位 → (档名, 区间低, 区间高(None=开区间), 代表值)（§3）
LUOGU_LEVELS = {
    1: ("入门", 800, 1000, 900),
    2: ("普及-", 1000, 1300, 1150),
    3: ("普及/提高-", 1300, 1600, 1450),
    4: ("普及+/提高", 1600, 1900, 1750),
    5: ("提高+/省选-", 1900, 2200, 2050),
    6: ("省选/NOI-", 2200, 2500, 2350),
    7: ("NOI/NOI+", 2500, 2800, 2650),
    8: ("超纲", 2800, None, 2900),
}

# 落 meta 的字段（§8 + 本实现新增；additive，不动历史键）
META_FIELDS = (
    "platform", "native_difficulty", "difficulty_source", "cf_eq_version",
    "cf_eq_rating", "cf_eq_band", "cf_eq_confidence", "training_band",
    "difficulty_evidence", "difficulty_override",
    "boundary_uncertain", "boundary_crossed", "boundary_note", "training_band_computed",
)


class CfEqError(Exception):
    """本模块拒绝的操作（不变量守卫）。"""


# ---------------------------------------------------------------- 基础件

def round100_half_up(x):
    """四舍五入到最近 100（.5 向上，中文口径「四舍五入」，不是 banker's rounding）。"""
    return int(math.floor(float(x) / 100.0 + 0.5)) * 100


def band_for_rating(r):
    """CF-EQ 代表值 → 训练分带（规格 §5 区间，左闭右开对齐，整数边界）。"""
    if r is None:
        return BAND_NEED
    if r < 1200:
        return BAND_TRIVIAL
    if r < 1400:
        return BAND_SELECTIVE
    if r < 1600:
        return BAND_FOUNDATION
    if r < 1800:
        return BAND_CORE
    if r < 2000:
        return BAND_CORE_HIGH
    if r < 2200:
        return BAND_TARGET
    if r < DEFER_MIN:
        return BAND_STRETCH
    return BAND_DEFER


def _mid(lo, hi):
    """区间中点（开区间上界 hi=None 时退化为 lo）。"""
    return float(lo) if hi is None else (float(lo) + float(hi)) / 2.0


def band_crosses(band, b):
    """区间 [lo, hi] 是否跨越关键边界 b（§6）。

    判据：存在取值可能落在 b 的两侧 ⟺ lo < b 且 (hi 为空集上界 或 b <= hi)。
    hi=None（如洛谷「超纲」2800+）按正无穷处理。
    """
    if not band:
        return False
    lo, hi = band[0], band[1]
    if lo is None:
        return hi is None or b <= hi
    return lo < b and (hi is None or b <= hi)


def _mk(platform, native, source, rating, band, conf, evidence):
    """组装记录并 finalize（换算函数一律返回自洽记录）。band 用 list；hi=None 表开区间上界。"""
    rec = {
        "platform": platform,
        "native_difficulty": native,
        "difficulty_source": source,
        "cf_eq_version": CF_EQ_VERSION,
        "cf_eq_rating": rating,
        "cf_eq_band": None if band is None else [band[0], band[1]],
        "cf_eq_confidence": conf,
        "difficulty_evidence": list(evidence or []),
        "difficulty_override": None,
        "training_band": None,
        "training_band_computed": None,
        "boundary_uncertain": False,
        "boundary_crossed": [],
        "boundary_note": None,
    }
    return finalize(rec)


def finalize(rec, override=None):
    """补 training_band / 边界不确定性 / override（幂等，可重复调用）。"""
    rating = rec["cf_eq_rating"]
    band = rec["cf_eq_band"]
    notes = []
    if rating is None:
        tier, crossed, uncertain = BAND_NEED, [], False
        notes.append("无难度证据 → NEED_DIFFICULTY（对齐管线 BLOCKED_PENDING_DIFFICULTY 语义，§5 八档之外）")
    else:
        tier = band_for_rating(rating)
        crossed = [b for b in KEY_BOUNDARIES if band_crosses(band, b)]
        uncertain = bool(crossed)
        if uncertain:
            notes.append("cf_eq_band 跨越关键边界 %s → 不能仅用代表值定收录/暂缓（§6）" % crossed)
        # §6：2300 上界处保守——跨界且原判暂缓时，进候选而不是丢弃
        if tier == BAND_DEFER and DEFER_MIN in crossed:
            notes.append("代表值原判 DEFERRED_ABOVE_TARGET，按 §6 保守上调为 TARGET_STRETCH（进候选）")
            tier = BAND_STRETCH
    rec["training_band_computed"] = tier
    rec["boundary_uncertain"] = uncertain
    rec["boundary_crossed"] = crossed
    rec["boundary_note"] = "；".join(notes) if notes else None
    if override and override.get("training_band"):
        rec["training_band"] = override["training_band"]
        rec["difficulty_override"] = dict(override)
    else:
        rec["training_band"] = tier
        rec["difficulty_override"] = None
    return rec


# ---------------------------------------------------------------- 四站换算

def cf_eq_codeforces(native=None, fallback_band=None,
                     fallback_source="CF_DIVISION_POSITION_FALLBACK"):
    """§1：有官方 rating 直用（HIGH）；无官方分只接受显式回退区间（LOW，优先保存区间）。"""
    if native is not None:
        n = int(native)
        return _mk(PLATFORM_CF, n, "CF_OFFICIAL_RATING", n, (n, n), CONF_HIGH,
                   ["官方 Problem Rating 直接采用（§1.1：不做二次换算）"])
    if fallback_band:
        lo, hi = int(fallback_band[0]), fallback_band[1]
        hi_i = None if hi is None else int(hi)
        return _mk(PLATFORM_CF, None, fallback_source, round100_half_up(_mid(lo, hi_i)), (lo, hi_i), CONF_LOW,
                   ["无官方 rating → 调用方给的比赛 division + 题位回退区间（§1.2；只用于粗筛/调度，"
                    "不得覆盖后续官方 rating）"])
    return _mk(PLATFORM_CF, None, "NONE", None, None, CONF_LOW,
               ["无官方 rating 且无回退区间 → 缺难度证据"])


def cf_eq_atcoder(native, source="ATCODER_PROBLEMS"):
    """§2：raw = 0.67 * kenkoooo + 650 → 最近 100；下限钳 800；MEDIUM。"""
    if native is None:
        return _mk(PLATFORM_ATCODER, None, source, None, None, CONF_LOW,
                   ["缺失 kenkoooo difficulty → 缺难度证据"])
    n = int(native)
    raw = 0.67 * n + 650.0
    rating = max(CF_EQ_FLOOR, round100_half_up(raw))
    band = (max(CF_EQ_FLOOR, rating - 100), rating + 100)
    return _mk(PLATFORM_ATCODER, n, source, rating, band, CONF_MEDIUM,
               ["CF-EQ-v1.0 经验训练映射 raw=0.67*%d+650=%.2f → %d（非官方统计等价；带 = 代表值±100）"
                % (n, raw, rating)])


def luogu_level_parse(v):
    """洛谷档位解析：int / "4" / "4（普及+/提高）" / "普及+/提高" → 档位 int；认不出返回 None。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v in LUOGU_LEVELS else None
    s = str(v).strip()
    m = re.match(r"^([1-8])\b", s)
    if m:
        return int(m.group(1))
    for k in LUOGU_LEVELS:
        if s == LUOGU_LEVELS[k][0]:
            return k
    return None


def cf_eq_luogu(level):
    """§3：官方档位 → 区间 + 代表值（LOW；代表值只供排序/粗调度）。"""
    lv = luogu_level_parse(level)
    if lv is None:
        return _mk(PLATFORM_LUOGU, None, "LUOGU_OFFICIAL_LEVEL", None, None, CONF_LOW,
                   ["洛谷档位缺失/认不出（0=暂无评定）→ 缺难度证据"])
    name, lo, hi, rep = LUOGU_LEVELS[lv]
    return _mk(PLATFORM_LUOGU, lv, "LUOGU_OFFICIAL_LEVEL", rep, (lo, hi), CONF_LOW,
               ["洛谷官方难度档 %d（%s）→ 区间 [%s, %s]、代表值 %d（§3：代表值仅供排序/粗调度）"
                % (lv, name, lo, "∞" if hi is None else hi, rep)])


def cf_eq_nowcoder(estimate=None, band=None, evidence=None,
                   half_width=NOWCODER_AI_HALF_WIDTH):
    """§4：无固定映射。证据给区间（LOW）；单值 = 区间中点四舍五入到 100。"""
    ev = list(evidence or [])
    if band:
        lo, hi = int(band[0]), band[1]
        hi_i = None if hi is None else int(hi)
        if estimate is not None:
            ev.append("证据估值 %d（非官方；区间以显式 band 为准）" % int(estimate))
        ev.append("证据区间由调用方给出（§4：不建立题号→CF Rating 固定映射）")
        return _mk(PLATFORM_NOWCODER, None, "NONE", round100_half_up(_mid(lo, hi_i)), (lo, hi_i),
                   CONF_LOW, ev)
    if estimate is not None:
        n = int(estimate)
        lo = max(CF_EQ_FLOOR, n - int(half_width))
        hi = n + int(half_width)
        ev.append("无官方/统计难度：按证据估值 %d 加宽 ±%d（实现常数，待拍板）" % (n, int(half_width)))
        return _mk(PLATFORM_NOWCODER, None, "NONE", round100_half_up(n), (lo, hi), CONF_LOW, ev)
    return _mk(PLATFORM_NOWCODER, None, "NONE", None, None, CONF_LOW,
               ev + ["无任何难度证据 → NEED_DIFFICULTY"])


def evaluate(platform, native_difficulty=None, difficulty_source=None, evidence=None,
             override=None, fallback_band=None, band=None):
    """统一入口：platform + 原始难度/证据 → CF-EQ 记录（含 training_band 与边界标记）。"""
    p = str(platform).strip().lower()
    if p == PLATFORM_CF:
        rec = cf_eq_codeforces(native_difficulty, fallback_band=fallback_band)
    elif p == PLATFORM_ATCODER:
        rec = cf_eq_atcoder(native_difficulty)
    elif p == PLATFORM_LUOGU:
        rec = cf_eq_luogu(native_difficulty)
    elif p == PLATFORM_NOWCODER:
        rec = cf_eq_nowcoder(estimate=native_difficulty, band=band)
    else:
        raise CfEqError("未知平台 %r（可选：%s）" % (platform, "/".join(PLATFORMS)))
    if difficulty_source:
        rec["difficulty_source"] = str(difficulty_source)
    if evidence:
        rec["difficulty_evidence"] = list(rec["difficulty_evidence"]) + [str(e) for e in evidence]
    return finalize(rec, override=override)


# ---------------------------------------------------------------- meta 合并（additive）

def merge_into_meta(meta, rec, allow_overwrite=False):
    """把 CF-EQ 字段**追加**进 meta 副本（纯函数，不写盘；§8 additive migration）。

    · 不碰既有键（difficulty / diff_source / route 等一律原样）；
    · 目标键已存在且值不同 → 默认拒（禁止无审计覆盖）；显式 allow_overwrite 才改。
    """
    out = dict(meta)
    for k in META_FIELDS:
        if k in out and out[k] != rec.get(k) and not allow_overwrite:
            raise CfEqError("meta 已有 %s=%r ≠ 新值 %r；禁止无审计覆盖（§8）"
                            % (k, out[k], rec.get(k)))
        out[k] = rec.get(k)
    return out


# ---------------------------------------------------------------- 自检

def _selftest():
    cases = []

    def case(name, ok, detail=""):
        cases.append((name, bool(ok), detail))

    # ---- §2 参考锚点（逐条） ----
    anchors = [(400, 900), (800, 1200), (1000, 1300), (1200, 1500), (1400, 1600),
               (1600, 1700), (1800, 1900), (2000, 2000), (2200, 2100), (2300, 2200),
               (2400, 2300), (2600, 2400), (2800, 2500)]
    for d, want in anchors:
        got = cf_eq_atcoder(d)["cf_eq_rating"]
        case("anchor: AtCoder %d → CF-EQ %d" % (d, want), got == want, "got %s" % got)

    # ---- AtCoder 换算细节 ----
    r = cf_eq_atcoder(148)
    case("atcoder: 148 → 钳 800（raw 749.16）", r["cf_eq_rating"] == 800
         and r["cf_eq_band"] == [800, 900] and r["cf_eq_confidence"] == CONF_MEDIUM)
    case("atcoder: native 原样保留", r["native_difficulty"] == 148
         and r["difficulty_source"] == "ATCODER_PROBLEMS")
    case("atcoder: 版本号 = CF-EQ-v1.0", r["cf_eq_version"] == CF_EQ_VERSION)
    case("atcoder: 0 → 钳 800", cf_eq_atcoder(0)["cf_eq_rating"] == 800)
    case("atcoder: None → NEED + LOW",
         cf_eq_atcoder(None)["cf_eq_rating"] is None
         and cf_eq_atcoder(None)["cf_eq_confidence"] == CONF_LOW)
    case("round: 四舍五入 .5 向上（1250→1300）", round100_half_up(1250) == 1300)
    case("round: 四舍五入 .5 向上（1350→1400）", round100_half_up(1350) == 1400)
    case("round: 1249.9→1200", round100_half_up(1249.9) == 1200)

    # ---- §1 Codeforces ----
    r = evaluate(PLATFORM_CF, 2200)
    case("cf: 官方 2200 → HIGH + 点区间", r["cf_eq_confidence"] == CONF_HIGH
         and r["cf_eq_band"] == [2200, 2200] and r["cf_eq_rating"] == 2200)
    case("cf: 官方分 = CF-EQ（零换算）", evaluate(PLATFORM_CF, 1234)["cf_eq_rating"] == 1234)
    r = evaluate(PLATFORM_CF, None, fallback_band=(1200, 1600))
    case("cf: 无官方 + 回退区间 → LOW + 中点 1400",
         r["cf_eq_confidence"] == CONF_LOW and r["cf_eq_rating"] == 1400
         and r["cf_eq_band"] == [1200, 1600])
    case("cf: 无官方又无回退 → NEED",
         evaluate(PLATFORM_CF, None)["training_band"] == BAND_NEED)
    case("cf: HIGH 点区间永不 BOUNDARY_UNCERTAIN",
         evaluate(PLATFORM_CF, 2200)["boundary_uncertain"] is False)

    # ---- §3 洛谷（逐档） ----
    lg_expect = {1: (900, [800, 1000]), 2: (1150, [1000, 1300]), 3: (1450, [1300, 1600]),
                 4: (1750, [1600, 1900]), 5: (2050, [1900, 2200]), 6: (2350, [2200, 2500]),
                 7: (2650, [2500, 2800]), 8: (2900, [2800, None])}
    for lv, (rep, bd) in lg_expect.items():
        r = cf_eq_luogu(lv)
        case("luogu: 档 %d → 代表 %d 区间 %s" % (lv, rep, bd),
             r["cf_eq_rating"] == rep and r["cf_eq_band"] == bd
             and r["cf_eq_confidence"] == CONF_LOW and r["native_difficulty"] == lv)
    case("luogu: 字符串 '4（普及+/提高）' 可解析", cf_eq_luogu("4（普及+/提高）")["cf_eq_rating"] == 1750)
    case("luogu: 档名 '普及-' 可解析", cf_eq_luogu("普及-")["cf_eq_rating"] == 1150)
    case("luogu: 档 0（暂无评定）→ NEED", cf_eq_luogu(0)["training_band"] == BAND_NEED)
    case("luogu: 认不出的档 → NEED", cf_eq_luogu("???")["cf_eq_rating"] is None)

    # ---- §4 牛客 ----
    r = cf_eq_nowcoder(estimate=1400)
    case("nowcoder: 估值 1400 → 1200–1700（±300）LOW",
         r["cf_eq_rating"] == 1400 and r["cf_eq_band"] == [1100, 1700]
         and r["cf_eq_confidence"] == CONF_LOW)
    r = cf_eq_nowcoder(band=(1600, 1900))
    case("nowcoder: 显式区间 → 中点 1800（四舍五入 100）",
         r["cf_eq_rating"] == 1800 and r["cf_eq_band"] == [1600, 1900])
    case("nowcoder: 无证据 → NEED", cf_eq_nowcoder()["training_band"] == BAND_NEED)

    # ---- §5 训练分带（边界逐点） ----
    tb = [(800, BAND_TRIVIAL), (1199, BAND_TRIVIAL), (1200, BAND_SELECTIVE),
          (1399, BAND_SELECTIVE), (1400, BAND_FOUNDATION), (1599, BAND_FOUNDATION),
          (1600, BAND_CORE), (1799, BAND_CORE), (1800, BAND_CORE_HIGH),
          (1999, BAND_CORE_HIGH), (2000, BAND_TARGET), (2199, BAND_TARGET),
          (2200, BAND_STRETCH), (2299, BAND_STRETCH), (2300, BAND_DEFER),
          (2500, BAND_DEFER)]
    for r_, want in tb:
        case("band: CF-EQ %d → %s" % (r_, want), band_for_rating(r_) == want)
    case("band: None → NEED", band_for_rating(None) == BAND_NEED)

    # ---- §6 边界不确定性 ----
    case("§6: [1200,1400] 跨 1400", band_crosses([1200, 1400], 1400) is True)
    case("§6: [1400,1600] 不跨 1400（下界即边界）", band_crosses([1400, 1600], 1400) is False)
    case("§6: [1400,1600] 不跨 1200", band_crosses([1400, 1600], 1200) is False)
    case("§6: [2800,∞) 不跨 2300（开区间上界）", band_crosses([2800, None], 2300) is False)
    case("§6: [2200,∞) 跨 2300（开区间上界）", band_crosses([2200, None], 2300) is True)
    r = evaluate(PLATFORM_ATCODER, 969)   # CF-EQ 1300，带 [1200,1400]
    case("§6: ARC C 969 → CF-EQ 1300 带跨 1400 → 标记",
         r["cf_eq_rating"] == 1300 and r["boundary_uncertain"] is True
         and r["boundary_crossed"] == [1400])
    r = evaluate(PLATFORM_ATCODER, 1352)  # CF-EQ 1600，带 [1500,1700]
    case("§6: ARC E 1352 → CF-EQ 1600 不跨关键边界", r["boundary_uncertain"] is False)
    r = evaluate(PLATFORM_LUOGU, 5)       # [1900,2200] 贴上边界 2200
    case("§6: 洛谷档5 [1900,2200] 跨 2200 → 标记", r["boundary_uncertain"] is True
         and r["training_band"] == BAND_TARGET)
    r = evaluate(PLATFORM_LUOGU, 6)       # [2200,2500] 跨 2300，代表 2350 原判 DEFER
    case("§6: 洛谷档6 跨 2300 → 保守上调 TARGET_STRETCH（留痕）",
         r["boundary_uncertain"] is True and r["training_band"] == BAND_STRETCH
         and "保守上调" in (r["boundary_note"] or ""))
    r = cf_eq_nowcoder(band=(2100, 2500))
    case("§6: [2100,2500] 中点 2300 原判 DEFER → 保守 TARGET_STRETCH",
         r["training_band"] == BAND_STRETCH and r["boundary_uncertain"] is True)
    r = cf_eq_nowcoder(band=(2400, 2600))
    case("§6: [2400,2600] 不跨 2300 → 保持 DEFER",
         r["training_band"] == BAND_DEFER and r["boundary_uncertain"] is False)

    # ---- override（留审计） ----
    r = evaluate(PLATFORM_CF, 2400, override={"training_band": BAND_STRETCH, "reason": "用户点名冲"})
    case("override: 生效且原判留痕",
         r["training_band"] == BAND_STRETCH and r["training_band_computed"] == BAND_DEFER
         and (r["difficulty_override"] or {}).get("reason") == "用户点名冲")

    # ---- §8 additive 合并 ----
    meta = {"problem": "D", "difficulty": 1573, "diff_source": "kenkoooo 1573", "vc": "V4"}
    rec = evaluate(PLATFORM_ATCODER, 1573)
    merged = merge_into_meta(meta, rec)
    case("merge: 既有键原样（difficulty 未被覆盖）",
         merged["difficulty"] == 1573 and merged["vc"] == "V4" and merged["problem"] == "D")
    case("merge: CF-EQ 字段就位", merged["cf_eq_rating"] == 1700
         and merged["cf_eq_version"] == CF_EQ_VERSION and merged["training_band"] == BAND_CORE)
    case("merge: 二次相同合并幂等", merge_into_meta(merged, rec) == merged)
    try:
        merge_into_meta(merged, evaluate(PLATFORM_ATCODER, 2000))
        case("merge: 不同值覆盖被拒", False, "没有抛错")
    except CfEqError:
        case("merge: 不同值覆盖被拒", True)
    case("merge: allow_overwrite 显式才改",
         merge_into_meta(merged, evaluate(PLATFORM_ATCODER, 2000),
                         allow_overwrite=True)["cf_eq_rating"] == 2000)

    # ---- §7 与 p3-2 成本路由严格分离（不做混用） ----
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import sched as sched_mod
        case("§7: sched.py 策略未被动过（native 1300）",
             sched_mod.POLICY["dsh_first_max_difficulty"] == 1300
             and sched_mod.POLICY_VERSION == "p3-2")

        def _route(d, oracle="strong"):
            return sched_mod.route({"problem": "X", "difficulty": d, "vc": "V3",
                                    "oracle_strength": oracle}, mode="backlog", budget=5)

        # 路由只看 native：969（CF-EQ 1300）走 DSH；1300（CF-EQ 1300）走 OPENAI
        rc = _route(969)
        re_ = _route(1352)
        rcf = _route(1300)
        case("§7: native 969（CF-EQ 1300）→ LOCAL_DSH（按 native 判）",
             rc["executor_decision"] == "LOCAL_DSH" and rc["execution_state"] == "READY_DSH")
        case("§7: native 1352（CF-EQ 1600）→ OPENAI-first（按 native 判）",
             re_["executor_decision"] == "OPENAI" and re_["execution_state"] == "READY_OPENAI")
        case("§7: 同为 CF-EQ 1300：native 969 → DSH、native 1300 → OPENAI",
             cf_eq_atcoder(969)["cf_eq_rating"] == evaluate(PLATFORM_CF, 1300)["cf_eq_rating"] == 1300
             and rc["executor_decision"] == "LOCAL_DSH" and rcf["executor_decision"] == "OPENAI")
        m1 = {"problem": "X", "difficulty": 1352, "vc": "V3", "oracle_strength": "strong"}
        m2 = merge_into_meta(m1, evaluate(PLATFORM_ATCODER, 1352))
        case("§7: 合并 CF-EQ 字段后 route 输出不变",
             sched_mod.route(m1, budget=5)["executor_decision"]
             == sched_mod.route(m2, budget=5)["executor_decision"]
             and sched_mod.route(m2, budget=5)["execution_state"] == "READY_OPENAI")
    except Exception as e:   # sched.py 不在同目录（独立分发）时跳过，不算失败
        case("§7: sched.py 不在同目录 → 跳过路由实测（%s）" % type(e).__name__, True)

    # ---- 汇总 ----
    bad = [c for c in cases if not c[1]]
    for name, ok, detail in cases:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  [%s]" % detail) if (detail and not ok) else ""))
    print("-" * 60)
    print("cf_eq selftest：%d 项，%d 过，%d 败" % (len(cases), len(cases) - len(bad), len(bad)))
    return 1 if bad else 0


# ---------------------------------------------------------------- 真实题样本

# 四站真实题（Phase 1 人工 sanity check 用；数值均为本机库存/官方数据实核，见 provenance）
_KENKOOOO_CANDIDATES = (
    os.path.join(os.path.expanduser("~"), ".dsh", "tasks", "batch-2026-10", "_run",
                 "problem-models.json"),
)

SAMPLE_ROWS = (
    # (题目标签, 平台, native 键/值, 证据说明, 管线 difficulty（给 route 用）, oracle, vc)
    ("ARC 224 A（Attach 00）", PLATFORM_ATCODER, "arc224_a", None, 148, "strong", "V2"),
    ("ARC 224 C（Ascending Labels）", PLATFORM_ATCODER, "arc224_c", None, 969, "strong", "V3"),
    ("ARC 224 E（ABC|AB|A）", PLATFORM_ATCODER, "arc224_e", None, 1352, "strong", "V3"),
    ("ARC 224 F（AND/OR）", PLATFORM_ATCODER, "arc224_f", None, 2407, "strong", "V3"),
    ("Div.4 1003 D（Skibidus and Sigma）", PLATFORM_CF, None, None, 1200, "strong", "V2"),
    ("Div.4 1003 H（Bro Thinks He's Him）", PLATFORM_CF, None, None, 2200, "strong", "V3"),
    ("Div.2 1112 C（Rank Subsequence）", PLATFORM_CF, None, None, 1300, "strong", "V2"),
    ("Div.2 1112 F（Xor Permutation Matrix）", PLATFORM_CF, None, None, 2300, "strong", "V3"),
    ("基础赛 31 A（红包）", PLATFORM_LUOGU, 1, None, 800, "strong", "V1"),
    ("基础赛 31 B（春运）", PLATFORM_LUOGU, 3, None, 1300, "strong", "V2"),
    ("基础赛 31 C（烟花）", PLATFORM_LUOGU, 4, None, 1600, "strong", "V3"),
    ("周赛 164 A（小红的好数）", PLATFORM_NOWCODER, 800, "题解目录表估值（非官方）", 800, "strong", "V1"),
    ("周赛 164 D（比那名居的桃子）", PLATFORM_NOWCODER, 1500, "题解目录表估值（非官方）", 1500, "strong", "V2"),
    ("周赛 164 G（小红删树 hard）", PLATFORM_NOWCODER, 2000, "题解目录表估值（非官方）", 2000, "strong", "V3"),
)

# CF 官方 rating（2026-10-08 curl problemset.problems 实核；Div2 1112 的 C–F 在 API 中
# 登记于 Div1 2249 的 A–D，同题不同编号——核对时按题名对上）
_CF_OFFICIAL = {
    "Div.4 1003 D（Skibidus and Sigma）": 1200,
    "Div.4 1003 H（Bro Thinks He's Him）": 2200,
    "Div.2 1112 C（Rank Subsequence）": 1300,
    "Div.2 1112 F（Xor Permutation Matrix）": 2300,
}

# AtCoder 归档值（ARC 224 `_work/题单.md`；同时与本机 kenkoooo problem-models.json 一致）
_ATCODER_ARCHIVED = {"arc224_a": 148, "arc224_c": 969, "arc224_e": 1352, "arc224_f": 2407}


def _load_kenkoooo():
    for p in _KENKOOOO_CANDIDATES:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f), p
            except Exception:
                return None, None
    return None, None


def cmd_sample(as_json=False):
    """四站各若干真实题 → CF-EQ 8 列对照（+ 现有 p3-2 route 列做对照）。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sched as sched_mod

    kenk, kenk_path = _load_kenkoooo()
    rows = []
    for label, pf, native_key, note, pipe_diff, oracle, vc in SAMPLE_ROWS:
        if pf == PLATFORM_ATCODER:
            native = None
            if kenk and native_key in kenk:
                native = kenk[native_key].get("difficulty")
            if native is None:
                native = _ATCODER_ARCHIVED[native_key]
            rec = evaluate(pf, native, evidence=["kenkoooo problem-models.json（本机副本实读）"]
                           if kenk else ["归档题单值（本机 kenkoooo 副本不在）"])
        elif pf == PLATFORM_CF:
            native = _CF_OFFICIAL[label]
            rec = evaluate(pf, native, evidence=["CF 官方 problemset API（2026-10-08 实拉核对）"])
        elif pf == PLATFORM_LUOGU:
            rec = evaluate(pf, native_key, evidence=["场次 `_work/题单.md` 官方档位实读"])
        else:
            rec = evaluate(pf, native_key, evidence=[note])
        meta = {"problem": label, "difficulty": pipe_diff, "vc": vc, "oracle_strength": oracle}
        rt = sched_mod.route(meta, mode="backlog", budget=5)
        rows.append({"label": label, "record": rec, "route": rt, "vc": vc, "oracle": oracle,
                     "pipe_diff": pipe_diff})

    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    # 文本表（中文按 2 宽对齐）
    def w(s):
        return sum(2 if ord(ch) > 0x2E7F else 1 for ch in str(s))

    def pad(s, width):
        return str(s) + " " * max(0, width - w(s))

    header = ["题目", "平台", "native", "source", "CF-EQ", "band", "conf", "training_band", "route(p3-2)"]
    table = []
    for r in rows:
        rec = r["record"]
        band = rec["cf_eq_band"]
        btxt = "—" if not band else "[%d, %s]" % (band[0], "∞" if band[1] is None else band[1])
        band_mark = " *" if rec["boundary_uncertain"] else ""
        tb = rec["training_band"]
        if "保守上调" in (rec["boundary_note"] or ""):
            tb += "(§6保守)"
        if rec["difficulty_override"]:
            tb += "(人工)"
        rt = r["route"]
        rtxt = "%s/%s" % (rt["executor_decision"] or "-", rt["execution_state"])
        table.append([r["label"], rec["platform"], rec["native_difficulty"] if rec["native_difficulty"] is not None else "—",
                      rec["difficulty_source"], rec["cf_eq_rating"] if rec["cf_eq_rating"] is not None else "—",
                      btxt + band_mark, rec["cf_eq_confidence"], tb, rtxt])
    widths = [max(w(header[i]), max(w(row[i]) for row in table)) for i in range(len(header))]
    print("  ".join(pad(header[i], widths[i]) for i in range(len(header))))
    print("-" * (sum(widths) + 2 * (len(header) - 1)))
    for row in table:
        print("  ".join(pad(row[i], widths[i]) for i in range(len(header))))
    print()
    print("数据来源：AtCoder = %s" % (kenk_path or "归档题单值（本机 kenkoooo 副本不在）"))
    print("          CF = 官方 problemset API（2026-10-08 实拉；Div2 1112 的 C–F 在 API 中登记于 Div1 2249 A–D）")
    print("          洛谷 = 基础赛 31 `_work/题单.md` 官方档位；牛客 = 题解目录表估值（无官方数据）")
    print("route 列 = `sched.py route`（**p3-2 未改动**）：oracle_strength=strong、mode=backlog、budget=5、")
    print("           difficulty 用各站原生/管线既有值；`*` = BOUNDARY_UNCERTAIN（§6）")
    return 0


def cmd_anchors():
    """打印 §2 的 13 个参考锚点 vs CF-EQ v1.0 公式输出（应与规格逐字一致）。"""
    spec = [(400, 900), (800, 1200), (1000, 1300), (1200, 1500), (1400, 1600), (1600, 1700),
            (1800, 1900), (2000, 2000), (2200, 2100), (2300, 2200), (2400, 2300), (2600, 2400),
            (2800, 2500)]
    ok_all = True
    print("AtCoder 难度 | 规格锚点 | 公式输出 | 一致")
    for d, want in spec:
        got = cf_eq_atcoder(d)["cf_eq_rating"]
        ok = got == want
        ok_all = ok_all and ok
        print("%12d | %8d | %8d | %s" % (d, want, got, "OK" if ok else "MISMATCH"))
    return 0 if ok_all else 1


def _fmt_record(rec):
    band = rec["cf_eq_band"]
    btxt = "—" if not band else "[%d, %s]" % (band[0], "∞" if band[1] is None else band[1])
    lines = [
        "platform        : %s" % rec["platform"],
        "native_difficulty: %s（原样保留，不换算覆盖）" % rec["native_difficulty"],
        "difficulty_source: %s" % rec["difficulty_source"],
        "cf_eq_version   : %s" % rec["cf_eq_version"],
        "cf_eq_rating    : %s" % rec["cf_eq_rating"],
        "cf_eq_band      : %s" % btxt,
        "cf_eq_confidence: %s" % rec["cf_eq_confidence"],
        "training_band   : %s%s" % (rec["training_band"],
                                    "" if rec["training_band"] == rec["training_band_computed"]
                                    else "（原判 %s）" % rec["training_band_computed"]),
        "boundary        : uncertain=%s crossed=%s" % (rec["boundary_uncertain"], rec["boundary_crossed"]),
        "boundary_note   : %s" % (rec["boundary_note"] or "—"),
        "difficulty_override: %s" % rec["difficulty_override"],
        "difficulty_evidence:",
    ]
    lines += ["  - " + e for e in rec["difficulty_evidence"]]
    return "\n".join(lines)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="cf_eq", description="CF-EQ v1.0 四站统一训练难度（训练规划层）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("selftest", help="机器自检（退出码 0 = 全过）")
    sub.add_parser("anchors", help="核对 §2 的 13 个参考锚点")
    s = sub.add_parser("sample", help="四站真实题 8 列对照（人工 sanity check）")
    s.add_argument("--json", action="store_true")

    e = sub.add_parser("eval", help="单题换算")
    e.add_argument("--platform", required=True, choices=PLATFORMS)
    e.add_argument("--native", default=None, help="原生难度：CF rating / kenkoooo / 洛谷档位 / 牛客估值")
    e.add_argument("--band", default=None, help="显式区间，如 1200-1600（牛客/CF 回退用）")
    e.add_argument("--source", default=None, help="覆盖 difficulty_source（留证据用）")
    e.add_argument("--evidence", action="append", default=None)
    e.add_argument("--override-band", default=None, help="人工改训练分带（留审计）")
    e.add_argument("--override-reason", default=None)
    e.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "selftest":
        return _selftest()
    if args.cmd == "anchors":
        return cmd_anchors()
    if args.cmd == "sample":
        return cmd_sample(as_json=args.json)

    # eval
    native = args.native
    if native is not None and str(native).strip() not in ("-", "none", "None", ""):
        try:
            native = int(native)
        except ValueError:
            pass   # 洛谷档位字符串等原样传给换算
    else:
        native = None
    band = None
    if args.band:
        parts = str(args.band).replace("~", "-").split("-")
        parts = [q for q in parts if q.strip() != ""]
        if len(parts) == 2:
            lo, hi = parts
            band = (int(lo), None if hi.strip() in ("+", "inf", "∞") else int(hi))
        else:
            print("--band 格式：lo-hi（如 1200-1600；上界可用 + 表开区间）")
            return 2
    override = None
    if args.override_band:
        override = {"training_band": args.override_band, "reason": args.override_reason or "人工 override"}
    rec = evaluate(args.platform, native, difficulty_source=args.source,
                   evidence=args.evidence, override=override, band=band)
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(_fmt_record(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
