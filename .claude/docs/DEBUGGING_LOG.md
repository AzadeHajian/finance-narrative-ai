# Debugging Log

Running history of bugs investigated in this repo. **Read this before
starting a new debugging session** — the symptom you're seeing may already
be diagnosed (and possibly still open) below.

**After every debugging session, append a new entry** using the template
at the bottom: date, symptom, root cause, fix/status, files touched. This
applies whether or not the issue was actually fixed — "diagnosed but not
fixed yet" is still worth recording so the next session doesn't redo the
investigation.

---

## 2026-06-23 — `ModuleNotFoundError: No module named 'langchain_mcp_adapters'` + VS Code "Error refreshing packages"

**Symptom:** Two related symptoms in the freshly-cloned project:
1. `streamlit run main.py` crashes with
   `ModuleNotFoundError: No module named 'langchain_mcp_adapters'` at
   `mcp_server/client.py -> from langchain_mcp_adapters.client import MultiServerMCPClient`.
2. VS Code's *Python Environments* extension repeatedly shows
   "Error refreshing packages".

**Root cause:** Both have the same root cause — the project's dependencies were
never fully installed into `.venv`. `requirements.txt` (mirrored from sql-agent)
pins no versions, and the broad `langchain` + `langchain-community` +
`langchain-classic` + `langgraph` + `langchain-mcp-adapters` set sent pip into
heavy dependency-resolution **backtracking**. The install ran for ~20+ min
(pip in state `D`, high CPU, no new packages landing) and never reached
`langchain-mcp-adapters`, so the import failed. That same long-running, churning
pip process is also what made VS Code's package refresh fail/time out.

**Fix/status:** **FIXED.** Killed the stuck unpinned install and reinstalled
from the **known-good pinned versions** of the working sibling `sql-agent` venv
(`sql-agent/.venv/bin/pip freeze` → install into this `.venv`). Pinned versions
skip backtracking, so the install completes quickly and consistently. Verified
`pip check` is clean and that `import langchain_mcp_adapters` / `from agent import
SQLAgent` succeed. After the env is stable, VS Code clears "Error refreshing
packages" on a window reload (and selecting `.venv/bin/python` as the interpreter).

**Files involved:** No repo files (environment only). `.venv` reinstalled from a
pinned freeze; `requirements.txt` left unpinned to match sql-agent.

---

## 2026-06-13 — `ModuleNotFoundError: No module named 'tools'`

**Symptom:** `streamlit run main.py` fails with
`ModuleNotFoundError: No module named 'tools'` at
`agent/agent.py:18 -> from tools import SUPABASE_TOOLS`. Same root cause
would also break `python -m mcp_server.server`.

**Root cause:** `agent/agent.py` does `from tools import SUPABASE_TOOLS`
and `mcp_server/server.py` does
`from tools.supabase_tools import (execute_sql, list_tables,
get_table_schema, get_sample_rows)`, but the package in this repo was named
`tool/` (singular) — there was no top-level `tools` package.

**Fix/status:** **FIXED.** Renamed `tool/` → `tools/` via `git mv` (the
internal header comments already said `tools/...`, and nothing else in the
codebase imports `tool.*`, so no other files needed changes). Verified via
WSL venv: `from tools import SUPABASE_TOOLS` and `from agent import
SQLAgent` both import cleanly, and `_get_client()` successfully builds a
Supabase client from the existing `.env` values.

**Files involved:** `tool/` → `tools/` (renamed, contains `__init__.py`,
`supabase_tools.py`). `agent/agent.py` and `mcp_server/server.py` were
already correct and needed no edits.

---

## 2026-06-13 — `_get_client()` error handling

**Symptom:** N/A (proactive change, not triggered by an error) — request
was to verify `SUPABASE_URL` / `SUPABASE_ANON_KEY` are present in `.env`
and wrap `create_client()` in try/except.

**Root cause:** `.env` checked and both `SUPABASE_URL` and
`SUPABASE_ANON_KEY` are present and parse correctly (no trailing-whitespace
issues — python-dotenv strips them). `create_client(url, key)` itself had
no error handling, so any failure there (bad URL format, network issue)
would surface as a raw, unlabeled exception.

**Fix/status:** **FIXED.** `tools/supabase_tools.py::_get_client()` now
wraps `create_client(url, key)` in try/except and re-raises as
`RuntimeError(f"Failed to create Supabase client: {e}")`, consistent with
the error-wrapping style already used in `llm/anthropic_client.py` and
`llm/openai_client.py`.

**Files involved:** `tools/supabase_tools.py`.

---

## 2026-06-13 — Agent says it can't access the list of tables ("configuration or permissions issue")

**Symptom:** Asking the agent anything that requires exploring the database
(e.g. "check all databases i have in supabase") returns a generic apology:
"It seems there is an issue with accessing the list of tables in your
Supabase database. This could be due to a configuration or permissions
issue."

**Root cause:** All 4 tools in `tools/supabase_tools.py` call
`client.rpc("execute_sql", {"query": ...})`, but the Supabase project
(`unsigymegludckhspfpm`) had no `public.execute_sql` Postgres function.
Direct call to `list_tables.invoke({})` returned:
`PGRST202: Could not find the function public.execute_sql(query) in the
schema cache`. The agent's LLM then paraphrased that raw error into the
generic "permissions issue" message shown to the user.

**Fix/status:** **FIXED.** Created `public.execute_sql(query text)` in the
Supabase project via the Management API
(`POST /v1/projects/{id}/database/query`, using `SUPABASE_ACCESS_TOKEN` from
`.env`). First version hit `42601: syntax error at or near ";"` because the
tools' SQL strings end with `;` and the function wraps the query in a
subquery (`from (%s) t`) — a trailing `;` there is invalid. Fixed by stripping
a trailing `;` (`regexp_replace(trim(query), ';\s*$', '')`) before wrapping.
Verified all 4 tools (`list_tables`, `get_table_schema`, `get_sample_rows`,
`execute_sql`) against the live `transaction` table.

**Files involved:** No repo files — this was a Supabase database schema
change (Postgres function + grants). The function's SQL is now documented in
`docs/SETUP.md` under "Database setup" so it can be recreated for a fresh
Supabase project.

---

## 2026-06-13 — Agent refuses to create/populate a table ("I cannot proceed with creating the table directly")

**Symptom:** After the `execute_sql` RPC fix above, asking the agent to
`CREATE TABLE students (...)` and fill it with sample data — even after the
user explicitly confirmed authorization — still failed. The agent said
"the database might have restrictions or specific configurations that are
causing the CREATE TABLE command to fail" and offered to give the user a
script to run manually instead.

**Root cause:** The `public.execute_sql` function created earlier always
wrapped the query as `select coalesce(jsonb_agg(t), '[]'::jsonb) from (%s) t`.
That wrapping is only valid SQL when `%s` is a `SELECT`/`WITH` (something
usable as a `FROM`-subquery). For `CREATE TABLE ...`, `INSERT ...`, etc., it
produced `42601: syntax error at or near "CREATE"`. The agent's LLM
misreported this raw Postgres syntax error as a "restrictions/permissions"
problem and fell back to suggesting the user run it manually — which also
goes against the intended design (the agent should execute SQL itself).

**Fix/status:** **FIXED.**
1. `public.execute_sql` (Supabase Management API, same as before) now
   branches: `SELECT`/`WITH` queries are wrapped as before (returns JSON
   array of rows); everything else is run via plain `execute cleaned` and
   returns `{"status": "ok"}`. Verified `CREATE TABLE`, `INSERT`, `SELECT`,
   and `DROP TABLE` all work, and `list_tables` still works.
2. `agent/prompt.py::task_prompt()` — STEP 5/6 rewritten to explicitly state
   the agent must call `execute_sql()` itself (never tell the user to run
   SQL manually / never refuse on "can't execute directly" grounds), and
   must always show the exact SQL it executed in its response. Also fixed
   stale tool-name references in the prompt (`list_all_tables`/`get_schema`/
   `sample_rows`/`run_sql` → the real tool names `list_tables`/
   `get_table_schema`/`get_sample_rows`/`execute_sql`).

**Files involved:** `agent/prompt.py` (repo). `public.execute_sql` in the
Supabase project (no repo file — SQL documented in `docs/SETUP.md` under
"Database setup").

---

## 2026-06-13 — `ValueError: OPENAI_API_KEY not found in .env` on Streamlit Cloud

**Symptom:** App deployed to Streamlit Community Cloud crashes on startup:
`ValueError: OPENAI_API_KEY not found in .env` at
`llm/openai_client.py:28`, raised from `SQLAgent.__init__` ->
`get_llm("openai")`, called from `main.py:78`.

**Root cause:** All credential lookups go through `os.getenv(...)`
(populated locally by `python-dotenv`'s `load_dotenv()` reading `.env`).
`.env` is gitignored and was never uploaded to Streamlit Cloud, so
`os.environ` had none of these keys. Streamlit Cloud's equivalent is the
"Secrets" dashboard (`st.secrets`), but nothing in the app ever touched
`st.secrets`.

**Fix/status:** **FIXED.** `main.py` now calls
`st.secrets.load_if_toml_exists()` near the top, before `SQLAgent` is
constructed. Per `streamlit/runtime/secrets.py`, the first time
`st.secrets` is parsed it copies every top-level string/int/float secret
into `os.environ` via `_maybe_set_environment_variable` — so as long as the
Streamlit Cloud "Secrets" box contains the same keys as `.env` (as quoted
TOML strings), every existing `os.getenv()` call keeps working unchanged.
`load_if_toml_exists()` swallows `StreamlitSecretNotFoundError` when no
`secrets.toml` exists (i.e. local dev), so this is a no-op locally.
Documented the required Secrets format in `docs/SETUP.md` under "Deploying
to Streamlit Community Cloud".

**Files involved:** `main.py`, `.claude/docs/SETUP.md`.

---

## 2026-06-23 — `NameError` on Streamlit Cloud at `main.py:11` (`_file_`)

**Symptom:** App deployed to Streamlit Community Cloud crashes on startup
with a redacted `NameError`. Traceback points to `main.py`, line 11:
`sys.path.insert(0, os.path.dirname(os.path.abspath(_file_)))`.

**Root cause:** Typo — `_file_` (single underscores) instead of Python's
builtin `__file__` (double underscores). `_file_` is not defined, so
referencing it raises `NameError`.

**Fix/status:** **FIXED.** Corrected `_file_` → `__file__` in `main.py:11`.

**Files involved:** `main.py`.

---

## Template for new entries

```
## YYYY-MM-DD — short symptom description

**Symptom:** what you observed (error message, wrong output, etc.)

**Root cause:** what was actually wrong.

**Fix/status:** what was changed (or "OPEN" if not yet fixed) and why.

**Files involved:** list of files touched or relevant.
```
