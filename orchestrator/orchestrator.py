import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from agents.analysis_agent import AnalysisAgent
from agents.chat_agent import ChatAgent
from agents.cleaning_agent import CleaningAgent
from agents.report_agent import ReportAgent
from agents.visualization_agent import VisualizationAgent

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

INTENT_PROMPT = """Classify the user's message into ONE of these intents:
- "clean"       → wants data cleaned or fixed
- "analyze"     → wants statistics, patterns, or data analysis
- "visualize"   → wants charts, graphs, or plots
- "report"      → wants a full report or summary document
- "chat"        → general question or conversation about the data

Respond with ONLY the intent word (lowercase). No explanation.

User message: {message}"""


class Orchestrator:
    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.chat_agent = ChatAgent()
        self.cleaning_agent = CleaningAgent()
        self.report_agent = ReportAgent()
        self.visualization_agent = VisualizationAgent()

    def _classify_intent(self, message: str) -> str:
        response = _client.models.generate_content(
            model=MODEL, contents=INTENT_PROMPT.format(message=message)
        )
        intent = response.text.strip().lower()
        valid = {"clean", "analyze", "visualize", "report", "chat"}
        return intent if intent in valid else "chat"

    def process(self, df: pd.DataFrame, user_message: str, history: list[dict]) -> dict:
        intent = self._classify_intent(user_message)
        result = {"intent": intent, "text": "", "figures": [], "cleaned_df": None}

        if intent == "clean":
            cleaned_df, report = self.cleaning_agent.clean(df)
            result["text"] = report
            result["cleaned_df"] = cleaned_df
        elif intent == "analyze":
            result["text"] = self.analysis_agent.analyze(df, query=user_message)
        elif intent == "visualize":
            figures = self.visualization_agent.generate(df, query=user_message)
            result["figures"] = figures
            result["text"] = (
                f"Generated {len(figures)} visualization(s) based on your request."
                if figures else "Could not generate visualizations for this dataset."
            )
        elif intent == "report":
            result["text"] = self.report_agent.generate(df)
        else:
            result["text"] = self.chat_agent.chat(df, history, user_message)

        return result
