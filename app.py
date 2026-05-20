import streamlit as st
import pandas as pd
from utils.file_handler import load_file
from orchestrator.orchestrator import Orchestrator
from ui.components import render_data_preview, render_figures, render_chat_message

st.set_page_config(
    page_title="Data Analyst AI",
    page_icon="📊",
    layout="wide",
)

# ── Session state initialisation ──────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "history" not in st.session_state:
    st.session_state.history = []
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Data Analyst AI")
    st.markdown("Upload a dataset and ask anything about it.")

    uploaded = st.file_uploader(
        "Upload file (CSV / Excel / JSON)",
        type=["csv", "xlsx", "xls", "json"],
    )

    if uploaded:
        try:
            st.session_state.df = load_file(uploaded)
            st.session_state.history = []
            st.success(f"Loaded **{uploaded.name}** — {st.session_state.df.shape[0]} rows × {st.session_state.df.shape[1]} cols")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    if st.button("📂 Load Sample Data", use_container_width=True):
        import pandas as pd, os
        sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample.csv")
        st.session_state.df = pd.read_csv(sample_path)
        st.session_state.history = []
        st.success(f"Loaded sample.csv — {st.session_state.df.shape[0]} rows × {st.session_state.df.shape[1]} cols")

    st.divider()
    st.markdown("**Quick prompts:**")
    quick_prompts = [
        "Clean the data",
        "Analyse the dataset",
        "Visualize the data",
        "Generate a full report",
    ]
    for qp in quick_prompts:
        if st.button(qp, use_container_width=True):
            st.session_state["quick_prompt"] = qp

    if st.session_state.df is not None:
        st.divider()
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.history = []

# ── Main content ───────────────────────────────────────────────────────────────
if st.session_state.df is None:
    st.title("Welcome to Data Analyst AI")
    st.markdown(
        """
        **Get started:**
        1. Upload a CSV, Excel, or JSON file in the sidebar.
        2. Ask questions in natural language.
        3. The AI will automatically route your request to the right agent.

        **What you can ask:**
        - *"Clean the data"* — remove duplicates, fill missing values
        - *"Analyse the dataset"* — statistical insights and patterns
        - *"Visualize the data"* — automatic chart generation
        - *"Generate a report"* — full markdown report
        - *Any question* — general Q&A about your data
        """
    )
    st.info("No file uploaded yet. Use the sidebar to upload your dataset.")
    st.stop()

# Tabs
tab_data, tab_chat = st.tabs(["📋 Data Preview", "💬 Chat"])

with tab_data:
    render_data_preview(st.session_state.df)

with tab_chat:
    # Render existing history
    for msg in st.session_state.history:
        render_chat_message(
            role=msg["role"],
            content=msg["content"],
            intent=msg.get("intent", ""),
        )
        if msg.get("figures"):
            render_figures(msg["figures"])

    # Handle quick-prompt button click
    quick = st.session_state.pop("quick_prompt", None)

    user_input = st.chat_input("Ask anything about your data…") or quick

    if user_input:
        # Display user message
        render_chat_message("user", user_input)
        st.session_state.history.append({"role": "user", "content": user_input})

        with st.spinner("Thinking…"):
            try:
                result = st.session_state.orchestrator.process(
                    df=st.session_state.df,
                    user_message=user_input,
                    history=st.session_state.history,
                )
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    st.error(
                        "**Gemini API quota exceeded.**\n\n"
                        "Your free-tier daily limit is used up. To fix this:\n"
                        "1. Get a new API key at https://aistudio.google.com/apikey\n"
                        "2. Replace `GEMINI_API_KEY` in your `.env` file\n"
                        "3. Restart the app\n\n"
                        "Or wait until tomorrow when the quota resets."
                    )
                else:
                    st.error(f"An error occurred: {err}")
                st.session_state.history.pop()  # remove the user message we added
                st.stop()

        # If cleaning produced a new df, update it
        if result["cleaned_df"] is not None:
            st.session_state.df = result["cleaned_df"]

        # Display assistant response
        render_chat_message("assistant", result["text"], intent=result["intent"])
        if result["figures"]:
            render_figures(result["figures"])

        st.session_state.history.append({
            "role": "assistant",
            "content": result["text"],
            "intent": result["intent"],
            "figures": result["figures"],
        })

        st.rerun()
