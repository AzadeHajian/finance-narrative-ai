# Architecture

## Two-process model

Finance Quarterly Report now follows the same pattern as PaperPilot:

```
Process 1 — MCP tool server (start first)
  python tools/supabase_tool.py
    └─> FastMCP("supabase") running on http://localhost:8001/sse
          └─> exposes 4 tools over SSE: list_tables, get_table_schema,
              get_sample_rows, execute_sql

Process 2 — Streamlit app
  streamlit run main.py
    └─> SQLAgent.run()          [agent/agent.py]
          └─> asyncio.run(agent_instance(...))
                └─> MultiServerMCPClient (SSE → localhost:8001)
                      └─> await mcp_tools.get_tools()   (4 tools loaded)
                            └─> create_react_agent(llm, tools)
                                  └─> await agent.ainvoke(messages)
                                        ReAct loop calls tools via MCP/SSE
                                        └─> supabase_tool.py hits Supabase
                                  └─> returns final answer string
```

## Request flow detail

```
User types question in main.py (Streamlit chat form)
  └─> st.session_state.agent.run(user_message, chat_history)   [agent/agent.py]
        └─> asyncio.run(agent_instance(...))                    [mcp_server/client.py]
              ├─ MultiServerMCPClient connects to localhost:8001/sse
              ├─ loads tools: list_tables, get_table_schema,
              │               get_sample_rows, execute_sql
              ├─ build messages: system_prompt + chat_history + user_message
              ├─ create_react_agent(llm.client, tools)
              │
              │   ReAct loop (driven by the LLM):
              │     1. list_tables()        -> information_schema.tables
              │     2. get_table_schema(t)  -> information_schema.columns
              │     3. get_sample_rows(t)   -> SELECT * FROM t LIMIT 5
              │     4. (LLM composes SQL)
              │     5. execute_sql(query)   -> runs the SQL
              │     6. (LLM explains results in prose + ```sql block)
              │
              └─> returns response["messages"][-1].content
  └─> appended to st.session_state.chat_history, rendered in chat UI
```

## File roles

| File | Role |
|---|---|
| `tools/supabase_tool.py` | Standalone FastMCP SSE server. Single source of truth for all 4 Supabase tools. Run separately before the app. |
| `mcp_server/client.py` | Async `agent_instance()`. Connects to the SSE server, loads tools, builds and runs the LangGraph ReAct agent. |
| `agent/agent.py` | `SQLAgent` class. Thin sync wrapper around `agent_instance` via `asyncio.run()`. Used by the Streamlit UI. |
| `agent/prompt.py` | System prompt: `task_prompt()` + `security_prompt()`. |
| `llm/` | Provider abstraction (`AnthropicLLM`, `OpenAILLM`) wrapping LangChain chat models. |
| `main.py` | Streamlit UI. Owns session state and chat rendering. |

## Provider abstraction

```
agent.py --> get_llm(provider) --> BaseLLM
                                      ├─ AnthropicLLM  (ChatAnthropic)
                                      └─ OpenAILLM     (ChatOpenAI)
```

`llm.client` is the underlying LangChain chat model passed to `create_react_agent`.

## System prompt composition

`agent/prompt.py` builds the system prompt as `task_prompt() + "\n" + security_prompt()`:

- **task_prompt** — the narrative chain-of-thought: READ THE DATA → CHECK DATA
  QUALITY (suspected-duplicate revenue) → WRITE (2–3 neutral sentences:
  revenue vs prior quarter, headcount, ESG) → TONE → OUTPUT valid JSON
  (`summary` + `data_used` + `flags`).
- **security_prompt** — hard rules: no invented numbers, no unverified trends,
  no auto-publish (draft only), stay in scope, always echo `data_used`.

## Transport: SSE vs stdio (previous)

The previous version used `stdio` transport: the MCP server was spawned as a subprocess on each query.
The current version uses `SSE` transport: the tool server runs as a persistent HTTP service.

| | SSE (current) | stdio (previous) |
|---|---|---|
| Server lifetime | Persistent, started once | Spawned per query |
| Startup | Run `python tools/supabase_tool.py` first | Automatic |
| Overhead | Low (reuses connection) | Higher (subprocess per call) |
| Debuggable | Yes (separate process, visible logs) | Harder |
