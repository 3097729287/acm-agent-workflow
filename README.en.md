# acm-agent-workflow

**An AI-agent pipeline for competitive-programming upsolving: solutions, verification, and archiving.** It turns "write solutions and forget about them" into a pipeline with machine-checked gates: fetch statements → write code → four-tier verification → render the write-up → format gate → archive reconciliation, plus a status tracker for every problem you upsolve (with a GUI).

[![ci](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml) [![release](https://img.shields.io/github/v/release/3097729287/acm-agent-workflow?include_prereleases&label=release)](https://github.com/3097729287/acm-agent-workflow/releases) ｜ [中文](README.md) ｜ Windows-first (GUI) ｜ Core pipeline CI-green on Ubuntu / macOS / Windows × Python 3.9 / 3.13 ｜ MIT License ｜ Currently **v0.1.0 (early preview)** — feedback welcome via [Issues](https://github.com/3097729287/acm-agent-workflow/issues)

---

## What this is

You compete on NowCoder / Codeforces / Luogu. After the contest you need to upsolve problems, write editorials, and archive algorithm notes — but **nothing enforces quality**: formats drift, verification is hearsay, archiving depends on memory.

This repo hands the whole workflow to an **AI agent** (Claude Code / Codex / anything that can read files and run commands), and **every step has a machine gate** — not "please be careful", but *run this command, check the exit code*:

| Gate | Command | Passing looks like |
|---|---|---|
| Verification | `verify.py` | Four tiers (samples / edge / stress / limits) with real numbers |
| Format | `check_solution.py` | 17 checks, each reporting the offending line |
| Archive | `archive_check.py RoundNNN` | **Exit code 0** = library, indexes and knowledge base all reconcile |
| Demo | `python install.py --check` | Runs the bundled example end-to-end right after install |

## What it solves

- **Fabricated "verification logs"?** Not allowed. Numbers must come verbatim from real runs; tiers you didn't run are honestly marked "unverified". The repo ships a [counter-example](knowledge/11-反面教材.md) (in Chinese): a log that looked real and failed on the first replay.
- **Editorial format drift?** The section whitelist is enforced line-by-line by `check_solution.py`.
- **Re-explaining an algorithm you already covered?** A cross-round ledger tracks what's been taught; repeats get a pointer, first-timers get a from-scratch section.
- **Forgetting your upsolve queue?** Every non-trivial problem lands in `题目状态.md` with a six-state lifecycle; `status_report.py` prints today's queue and a Tkinter GUI edits states with one keypress.
- **Losing files while reorganizing?** Content-hash reconciliation tooling — comparing by filename lies when same-named files overwrite each other.

## Track record

This isn't a slide deck — it's the author's daily pipeline (as of 2026-10-03):

- **9 NowCoder weekly rounds** (Round 123–163) processed through the full six steps; Round 163 (a full round) and Round 161's C–E (a mini round showing the cross-round ledger) ship in this repo's `demo\`;
- **43 problems** moving through the upsolve status table (can't → to-rewrite → reproduced-AC → solved-independently → consolidated);
- **32** four-tier verification drivers, re-runnable with the code;
- **57 archive records** across **31 algorithm folders**.

## Quick start (5 minutes)

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow

python install.py           # writes config.json (points at the bundled demo) + env check + demo gate
```

The check prints Python / g++ / node status and then runs the demo gate — `archive_check.py` reconciling both bundled rounds, **exit code 0**:

```
  Python      3.14.7  OK
  g++         g++ (Rev4, Built by MSYS2 project) 16.2.0  OK
  node        v24.18.1  OK
  == 示例闸门：archive_check.py Round163（自带示例数据）==
  [通过] Round163 退出码 0（0 = 四处对账通过）
  == 示例闸门：archive_check.py Round161（自带示例数据）==
  [通过] Round161 退出码 0（0 = 四处对账通过）
```

(Script output is Chinese — the project is CN-first. g++ and node are optional: without g++ the verification tiers are honestly reported as "unverified"; node only powers the KaTeX math render check.)

<img src="docs/demo-install.gif" width="900" alt="Recorded run of python install.py --check: env check + demo gate, exit code 0">

Then run a full four-tier verification on the bundled examples (a complete round, plus a three-problem mini round, from NowCoder Weekly):

```bash
python demo/题解/牛客周赛/Round163/B-G/B/verify_b.py
python demo/题解/牛客周赛/Round161/A-F/C/verify_c.py
```

```
  编译       通过     通过（无警告）
  官方样例     通过     3 组全过
  边界用例     通过     9 条全过
  随机对拍     通过     500 组全一致
  极限计时     通过     极限：|x|=8×10^5 全零串, k=10^5 0.007 s、极限：|x|=8×10^5 随机十六进制, k=10^5 0.007 s
```

Tier names: compile / samples / edge cases / stress test / time limits — all PASS. (Output above is verbatim from a real run; timings vary by machine.)

<img src="docs/demo-verify.gif" width="900" alt="Recorded run of verify_b.py: compile / samples / edge / stress / limits — all PASS">

## Tutorial: run one full round

### Step 0 — point your agent at the rules

Open this repo in Claude Code (or any agent) and say:

> Read AGENTS.md at the repo root, then process this contest: `https://ac.nowcoder.com/acm/contest/<id>`

`AGENTS.md` is the rule backbone (10 laws + an index table); details live in `knowledge\` (14 docs, in Chinese) and are read on demand.

### The six-step pipeline

| Step | Command (the agent runs these) | Output | Gate |
|---|---|---|---|
| 1. Fetch | `python tools/fetch_problem.py <URL>` | statements + sample tables + difficulty suggestions | fetched count == problem count |
| 2. Calibrate | (agent checks the "already taught" ledger) | what to explain, how deep | — |
| 3. Code | one folder per problem `RoundN\<range>\<letter>\` | `x.cpp` + brute force + `verify_x.py` | — |
| 4. Verify | `python verify_x.py` | four tiers of real numbers | all pass, numbers from real runs |
| 5. Write-up + self-check | `python tools/check_solution.py <md>` | `RoundN题解.md` | 17/17 checks |
| 6. Re-verify + archive | `md_full.py` → `archive_check.py RoundN` | library records / indexes / status table | **exit code 0** |

<img src="docs/demo-gates.gif" width="900" alt="Recorded run of check_solution.py: 17 checks, all clear">

Layout of one self-contained round:

```
<data-root>\
├── 题解\牛客周赛\RoundN\        <- in demo: Round163 (full) + Round161 (C~E mini round)
│   ├── RoundN题解.md            <- the deliverable editorial
│   ├── <range>\<letter>\        <- per problem: solution + brute + verify driver (+ viz scripts)
│   └── _work\                   <- disposables (statements/samples), regenerable
├── 算法\                        <- archive: one condensed record per problem, grouped by algorithm
├── 索引\题解算法索引.md          <- full index (round sections are script-generated)
└── 题解\题目状态.md              <- upsolve status table
```

### Use your own data root

```bash
python install.py --new-data D:\my-cp       # scaffold: folders + template + empty index/status table
python install.py --data-root D:\my-cp      # point config.json at it
```

### The upsolve status tracker

```bash
python tools/status_report.py    # today's queue: to-rewrite / to-upsolve / D+7 review / D+30 spot check
python tools/status_gui.py       # Tkinter GUI
```

GUI keys: `1`-`6` set state ｜ `Enter` popup ｜ `Ctrl+Z` undo ｜ `Shift+Enter` open the original problem ｜ `F11` fullscreen. Only the target row is touched; every write is backed up first.

<img src="docs/demo-gui.gif" width="900" alt="Recorded run of status_gui.py: number keys change the state, Ctrl+Z undoes, the problem page and the archive record open">

## Tools

| Script | Purpose |
|---|---|
| `install.py` | Setup: config.json / env check / scaffold a new data root |
| `fetch_problem.py` | Fetch NowCoder statements + sample tables (auto-detects round number) |
| `new_round.py` | New-round skeleton (folders + markdown shell; idempotent, never overwrites) |
| `verify.py` | Four-tier verification driver |
| `md_full.py` | Pre-delivery re-verification of the code **as pasted in the editorial** |
| `check_solution.py` | 17-check format gate for the editorial |
| `archive_check.py` | Archive reconciliation, **exit 0 = done** |
| `index_sync.py` | Generates index tables from record files (single source of truth) |
| `status_report.py` / `status_gui.py` / `fill_knowledge.py` | Status-table trio (report / GUI / knowledge column) |
| `vizgrid.py` | Terminal character-art engine for algorithm diagrams |
| `unify_latex.py` / `unpair_ticks.py` / `extract_math.py` + `katex_check.js` | LaTeX trio (convert / clean / render-check) |
| `check_lost_by_hash.py` | Content-hash reconciliation after file moves |

Full reference (design trade-offs and traps): [knowledge/10-工具链.md](knowledge/10-工具链.md) (Chinese).

## Knowledge base (`knowledge\`, 14 docs, Chinese)

Covers the pipeline definition, editorial format + LaTeX rules, the verification protocol, archiving + the cross-round "already taught" ledger, runnable character-art diagrams, from-scratch explanation rules, a falsified verification-log post-mortem, an algorithm pitfall collection, environment setup, and NowCoder scraping notes.

## Configuration (config.json)

```json
{
  "data_root": "./demo",        // data root: editorials / archive / indexes / status table
  "backup_root": "./.backups",  // backups made before every file edit
  "desktop_copy_dir": null      // optional desktop copy of the editorial; null = off
}
```

No hard-coded paths: set `AGENT_CP_TOOLS` / `AGENT_CP_CONFIG` to relocate the toolchain or config.

## FAQ

**Do I need Claude Code?** No — any agent that can read files and run commands works (Codex / Cursor / your own). `AGENTS.md` is written for them. Humans can follow the six steps manually too.

**No g++ / node?** Fine. Without g++ the verification tiers are honestly reported as "unverified"; node only powers the KaTeX render check (that item reports "N/A").

**Non-Windows?** The core pipeline is CI-green on Ubuntu / macOS / Windows × Python 3.9 / 3.13 (badge above): env check, demo gate, index sync, four-tier re-verification and the 17-check format gate all run on Linux/macOS. The Tkinter GUI and some `.cmd` helpers are Windows-oriented. All paths come from config.

**KaTeX render check:** `cd tools && npm install katex` (optional).

## Design principles

1. **Machine gates over pep talks** — every key claim maps to an exit code.
2. **Never fabricate conclusions** — logs come from real runs; unrun tiers say "unverified".
3. **Single source of truth** — index tables are generated from record files, never hand-edited.
4. **Keep the evidence** — post-mortems and traps are archived, not forgotten.
5. **Disposables vs. assets** — build artifacts are trash; `.cpp` / `.py` / `.md` are deleted only when their owner says so.

## Bundled example

`demo\` holds two rounds: NowCoder Weekly 163, problems B–G (a complete round — editorial, per-problem code, verify drivers where B shows the framework-style `verify_b.py` and F is a self-contained script), and Round 161's C–E (a mini round whose three problems all use framework-style drivers). Together: nine archive records, indexes, status table. Both `install.py --check` and `archive_check.py Round163` / `Round161` run against it.

The second round is not padding: it demonstrates the **cross-round ledger** — once a second round lands in the same algorithm folders, 《已讲过概念清单》 must register newly taught concepts with "first appearance = the earliest round" and strike the entries that were finally taught (`knowledge\09-已讲过概念清单.md` shows the real wording).

A deliberately broken counterpart ships in `examples\`: the same format gate flags it with eight red items and exit code 1 — run it once and you can see exactly what the gate catches.

## Contributing

Issues and PRs welcome. Before changing a script, run its self-test (`--help` on most; `status_gui.py --selftest` and `selfcheck_unpair.py` are ready-made regressions). Note that `verify_<letter>.py` drivers have **no `--help`** — running one with no arguments *is* the verification.

## License

[MIT](LICENSE)
