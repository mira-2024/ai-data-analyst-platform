"""
ChatAgent — conversational Q&A over the dataset.

This agent does genuinely need a language model. When one is configured it
answers free-form questions grounded in a computed dataset summary; when no key
is available it returns a helpful message pointing the user to the
deterministic Analysis / Modeling features that work offline.
"""

from __future__ import annotations

import pandas as pd

from utils.data_utils import get_df_summary, get_data_sample
from utils import llm


class ChatAgent:
    def chat(self, df: pd.DataFrame, history: list[dict], user_message: str) -> str:
        if not llm.available():
            return (
                "💬 Free-form chat needs a Gemini API key (set `GEMINI_API_KEY` in "
                "`.env`). The data-science features work without it — try "
                "**Analyse the dataset**, **Model / predict**, **Visualize the data**, "
                "or **Generate a report**, which all run on real computation."
            )

        summary = get_df_summary(df)
        sample = get_data_sample(df, n=15)

        # Build a single grounded prompt (provider-agnostic, no SDK type objects).
        convo = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in history[-8:]
        )
        prompt = (
            "You are a helpful data analyst assistant. Answer the user's question "
            "about the dataset below. Be concise, precise, and use markdown where "
            "helpful. If the question requires a precise statistic you cannot see, "
            "say so and suggest running the Analysis or Modeling feature.\n\n"
            f"Dataset Summary:\n{summary}\n\nSample Data (first 15 rows):\n{sample}\n\n"
            f"Conversation so far:\n{convo}\n\nUser: {user_message}"
        )
        answer = llm.narrate(prompt)
        return answer or "Sorry, I couldn't generate a response (the LLM call failed)."
