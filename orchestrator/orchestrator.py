"""
Orchestrator — intent router for the multi-agent pipeline.

Routes a user message to one of six agents: clean, analyze, model, visualize,
report, or chat. Intent classification uses the LLM when available and falls
back to a deterministic keyword matcher otherwise, so routing never depends on
a network call.
"""

from __future__ import annotations

import re

import pandas as pd

from agents.analysis_agent import AnalysisAgent
from agents.chat_agent import ChatAgent
from agents.cleaning_agent import CleaningAgent
from agents.modeling_agent import ModelingAgent
from agents.report_agent import ReportAgent
from agents.visualization_agent import VisualizationAgent
from utils import llm

VALID_INTENTS = {"clean", "analyze", "model", "visualize", "report", "chat"}

INTENT_PROMPT = """Classify the user's message into ONE of these intents:
- "clean"     -> wants data cleaned, fixed, or prepared
- "analyze"   -> wants statistics, correlations, patterns, hypothesis tests
- "model"     -> wants prediction, machine learning, a model, feature importance, accuracy
- "visualize" -> wants charts, graphs, or plots
- "report"    -> wants a full report or summary document
- "chat"      -> general question or conversation about the data

Respond with ONLY the intent word (lowercase). No explanation.

User message: {message}"""

# Keyword fallback used when no LLM is configured.
_KEYWORDS = {
    "model": ["predict", "model", "machine learning", "ml ", "classifier", "regression",
              "forecast", "accuracy", "feature importance", "train", "random forest"],
    "clean": ["clean", "fix", "prepare", "missing", "duplicate", "impute", "tidy"],
    "visualize": ["visual", "chart", "graph", "plot", "histogram", "scatter", "heatmap"],
    "report": ["report", "summary document", "full report", "executive"],
    "analyze": ["analyz", "analyse", "statistic", "correlat", "distribut", "insight",
                "outlier", "hypothesis", "test", "describe"],
}


class Orchestrator:
    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.chat_agent = ChatAgent()
        self.cleaning_agent = CleaningAgent()
        self.modeling_agent = ModelingAgent()
        self.report_agent = ReportAgent()
        self.visualization_agent = VisualizationAgent()

    def _classify_intent(self, message: str) -> str:
        if llm.available():
            raw = llm.narrate(INTENT_PROMPT.format(message=message))
            if raw:
                intent = raw.strip().lower().split()[0] if raw.strip() else ""
                if intent in VALID_INTENTS:
                    return intent
        return self._keyword_intent(message)

    @staticmethod
    def _keyword_intent(message: str) -> str:
        m = f" {message.lower()} "
        # Priority order: model > clean > visualize > report > analyze.
        for intent in ("model", "clean", "visualize", "report", "analyze"):
            if any(kw in m for kw in _KEYWORDS[intent]):
                return intent
        return "chat"

    def process(self, df: pd.DataFrame, user_message: str, history: list[dict]) -> dict:
        intent = self._classify_intent(user_message)
        result = {"intent": intent, "text": "", "figures": [], "cleaned_df": None}

        if intent == "clean":
            cleaned_df, report = self.cleaning_agent.clean(df)
            result["text"] = report
            result["cleaned_df"] = cleaned_df
        elif intent == "analyze":
            result["text"] = self.analysis_agent.analyze(df, query=user_message)
        elif intent == "model":
            target = self._extract_target(df, user_message)
            out = self.modeling_agent.run(df, target=target)
            result["text"] = out["text"]
            result["figures"] = out["figures"]
        elif intent == "visualize":
            figures = self.visualization_agent.generate(df, query=user_message)
            result["figures"] = figures
            result["text"] = (
                f"Generated {len(figures)} visualization(s)."
                if figures else "Could not generate visualizations for this dataset."
            )
        elif intent == "report":
            result["text"] = self.report_agent.generate(df)
        else:
            result["text"] = self.chat_agent.chat(df, history, user_message)

        return result

    @staticmethod
    def _extract_target(df: pd.DataFrame, message: str) -> str | None:
        """If the user names a column to predict, honour it; else let the agent decide."""
        msg = message.lower()
        # "predict X", "model X", "target X"
        m = re.search(r"(?:predict|model|target|classify|forecast)\s+(?:the\s+)?([\w ]+)", msg)
        if m:
            phrase = m.group(1).strip()
            for col in df.columns:
                if col.lower() in phrase or phrase.startswith(col.lower()):
                    return col
        # Otherwise check any column name appearing in the message.
        for col in df.columns:
            if re.search(rf"\b{re.escape(col.lower())}\b", msg):
                return col
        return None
