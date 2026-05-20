/**
 * TraceViewerPage — granular execution trace for a single agent run.
 * Shows every tool call, reasoning step, input/output, and timing.
 */
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Wrench, MessageSquare, AlertCircle, Clock,
  ChevronRight, ChevronDown, ChevronUp, ArrowLeft
} from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { get }          from "@/lib/api";
import { PageHeader }   from "@/components/ui/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge }        from "@/components/ui/Badge";
import { Button }       from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState }   from "@/components/ui/EmptyState";
import { agentLabel, agentColor, formatDuration, cn } from "@/lib/utils";
import type { ExecutionTrace } from "@/types";

// ── Step type icon ─────────────────────────────────────────────────────────────
function StepIcon({ type }: { type: string }) {
  switch (type) {
    case "tool_call":    return <Wrench      className="w-3.5 h-3.5" />;
    case "llm_message":  return <MessageSquare className="w-3.5 h-3.5" />;
    case "error":        return <AlertCircle  className="w-3.5 h-3.5" />;
    default:             return <Clock        className="w-3.5 h-3.5" />;
  }
}

function stepVariant(type: string) {
  switch (type) {
    case "tool_call":   return "text-info    bg-info/10    border-info/30";
    case "llm_message": return "text-brand-400 bg-brand-500/10 border-brand-500/30";
    case "error":       return "text-danger  bg-danger/10  border-danger/30";
    default:            return "text-zinc-400 bg-surface-3   border-surface-4";
  }
}

// ── Trace step card ───────────────────────────────────────────────────────────
function TraceStepCard({ trace }: { trace: ExecutionTrace }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = trace.input_json || trace.output_json;

  return (
    <div className="card overflow-hidden">
      {/* Header row */}
      <div
        className={cn(
          "flex items-center gap-3 p-4",
          hasDetails && "cursor-pointer hover:bg-surface-3/30 transition-colors"
        )}
        onClick={() => hasDetails && setExpanded(v => !v)}
      >
        {/* Sequence number */}
        <span className="text-2xs text-zinc-600 font-mono w-8 shrink-0 text-right">
          #{trace.sequence_num}
        </span>

        {/* Step icon */}
        <div className={cn("flex items-center justify-center w-7 h-7 rounded-lg border shrink-0", stepVariant(trace.step_type))}>
          <StepIcon type={trace.step_type} />
        </div>

        {/* Name + summary */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold text-zinc-200 truncate">
              {trace.tool_name ?? trace.step_name}
            </p>
            {trace.tool_name && (
              <Badge variant="default" className="text-2xs">{trace.step_type}</Badge>
            )}
          </div>
          {trace.summary && (
            <p className="text-2xs text-zinc-500 mt-0.5 truncate">{trace.summary}</p>
          )}
          {trace.error_message && (
            <p className="text-2xs text-danger mt-0.5">{trace.error_message}</p>
          )}
        </div>

        {/* Duration */}
        {trace.duration_ms !== null && (
          <span className="text-2xs text-zinc-600 font-mono shrink-0">
            {formatDuration(trace.duration_ms)}
          </span>
        )}

        {/* Expand toggle */}
        {hasDetails && (
          <span className="text-zinc-600 shrink-0">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </span>
        )}
      </div>

      {/* Expanded I/O */}
      {expanded && (
        <div className="border-t border-surface-4 grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-surface-4">
          {trace.input_json && (
            <div className="p-4">
              <p className="text-2xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Input</p>
              <pre className="code-block text-2xs text-zinc-400 max-h-60 overflow-y-auto">
                {JSON.stringify(trace.input_json, null, 2)}
              </pre>
            </div>
          )}
          {trace.output_json && (
            <div className="p-4">
              <p className="text-2xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Output</p>
              <pre className="code-block text-2xs text-zinc-400 max-h-60 overflow-y-auto">
                {JSON.stringify(trace.output_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export function TraceViewerPage() {
  const { sessionId, agentRunId } = useParams<{ sessionId: string; agentRunId: string }>();
  const navigate = useNavigate();

  const { data: traces, isLoading } = useQuery({
    queryKey: ["traces", agentRunId],
    queryFn:  () => get<ExecutionTrace[]>(`/agents/${agentRunId}/traces`),
    enabled:  !!agentRunId,
  });

  const totalDuration = traces?.reduce((s, t) => s + (t.duration_ms ?? 0), 0) ?? 0;
  const toolCalls     = traces?.filter(t => t.step_type === "tool_call").length ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Agent Trace Viewer"
        description={`Execution trace for run ${agentRunId?.slice(0, 8)}`}
        breadcrumb={
          <span className="flex items-center gap-1">
            <Link to="/dashboard" className="hover:text-zinc-300">Dashboard</Link>
            <ChevronRight className="w-3 h-3" />
            <Link to={`/session/${sessionId}/timeline`} className="hover:text-zinc-300">Timeline</Link>
          </span>
        }
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </Button>
        }
      />

      {/* Summary stats */}
      {traces && traces.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <Card className="p-4">
            <p className="text-2xs text-zinc-500 mb-1">Total Steps</p>
            <p className="text-xl font-bold text-zinc-100">{traces.length}</p>
          </Card>
          <Card className="p-4">
            <p className="text-2xs text-zinc-500 mb-1">Tool Calls</p>
            <p className="text-xl font-bold text-zinc-100">{toolCalls}</p>
          </Card>
          <Card className="p-4">
            <p className="text-2xs text-zinc-500 mb-1">Total Time</p>
            <p className="text-xl font-bold text-zinc-100">{formatDuration(totalDuration)}</p>
          </Card>
        </div>
      )}

      {/* Trace list */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !traces || traces.length === 0 ? (
        <EmptyState
          icon={Wrench}
          title="No traces recorded"
          description="Execution traces may not be available for this agent run."
          action={{ label: "Back to Timeline", onClick: () => navigate(`/session/${sessionId}/timeline`) }}
        />
      ) : (
        <div className="space-y-2">
          {traces.map((trace) => (
            <TraceStepCard key={trace.id} trace={trace} />
          ))}
        </div>
      )}
    </div>
  );
}
