// ── Dataset ────────────────────────────────────────────────────────────────────

export type DatasetStatus = "pending" | "profiling" | "ready" | "error";

export interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number | null;
  sample_values: unknown[];
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  columns: ColumnProfile[];
  likely_datetime_columns: string[];
  likely_id_columns: string[];
  quality_score: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  original_filename: string;
  file_size_bytes: number;
  file_extension: string;
  mime_type: string;
  row_count: number | null;
  column_count: number | null;
  status: DatasetStatus;
  schema_json: ColumnProfile[] | null;
  preview_json: Record<string, unknown>[] | null;
  statistics_json: DatasetProfile | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetListResponse {
  items: Dataset[];
  total: number;
  page: number;
  page_size: number;
}

// ── Analysis Session ───────────────────────────────────────────────────────────

export type SessionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type AgentStatus   = "pending" | "running" | "completed" | "failed" | "skipped";

export interface AgentRun {
  id: string;
  agent_name: string;
  status: AgentStatus;
  started_at: string | null;
  completed_at: string | null;
  tokens_input: number;
  tokens_output: number;
  error_message: string | null;
}

export interface AnalysisSession {
  id: string;
  dataset_id: string;
  status: SessionStatus;
  started_at: string | null;
  completed_at: string | null;
  total_tokens_used: number;
  config_json: Record<string, unknown>;
  agent_runs: AgentRun[];
  created_at: string;
  updated_at: string;
}

export interface AnalysisConfig {
  run_cleaner?: boolean;
  run_analyst?: boolean;
  run_visualizer?: boolean;
  run_storyteller?: boolean;
  focus_areas?: string[];
  max_charts?: number;
}

export interface StartAnalysisRequest {
  dataset_id: string;
  config?: AnalysisConfig;
}

export interface AnalysisSessionListResponse {
  items: AnalysisSession[];
  total: number;
}

// ── Agent outputs ──────────────────────────────────────────────────────────────

export interface Insight {
  title: string;
  description: string;
  category: string;
  confidence: number;
  columns_involved: string[];
  supporting_statistics: Record<string, unknown>;
  importance: "high" | "medium" | "low";
}

export interface CorrelationResult {
  column_a: string;
  column_b: string;
  correlation: number;
  interpretation: string;
}

export interface PlotlyChartSpec {
  chart_type: string;
  title: string;
  description: string;
  columns_used: string[];
  plotly_figure: Record<string, unknown>;
  insight_context: string;
}

export interface NarrativeBlock {
  block_type: string;
  heading: string;
  content: string;
  importance: "high" | "medium" | "low";
}

export interface Recommendation {
  title: string;
  action: string;
  rationale: string;
  priority: "high" | "medium" | "low";
  expected_impact: string;
}

// ── Report ─────────────────────────────────────────────────────────────────────

export interface Report {
  id: string;
  session_id: string;
  dataset_id: string;
  title: string;
  executive_summary: string;
  narrative_json: NarrativeBlock[];
  insights_json: Insight[];
  recommendations_json: Recommendation[];
  charts: PlotlyChartSpec[];
  created_at: string;
}

// ── Execution Trace ────────────────────────────────────────────────────────────

export interface ExecutionTrace {
  id: string;
  step_type: string;
  step_name: string;
  tool_name: string | null;
  sequence_num: number;
  duration_ms: number | null;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  summary: string | null;
  error_message: string | null;
}

// ── SSE Events ────────────────────────────────────────────────────────────────

export type WorkflowEventType =
  | "ANALYSIS_STARTED"
  | "AGENT_STARTED"
  | "AGENT_COMPLETED"
  | "AGENT_FAILED"
  | "TOOL_CALLED"
  | "TOOL_COMPLETED"
  | "TOOL_FAILED"
  | "ANALYSIS_PROGRESS"
  | "CLEANING_COMPLETED"
  | "INSIGHT_GENERATED"
  | "CHART_GENERATED"
  | "REPORT_CREATED"
  | "ANALYSIS_COMPLETED"
  | "ANALYSIS_FAILED"
  | "STREAM_CLOSED"
  | "REPLAY_COMPLETE";

export interface WorkflowEvent {
  event_id: string;
  event_type: WorkflowEventType;
  session_id: string;
  agent_run_id: string | null;
  agent_name: string | null;
  emitted_at: string;
  sequence_num: number;
  // Agent-specific fields
  step?: string;
  message?: string;
  progress?: number;
  title?: string;
  description?: string;
  category?: string;
  confidence?: number;
  chart_type?: string;
  columns_used?: string[];
  error?: string;
  [key: string]: unknown;
}
