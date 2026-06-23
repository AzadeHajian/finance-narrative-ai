# Finance Quarterly Report — Claude Project Guide

Finance Quarterly Report is a Streamlit app where a LangGraph ReAct agent (Claude or GPT-4o)
reads an impact-investment portfolio database in Supabase and drafts short, neutral
narrative summaries of a company's quarterly performance (revenue, headcount, ESG).
Every answer is a JSON draft for human review (`summary` + `data_used` + `flags`) and
is never auto-published.

This file is an index. Detailed docs live in `.claude/docs/`:

- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — folder-by-folder breakdown of the codebase
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the pieces connect (data flow, providers, MCP)
- [docs/SETUP.md](docs/SETUP.md) — env vars, install, how to run the app and MCP server
- [docs/DEBUGGING_LOG.md](docs/DEBUGGING_LOG.md) — running log of bugs found/fixed (read before debugging)

## Working agreement for Claude in this repo

1. **Before debugging anything**, check `docs/DEBUGGING_LOG.md` for prior
   investigations of the same symptom — don't re-diagnose something already
   solved (or already known-and-open).
2. **After every debugging session** (whether you fixed it or just diagnosed
   it), append an entry to `docs/DEBUGGING_LOG.md`: date, symptom, root
   cause, fix/status, files touched. Do this before ending the turn.
3. If the fix changes how the project is structured, run, or configured,
   also update `docs/PROJECT_OVERVIEW.md`, `docs/ARCHITECTURE.md`, or
   `docs/SETUP.md` as appropriate.
4. Never write real secret values (API keys, tokens) into any doc — `.env`
   is gitignored and holds the real credentials. Docs should only reference
   variable *names*.

## Known open issues

None currently open. See `docs/DEBUGGING_LOG.md` for resolved history.
