import os
import sys
import traceback
from typing import List, Dict
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from agent.prompt import get_full_prompt

load_dotenv()

# Absolute path to the tool server — works locally and on Streamlit Cloud
# regardless of the current working directory.
_TOOL_SERVER = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "tools", "supabase_tool.py")
)


async def agent_instance(
    user_prompt: str,
    provider: str = "anthropic",
    chat_history: List[Dict] = [],
    temperature: float = 0.0,
) -> str:
    """
    Creates and runs a LangGraph ReAct agent that loads tools from
    tools/supabase_tool.py via stdio (spawned as a subprocess automatically).

    Args:
        user_prompt:   The user's natural-language question.
        provider:      LLM provider — 'anthropic' or 'openai'.
        chat_history:  Previous turns as [{"role": ..., "content": ...}].

    Returns:
        The agent's final answer as a string.
    """
    mcp_tools = MultiServerMCPClient(
        {
            "supabase_tool": {
                # sys.executable ensures we use the same Python interpreter
                # that is running the app — critical on Streamlit Cloud where
                # a bare "python" command may not be on PATH.
                "command": sys.executable,
                "args": [_TOOL_SERVER],
                "transport": "stdio",
                # Explicitly forward all env vars so the subprocess sees
                # SUPABASE_URL, SUPABASE_ANON_KEY, etc. — required on
                # Streamlit Cloud where secrets live in os.environ of the
                # parent but are not automatically inherited by child processes
                # spawned through the MCP stdio transport layer.
                "env": dict(os.environ),
            },
        }
    )

    print("Connecting to Supabase MCP tool server...")

    try:
        tools = await mcp_tools.get_tools()
    except Exception as e:
        traceback.print_exception(e)
        raise RuntimeError(
            "Failed to load tools from tools/supabase_tool.py. "
            "Check that the file exists and SUPABASE_URL / SUPABASE_ANON_KEY are set."
        )

    print(f"Loaded tools: {[tool.name for tool in tools]}")

    llm = get_llm(provider, temperature)
    agent = create_react_agent(model=llm.client, tools=tools)

    system_prompt = get_full_prompt()
    messages = [{"role": "system", "content": system_prompt}]

    for m in chat_history:
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt})

    response = await agent.ainvoke({"messages": messages})

    print("Agent response received.")
    return response["messages"][-1].content
