"""
VisualizerAgent tool implementations.

Each function takes a DataFrame + column names and returns a complete
Plotly figure dict ready for frontend rendering via Plotly.js.

Design rules:
  - All charts use the dark theme (plotly_dark base + brand overrides)
  - Data arrays are computed from real DataFrame values — no fake data
  - Every figure dict is validated to be JSON-serializable before return
  - Functions return {"chart_type", "title", "plotly_figure", "columns_used"}
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd

# ── Brand design tokens (mirror frontend CSS variables) ────────────────────────
BRAND_COLOR = "#6366f1"
BRAND_COLORS = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981",
    "#f59e0b", "#ef4444", "#ec4899", "#84cc16",
]
DARK_BG = "rgba(17,17,19,1)"
PAPER_BG = "rgba(0,0,0,0)"
FONT_FAMILY = "Inter, system-ui, sans-serif"

BASE_LAYOUT = {
    "paper_bgcolor": PAPER_BG,
    "plot_bgcolor": DARK_BG,
    "font": {"family": FONT_FAMILY, "size": 13, "color": "#a1a1aa"},
    "title_font": {"family": FONT_FAMILY, "size": 15, "color": "#f4f4f5"},
    "margin": {"t": 60, "r": 24, "b": 60, "l": 64},
    "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"color": "#a1a1aa"}},
    "xaxis": {
        "gridcolor": "#2a2a32",
        "linecolor": "#2a2a32",
        "tickfont": {"color": "#71717a"},
    },
    "yaxis": {
        "gridcolor": "#2a2a32",
        "linecolor": "#2a2a32",
        "tickfont": {"color": "#71717a"},
    },
}


def _base_layout(title: str, xaxis_title: str = "", yaxis_title: str = "") -> dict:
    layout = dict(BASE_LAYOUT)
    layout["title"] = {"text": title, "x": 0.0, "xanchor": "left"}
    if xaxis_title:
        layout["xaxis"] = {**layout["xaxis"], "title": {"text": xaxis_title, "font": {"color": "#71717a"}}}
    if yaxis_title:
        layout["yaxis"] = {**layout["yaxis"], "title": {"text": yaxis_title, "font": {"color": "#71717a"}}}
    return layout


def create_bar_chart(
    df: pd.DataFrame,
    category_column: str,
    value_column: str | None = None,
    title: str | None = None,
    top_n: int = 15,
) -> dict:
    """
    Create a horizontal bar chart showing category frequencies or aggregated values.

    Args:
        category_column: Categorical column for the y-axis
        value_column:    Numeric column to aggregate (None = count occurrences)
        title:           Chart title
        top_n:           Show top N categories only
    """
    if category_column not in df.columns:
        return {"error": f"Column '{category_column}' not found"}

    if value_column and value_column in df.columns:
        data = df.groupby(category_column)[value_column].mean().sort_values(ascending=True).tail(top_n)
        y_label = f"Avg {value_column}"
    else:
        data = df[category_column].value_counts().tail(top_n).sort_values(ascending=True)
        y_label = "Count"

    categories = [str(v) for v in data.index.tolist()]
    values = [_safe(v) for v in data.values.tolist()]

    fig = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": values,
            "y": categories,
            "marker": {
                "color": BRAND_COLOR,
                "opacity": 0.9,
                "line": {"color": BRAND_COLOR, "width": 0},
            },
            "hovertemplate": "%{y}: %{x:,.0f}<extra></extra>",
        }],
        "layout": _base_layout(
            title or f"{category_column} Distribution",
            xaxis_title=y_label,
            yaxis_title=category_column,
        ),
    }

    return {
        "chart_type": "bar",
        "title": title or f"{category_column} Distribution",
        "columns_used": [category_column] + ([value_column] if value_column else []),
        "plotly_figure": _safe_fig(fig),
    }


def create_histogram(
    df: pd.DataFrame,
    column: str,
    bins: int = 30,
    title: str | None = None,
) -> dict:
    """
    Create a histogram with KDE overlay for a numeric column.
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric"}

    values = df[column].dropna().tolist()
    values = [_safe(v) for v in values if v is not None]

    fig = {
        "data": [{
            "type": "histogram",
            "x": values,
            "nbinsx": bins,
            "marker": {
                "color": BRAND_COLOR,
                "opacity": 0.8,
                "line": {"color": "#111113", "width": 0.5},
            },
            "hovertemplate": "Value: %{x}<br>Count: %{y}<extra></extra>",
        }],
        "layout": {
            **_base_layout(
                title or f"Distribution of {column}",
                xaxis_title=column,
                yaxis_title="Frequency",
            ),
            "bargap": 0.05,
        },
    }

    return {
        "chart_type": "histogram",
        "title": title or f"Distribution of {column}",
        "columns_used": [column],
        "plotly_figure": _safe_fig(fig),
    }


def create_scatter_plot(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str | None = None,
    title: str | None = None,
    sample_size: int = 2000,
) -> dict:
    """
    Create a scatter plot between two numeric columns, with optional color grouping.
    Samples large datasets to keep the frontend responsive.
    """
    for col in [x_column, y_column]:
        if col not in df.columns:
            return {"error": f"Column '{col}' not found"}

    plot_df = df[[x_column, y_column] + ([color_column] if color_column and color_column in df.columns else [])].dropna()

    if len(plot_df) > sample_size:
        plot_df = plot_df.sample(sample_size, random_state=42)

    traces = []
    if color_column and color_column in plot_df.columns:
        for i, group in enumerate(plot_df[color_column].unique()):
            mask = plot_df[color_column] == group
            subset = plot_df[mask]
            traces.append({
                "type": "scatter",
                "mode": "markers",
                "name": str(group),
                "x": [_safe(v) for v in subset[x_column].tolist()],
                "y": [_safe(v) for v in subset[y_column].tolist()],
                "marker": {
                    "color": BRAND_COLORS[i % len(BRAND_COLORS)],
                    "size": 6,
                    "opacity": 0.7,
                },
                "hovertemplate": f"{x_column}: %{{x}}<br>{y_column}: %{{y}}<extra>{group}</extra>",
            })
    else:
        # Add trend line
        x_vals = [_safe(v) for v in plot_df[x_column].tolist()]
        y_vals = [_safe(v) for v in plot_df[y_column].tolist()]

        traces.append({
            "type": "scatter",
            "mode": "markers",
            "name": "Data",
            "x": x_vals,
            "y": y_vals,
            "marker": {"color": BRAND_COLOR, "size": 5, "opacity": 0.65},
            "hovertemplate": f"{x_column}: %{{x}}<br>{y_column}: %{{y}}<extra></extra>",
        })

        # Add OLS trend line
        try:
            x_arr = np.array([v for v in x_vals if v is not None], dtype=float)
            y_arr = np.array([v for v in y_vals if v is not None], dtype=float)
            valid = ~(np.isnan(x_arr) | np.isnan(y_arr))
            if valid.sum() > 2:
                coeffs = np.polyfit(x_arr[valid], y_arr[valid], 1)
                x_line = [float(x_arr[valid].min()), float(x_arr[valid].max())]
                y_line = [float(np.polyval(coeffs, v)) for v in x_line]
                traces.append({
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Trend",
                    "x": x_line,
                    "y": y_line,
                    "line": {"color": "#ef4444", "width": 2, "dash": "dash"},
                    "hoverinfo": "skip",
                })
        except Exception:
            pass

    fig = {
        "data": traces,
        "layout": _base_layout(
            title or f"{x_column} vs {y_column}",
            xaxis_title=x_column,
            yaxis_title=y_column,
        ),
    }

    return {
        "chart_type": "scatter",
        "title": title or f"{x_column} vs {y_column}",
        "columns_used": [x_column, y_column] + ([color_column] if color_column else []),
        "plotly_figure": _safe_fig(fig),
    }


def create_correlation_heatmap(df: pd.DataFrame, title: str | None = None) -> dict:
    """
    Create a correlation matrix heatmap for all numeric columns.
    """
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return {"error": "Need at least 2 numeric columns for a correlation heatmap"}

    corr = numeric_df.corr(method="pearson")
    cols = corr.columns.tolist()

    z = []
    for col in cols:
        row = []
        for c2 in cols:
            val = corr.loc[col, c2]
            row.append(None if math.isnan(val) else round(float(val), 3))
        z.append(row)

    fig = {
        "data": [{
            "type": "heatmap",
            "x": cols,
            "y": cols,
            "z": z,
            "colorscale": "RdBu",
            "zmid": 0,
            "zmin": -1,
            "zmax": 1,
            "text": [[str(v) if v is not None else "" for v in row] for row in z],
            "texttemplate": "%{text}",
            "textfont": {"size": 10, "color": "#f4f4f5"},
            "hovertemplate": "%{x} × %{y}: %{z:.3f}<extra></extra>",
            "colorbar": {
                "tickfont": {"color": "#71717a"},
                "title": {"text": "r", "font": {"color": "#a1a1aa"}},
            },
        }],
        "layout": {
            **_base_layout(title or "Correlation Matrix"),
            "xaxis": {
                **BASE_LAYOUT["xaxis"],
                "tickangle": -45,
                "tickfont": {"color": "#71717a", "size": 11},
            },
        },
    }

    return {
        "chart_type": "correlation_matrix",
        "title": title or "Correlation Matrix",
        "columns_used": cols,
        "plotly_figure": _safe_fig(fig),
    }


def create_line_chart(
    df: pd.DataFrame,
    x_column: str,
    y_columns: list[str],
    title: str | None = None,
) -> dict:
    """
    Create a line chart for time-series or ordered data.

    Args:
        x_column:  Datetime or ordered numeric column for x-axis
        y_columns: One or more numeric columns to plot as lines
    """
    if x_column not in df.columns:
        return {"error": f"Column '{x_column}' not found"}

    valid_y = [c for c in y_columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not valid_y:
        return {"error": "No valid numeric y-columns found"}

    temp = df[[x_column] + valid_y].dropna(subset=[x_column]).sort_values(x_column)

    try:
        x_vals = pd.to_datetime(temp[x_column]).dt.strftime("%Y-%m-%d").tolist()
    except Exception:
        x_vals = temp[x_column].astype(str).tolist()

    traces = []
    for i, col in enumerate(valid_y):
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "name": col,
            "x": x_vals,
            "y": [_safe(v) for v in temp[col].tolist()],
            "line": {"color": BRAND_COLORS[i % len(BRAND_COLORS)], "width": 2},
            "marker": {"size": 4},
            "hovertemplate": f"{col}: %{{y:,.2f}}<extra></extra>",
        })

    fig = {
        "data": traces,
        "layout": _base_layout(
            title or f"Trend: {', '.join(valid_y)}",
            xaxis_title=x_column,
            yaxis_title=valid_y[0] if len(valid_y) == 1 else "Value",
        ),
    }

    return {
        "chart_type": "time_series",
        "title": title or f"Trend: {', '.join(valid_y)}",
        "columns_used": [x_column] + valid_y,
        "plotly_figure": _safe_fig(fig),
    }


def create_box_plot(
    df: pd.DataFrame,
    value_column: str,
    group_column: str | None = None,
    title: str | None = None,
) -> dict:
    """
    Create a box plot showing distribution and outliers.

    Args:
        value_column: Numeric column
        group_column: Optional categorical column to group boxes
    """
    if value_column not in df.columns:
        return {"error": f"Column '{value_column}' not found"}

    traces = []
    if group_column and group_column in df.columns:
        for i, group in enumerate(df[group_column].dropna().unique()):
            vals = df[df[group_column] == group][value_column].dropna()
            traces.append({
                "type": "box",
                "name": str(group),
                "y": [_safe(v) for v in vals.tolist()],
                "marker": {"color": BRAND_COLORS[i % len(BRAND_COLORS)]},
                "boxmean": "sd",
                "hovertemplate": f"{group}<br>%{{y}}<extra></extra>",
            })
    else:
        vals = df[value_column].dropna()
        traces.append({
            "type": "box",
            "name": value_column,
            "y": [_safe(v) for v in vals.tolist()],
            "marker": {"color": BRAND_COLOR},
            "boxmean": "sd",
        })

    fig = {
        "data": traces,
        "layout": _base_layout(
            title or f"Distribution of {value_column}",
            yaxis_title=value_column,
            xaxis_title=group_column or "",
        ),
    }

    return {
        "chart_type": "box",
        "title": title or f"Distribution of {value_column}",
        "columns_used": [value_column] + ([group_column] if group_column else []),
        "plotly_figure": _safe_fig(fig),
    }


# ── Utilities ─────────────────────────────────────────────────────────────────

def _safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return value


def _safe_fig(fig: dict) -> dict:
    """Ensure figure is fully JSON-serializable."""
    return json.loads(json.dumps(fig, default=str))
