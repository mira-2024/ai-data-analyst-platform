"""
insights.py — one-click "auto analysis".

Runs the whole data-science pipeline (clean → profile → key statistics →
modelling) and turns the results into a short, plain-language summary that a
non-technical reader can understand. This is the engine behind the app's
guided **Overview** tab. No language model required.
"""

from __future__ import annotations

import pandas as pd

from agents.cleaning_agent import CleaningAgent
from ml import eda, statistics, modeling


def _pct(x: float) -> str:
    return f"{round(x * 100):.0f}%"


def auto_analysis(df: pd.DataFrame) -> dict:
    """Run a full analysis and return structured results + plain-language findings."""
    before = eda.profile_dataset(df)

    # 1) clean
    cleaned, _report = CleaningAgent().clean(df)
    after = eda.profile_dataset(cleaned)
    filled = max(0, before["missing_cells"] - after["missing_cells"])
    dupes_removed = before["duplicate_rows"]

    findings: list[str] = []
    findings.append(
        f"Your dataset has **{before['n_rows']:,} rows** and **{before['n_cols']} columns** "
        f"({before['n_numeric']} numeric, {before['n_categorical']} categorical).")
    if filled or dupes_removed:
        bits = []
        if filled:
            bits.append(f"filled **{filled:,}** missing values")
        if dupes_removed:
            bits.append(f"removed **{dupes_removed}** duplicate rows")
        findings.append("Cleaned automatically: " + " and ".join(bits) + ".")
    else:
        findings.append("The data was already clean — no missing values or duplicates.")

    # 2) strongest relationship
    top_corr = None
    sig = statistics.correlation_significance(cleaned)
    if not sig.empty:
        r = sig.iloc[0]
        top_corr = {"a": r["feature_a"], "b": r["feature_b"], "r": float(r["r"])}
        strength = ("strongly" if abs(r["r"]) >= 0.7 else
                    "moderately" if abs(r["r"]) >= 0.4 else "weakly")
        direction = "together" if r["r"] > 0 else "in opposite directions"
        findings.append(
            f"**{r['feature_a']}** and **{r['feature_b']}** move {strength} {direction} "
            f"(correlation r = {r['r']:.2f}).")

    # 3) modelling
    out = {
        "rows": before["n_rows"], "cols": before["n_cols"],
        "missing_pct": before["missing_pct"], "duplicates": before["duplicate_rows"],
        "filled": int(filled), "dupes_removed": int(dupes_removed),
        "top_correlation": top_corr, "cleaned_df": cleaned,
        "model_results": None, "target": None, "findings": findings,
        "headline": "Here is what the analysis found.",
    }

    target = modeling.suggest_target(cleaned)
    try:
        res = modeling.train_and_evaluate(cleaned, target)
    except Exception:
        res = None

    if res is not None:
        out["model_results"] = res
        out["target"] = target
        task = res["task"]
        score = res["best_score"]
        best = res["best_model"]
        rdf = res["results"]
        top_features = list(res["feature_importance"]["feature"].head(3)) \
            if res.get("feature_importance") is not None and not res["feature_importance"].empty else []

        if task == "classification":
            acc = float(rdf.loc[best, "accuracy"]) if "accuracy" in rdf.columns else score
            findings.append(
                f"To predict **{target}**, the best model (**{best}**) is correct about "
                f"**{_pct(acc)}** of the time (F1 score {score:.2f}).")
            out["headline"] = f"We can predict {target} with ~{_pct(acc)} accuracy."
        else:
            findings.append(
                f"To predict **{target}**, the best model (**{best}**) explains about "
                f"**{_pct(max(0.0, score))}** of the variation (R² {score:.2f}).")
            out["headline"] = f"We can explain {_pct(max(0.0, score))} of {target}."

        if top_features:
            out["top_features"] = top_features
            findings.append(
                "The biggest drivers are " +
                ", ".join(f"**{f}**" for f in top_features) + ".")
    else:
        out["headline"] = "Exploratory analysis complete."
        findings.append(
            "No predictive model was built (the data needs a clear target column "
            "and at least 20 rows).")

    return out
