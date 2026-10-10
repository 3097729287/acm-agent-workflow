# TB development rules

TB is the primary product. Active code belongs in `frontend/`, `backend/`, `desktop/`, and `server/leaderboard/`.

- Read `docs/architecture.md` before changing storage, API boundaries, or packaging.
- Back up existing files before editing. Keep backups outside source directories, in `.backups/`. Verify moved source files by SHA-256.
- Keep the original educational archive and users' live installations read-only during development. Use temporary state for every test. Set `TB_OFFLINE=1` unless a test supplies its own local service.
- SQLite is the persistent storage for library content, personal progress, and settings/cache documents. Markdown is a rendering/interchange format. Never reintroduce filesystem-dependent solution lookup.
- Preserve code, identities, records, API keys, and local imports during migration or upgrade. Back up existing databases with SQLite's online backup API, including committed WAL content. Never replace a personal database with a bundled file.
- Share only public educational data. Distributed content must have no developer progress, credentials, cookies, or absolute machine paths. Translation keys remain protected with DPAPI on Windows.
- Preserve original site login, CSRF, and submit behavior. Compiler adapters act on actual language controls and use native form events. Do not perform account submissions merely to test an adapter.
- API write requests require the session token. Cross-origin access requires an explicit frontend origin; keep the default local-origin guards.
- After backend changes run `python scripts/check.py`. After UI changes run the frontend build and relevant Playwright tests. Run shared-service tests after Worker changes. Packaging requires fresh-install and upgrade checks against disposable state.
- Every version or PR update must also be visible in the user's designated local project directory. Save the corresponding source snapshot and update the local version index with its commit, status, validation, and actual startup entry. Distinguish pending PRs, merged code, local builds, and published releases. State explicitly when an update has not been packaged; retain the last runnable version and change the latest shortcut only after isolated validation.
- Report actual checks and limitations. Never claim real official submission or provider success from a fixture. Do not publish releases, deploy services, or merge a PR unless authorized in the conversation.
