# main.py
# -----------------------------------------------------------
# Finance Quarterly Report - AI narrative quarterly summaries
# Streamlit UI that connects to the portfolio-narrative agent.
# Only file that has UI code — agent logic stays in agent/
# -----------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# On Streamlit Community Cloud there is no .env file — secrets are configured
# via the app's "Secrets" dashboard instead. Accessing st.secrets (if a
# secrets.toml exists) makes Streamlit copy top-level secrets into
# os.environ, so the existing os.getenv() calls in agent/, llm/, and tools/
# keep working unchanged both locally and when deployed.
st.secrets.load_if_toml_exists()

from agent import SQLAgent

# -----------------------------------------------------------
# Page config — must be first Streamlit command
# -----------------------------------------------------------
st.set_page_config(
    page_title="Finance Quarterly Report",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------
# Custom CSS
# -----------------------------------------------------------
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(120deg, #10b981, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .result-card {
        padding: 1.5rem;
        border-radius: 10px;
        background: white;
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(120deg, #10b981, #3b82f6);
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        border: none;
        font-size: 1rem;
    }
    .stButton>button:hover {
        background: linear-gradient(120deg, #059669, #2563eb);
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------
# Initialize session state
# -----------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "query_count" not in st.session_state:
    st.session_state.query_count = 0
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.0
if "agent" not in st.session_state:
    st.session_state.agent = SQLAgent(provider="openai", temperature=st.session_state.temperature)
if "provider" not in st.session_state:
    st.session_state.provider = "openai"
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# -----------------------------------------------------------
# Header
# -----------------------------------------------------------
st.markdown('<div class="main-header">📝 Finance Quarterly Report</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Drafts neutral quarterly narrative summaries of portfolio companies from data in Supabase — for human review</div>', unsafe_allow_html=True)

# -----------------------------------------------------------
# Sidebar
# -----------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.divider()

    # Model selector
    st.markdown("### 🤖 Model")
    provider = st.radio(
        label="Choose LLM provider:",
        options=["openai", "anthropic"],
        format_func=lambda x: "🟢 GPT-4o (OpenAI)" if x == "openai" else "🟣 Claude (Anthropic)",
        index=0,
    )

    # Recreate agent if provider changed
    if provider != st.session_state.provider:
        st.session_state.provider = provider
        st.session_state.agent = SQLAgent(
            provider=provider, temperature=st.session_state.temperature
        )
        st.success(f"Switched to {provider}!")

    st.divider()

    # Temperature — fixed at 0 for deterministic, faithful drafts.
    # Shown (grayed out) so the setting is visible but cannot be changed.
    st.markdown("### 🌡️ Temperature")
    temperature = st.slider(
        "Sampling temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.temperature,
        step=0.1,
        disabled=True,
        help="Locked at 0 so summaries are deterministic and faithful to the data.",
    )
    if temperature != st.session_state.temperature:
        st.session_state.temperature = temperature
        st.session_state.agent = SQLAgent(
            provider=st.session_state.provider, temperature=temperature
        )

    st.divider()

    # Current model info
    st.markdown("### 📋 Current Model")
    st.code(st.session_state.agent.get_model_name())

    st.divider()

    # Database info
    st.markdown("### 🗄️ Database")
    st.info("Connected to Supabase\nProject: P01\neu-central-1")

    st.divider()

    # Statistics
    st.markdown("### 📈 Statistics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Queries", st.session_state.query_count)
    with col2:
        st.metric("History", len(st.session_state.chat_history) // 2)

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.current_result = None
        st.session_state.query_count = 0
        st.rerun()

# -----------------------------------------------------------
# Example questions
# -----------------------------------------------------------
st.markdown("---")
with st.expander("💡 Example requests & tips", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**📋 Summarise**")
        st.code("Summarise C-014 for 2025-Q2")
        st.code("Write the quarterly narrative for C-022, 2025-Q1")
    with col2:
        st.markdown("**🔍 Compare**")
        st.code("Compare C-014's Q1 and Q2 2025 revenue")
        st.code("How did C-014's headcount change in 2025-Q3?")
    with col3:
        st.markdown("**📊 ESG & quality**")
        st.code("Summarise C-014's ESG trend for 2025-Q2")
        st.code("Flag any duplicate revenue for C-014")

# -----------------------------------------------------------
# Chat history
# -----------------------------------------------------------
st.markdown("---")
st.markdown("### 💬 Chat")

for message in st.session_state.chat_history:
    role = message["role"]
    content = message["content"]

    if role == "user":
        with st.chat_message("user"):
            st.write(content)

    elif role == "assistant":
        with st.chat_message("assistant", avatar="🗄️"):
            parts = content.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    if part.strip():
                        st.markdown(part)
                else:
                    lines = part.strip().split("\n")
                    language = lines[0].lower() if lines else ""
                    if language in ["sql", "postgresql"]:
                        sql_code = "\n".join(lines[1:]) if len(lines) > 1 else part
                        st.code(sql_code, language="sql")
                    else:
                        st.code(part)

# -----------------------------------------------------------
# Query input — pinned to the bottom, submits on Enter
# -----------------------------------------------------------
user_query = st.chat_input("Ask your request...")

# -----------------------------------------------------------
# Process query
# -----------------------------------------------------------
if user_query:
    with st.spinner("🤖 Thinking..."):
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("🔌 Connecting to Supabase...")
            progress_bar.progress(25)

            status_text.text("🤖 Agent is exploring the database...")
            progress_bar.progress(50)

            # Run the agent
            response = st.session_state.agent.run(
                user_message=user_query,
                chat_history=st.session_state.chat_history,
            )

            status_text.text("📊 Processing results...")
            progress_bar.progress(75)

            # Save to history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_query,
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
            })

            st.session_state.current_result = response
            st.session_state.last_query = user_query
            st.session_state.query_count += 1

            progress_bar.progress(100)
            status_text.text("✅ Done!")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 **Troubleshooting:**\n- Check your .env keys\n- Make sure Supabase is reachable\n- Check the terminal for detailed errors")

    st.rerun()

# -----------------------------------------------------------
# Result actions
# -----------------------------------------------------------
if st.session_state.current_result:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Copy Result"):
            st.code(st.session_state.current_result)
    with col2:
        if st.button("💾 Save to File"):
            from datetime import datetime
            filename = f"finance_quarterly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w") as f:
                f.write(f"Query: {st.session_state.last_query}\n\n")
                f.write(f"Result:\n{st.session_state.current_result}")
            st.success(f"✅ Saved to {filename}")
    with col3:
        if st.button("🔄 New Query"):
            st.session_state.current_result = None
            st.rerun()

# -----------------------------------------------------------
# Footer
# -----------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**🗄️ Database**")
    st.markdown("Supabase • PostgreSQL")
with col2:
    st.markdown("**🤖 Powered by**")
    st.markdown("Claude • GPT-4o • LangChain")
with col3:
    st.markdown("**📝 Finance Quarterly Report**")
    st.markdown("AI narrative summaries · human-reviewed")