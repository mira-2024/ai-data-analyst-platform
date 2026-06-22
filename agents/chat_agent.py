import os
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv
from utils.data_utils import get_df_summary, get_data_sample

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"


class ChatAgent:
    def chat(self, df: pd.DataFrame, history: list[dict], user_message: str) -> str:
        summary = get_df_summary(df)
        sample = get_data_sample(df, n=15)

        system_instruction = (
            "You are a helpful data analyst assistant. Answer questions about the dataset below. "
            "Be concise, precise, and use markdown formatting where helpful.\n\n"
            f"Dataset Summary:\n{summary}\n\nSample Data (first 15 rows):\n{sample}"
        )

        contents = []
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

        response = _client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )
        return response.text.strip()
