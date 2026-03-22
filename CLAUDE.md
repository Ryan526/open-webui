# Open WebUI Fork - Claude Code Instructions

## Commit Rules
- Do NOT add "Co-Authored-By" lines to commit messages.

## Project Overview
This is a fork of [open-webui/open-webui](https://github.com/open-webui/open-webui) with a custom QC (Quality Control) feature added. The QC feature will never be merged upstream — it is maintained exclusively in this fork.

- **Origin:** `Ryan526/open-webui.git` (this fork)
- **Upstream:** `open-webui/open-webui.git` (original project)

## Fork Sync Workflow

When asked to sync with upstream, run:
```
bash scripts/sync-upstream.sh
```

The script handles fetching, backup branches, and merging. If conflicts occur, resolve them keeping both upstream changes and our QC additions.

### Files that will conflict during sync
These are the only shared files our QC commit modifies:
- `backend/open_webui/config.py` — QC permission defaults added to `DEFAULT_USER_PERMISSIONS`
- `backend/open_webui/main.py` — QC router import and `include_router()` call
- `backend/requirements.txt` — pymupdf dependency
- `pyproject.toml` — pymupdf dependency
- `src/lib/components/layout/Sidebar.svelte` — QC nav entry (both collapsed and expanded sections)
- `src/lib/stores/index.ts` — QC store additions

### QC-only files (will never conflict)
- `backend/open_webui/models/qc.py`
- `backend/open_webui/routers/qc.py`
- `backend/open_webui/utils/qc_document.py`, `qc_analysis.py`
- `backend/open_webui/migrations/versions/c3d4e5f6a7b8_add_qc_tables.py`
- `src/lib/apis/qc/`
- `src/lib/components/qc/`
- `src/routes/(app)/qc/`

### Conflict resolution tips
- **config.py**: Our QC additions are at the end of the `DEFAULT_USER_PERMISSIONS["features"]` dict and the `USER_PERMISSIONS_FEATURES_QC` env var block. Keep both upstream's changes and our additions.
- **main.py**: Our additions are a `from open_webui.routers import qc` import and an `app.include_router(qc.router, ...)` call. Keep both.
- **Sidebar.svelte**: Our QC nav entry appears in both the collapsed and expanded sidebar sections. Keep upstream's sidebar changes and re-add our QC block.
- **requirements.txt / pyproject.toml**: Just ensure `pymupdf` stays in the dependency list.
- **Alembic migrations**: If upstream adds new migrations, our `c3d4e5f6a7b8` migration's `down_revision` may need updating to point to the new upstream chain head.

### Post-sync verification
After merging upstream, always **rebuild the Docker image and check container logs** before considering the sync complete. Upstream has shipped yanked/broken dependency pins before (e.g. `ddgs==9.11.2` was removed from PyPI). A successful `git merge` does not guarantee the build works. If `uv pip install` fails on a missing package version, check PyPI for the latest available version and update both `backend/requirements.txt` and `pyproject.toml`.

## Tech Stack
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Frontend:** SvelteKit, TypeScript, Svelte 4 (uses `on:click` not `onclick`)
- **Package type:** `"module"` in package.json (use `.cjs` for CommonJS scripts)
- **Python:** Not directly on PATH on this Windows machine; use node for scripting when needed
