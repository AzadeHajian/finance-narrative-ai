# Setup & Running

## Requirements
- Python 3.10 (matches `.venv/lib/python3.10`)
- A Supabase project with a Postgres RPC function called `execute_sql`
  (callable as `client.rpc("execute_sql", {"query": "..."})`) — required by
  every tool in `tools/supabase_tool.py`. See "Database setup" below.

## Database setup

Run this once in the Supabase SQL Editor for the project (it's not part of
any default Supabase project — without it every tool in
`tools/supabase_tools.py` fails with `PGRST202: Could not find the function
public.execute_sql(query) in the schema cache`):

```sql
create or replace function public.execute_sql(query text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  result jsonb;
  cleaned text;
begin
  cleaned := regexp_replace(trim(query), ';\s*$', '');

  if cleaned ~* '^\s*(select|with)\s' then
    execute format('select coalesce(jsonb_agg(t), ''[]''::jsonb) from (%s) t', cleaned) into result;
  else
    execute cleaned;
    result := jsonb_build_object('status', 'ok');
  end if;

  return result;
end;
$$;

grant execute on function public.execute_sql(text) to anon, authenticated, service_role;
```

This strips a trailing `;` (the tools' queries all end with one, which would
otherwise be a syntax error inside the wrapping subquery). `SELECT`/`WITH`
queries are wrapped to return rows as a JSON array; everything else (DDL like
`CREATE TABLE`, or DML like `INSERT`/`UPDATE`/`DELETE`) is executed directly
and returns `{"status": "ok"}` — these can't be used inside a `FROM (...)`
subquery, which is why the original wrapped-only version raised
`42601: syntax error at or near "CREATE"` for anything but a `SELECT`.
`security definer` + granting to `anon` means the anon key can run arbitrary
SQL (including writes/DDL) against this project — intentional, since
`execute_sql` in `tools/supabase_tools.py` is designed to support
inserts/updates/creates when the user asks for them, but worth knowing since
the anon key is the least-privileged credential by convention.

## Install
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Environment variables (`.env`, gitignored — never commit real values)

| Variable | Used by | Notes |
|---|---|---|
| `OPENAI_API_KEY` | `llm/openai_client.py` | required only if provider = `openai` |
| `ANTHROPIC_API_KEY` | `llm/anthropic_client.py` | required only if provider = `anthropic` |
| `LLM_PROVIDER` | (informational) | actual provider is chosen via Streamlit sidebar (defaults to `"openai"` / GPT-4o) or `SQLAgent(provider=...)` (constructor default `"anthropic"`) |
| `LANGSMITH_TRACING` | LangChain/LangGraph | enables tracing |
| `LANGSMITH_ENDPOINT` | LangChain/LangGraph | e.g. `https://eu.api.smith.langchain.com` |
| `LANGSMITH_API_KEY` | LangChain/LangGraph | |
| `LANGSMITH_PROJECT` | LangChain/LangGraph | e.g. `finance-quarterly-report` |
| `SUPABASE_URL` | `tools/supabase_tool.py` | project REST URL |
| `SUPABASE_ANON_KEY` | `tools/supabase_tool.py` | anon/public key used by `create_client` |
| `SUPABASE_ACCESS_TOKEN` | (informational/CLI use) | not read directly by app code |
| `SUPABASE_PROJECT_ID` | (informational) | not read directly by app code |

## Run the app

```bash
streamlit run main.py
```

The MCP tool server (`tools/supabase_tool.py`) is spawned automatically as a
subprocess when the first query is submitted — no separate terminal needed.
This also means the app works on **Streamlit Cloud** without any extra setup.

## Deploying to Streamlit Community Cloud

There is no `.env` file on Streamlit Cloud — secrets are configured via the
app's **Settings → Secrets** dashboard, as TOML. `main.py` calls
`st.secrets.load_if_toml_exists()` at startup, which makes Streamlit copy
every top-level secret into `os.environ`, so all the existing `os.getenv()`
calls in `agent/`, `llm/`, and `tools/` keep working unchanged.

Paste the same values from your local `.env` into the Secrets box, **quoting
every value as a string** (so `_maybe_set_environment_variable` copies it —
unquoted TOML booleans/numbers are not copied to `os.environ`):

```toml
OPENAI_API_KEY = "sk-..."
ANTHROPIC_API_KEY = "sk-ant-..."
LANGSMITH_TRACING = "true"
LANGSMITH_ENDPOINT = "https://eu.api.smith.langchain.com"
LANGSMITH_API_KEY = "lsv2_pt_..."
LANGSMITH_PROJECT = "finance-quarterly-report"
SUPABASE_URL = "https://<project-id>.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_..."
SUPABASE_PROJECT_ID = "<project-id>"
SUPABASE_ACCESS_TOKEN = "sbp_..."
```

After saving secrets, use "Reboot app" so the new environment variables take
effect.

