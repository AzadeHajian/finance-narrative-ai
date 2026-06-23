# Project Overview — Finance Quarterly Report

Finance Quarterly Report is an AI text-to-SQL assistant. A user types a question in plain
English, a LangGraph ReAct agent explores a Supabase Postgres database
(tables → schema → sample rows), writes a SQL query, runs it, and explains
the result back to the user in a Streamlit chat UI.

## Folder-by-folder breakdown

### `main.py` (root)
The only file with UI code. A Streamlit app that:
- Sets up page config, custom CSS, and session state
  (`chat_history`, `current_result`, `query_count`, `agent`, `provider`).
- Sidebar lets the user pick the LLM provider (`anthropic` / `openai`) and
  recreates `SQLAgent` when it changes.
- Renders chat history, splitting assistant messages on ``` fences so SQL
  blocks get syntax highlighting.
- On submit, calls `SQLAgent.run(user_message, chat_history)` and appends
  the result to chat history.
- Has "Copy Result", "Save to File" (writes `finance-quarterly-report_<timestamp>.txt`), and
  "New Query" buttons.

### `agent/`
The agent's "brain".

- `agent.py` — `SQLAgent` class:
  - `__init__(provider)`: gets an LLM via `llm.get_llm(provider)`, loads
    `SUPABASE_TOOLS`, builds the system prompt via
    `agent.prompt.get_full_prompt()`, and constructs a LangGraph
    `create_react_agent(model=..., tools=..., prompt=...)`.
  - `run(user_message, chat_history)`: converts chat history dicts into
    `HumanMessage`/`AIMessage`, invokes the agent, returns the last
    message's content. Catches exceptions and returns `"Agent error: {e}"`.
  - `get_model_name()` / `get_provider()`: simple getters.
- `prompt.py` — system prompt, split into two composable parts:
  - `task_prompt()`: the chain-of-thought the agent should follow —
    EXPLORE (`list_all_tables`) → UNDERSTAND (`get_schema`) → PREVIEW
    (`sample_rows`) → GENERATE SQL → EXECUTE (`run_sql`) → EXPLAIN.
  - `security_prompt()`: hard rules — read-only by default (SELECT unless
    explicitly asked otherwise), no `DROP`/`TRUNCATE`/unscoped `DELETE`/
    `ALTER TABLE`, no raw SQL injection, stay within this DB's public
    tables, always show the SQL being run.
  - `get_full_prompt()`: concatenation of the two, passed to
    `create_react_agent` as the system prompt.
- `__init__.py` — re-exports `SQLAgent`, `get_full_prompt`, `task_prompt`,
  `security_prompt`.

### `llm/`
Provider abstraction so the rest of the app never talks to a specific
vendor SDK directly.

- `base.py` — `BaseLLM` ABC with `invoke(prompt)`,
  `invoke_with_history(messages)`, `get_model_name()`. Every provider must
  implement all three.
- `anthropic_client.py` — `AnthropicLLM(BaseLLM)`. Wraps
  `langchain_anthropic.ChatAnthropic`, default model
  `claude-sonnet-4-5-20250929`, `temperature=0.2`, `max_tokens=2048`. Reads
  `ANTHROPIC_API_KEY`.
- `openai_client.py` — `OpenAILLM(BaseLLM)`. Wraps
  `langchain_openai.ChatOpenAI`, default model `gpt-4o-2024-11-20`, same
  temperature/max_tokens. Reads `OPENAI_API_KEY`.
- `__init__.py` — `get_llm(provider)` factory: `"anthropic"` →
  `AnthropicLLM()`, `"openai"` → `OpenAILLM()`, else `ValueError`.

### `tools/`
LangChain `@tool`-decorated functions that talk to Supabase. These are the
tools the ReAct agent calls.

- `supabase_tools.py`:
  - `_get_client()` — builds a `supabase.Client` from `SUPABASE_URL` +
    `SUPABASE_ANON_KEY`. Raises `ValueError` if either is missing, and
    wraps `create_client()` in try/except, re-raising as `RuntimeError`
    on failure.
  - `list_tables(dummy="")` — runs an `execute_sql` RPC that selects
    `table_name` from `information_schema.tables` (schema = `public`).
  - `get_table_schema(table_name)` — selects `column_name`, `data_type`,
    `is_nullable` from `information_schema.columns` for the given table.
    **Builds the SQL via f-string interpolation of `table_name`.**
  - `get_sample_rows(table_name)` — `SELECT * FROM {table_name} LIMIT 5`,
    also via f-string interpolation.
  - `execute_sql(query)` — runs an arbitrary query through the same
    `execute_sql` RPC and returns `response.data` as a string.
  - All four tools rely on a Postgres RPC function called `execute_sql`
    existing in the Supabase project (it is not defined in this repo).
- `__init__.py` — exports the four tool functions plus `SUPABASE_TOOLS`,
  the list passed to `create_react_agent`.

### `mcp_server/`
An alternative way to expose the same Supabase tools, this time over the
Model Context Protocol via FastMCP, so any MCP client (not just this
Streamlit app) can use them.

- `server.py` — creates a `FastMCP(name="finance-quarterly-report-mcp", instructions=...)`
  instance and re-exposes the tool functions under MCP-friendly names:
  - `list_all_tables()` → calls `list_tables.invoke({"dummy": ""})`
  - `get_schema(table_name)` → calls `get_table_schema.invoke(...)`
  - `sample_rows(table_name)` → calls `get_sample_rows.invoke(...)`
  - `run_sql(query)` → calls `execute_sql.invoke(...)`
  - Run with `python -m mcp_server.server`.
- `__init__.py` — re-exports the `mcp` instance.

### Top-level config files
- `requirements.txt` — grouped by purpose: LLM providers (anthropic,
  langchain-anthropic, openai, langchain-openai), LangChain core
  (langchain, langchain-core, langchain-community,
  langchain-mcp-adapters, langchain-classic), LangGraph
  (langgraph, langgraph-prebuilt), MCP (fastmcp, mcp), `supabase`,
  `streamlit`, `python-dotenv`, `langsmith`.
- `.env` — **gitignored**, holds real secrets (OpenAI/Anthropic/LangSmith/
  Supabase keys, `LLM_PROVIDER`, `SUPABASE_URL`, `SUPABASE_PROJECT_ID`,
  `SUPABASE_ACCESS_TOKEN`, `SUPABASE_ANON_KEY`). See
  [SETUP.md](SETUP.md) for the variable list — never copy actual values
  into docs or commits.
- `.gitignore` — ignores `.env`, `.venv`, `__pycache__/`.
- `.venv/` — Python 3.10 virtualenv.
