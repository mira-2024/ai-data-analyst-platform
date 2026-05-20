import streamlit as st
import pandas as pd


INTENT_LABELS = {
    "clean": "🧹 Cleaning",
    "analyze": "📊 Analysis",
    "visualize": "📈 Visualization",
    "report": "📄 Report",
    "chat": "💬 Chat",
}


def render_data_preview(df: pd.DataFrame):
    """Render a data preview with basic stats."""
    st.subheader("Data Preview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", df.shape[0])
    col2.metric("Columns", df.shape[1])
    col3.metric("Missing Values", int(df.isnull().sum().sum()))
    st.dataframe(df.head(50), use_container_width=True)

    with st.expander("Column Details"):
        info = pd.DataFrame({
            "Type": df.dtypes,
            "Non-Null": df.count(),
            "Null": df.isnull().sum(),
            "Unique": df.nunique(),
        })
        st.dataframe(info, use_container_width=True)


def render_figures(figures: list[dict]):
    """Render a list of plotly figures in a 2-column grid."""
    if not figures:
        return
    cols = st.columns(2)
    for i, item in enumerate(figures):
        with cols[i % 2]:
            st.plotly_chart(item["figure"], use_container_width=True)
            if item.get("description"):
                st.caption(item["description"])


def render_chat_message(role: str, content: str, intent: str = ""):
    """Render a single chat message bubble."""
    with st.chat_message(role):
        if intent and role == "assistant":
            label = INTENT_LABELS.get(intent, "")
            if label:
                st.caption(label)
        st.markdown(content)
