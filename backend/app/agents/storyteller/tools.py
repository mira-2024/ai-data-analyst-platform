"""
StorytellerAgent tool implementations.

These tools synthesize outputs from all upstream agents into
business-readable narrative components. They do NOT touch the DataFrame
directly — they operate on structured agent outputs and statistics.

All functions are synchronous and return JSON-serializable dicts.
"""

from __future__ import annotations

import math
from typing import Any


def build_executive_summary(
    dataset_description: str,
    key_findings: list[str],
    quality_score: float | None = None,
) -> dict:
    """
    Build the building blocks for a concise executive summary.

    Args:
        dataset_description: One-line description of the dataset
        key_findings:        List of the most important findings to highlight
        quality_score:       Data quality score (0.0–1.0) from CleanerAgent
    """
    if not key_findings:
        return {"error": "No key findings provided"}

    quality_assessment = ""
    if quality_score is not None:
        if quality_score >= 0.9:
            quality_assessment = "The data is of high quality and findings are reliable."
        elif quality_score >= 0.7:
            quality_assessment = "The data is of moderate quality; findings are generally reliable with minor caveats."
        else:
            quality_assessment = (
                "The data has notable quality issues (score: "
                f"{quality_score:.0%}); interpret findings with caution."
            )

    return {
        "dataset_description": dataset_description,
        "finding_count": len(key_findings),
        "top_findings": key_findings[:5],
        "quality_assessment": quality_assessment,
        "quality_score": quality_score,
    }


def build_finding_narrative(
    title: str,
    description: str,
    supporting_data: dict[str, Any],
    category: str = "general",
    importance: str = "medium",
) -> dict:
    """
    Structure a single analytical finding into a narrative block.

    Args:
        title:          Short finding title
        description:    Full finding description with specific numbers
        supporting_data: Key statistics that back the finding
        category:       Finding category (correlation, anomaly, trend, distribution, comparison)
        importance:     high | medium | low
    """
    # Derive a plain-English implication from the category
    implication_map = {
        "correlation": "This relationship may enable predictive modeling or root-cause analysis.",
        "anomaly": "These anomalies may represent data quality issues, fraud, or exceptional events worth investigating.",
        "trend": "This trajectory should inform planning and forecasting decisions.",
        "distribution": "Understanding this distribution helps set realistic benchmarks and targets.",
        "comparison": "Group differences suggest segmentation may improve targeting or operations.",
    }
    default_implication = "This finding warrants further investigation and stakeholder review."
    implication = implication_map.get(category.lower(), default_implication)

    # Format supporting statistics for readability
    stat_lines = []
    for key, val in supporting_data.items():
        if isinstance(val, float):
            stat_lines.append(f"{key}: {val:,.4g}")
        else:
            stat_lines.append(f"{key}: {val}")

    return {
        "title": title,
        "description": description,
        "category": category,
        "importance": importance,
        "implication": implication,
        "supporting_statistics": supporting_data,
        "formatted_stats": stat_lines,
    }


def build_recommendation(
    action: str,
    rationale: str,
    expected_impact: str,
    priority: str = "medium",
    owner_role: str | None = None,
    timeframe: str | None = None,
) -> dict:
    """
    Structure a single actionable recommendation.

    Args:
        action:          Specific, imperative action (e.g., "Investigate the 12% outlier rate in column X")
        rationale:       Why this action is needed (link back to a finding)
        expected_impact: Measurable expected outcome
        priority:        high | medium | low
        owner_role:      Suggested team or role responsible (optional)
        timeframe:       Suggested timeframe (e.g., "Within 2 weeks") (optional)
    """
    if not action or not rationale:
        return {"error": "Action and rationale are required"}

    priority_weight = {"high": 3, "medium": 2, "low": 1}.get(priority.lower(), 2)

    return {
        "action": action,
        "rationale": rationale,
        "expected_impact": expected_impact,
        "priority": priority.lower(),
        "priority_weight": priority_weight,
        "owner_role": owner_role,
        "timeframe": timeframe,
    }


def compute_dataset_health_score(
    quality_score: float | None,
    insight_count: int,
    anomaly_count: int,
    row_count: int,
    column_count: int,
) -> dict:
    """
    Compute a holistic dataset health score for the report header.

    Args:
        quality_score:  CleanerAgent quality score (0.0–1.0)
        insight_count:  Number of insights found by AnalystAgent
        anomaly_count:  Total anomalies detected
        row_count:      Dataset row count
        column_count:   Dataset column count
    """
    # Weighted health calculation
    data_quality = (quality_score or 0.5) * 40          # Max 40 points
    insight_richness = min(insight_count / 5, 1.0) * 30  # Max 30 points (5+ insights = full score)
    anomaly_penalty = max(0, 15 - (anomaly_count / max(row_count, 1)) * 1000)  # Max 15 points
    size_score = min(math.log10(max(row_count, 1)) / 4, 1.0) * 15  # Max 15 points (log scale)

    total = data_quality + insight_richness + anomaly_penalty + size_score

    if total >= 80:
        grade, label = "A", "Excellent"
    elif total >= 65:
        grade, label = "B", "Good"
    elif total >= 50:
        grade, label = "C", "Fair"
    else:
        grade, label = "D", "Needs Improvement"

    return {
        "overall_score": round(total, 1),
        "grade": grade,
        "label": label,
        "breakdown": {
            "data_quality": round(data_quality, 1),
            "insight_richness": round(insight_richness, 1),
            "anomaly_score": round(anomaly_penalty, 1),
            "dataset_size_score": round(size_score, 1),
        },
        "row_count": row_count,
        "column_count": column_count,
        "insight_count": insight_count,
        "anomaly_count": anomaly_count,
    }


def extract_key_takeaways(
    insights: list[dict],
    max_takeaways: int = 5,
) -> dict:
    """
    Extract the most important takeaways from the full insight list.

    Args:
        insights:       List of insight dicts (with title, description, importance, confidence)
        max_takeaways:  Maximum number of takeaways to return
    """
    if not insights:
        return {"error": "No insights provided", "takeaways": []}

    # Score insights by importance × confidence
    importance_map = {"high": 3, "medium": 2, "low": 1}
    scored = []
    for ins in insights:
        score = importance_map.get(ins.get("importance", "medium"), 2) * float(ins.get("confidence", 0.7))
        scored.append((score, ins))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [item for _, item in scored[:max_takeaways]]

    takeaways = []
    for ins in top:
        # Condense to a single punchy sentence
        takeaways.append(f"{ins.get('title', 'Finding')}: {ins.get('description', '')}")

    return {
        "takeaways": takeaways,
        "total_insights_processed": len(insights),
        "takeaway_count": len(takeaways),
    }
