# acm-agent-workflow

**An upsolving pipeline for competitive programming — from fetching the statement to archiving the write-up, driven end-to-end by an AI agent, with a machine gate at every step.**

Not "please be careful, agent" — **run one command, read the exit code**: every measured number comes verbatim from a real run, the editorial format is checked item by item (17 checks), and archiving only counts as done when the reconciliation exits 0. You just review.

[![ci](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/3097729287/acm-agent-workflow/actions/workflows/ci.yml) [![release](https://img.shields.io/github/v/release/3097729287/acm-agent-workflow?include_prereleases&label=release)](https://github.com/3097729287/acm-agent-workflow/releases) ｜ [中文](README.md) ｜ [Online docs](https://3097729287.github.io/acm-agent-workflow/) ｜ [MIT](LICENSE) ｜ **v0.1.0 (early preview)** — feedback welcome via [Issues](https://github.com/3097729287/acm-agent-workflow/issues)

---

## Pick a path

| Who you are | Start here | Takes |
|---|---|---|
| **Competitive programmer** — just want to use it, no agent involved | [**Path A: Just use it**](#path-a-just-use-it) | 3 minutes |
| **You have an AI agent** (Claude Code / Codex / Cursor…) | [**Path B: Hand it to an agent**](#path-b-hand-it-to-an-ai-agent) | one sentence |
| **Contributing an editorial / wiring up CI / hacking on the code** | [**Path C: Contribute and develop**](#path-c-contribute-and-develop) | as needed |
| Just want to know **why it's trustworthy** | [The four gates](#why-its-trustworthy-four-gates) | 1 minute |

## Path A: Just use it

**No Python needed (Windows):** grab `TimuZhuangtai-v0.1.0-win64.zip` from [Releases](https://github.com/3097729287/acm-agent-workflow/releases), unzip it, double-click `TimuZhuangtai.exe`.

One window manages your problem-status table: today's upsolving queue, `1`~`6` to change a status (every write is backed up first), import/export solution packs. A sample dataset ships inside, so it works out of the box; to point it at **your own** data, edit `config.json` inside the folder (three fields, see [Configuration](#configuration-configjson)).

**With Python 3.9+ (Windows / macOS / Linux):**

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow
python install.py                # environment check + runs every gate against the bundled sample
python tools/status_report.py    # today's queue: ①to-rewrite ②to-upsolve ③review ④spot-check
python tools/status_gui.py       # the GUI
```

`status_report.py` can also filter: `--todo --knowledge DP` (DP problems you haven't cracked yet), `--status 未做,不会 --difficulty 1200-1600`.

GUI keys: `1`~`6` set status ｜ `Enter` overlay ｜ `Ctrl+Z` undo chain ｜ `Shift+Enter` open the problem page ｜ `F11` fullscreen ｜ `↓` in the search box opens the filter panel. Only the targeted row is touched, invalid states are refused.

Want to build your own exe (same code as the CLI — `TimuZhuangtai.exe --pack-check pack.zip` also works): see [docs/打包图形端exe.md](docs/打包图形端exe.md) (Chinese).

<img src="docs/demo-gui.gif" width="900" alt="Recorded run of status_gui.py: number keys change the state, Ctrl+Z undoes, the problem page and the archive record open">

> Want an agent to **write** the editorials and run the verification? Go to Path B.

## Path B: Hand it to an AI agent

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cd acm-agent-workflow
python install.py      # needs only Python 3.9+, zero third-party packages; g++ / node optional
```

Open this directory with your agent (with Claude Code, just `cd` into it) and say one sentence:

> Read AGENTS.md at the repo root, then process this contest: `https://ac.nowcoder.com/acm/contest/<id>`

(A whole-contest Luogu URL works the same way.) It walks the six steps by itself:

**fetch statement → calibrate depth → write code + verification driver → four-tier verification → write editorial + 17-item self-check → re-verify + archive reconciliation**

You only look at two things: **the measured numbers it reports** (they must come verbatim from a real run) and **exit code 0**.

<img src="docs/demo-install.gif" width="900" alt="Recorded run of the installer: env check + sample gates, exit code 0">

What each step leaves on disk: see [What a finished round leaves on disk](#what-a-finished-round-leaves-on-disk).

**Point it at your own data** (the default data root is the bundled sample `demo\`):

```bash
python install.py --new-data D:\my-cp     # scaffold your own data root (folders + template + empty index/status table)
python install.py --data-root D:\my-cp    # point config.json at it
```

## Path C: Contribute and develop

**Send in one round's editorial.** Export a solution pack first:

```bash
python tools/export_solution.py Round163     # -> 牛客周赛Round163.zip
```

| Your situation | How to send it |
|---|---|
| You know git | fork → drop the zip into `contributions\` → open a PR; CI validates each pack for you |
| You don't know git | Add the maintainer on QQ **3660535264** (note "题解投稿") and send the zip; or attach it to an [Issue](https://github.com/3097729287/acm-agent-workflow/issues) |
| Can't even export a pack | Send the editorial markdown + source files as they are; the maintainer packs them for you |

All three routes **go through the same importer and the same validation, and your credit is kept**. Details in [CONTRIBUTING.md](CONTRIBUTING.md) (Chinese).

**Hang the format gate on your own repo** (GitHub Action — a failing editorial turns your CI red):

```yaml
- uses: actions/checkout@v4
- uses: 3097729287/acm-agent-workflow@main
  with:
    path: 'editorials/**/*.md'   # which markdown files are editorials is up to you (multiple / dirs / globs)
```

Your repo does not have to look like this one. Inputs, exit codes and graceful degradation are documented in [docs/格式闸Action.md](docs/格式闸Action.md) (Chinese), along with how to dry-run it locally.

**Just want the editorial QC skill** (Claude Code):

```bash
git clone https://github.com/3097729287/acm-agent-workflow
cp -r acm-agent-workflow/skills/check-solution ~/.claude/skills/
```

Then say "run the editorial QC on 我的题解.md": 17 format checks, every complaint carries a line number and the offending sentence. See [skills/check-solution/README.md](skills/check-solution/README.md) (Chinese).

**Hacking on the code**: run the matching self-test first (most scripts take `--help`): `status_gui.py --selftest`, `selfcheck_filter.py`, `selfcheck_import.py`, `check_contributions.py`, `knowledge_dict.py selftest`, `fetch_problem.py --selftest`. Note that `verify_<letter>.py` drivers have **no `--help`** — running one with no arguments *is* the verification.

## Why it's trustworthy: four gates

| Gate | Command | Passing means |
|---|---|---|
| Verification | `verify_<letter>.py` | Four tiers (samples / edge cases / stress test / time limits) each report **measured numbers** |
| Format | `check_solution.py <md>` | All 17 checks pass, each reporting the offending line and sentence |
| Archive | `archive_check.py RoundNNN` | **Exit code 0** = algorithm library, indexes and knowledge base all reconcile |
| Install | `python install.py --check` | Runs every gate against the bundled sample (check only — writes nothing) |

Two hard rules: **no fabricated logs** — a tier you didn't run says "unverified", and the repo ships a [counter-example](knowledge/11-反面教材.md) (Chinese): a log that looked completely real and failed on the very first replay; **no hand-edited indexes** — index tables are generated from the record files (`index_sync.py`), a single source of truth.

## What ships in the box

`demo\` holds two **real** rounds: NowCoder Weekly Round 163 (a full round) and Round 161's C~E (a mini round demonstrating the cross-round ledger). Clone it and run:

```bash
python demo/题解/牛客周赛/Round163/B-G/B/verify_b.py
```

```
  编译       通过     通过（无警告）
  官方样例     通过     3 组全过
  边界用例     通过     9 条全过
  随机对拍     通过     500 组全一致
  极限计时     通过     极限：|x|=8×10^5 全零串, k=10^5 0.007 s、极限：|x|=8×10^5 随机十六进制, k=10^5 0.007 s
```

Tier names: compile / samples / edge cases / stress test / time limits — all PASS. (Output above is verbatim from a real run; timings vary by machine. Script output is Chinese — the project is CN-first.)

<img src="docs/demo-verify.gif" width="900" alt="Recorded run of verify_b.py: compile / samples / edge / stress / limits — all PASS">

`examples\` carries a **deliberately broken editorial**: the same format gate flags it with eight red items and exit code 1 — run it once and you see exactly what the gate catches.

This is not a slide deck — it's the author's daily pipeline: **9 NowCoder weekly rounds** through the full six steps, **43 problems** moving through the status table, **57 archive records** across **31 algorithm folders** (as of 2026-10-03).

---

# Technical reference

## What a finished round leaves on disk

| Step | What the agent runs | Output | Gate |
|---|---|---|---|
| 1. Fetch | `python tools/fetch_problem.py <URL>` (NowCoder / Luogu) | statements + sample tables + difficulty suggestions under `RoundN\_work\` | fetched count == problem count |
| 2. Calibrate | consults the "already taught" ledger + the tier table | what to explain, how deep | — |
| 3. Code | one folder per problem `RoundN\<range>\<letter>\` | `x.cpp` + brute force + `verify_x.py` | — |
| 4. Verify | `python verify_x.py` | four tiers of real numbers | all pass, numbers from real runs |
| 5. Write-up + self-check | `python tools/check_solution.py <md>` | `RoundN题解.md` | 17/17 checks |
| 6. Re-verify + archive | `python tools/md_full.py <md> <letter>` → `archive_check.py RoundN` | library records / indexes / status table | **exit code 0** |

<img src="docs/demo-gates.gif" width="900" alt="Recorded run of check_solution.py: 17 checks, all clear">

One round, one self-contained folder:

```
<data-root>\
├── 题解\牛客周赛\RoundN\
│   ├── RoundN题解.md            <- the deliverable editorial
│   ├── <range>\<letter>\        <- per problem: solution + brute + verify driver (+ viz scripts)
│   └── _work\                   <- disposables (statements/samples), regenerable
├── 算法\                        <- archive: one condensed record per problem, grouped by algorithm
├── 索引\题解算法索引.md          <- full index (round sections are script-generated)
└── 题解\题目状态.md              <- upsolve status table
```

## Solution packs: export / import

A solution pack is a portable bundle of one round's editorials plus its archive records; pack files round-trip byte-for-byte (`selfcheck_import.py` is the gate that proves it).

```bash
python tools/export_solution.py Round163              # -> 牛客周赛Round163.zip
python tools/export_solution.py Round163-G -o G.zip   # single problem

python tools/import_solution.py 牛客周赛Round163.zip          # validate only (no writes)
python tools/import_solution.py 牛客周赛Round163.zip --apply  # write + wire up + reconcile
```

What `--apply` chains: copy files → back-index rows → editorial pointers → status table rows (new problems default to "not done") → generated index sections → knowledge column → **`archive_check.py` exit code 0**. Exit code 0 is the finish line — "the files were copied" is not.

Two rules worth calling out: **knowledge-point names have a single dictionary** (`knowledge\15-知识点词典.md`) — the same concept written two ways (`状态压缩DP` ≡ `状压 DP`) is normalized on both export and import, so the index never splits one concept into two columns; and **unknown names are accepted, not rejected** — only hard failures bounce (missing fields, unparseable file names, format-gate failures, overwriting existing files), while an unregistered name is written as-is and listed in a "to-register" report.

Prefer not to touch the CLI: the GUI menu has **Import pack… / Export pack… / Validate…** — pick a pack, get a report, and only "apply to data root" actually writes.

## Tools

| Script | Purpose |
|---|---|
| `install.py` | Setup: config.json / env check / scaffold a new data root |
| `fetch_problem.py` | Fetch statements + sample tables: NowCoder (whole round, auto-detects the round number) / Luogu (whole round or a single problem); `--selftest` replays the parsing chain offline |
| `new_round.py` | New-round skeleton (folders + markdown shell; idempotent, never overwrites) |
| `verify.py` | Four-tier verification driver: compile → samples → edge cases → stress test → time limits |
| `md_full.py` | Pre-delivery re-verification of the code **as pasted in the editorial** |
| `check_solution.py` | The 17-check format gate for the editorial (line number + offending sentence per complaint) |
| `archive_check.py` | Archive reconciliation, **exit 0 = done** |
| `index_sync.py` | Generates index tables from record files (single source of truth) |
| `status_report.py` / `status_gui.py` / `fill_knowledge.py` | Status-table trio (report + filtering / GUI / knowledge column) |
| `selfcheck_filter.py` | Machine gate for the filter logic (28 unit assertions + 20 end-to-end result-set comparisons) |
| `export_solution.py` / `import_solution.py` | Solution packs: export a round (or one problem) / import someone else's |
| `knowledge_dict.py` | Knowledge-point dictionary: canonical names, aliases, suggestions |
| `selfcheck_import.py` | Gate for import/export (round-trip losslessness + unknown names accepted) |
| `check_contributions.py` | Validates every pack in `contributions\` inside a throwaway data root (runs in CI) |
| `skills/check-solution` | Editorial QA skill: packages the 17-check format gate as "clone and use" |
| `vizgrid.py` | Terminal character-art engine for algorithm diagrams |
| `unify_latex.py` / `unpair_ticks.py` / `unpair_ticks_relaxed.py` / `extract_math.py` + `katex_check.js` | LaTeX tooling (convert / strip backticks / render-check) |
| `check_lost_by_hash.py` | Content-hash reconciliation after file moves (comparing by filename lies) |
| `lfcheck.py` | Line-ending / BOM normalization check |

Full reference (design trade-offs and traps): [knowledge/10-工具链.md](knowledge/10-工具链.md) (Chinese).

## Configuration (config.json)

```json
{
  "data_root": "./demo",        // data root: editorials / archive / indexes / status table
  "backup_root": "./.backups",  // backups made before every file edit
  "desktop_copy_dir": null      // optional desktop copy of the editorial; null = off
}
```

No hard-coded paths: set `AGENT_CP_TOOLS` / `AGENT_CP_CONFIG` to relocate the toolchain or the config.

## Knowledge base

`knowledge\` holds the rule details (16 documents, Chinese); the root `AGENTS.md` keeps only the trunk and the agent reads details on demand.

Covers the pipeline definition, editorial format + LaTeX rules, the verification protocol, archiving + the cross-round "already taught" ledger, runnable character-art diagrams, from-scratch explanation rules, a falsified verification-log post-mortem, an algorithm pitfall collection, environment setup, NowCoder and Luogu scraping notes (including how to treat prompt-injection text found in statements), and the knowledge-point dictionary (the single source of truth for concept names).

## Platforms and CI

The core pipeline is CI-green on three platforms (Ubuntu / macOS / Windows × Python 3.9 / 3.13): env check, sample gates, index sync, dictionary self-test and scraping self-test run on all six cells; four-tier re-verification, the 17-check format gate (with KaTeX rendering), the counter-example assertion and the Action entry's three exit codes run on Linux + 3.13; solution-pack round-trip and contribution validation run on Linux / Windows + 3.13.

The Tkinter GUI and some `.cmd` helpers are Windows-oriented; on Linux, install `python3-tk` if the GUI complains about tkinter. All paths come from config.

## FAQ

**Do I need Claude Code?** No — any agent that can read files and run commands works (Codex / Cursor / your own). `AGENTS.md` is written for them. Humans can follow the six steps manually too.

**No g++ / node?** Fine. Without g++ the verification tiers are honestly reported as "unverified"; node only powers the KaTeX render check (that item reports "N/A"). Install: `cd tools && npm install katex` (optional).

**Is my data uploaded anywhere?** No. The data root lives on your machine and the repo only ships the sample. Network access happens only when fetching statements (NowCoder / Luogu) and in the optional KaTeX rendering.

## Design principles

1. **Machine gates over pep talks** — every key claim maps to an exit code; "I'm pretty sure it's fine" is not a result.
2. **Never fabricate conclusions** — logs come from real runs; unrun tiers say "unverified".
3. **Single source of truth** — index tables are generated from record files, never hand-edited.
4. **Keep the evidence** — post-mortems and traps are archived, not forgotten.
5. **Disposables vs. assets** — build artifacts are trash; `.cpp` / `.py` / `.md` are deleted only when their owner says so.

## Repository layout

```
acm-agent-workflow\
├── AGENTS.md            <- rule trunk for AI agents (11 iron rules)
├── README.md / README.en.md
├── CONTRIBUTING.md      <- how to contribute a round's editorial (three routes / pack format)
├── install.py           <- installer (config.json / env check / new data root)
├── config.example.json
├── knowledge\           <- rule details (16 docs)
├── tools\               <- every script
├── templates\           <- verify-driver template
├── skills\              <- check-solution: the editorial QC gate (copy into ~/.claude/skills/)
├── docs\                <- format-gate Action / exe packaging / GUI layout names + the docs site
├── contributions\       <- contribution inbox (drop a pack, open a PR, CI validates)
├── 题库\                <- the release data root (same layout as demo\)
├── examples\            <- runnable counter-example (deliberately broken editorial) + Luogu scraping fixtures
└── demo\                <- bundled sample data (Round 163 full + Round 161 C~E)
```

## Contact and contributions

- **QQ: 3660535264** (note "题解投稿") — the easiest way to send an editorial: drop the zip produced by `export_solution.py` into the chat. Can't export? Send the markdown and source files as they are and the maintainer will pack them. Questions, bug reports and suggestions are welcome too.
- Prefer not to add QQ? [Issues](https://github.com/3097729287/acm-agent-workflow/issues) / PRs work as always.

## License

[MIT](LICENSE)
