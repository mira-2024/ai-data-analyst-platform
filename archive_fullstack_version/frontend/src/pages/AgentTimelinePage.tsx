/**
 * AgentTimelinePage — the heart of DataFlow.
 *
 * Shows the real-time multi-agent pipeline in action:
 *  - Live SSE event stream for running sessions
 *  - Stored event replay for completed sessions
 *  - Per-agent status cards with progress bars
 *  - Scrollable event log with timestamps and type icons
 *  - Tool call details expandable inline
 */

import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Activity, CheckCircle2, AlertCircle, Clock,
  ChevronRight, Wrench, Lightbulb, BarChart3,
  FileText, Zap, ArrowRight, XCircle, Radio,
  RotateCcw, Eye
} from "lucide-react";
import { PageHeader }     from "@/components/ui/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button }         from "@/components/ui/Button";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { ProgressBar }    from "@/components/ui/ProgressBar";
import { SkeletonCard }   from "@/components/ui/Skeleton";
import { useSession, useCancelSession } from "@/hooks/useAnalysis";
import { useSSE, getAgentProgress }     from "@/hooks/useSSE";
import { toast }          from "@/components/ui/Toaster";
import { agentLabel, agentColor, formatDate, cn } from "@/lib/utils";
import type { WorkflowEvent, AgentRun } from "@/types";

// ── Agent status icon ─────────────────────────────────────────────────────────
function AgentIcon({ status }: { status: string }) {
  const base = "w-4 h-4";
  switch (status) {
    case "running":   return <Activity   className={cn(base, "text-brand-400 animate-pulse")} />;
    case "completed": return <CheckCircle2 className={cn(base, "text-success")} />;
    case "failed":    return <AlertCircle  className={cn(base, "text-danger")} />;
    case "skipped":   return <XCircle      className={cn(base, "text-zinc-600")} />;
    default:          return <Clock        className={cn(base, "text-zinc-600")} />;
  }
}

// ── Agent pipeline card ───────────────────────────────────────────────────────
function AgentCard({
  agentRun,
  progress,
  events,
  onViewTraces,
}: {
  agentRun: AgentRun;
  progress: number;
  events: WorkflowEvent[];
  onViewTraces: () => void;
}) {
  const lastProgress = events
    .filter(e => e.agent_name === agentRun.agent_name && e.event_type === "ANALYSIS_PROGRESS")
    .at(-1);

  const agentColorClass: Record<string, string> = {
    cleaner:     "border-info/30    bg-info/5",
    analyst:     "border-brand-500/30 bg-brand-500/5",
    visualizer:  "border-success/30  bg-success/5",
    storyteller: "border-warning/30  bg-warning/5",
  };

  const isActive = agentRun.status === "running";

  return (
    <div className={cn(
      "rounded-xl border p-4 transition-all duration-300",
      isActive
        ? (agentColorClass[agentRun.agent_name] ?? "border-surface-4 bg-surface-3/20")
        : "border-surface-4 bg-surface-3/10",
      isActive && "shadow-glow"
    )}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <AgentIcon status={agentRun.status} />
          <div>
            <p className={cn("text-sm font-semibold", agentColor(agentRun.agent_name))}>
              {agentLabel(agentRun.agent_name)}
            </p>
            {lastProgress && (
              <p className="text-2xs text-zinc-500 mt-0.5">{lastProgress.step as string}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusVariant(agentRun.status)}>
            {agentRun.status}
          </Badge>
          {agentRun.status === "completed" && (
            <Button variant="ghost" size="icon-sm" onClick={onViewTraces} title="View traces">
              <Eye className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Progress bar — only show when running or just completed */}
      {(agentRun.status === "running" || agentRun.status === "completed") && (
        <ProgressBar
          value={agentRun.status === "completed" ? 100 : progress * 100}
          size="sm"
          fillClassName={agentRun.status === "completed" ? "bg-success" : undefined}
          className="mb-2"
        />
      )}

      {/* Token count */}
      {agentRun.tokens_input + agentRun.tokens_output > 0 && (
        <p className="text-2xs text-zinc-600 mt-1">
          {(agentRun.tokens_input + agentRun.tokens_output).toLocaleString()} tokens
          {agentRun.started_at && agentRun.completed_at && ` · ${
            ((new Date(agentRun.completed_at).getTime() - new Date(agentRun.started_at).getTime()) / 1000).toFixed(1)
          }s`}
        </p>
      )}

      {/* Error message */}
      {agentRun.error_message && (
        <p className="text-2xs text-danger mt-2 leading-relaxed">{agentRun.error_message}</p>
      )}
    </div>
  );
}

// ── Event log item ────────────────────────────────────────────────────────────
const EVENT_ICONS: Record<string, typeof Activity> = {
  AGENT_STARTED:      Activity,
  AGENT_COMPLETED:    CheckCircle2,
  AGENT_FAILED:       AlertCircle,
  TOOL_CALLED:        Wrench,
  TOOL_COMPLETED:     Wrench,
  INSIGHT_GENERATED:  Lightbulb,
  CHART_GENERATED:    BarChart3,
  REPORT_CREATED:     FileText,
  ANALYSIS_PROGRESS:  Zap,
  ANALYSIS_STARTED:   Radio,
  ANALYSIS_COMPLETED: CheckCircle2,
  ANALYSIS_FAILED:    AlertCircle,
  CLEANING_COMPLETED: CheckCircle2,
};

const EVENT_COLORS: Record<string, string> = {
  AGENT_STARTED:      "text-brand-400",
  AGENT_COMPLETED:    "text-success",
  AGENT_FAILED:       "text-danger",
  TOOL_CALLED:        "text-zinc-400",
  TOOL_COMPLETED:     "text-zinc-400",
  INSIGHT_GENERATED:  "text-warning",
  CHART_GENERATED:    "text-success",
  REPORT_CREATED:     "text-brand-400",
  ANALYSIS_STARTED:   "text-info",
  ANALYSIS_COMPLETED: "text-success",
  ANALYSIS_FAILED:    "text-danger",
};

function EventLogItem({ event, isNew }: { event: WorkflowEvent; isNew: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = EVENT_ICONS[event.event_type] ?? Zap;
  const colorClass = EVENT_COLORS[event.event_type] ?? "text-zinc-500";

  const hasDetails = event.event_type === "TOOL_CALLED" || event.event_type === "TOOL_COMPLETED"
    || event.event_type === "INSIGHT_GENERATED" || event.event_type === "AGENT_FAILED";

  const mainLabel = (() => {
    switch (event.event_type) {
      case "AGENT_STARTED":      return `${agentLabel(event.agent_name ?? "")} started`;
      case "AGENT_COMPLETED":    return `${agentLabel(event.agent_name ?? "")} completed`;
      case "AGENT_FAILED":       return `${agentLabel(event.agent_name ?? "")} failed`;
      case "TOOL_CALLED":        return `Tool: ${(event.tool_name as string) ?? "unknown"}`;
      case "TOOL_COMPLETED":     return `Tool done: ${(event.tool_name as string) ?? "unknown"}`;
      case "ANALYSIS_PROGRESS":  return `${agentLabel(event.agent_name ?? "")} · ${event.step}`;
      case "INSIGHT_GENERATED":  return `Insight: ${event.title}`;
      case "CHART_GENERATED":    return `Chart: ${event.title}`;
      case "REPORT_CREATED":     return `Report ready: ${event.title}`;
      case "CLEANING_COMPLETED": return `Data cleaning complete`;
      case "ANALYSIS_STARTED":   return "Analysis pipeline started";
      case "ANALYSIS_COMPLETED": return "Analysis pipeline complete";
      case "ANALYSIS_FAILED":    return "Analysis pipeline failed";
      default: return event.event_type.replace(/_/g, " ");
    }
  })();

  return (
    <div className={cn(
      "flex gap-3 py-2 px-1 rounded-lg transition-all duration-300",
      isNew && "animate-slide-in"
    )}>
      {/* Timeline dot */}
      <div className="flex flex-col items-center gap-1 shrink-0 pt-0.5">
        <div className={cn("w-6 h-6 flex items-center justify-center rounded-full bg-surface-3 border border-surface-4", colorClass)}>
          <Icon className="w-3 h-3" />
        </div>
        <div className="w-px flex-1 bg-surface-4 min-h-[8px]" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium text-zinc-200 leading-relaxed">{mainLabel}</p>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-2xs text-zinc-600 font-mono whitespace-nowrap">
              #{event.sequence_num}
            </span>
            {hasDetails && (
              <button
                className="text-2xs text-zinc-600 hover:text-zinc-400 transition-colors"
                onClick={() => setExpanded(v => !v)}
              >
                {expanded ? "less" : "more"}
              </button>
            )}
          </div>
        </div>

        {/* Sub-label */}
        {(event.message || event.description) && (
          <p className="text-2xs text-zinc-500 mt-0.5 leading-relaxed">
            {(event.message as string) || (event.description as string)}
          </p>
        )}

        {/* Expanded details */}
        {expanded && (
          <pre className="code-block mt-2 text-2xs text-zinc-400 overflow-x-auto">
            {JSON.stringify(
              Object.fromEntries(
                Object.entries(event).filter(([k]) =>
                  !["event_type", "event_id", "session_id", "emitted_at", "sequence_num"].includes(k)
                )
              ),
              null,
              2
            )}
          </pre>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function AgentTimelinePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate      = useNavigate();
  const logBottomRef  = useRef<HTMLDivElement>(null);
  const prevCount     = useRef(0);

  const { data: session, isLoading, refetch } = useSession(sessionId);
  const cancel = useCancelSession();

  const { events, isConnected, isComplete } = useSSE(
    session?.status === "running" || session?.status === "pending" ? sessionId : null,
    {
      onComplete: () => {
        refetch();
        toast.success("Analysis complete!", "All agents finished successfully.");
      },
      onError: () => toast.error("Stream disconnected", "Trying to reconnect…"),
    }
  );

  // Auto-scroll event log
  useEffect(() => {
    if (events.length !== prevCount.current) {
      prevCount.current = events.length;
      logBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length]);

  const handleCancel = async () => {
    if (!sessionId) return;
    try {
      await cancel.mutateAsync(sessionId);
      toast.info("Session cancelled");
      refetch();
    } catch {
      toast.error("Failed to cancel session");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-fade-in">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-16 text-zinc-500 text-sm">Session not found.</div>
    );
  }

  const agentRuns = session.agent_runs;
  const isLive = session.status === "running" || session.status === "pending";

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Agent Workflow Timeline"
        description={`Session ${session.id.slice(0, 8)} · ${session.status}`}
        breadcrumb={
          <span className="flex items-center gap-1">
            <Link to="/dashboard" className="hover:text-zinc-300">Dashboard</Link>
            <ChevronRight className="w-3 h-3" />
            <Link to={`/workspace/${session.dataset_id}`} className="hover:text-zinc-300">Dataset</Link>
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            {/* Live indicator */}
            {isConnected && (
              <span className="flex items-center gap-1.5 text-xs text-success">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                Live
              </span>
            )}

            {session.status === "completed" && (
              <>
                <Button variant="outline" size="sm" onClick={() => navigate(`/session/${session.id}/visualizations`)}>
                  <BarChart3 className="w-3.5 h-3.5" />
                  Visualizations
                </Button>
                <Button size="sm" onClick={() => navigate(`/session/${session.id}/report`)}>
                  <FileText className="w-3.5 h-3.5" />
                  View Report
                </Button>
              </>
            )}

            {isLive && (
              <Button variant="outline" size="sm" isLoading={cancel.isPending} onClick={handleCancel}>
                Cancel
              </Button>
            )}

            <Button variant="ghost" size="icon" onClick={() => refetch()}>
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
        }
      />

      {/* Overall status bar */}
      <Card className={cn(
        "border",
        session.status === "running"   ? "border-brand-500/30 bg-brand-500/5" :
        session.status === "completed" ? "border-success/30  bg-success/5" :
        session.status === "failed"    ? "border-danger/30   bg-danger/5"  :
        "border-surface-4"
      )}>
        <CardContent className="py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {session.status === "running" && <Activity className="w-4 h-4 text-brand-400 animate-pulse" />}
            {session.status === "completed" && <CheckCircle2 className="w-4 h-4 text-success" />}
            {session.status === "failed"    && <AlertCircle  className="w-4 h-4 text-danger" />}
            {session.status === "pending"   && <Clock        className="w-4 h-4 text-zinc-500" />}
            <div>
              <p className="text-sm font-semibold text-zinc-100">
                {session.status === "running"   ? "Analysis in progress…" :
                 session.status === "completed" ? "Analysis complete" :
                 session.status === "failed"    ? "Analysis failed" :
                 "Queued for analysis"}
              </p>
              <p className="text-xs text-zinc-500">
                {agentRuns.filter(r => r.status === "completed").length}/{agentRuns.length} agents finished
                {session.total_tokens_used > 0 && ` · ${session.total_tokens_used.toLocaleString()} tokens`}
              </p>
            </div>
          </div>
          <Badge variant={statusVariant(session.status)}>{session.status}</Badge>
        </CardContent>
      </Card>

      {/* Agent pipeline grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {agentRuns.map((run) => (
          <AgentCard
            key={run.id}
            agentRun={run}
            progress={getAgentProgress(events, run.agent_name)}
            events={events}
            onViewTraces={() => navigate(`/session/${session.id}/traces/${run.id}`)}
          />
        ))}
      </div>

      {/* Pipeline flow arrows (desktop) */}
      <div className="hidden lg:flex items-center justify-center gap-2 text-zinc-700">
        {agentRuns.map((run, i) => (
          <div key={run.id} className="flex items-center gap-2">
            <span className={cn("text-xs font-medium", agentColor(run.agent_name))}>
              {agentLabel(run.agent_name)}
            </span>
            {i < agentRuns.length - 1 && <ArrowRight className="w-3.5 h-3.5" />}
          </div>
        ))}
      </div>

      {/* Event log */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              Event Log
              <span className="ml-2 text-xs text-zinc-500 font-normal">
                {events.length} events
              </span>
            </CardTitle>
            {isConnected && (
              <span className="text-2xs text-success flex items-center gap-1">
                <span className="w-1 h-1 rounded-full bg-success animate-pulse" />
                streaming
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {events.length === 0 && !isLive ? (
            <p className="text-xs text-zinc-600 text-center py-6">
              No events recorded for this session.
            </p>
          ) : events.length === 0 ? (
            <p className="text-xs text-zinc-600 text-center py-6 flex items-center justify-center gap-2">
              <Activity className="w-4 h-4 animate-pulse text-brand-400" />
              Waiting for agent events…
            </p>
          ) : (
            <div className="max-h-[480px] overflow-y-auto pr-1 space-y-0.5">
              {events.map((event, i) => (
                <EventLogItem
                  key={event.event_id ?? i}
                  event={event}
                  isNew={i >= events.length - 3}
                />
              ))}
              <div ref={logBottomRef} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
