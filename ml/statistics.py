"""
Inferential statistics / hypothesis testing.

These functions answer the question a data-science examiner always asks of an
"insight": *is it statistically significant, or could it be noise?* Each test
returns the test statistic, the p-value, and a plain-language verdict at the
conventional alpha = 0.05 level. Built on SciPy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ml import eda

ALPHA = 0.05


def _verdict(p: float, alpha: float = ALPHA) -> str:
    return "significant" if (p is not None and not np.isnan(p) and p < alpha) else "not significant"


# ──────────────────────────────────────────────────────────────────────────────
# Normality
# ──────────────────────────────────────────────────────────────────────────────
def normality_test(series: pd.Series, alpha: float = ALPHA) -> dict:
    """
    Test whether a numeric column is normally distributed.

    Uses Shapiro-Wilk for small samples (n <= 5000) and D'Agostino-Pearson
    otherwise, since Shapiro-Wilk is unreliable on large samples.
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 8:
        return {"test": "n/a", "statistic": np.nan, "p_value": np.nan,
                "normal": None, "note": "too few observations (n < 8)"}

    if len(s) <= 5000:
        stat, p = stats.shapiro(s)
        test = "Shapiro-Wilk"
    else:
        stat, p = stats.normaltest(s)
        test = "D'Agostino-Pearson"

    return {
        "test": test,
        "statistic": round(float(stat), 4),
        "p_value": float(p),
        "normal": bool(p >= alpha),
        "note": "fails to reject normality" if p >= alpha else "departs from normality",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Correlation significance
# ──────────────────────────────────────────────────────────────────────────────
def correlation_significance(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """
    Pairwise correlations *with* p-values, so spurious correlations can be
    filtered out. method: 'pearson' (linear) or 'spearman' (monotonic/rank).
    """
    num = df[eda.numeric_columns(df)].dropna()
    # Drop constant (zero-variance) columns: their correlation is undefined and
    # would raise a ConstantInputWarning and produce NaN.
    num = num.loc[:, num.nunique() > 1]
    cols = num.columns
    if len(cols) < 2 or len(num) < 3:
        return pd.DataFrame()

    fn = stats.pearsonr if method == "pearson" else stats.spearmanr
    rows = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r, p = fn(num[cols[i]], num[cols[j]])
            rows.append(
                {
                    "feature_a": cols[i],
                    "feature_b": cols[j],
                    "r": round(float(r), 4),
                    "p_value": float(p),
                    "significant": _verdict(p),
                }
            )
    out = pd.DataFrame(rows)
    return out.reindex(out["r"].abs().sort_values(ascending=False).index).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# Group comparison: t-test & ANOVA
# ──────────────────────────────────────────────────────────────────────────────
def compare_groups(df: pd.DataFrame, numeric_col: str, group_col: str,
                   alpha: float = ALPHA) -> dict:
    """
    Compare the mean of ``numeric_col`` across the categories of ``group_col``.

    * 2 groups   → Welch's two-sample t-test (does not assume equal variance)
    * 3+ groups  → one-way ANOVA (F-test)
    """
    sub = df[[numeric_col, group_col]].dropna()
    groups = [g[numeric_col].values for _, g in sub.groupby(group_col, observed=True)
              if len(g) >= 2]
    labels = [k for k, g in sub.groupby(group_col, observed=True) if len(g) >= 2]
    if len(groups) < 2:
        return {"test": "n/a", "note": "need at least two groups with >= 2 observations"}

    if len(groups) == 2:
        stat, p = stats.ttest_ind(groups[0], groups[1], equal_var=False)
        test = "Welch t-test"
    else:
        stat, p = stats.f_oneway(*groups)
        test = "one-way ANOVA"

    means = {str(lbl): round(float(np.mean(g)), 4) for lbl, g in zip(labels, groups)}
    return {
        "test": test,
        "numeric": numeric_col,
        "group": group_col,
        "n_groups": len(groups),
        "group_means": means,
        "statistic": round(float(stat), 4),
        "p_value": float(p),
        "result": _verdict(p, alpha),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Chi-square test of independence
# ──────────────────────────────────────────────────────────────────────────────
def chi_square_independence(df: pd.DataFrame, col_a: str, col_b: str,
                            alpha: float = ALPHA) -> dict:
    """Test whether two categorical variables are independent (with Cramér's V)."""
    sub = df[[col_a, col_b]].dropna()
    if sub.empty:
        return {"test": "n/a", "note": "no overlapping non-null data"}

    table = pd.crosstab(sub[col_a], sub[col_b])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"test": "n/a", "note": "each variable needs >= 2 categories"}

    chi2, p, dof, _ = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    min_dim = min(table.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * min_dim))) if min_dim > 0 else np.nan

    return {
        "test": "chi-square independence",
        "var_a": col_a,
        "var_b": col_b,
        "chi2": round(float(chi2), 4),
        "dof": int(dof),
        "p_value": float(p),
        "cramers_v": round(cramers_v, 4),
        "result": _verdict(p, alpha),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Automatic feature-vs-target screen
# ──────────────────────────────────────────────────────────────────────────────
def feature_target_screen(df: pd.DataFrame, target: str, alpha: float = ALPHA) -> pd.DataFrame:
    """
    Automatically test each feature for association with ``target`` and rank
    by p-value. Picks the appropriate test for each feature/target type pair:

        numeric feature  vs categorical target → ANOVA / t-test
        categorical feat vs categorical target → chi-square
        numeric feature  vs numeric  target    → Pearson correlation
        categorical feat vs numeric  target    → ANOVA / t-test (groups on feature)
    """
    if target not in df.columns:
        return pd.DataFrame()

    num_cols = set(eda.numeric_columns(df))
    target_numeric = target in num_cols
    # Treat a low-cardinality numeric target as categorical (e.g. 0/1 labels).
    if target_numeric and df[target].nunique(dropna=True) <= eda.LOW_CARDINALITY_THRESHOLD:
        target_numeric = False

    rows = []
    for feat in df.columns:
        if feat == target:
            continue
        feat_numeric = feat in num_cols
        try:
            if target_numeric and feat_numeric:
                sub = df[[feat, target]].dropna()
                if len(sub) < 3 or sub[feat].nunique() < 2 or sub[target].nunique() < 2:
                    continue  # skip too-small or constant (zero-variance) columns
                r, p = stats.pearsonr(sub[feat], sub[target])
                rows.append({"feature": feat, "test": "pearson",
                             "statistic": round(float(r), 4), "p_value": float(p)})
            elif (not target_numeric) and feat_numeric:
                res = compare_groups(df, numeric_col=feat, group_col=target, alpha=alpha)
                if "p_value" in res:
                    rows.append({"feature": feat, "test": res["test"],
                                 "statistic": res["statistic"], "p_value": res["p_value"]})
            elif (not target_numeric) and (not feat_numeric):
                res = chi_square_independence(df, feat, target, alpha=alpha)
                if "p_value" in res:
                    rows.append({"feature": feat, "test": "chi-square",
                                 "statistic": res["chi2"], "p_value": res["p_value"]})
            else:  # numeric target, categorical feature
                res = compare_groups(df, numeric_col=target, group_col=feat, alpha=alpha)
                if "p_value" in res:
                    rows.append({"feature": feat, "test": res["test"],
                                 "statistic": res["statistic"], "p_value": res["p_value"]})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["significant"] = out["p_value"].apply(lambda p: _verdict(p, alpha))
    return out.sort_values("p_value").reset_index(drop=True)
