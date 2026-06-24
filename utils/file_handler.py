import pandas as pd
import io


def load_file(uploaded_file) -> pd.DataFrame:
    """Load a CSV, Excel, or JSON file into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    elif name.endswith(".json"):
        return pd.read_json(uploaded_file)
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")
