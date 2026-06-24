import pandas as pd


def get_df_summary(df: pd.DataFrame) -> str:
    """Return a compact text summary of a DataFrame for use in LLM prompts."""
    numeric = df.select_dtypes(include="number")
    categorical = df.select_dtypes(include=["object", "category"])

    lines = [
        f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
        f"Columns: {list(df.columns)}",
        "",
        "Data types:",
        df.dtypes.to_string(),
        "",
        f"Missing values:\n{df.isnull().sum().to_string()}",
    ]

    if not numeric.empty:
        lines += ["", "Numeric summary:", numeric.describe().round(2).to_string()]

    if not categorical.empty:
        top = {col: df[col].value_counts().head(5).to_dict() for col in categorical.columns}
        lines += ["", "Top categorical values:"]
        for col, vals in top.items():
            lines.append(f"  {col}: {vals}")

    return "\n".join(lines)


def get_data_sample(df: pd.DataFrame, n: int = 10) -> str:
    """Return the first n rows of a DataFrame as a string."""
    return df.head(n).to_string(index=False)
