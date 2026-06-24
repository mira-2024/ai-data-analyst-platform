"""
ModelingAgent — the machine-learning agent.

This is the agent that gives the project its data-science backbone. It runs the
real scikit-learn pipeline in ``ml.modeling`` (task detection, cross-validated
training of several models, held-out evaluation, permutation feature
importance) and then produces:

  * a structured results dict (metrics tables, best model, importances),
  * Plotly figures (model comparison, feature importance, confusion matrix),
  * a markdown narrative that interprets the metrics — written by the LLM when
    available, or by a deterministic template when it is not.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px

from ml import modeling
from utils import llm


class ModelingAgent:
    def run(self, df: pd.DataFrame, target: str | None = None) -> dict:
        """
        Train and evaluate models. Returns:
            {text, figures, results, target, error}
        """
        if target is None:
            target = modeling.suggest_target(df)
        if target is None:
            return {"text": "Could not identify a target column to model.",
                    "figures": [], "results": None, "target": None, "error": True}

        try:
            res = modeling.train_and_evaluate(df, target)
        except ValueError as e:
            return {"text": f"Modeling could not run: {e}", "figures": [],
                    "results": None, "target": target, "error": True}

        figures = self._build_figures(res)
        text = self._narrate(res)
        return {"text": text, "figures": figures, "results": res,
                "target": target, "error": False}

    # ── visualisations ──────────────────────────────────────────────────────
    def _build_figures(self, res: dict) -> list[dict]:
        figs = []
        metric = res["primary_metric"]
        results_df = res["results"]

        # 1) Model comparison on the held-out metric
        comp = results_df[[metric]].reset_index()
        fig = px.bar(comp, x="model", y=metric, title=f"Model comparison ({metric.upper()})",
                     text=metric, template="plotly_white", color="model")
        fig.update_traces(textposition="outside")
        figs.append({"title": "Model comparison", "figure": fig,
                     "description": f"Held-out {metric.upper()} per candidate model."})

        # 2) Feature importance
        imp = res.get("feature_importance")
        if imp is not None and not imp.empty:
            top = imp.head(15).iloc[::-1]
            fig = px.bar(top, x="importance", y="feature", orientation="h",
                         title="Permutation feature importance",
                         template="plotly_white", error_x="std")
            figs.append({"title": "Feature importance", "figure": fig,
                         "description": "Drop in held-out score when each feature is shuffled."})

        # 3) Confusion matrix (classification only)
        cm = res.get("confusion_matrix")
        if cm is not None and not cm.empty:
            fig = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                            title=f"Confusion matrix — {res['best_model']}",
                            template="plotly_white", aspect="auto")
            figs.append({"title": "Confusion matrix", "figure": fig,
                         "description": "Rows = actual class, columns = predicted class."})
        return figs

    # ── narrative ───────────────────────────────────────────────────────────
    def _narrate(self, res: dict) -> str:
        metric = res["primary_metric"]
        best = res["best_model"]
        score = res["best_score"]
        results_df = res["results"]

        # Deterministic, always-correct summary built from the real numbers.
        lines = [
            f"### Predictive Modeling — `{res['target']}`",
            "",
            f"**Task type:** {res['task']}  ·  "
            f"**Train/Test split:** {res['n_train']}/{res['n_test']} rows  ·  "
            f"**Features used:** {res['n_features']}  ·  "
            f"**Cross-validation:** {res['cv_folds']}-fold",
            "",
            f"**Best model: {best}** (held-out {metric.upper()} = {score:.3f}).",
            "",
            "**Model leaderboard:**",
            "",
            results_df.to_markdown(),
        ]
        if res.get("dropped_id_columns"):
            lines += ["", f"_Identifier-like columns excluded from features: "
                          f"{', '.join(res['dropped_id_columns'])}._"]

        imp = res.get("feature_importance")
        if imp is not None and not imp.empty:
            top3 = ", ".join(f"`{r.feature}`" for r in imp.head(3).itertuples())
            lines += ["", f"**Most predictive features:** {top3}."]

        deterministic = "\n".join(lines)

        # Optional LLM interpretation layered on top of the real metrics.
        prompt = (
            "You are a data scientist explaining model results to a non-technical "
            "stakeholder. In 3-4 sentences, interpret these results: what the best "
            "model achieved, whether the performance is trustworthy (consider the "
            f"cross-validation std), and what the top features imply.\n\n{deterministic}"
        )
        interpretation = llm.narrate(prompt)
        if interpretation:
            return deterministic + "\n\n**Interpretation:**\n\n" + interpretation
        return deterministic
