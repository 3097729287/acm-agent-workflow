# TB · Training Workbench

TB brings competitive programming problems, editorials, C++ editing, local judging and training records into one desktop workspace. It supports Nowcoder, Codeforces, AtCoder and Luogu.

[Download](https://github.com/3097729287/acm-agent-workflow/releases) · [中文](README.md) · [Architecture](docs/architecture.md) · [Development](docs/development.md)

![TB workbench](docs/assets/workbench.png)

The Windows installer includes the Python runtime, C++ toolchain and offline WebView2 installer. Extract the entire portable ZIP; it requires an existing WebView2 runtime.

The bundled SQLite library contains 607 problems, 607 editorials and 378 foundation lessons. It works without the developer's Markdown archive. Newly discovered public problems may have no editorial yet. Foundation links come from the current problem and explicit references, rather than every lesson sharing a tag.

Use **Run** for samples, **Local submit** for available local tests, and **Official submit** for the original site's authenticated submission form. Sample passes, reviewed local passes and official results are tracked separately. Daily missions, practice recommendations and knowledge coverage use actual training evidence.

The API starts independently of the React frontend. `frontend/` contains the UI, `backend/` owns HTTP and SQLite, `desktop/` owns the native shell and official-site adapters, and `server/leaderboard/` contains the Cloudflare Worker + D1 service. The earlier workflow is preserved under `legacy/` and is excluded from application builds.

The shared ranking client defaults to https://tb-leaderboard.fsxxxg.workers.dev/. It sends only identity/nickname and summaries of first reviewed local passes. Code, drafts, provider keys and site cookies stay local. Translation supports DeepSeek and custom compatible APIs, preserves code/math/examples, and includes a connection test.

Upgrades preserve personal records and identities, encrypted settings and local imports. Legacy JSON settings migrate once to SQLite without deleting the original files. See [usage](docs/usage.md), [migration](docs/architecture.md#数据与迁移), and [contributing](CONTRIBUTING.md).

```powershell
python backend/backend.py --offline
# In another terminal
cd frontend
npm ci
npm run dev
```

The repository URL remains `acm-agent-workflow`; TB is the primary product. Application source is MIT licensed. See [third-party notices](THIRDPARTY.md) for distributed components.
