"""
StorytellerAgent — business narrative generation and report synthesis.

Final agent in the pipeline. Consumes structured outputs from:
  - CleanerAgent  → quality score, cleaning actions
  - AnalystAgent  → insights, correlations, key statistics
  - VisualizerAgent → chart titles and descriptions

Produces a human-readable executive report with:
  - Executive summary
  - Narrative finding blocks
  - Actionable recommendations
  - Key takeaways
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.agents.llm_client import LLMResponse, ToolDefinition
from app.agents.storyteller.tools import (
    build_executive_summary,
    build_finding_narrative,
    build_recommendation,
    compute_dataset_health_score,
    extract_key_takeaways,
)
from app.orchestration.event_bus import EventBus
from app.orchestration.events import ReportCreatedEvent
from app.orchestration.state import AnalysisState
from app.schemas.agent import NarrativeBlock, Recommendation, StorytellerOutput


class StorytellerAgent(BaseAgent):
    agent_name = "storyteller"

    def __init__(self, bus: EventBus, db: AsyncSession) -> None:
        super().__init__(bus=bus, db=db)

    # ── Tool definitions ───────────────────────────────────────────────────────

    def _get_tools(self) -> list[ToolDefinition]:
        return [
            {
                "name": "build_executive_summary",
                "description": (
                    "Build the building blocks for the executive summary section. "
                    "Call this first to frame the overall narrative."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dataset_description": {
                            "type": "string",
                            "description": "One-line description of the dataset and what it represents",
                        },
                        "key_findings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of 3–5 most important findings with specific numbers",
                        },
                        "quality_score": {
                            "type": "number",
                            "description": "Data quality score from CleanerAgent (0.0–1.0)",
                        },
                    },
                    "required": ["dataset_description", "key_findings"],
                },
            },
            {
                "name": "build_finding_narrative",
                "description": (
                    "Structure a single analytical finding into a narrative block. "
                    "Call once per major insight (3–5 times)."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short, punchy finding title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Full finding description with specific statistics and column names",
                        },
                        "supporting_data": {
                            "type": "object",
                            "description": "Key statistics that support this finding (e.g. {'mean': 42.3, 'std': 8.1})",
                        },
                        "category": {
                            "type": "string",
                            "description": "correlation | anomaly | trend | distribution | comparison",
                        },
                        "importance": {
                            "type": "string",
                            "description": "high | medium | low",
                        },
                    },
                    "required": ["title", "description", "supporting_data"],
                },
            },
            {
                "name": "build_recommendation",
                "description": (
                    "Structure a single actionable business recommendation. "
                    "Call once per recommendation (2–4 times)."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Specific imperative action the business should take",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this action is needed — link to a specific finding",
                        },
                        "expected_impact": {
                            "type": "string",
                            "description": "Concrete measurable expected outcome",
                        },
                        "priority": {
                            "type": "string",
                            "description": "high | medium | low",
                        },
                        "owner_role": {
                            "type": "string",
                            "description": "Suggested team or role responsible (optional)",
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Suggested timeframe (e.g. 'Within 2 weeks') (optional)",
                        },
                    },
                    "required": ["action", "rationale", "expected_impact"],
                },
            },
            {
                "name": "compute_dataset_health_score",
                "description": (
                    "Compute a holistic dataset health score. "
                    "Call this once to generate the report's health badge."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "quality_score": {
                            "type": "number",
                            "description": "CleanerAgent quality score (0.0–1.0)",
                        },
                        "insight_count": {
                            "type": "integer",
                            "description": "Number of insights found",
                        },
                        "anomaly_count": {
                            "type": "integer",
                            "description": "Total anomalies across all columns",
                        },
                        "row_count": {"type": "integer", "description": "Dataset row count"},
                        "column_count": {"type": "integer", "description": "Dataset column count"},
                    },
                    "required": ["insight_count", "anomaly_count", "row_count", "column_count"],
                },
            },
            {
                "name": "extract_key_takeaways",
                "description": (
                    "Extract the most important takeaways ranked by insight importance and confidence. "
                    "Call once after all narrative blocks are built."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "insights": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "importance": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                            },
                            "description": "Full list of insights from the AnalystAgent",
                        },
                        "max_takeaways": {
                            "type": "integer",
                            "description": "Maximum number of takeaways to return (default 5)",
                        },
                    },
                    "required": ["insights"],
                },
            },
        ]

    # ── Tool dispatch ──────────────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, tool_input: dict):
        if tool_name == "build_executive_summary":
            return build_executive_summary(
                dataset_description=tool_input["dataset_description"],
                key_findings=tool_input["key_findings"],
                quality_score=tool_input.get("quality_score"),
            )
        if tool_name == "build_finding_narrative":
            return build_finding_narrative(
                title=tool_input["title"],
                description=tool_input["description"],
                supporting_data=tool_input.get("supporting_data", {}),
                category=tool_input.get("category", "general"),
                importance=tool_input.get("importance", "medium"),
            )
        if tool_name == "build_recommendation":
            return build_recommendation(
                action=tool_input["action"],
                rationale=tool_input["rationale"],
                expected_impact=tool_input["expected_impact"],
                priority=tool_input.get("priority", "medium"),
                owner_role=tool_input.get("owner_role"),
                timeframe=tool_input.get("timeframe"),
            )
        if tool_name == "compute_dataset_health_score":
            return compute_dataset_health_score(
                quality_score=tool_input.get("quality_score"),
                insight_count=tool_input["insight_count"],
                anomaly_count=tool_input["anomaly_count"],
                row_count=tool_input["row_count"],
                column_count=tool_input["column_count"],
            )
        if tool_name == "extract_key_takeaways":
            return extract_key_takeaways(
                insights=tool_input["insights"],
                max_takeaways=tool_input.get("max_takeaways", 5),
            )

        return {"error": f"Unknown tool: {tool_name}"}

    # ── Prompt construction ────────────────────────────────────────────────────

    def _build_user_message(self, state: AnalysisState) -> str:
        summary = state["agent_summary"]
        cleaner_output = state.get("cleaner_output")
        analyst_output = state.get("analyst_output")
        visualizer_output = state.get("visualizer_output")

        # Cleaner section
        cleaner_section = ""
        quality_score = None
        if cleaner_output:
            quality_score = cleaner_output.quality_score
            cleaner_section = f"""
## Data Quality Report (CleanerAgent)
- Quality score: {cleaner_output.quality_score:.2f}
- Rows cleaned: {cleaner_output.rows_before} → {cleaner_output.rows_after}
- Actions taken: {len(cleaner_output.actions)}
- Summary: {cleaner_output.summary}
"""

        # Analyst section
        analyst_section = ""
        insights_json = "[]"
        if analyst_output:
            insight_dicts = [
                {
                    "title": i.title,
                    "description": i.description,
                    "category": i.category,
                    "confidence": i.confidence,
                    "importance": i.importance,
                    "columns_involved": i.columns_involved,
                    "supporting_statistics": i.supporting_statistics,
                }
                for i in analyst_output.insights
            ]
            insights_json = json.dumps(insight_dicts, indent=2)

            corr_lines = "\n".join(
                f"  • {c.column_a} ↔ {c.column_b}: r={c.correlation:.3f} — {c.interpretation}"
                for c in analyst_output.correlations[:5]
            )

            analyst_section = f"""
## Analytical Findings (AnalystAgent)
### Summary
{analyst_output.summary}

### Insights ({len(analyst_output.insights)} total)
{insights_json}

### Key Correlations
{corr_lines}

### Hypothesis
{json.dumps(analyst_output.hypothesis, indent=2)}
"""

        # Visualizer section
        visualizer_section = ""
        if visualizer_output and visualizer_output.charts:
            chart_lines = "\n".join(
                f"  • [{c.chart_type}] {c.title}: {c.description}"
                for c in visualizer_output.charts
            )
            visualizer_section = f"""
## Visualizations Generated (VisualizerAgent)
{chart_lines}
"""

        return f"""You are writing the final business intelligence report for a senior executive audience.
Synthesize ALL agent outputs into a clear, professional narrative.

## Dataset Overview
- Name: {summary.get('name', 'Dataset')}
- Shape: {summary['shape']['rows']} rows × {summary['shape']['columns']} columns
- Numeric columns: {[c['name'] for c in summary['columns'] if c['dtype'] in ('integer', 'float', 'numeric')]}
- Categorical columns: {[c['name'] for c in summary['columns'] if c['dtype'] in ('object', 'string', 'category')]}
{cleaner_section}{analyst_section}{visualizer_section}

## Instructions
1. Call `build_executive_summary` first — frame the narrative with the top 3–5 findings
2. Call `compute_dataset_health_score` to generate the health badge
3. Call `build_finding_narrative` for each major insight (3–5 most impactful)
4. Call `build_recommendation` for each actionable recommendation (2–4)
5. Call `extract_key_takeaways` with the full insight list

After all tool calls, produce the final StorytellerOutput JSON:
```json
{{
  "title": "<dataset name> — Data Intelligence Report",
  "executive_summary": "<3–4 sentence executive summary with specific numbers. No jargon. C-suite readable.>",
  "narrative_blocks": [
    {{
      "block_type": "intro | finding | recommendation | conclusion",
      "heading": "<section heading>",
      "content": "<narrative paragraph with specific numbers and column names>",
      "importance": "high | medium | low"
    }}
  ],
  "recommendations": [
    {{
      "title": "<recommendation title>",
      "action": "<specific imperative action>",
      "rationale": "<why — link to finding>",
      "priority": "high | medium | low",
      "expected_impact": "<measurable expected outcome>"
    }}
  ],
  "key_takeaways": ["<takeaway 1>", "<takeaway 2>", "<takeaway 3>"]
}}
```

Rules:
- Always cite specific numbers (percentages, means, counts) — never vague statements
- Narrative arc: context → key findings → business implications → recommendations
- Every recommendation must reference a specific finding
- Executive summary must stand alone without requiring the full report
- Minimum 3 narrative blocks, minimum 2 recommendations, minimum 3 key takeaways
"""

    # ── Output parsing ─────────────────────────────────────────────────────────

    def _parse_output(self, llm_response: LLMResponse, state: AnalysisState) -> StorytellerOutput:
        try:
            data = self._extract_json_from_response(llm_response.content)
        except ValueError:
            return StorytellerOutput(
                title="Data Analysis Report",
                executive_summary="Analysis complete. Report generation encountered a parsing error.",
                narrative_blocks=[],
                recommendations=[],
                key_takeaways=[],
            )

        narrative_blocks = [
            NarrativeBlock(
                block_type=b.get("block_type", "finding"),
                heading=b.get("heading", "Finding"),
                content=b.get("content", ""),
                importance=b.get("importance", "medium"),
            )
            for b in data.get("narrative_blocks", [])
        ]

        recommendations = [
            Recommendation(
                title=r.get("title", "Recommendation"),
                action=r.get("action", ""),
                rationale=r.get("rationale", ""),
                priority=r.get("priority", "medium"),
                expected_impact=r.get("expected_impact", ""),
            )
            for r in data.get("recommendations", [])
        ]

        return StorytellerOutput(
            title=data.get("title", "Data Analysis Report"),
            executive_summary=data.get("executive_summary", ""),
            narrative_blocks=narrative_blocks,
            recommendations=recommendations,
            key_takeaways=data.get("key_takeaways", []),
        )

    # ── Main run ───────────────────────────────────────────────────────────────

    async def run(self, state: AnalysisState, bus: EventBus) -> AnalysisState:
        await self._emit_progress(state, "Building narrative", "Synthesizing findings into report", 0.05)

        llm_response = await self._run_llm(state)

        await self._emit_progress(state, "Structuring report", "Writing executive summary", 0.80)

        output = self._parse_output(llm_response, state)
        output._tokens_in = llm_response.tokens_in   # type: ignore[attr-defined]
        output._tokens_out = llm_response.tokens_out  # type: ignore[attr-defined]

        # Emit report created event for SSE
        visualizer_output = state.get("visualizer_output")
        analyst_output = state.get("analyst_output")
        await bus.emit(ReportCreatedEvent(
            session_id=state["session_id"],
            agent_run_id=state.get("storyteller_run_id"),
            agent_name="storyteller",
            report_id=state["session_id"],  # session-scoped; real report_id set by ReportService
            title=output.title,
            insight_count=len(analyst_output.insights) if analyst_output else 0,
            recommendation_count=len(output.recommendations),
            chart_count=len(visualizer_output.charts) if visualizer_output else 0,
        ))

        await self._emit_progress(state, "Done", "Report complete", 1.0)

        state["storyteller_output"] = output
        return state
