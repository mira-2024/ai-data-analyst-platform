import { useNavigate } from "react-router-dom";
import {
  Upload, Database, Activity, FileText,
  ArrowRight, Clock, CheckCircle2, AlertCircle,
  TrendingUp, BarChart3, Sparkles
} from "lucide-react";
import { PageHeader }    from "@/components/ui/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button }        from "@/components/ui/Button";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { SkeletonCard }  from "@/components/ui/Skeleton";
import { useDatasets }   from "@/hooks/useDatasets";
import { useSessions }   from "@/hooks/useAnalysis";
import { formatBytes, timeAgo, formatDuration, agentLabel } from "@/lib/utils";
import type { Dataset, AnalysisSession } from "@/types";

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Database;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-zinc-500 mb-1">{label}</p>
          <p className="text-2xl font-bold text-zinc-100">{value}</p>
          {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
        </div>
        <div className={`flex items-center justify-center w-9 h-9 rounded-lg bg-surface-3 border border-surface-4 ${color ?? ""}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
    </Card>
  );
}

// ── Dataset row ───────────────────────────────────────────────────────────────
function DatasetRow({ dataset }: { dataset: Dataset }) {
  const navigate = useNavigate();
  return (
    <div
      className="flex items-center justify-between py-3 px-1 border-b border-surface-3/50 last:border-0 cursor-pointer hover:bg-surface-3/30 rounded-lg px-3 transition-colors"
      onClick={() => navigate(`/workspace/${dataset.id}`)}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-surface-3 border border-surface-4 shrink-0">
          <Database className="w-3.5 h-3.5 text-zinc-400" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-zinc-100 truncate">{dataset.name}</p>
          <p className="text-xs text-zinc-500">
            {dataset.row_count != null
              ? `${dataset.row_count.toLocaleString()} rows · ${dataset.column_count ?? '?'} cols`
              : (dataset.file_extension ?? 'unknown').toUpperCase()
            } · {formatBytes(dataset.file_size_bytes ?? 0)}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <Badge variant={statusVariant(dataset.status)}>
          {dataset.status}
        </Badge>
        <span className="text-xs text-zinc-600">{timeAgo(dataset.created_at)}</span>
        <ArrowRight className="w-3.5 h-3.5 text-zinc-600" />
      </div>
    </div>
  );
}

// ── Session row ───────────────────────────────────────────────────────────────
function SessionRow({ session }: { session: AnalysisSession }) {
  const navigate = useNavigate();
  const duration = session.started_at && session.completed_at
    ? formatDuration(
        new Date(session.completed_at).getTime() - new Date(session.started_at).getTime()
      )
    : null;

  return (
    <div
      className="flex items-center justify-between py-3 px-3 border-b border-surface-3/50 last:border-0 cursor-pointer hover:bg-surface-3/30 rounded-lg transition-colors"
      onClick={() => navigate(`/session/${session.id}/timeline`)}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className={`flex items-center justify-center w-8 h-8 rounded-lg border shrink-0 ${
          session.status === "running"   ? "bg-brand-500/10 border-brand-500/30" :
          session.status === "completed" ? "bg-success/10 border-success/30" :
          session.status === "failed"    ? "bg-danger/10 border-danger/30"  :
          "bg-surface-3 border-surface-4"
        }`}>
          {session.status === "running"   ? <Activity className="w-3.5 h-3.5 text-brand-400 animate-pulse" /> :
           session.status === "completed" ? <CheckCircle2 className="w-3.5 h-3.5 text-success" /> :
           session.status === "failed"    ? <AlertCircle className="w-3.5 h-3.5 text-danger" /> :
           <Clock className="w-3.5 h-3.5 text-zinc-500" />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-zinc-100 truncate">
            Session #{session.id.slice(0, 8)}
          </p>
          <p className="text-xs text-zinc-500">
            {session.agent_runs.length} agents · {session.total_tokens_used.toLocaleString()} tokens
            {duration && ` · ${duration}`}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <Badge variant={statusVariant(session.status)}>{session.status}</Badge>
        <span className="text-xs text-zinc-600">{timeAgo(session.created_at)}</span>
        <ArrowRight className="w-3.5 h-3.5 text-zinc-600" />
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export function DashboardPage() {
  const navigate = useNavigate();
  const { data: datasetsResp, isLoading: datasetsLoading } = useDatasets(1, 5);
  const { data: sessionsResp, isLoading: sessionsLoading } = useSessions();

  const datasets = datasetsResp?.items ?? [];
  const sessions = sessionsResp?.items ?? [];
  const totalTokens = sessions.reduce((s, x) => s + x.total_tokens_used, 0);
  const completedSessions = sessions.filter((s) => s.status === "completed").length;

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Dashboard"
        description="Overview of your datasets and analysis sessions."
        actions={
          <Button onClick={() => navigate("/upload")}>
            <Upload className="w-3.5 h-3.5" />
            Upload Dataset
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Database}
          label="Total Datasets"
          value={datasetsResp?.total ?? "—"}
          sub="uploaded files"
          color="text-info"
        />
        <StatCard
          icon={Activity}
          label="Analysis Sessions"
          value={sessionsResp?.total ?? "—"}
          sub={`${completedSessions} completed`}
          color="text-brand-400"
        />
        <StatCard
          icon={Sparkles}
          label="Tokens Used"
          value={totalTokens > 0 ? (totalTokens / 1000).toFixed(1) + "K" : "—"}
          sub="across all agents"
          color="text-success"
        />
        <StatCard
          icon={TrendingUp}
          label="Insights Generated"
          value="—"
          sub="from analysis runs"
          color="text-warning"
        />
      </div>

      {/* Two-column content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Recent datasets */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Datasets</CardTitle>
                <CardDescription>Your most recently uploaded files</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
                View all <ArrowRight className="w-3 h-3" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {datasetsLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
              </div>
            ) : datasets.length === 0 ? (
              <div className="text-center py-8">
                <Database className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                <p className="text-xs text-zinc-500">No datasets yet.</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => navigate("/upload")}
                >
                  Upload your first dataset
                </Button>
              </div>
            ) : (
              <div className="-mx-1">
                {datasets.map((d) => <DatasetRow key={d.id} dataset={d} />)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent sessions */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Analysis Sessions</CardTitle>
                <CardDescription>Latest multi-agent pipeline runs</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
                View all <ArrowRight className="w-3 h-3" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {sessionsLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-8">
                <BarChart3 className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                <p className="text-xs text-zinc-500">No analysis sessions yet.</p>
                <p className="text-xs text-zinc-600 mt-1">Upload a dataset to get started.</p>
              </div>
            ) : (
              <div className="-mx-1">
                {sessions.slice(0, 5).map((s) => <SessionRow key={s.id} session={s} />)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick-start CTA (only when no data) */}
      {datasets.length === 0 && !datasetsLoading && (
        <Card className="border-brand-500/20 bg-brand-500/5">
          <CardContent className="flex items-center justify-between py-5">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-brand-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-zinc-100">Get started with DataFlow</p>
                <p className="text-xs text-zinc-500">Upload a CSV or Excel file to run your first multi-agent analysis.</p>
              </div>
            </div>
            <Button onClick={() => navigate("/upload")}>
              <Upload className="w-3.5 h-3.5" />
              Upload Now
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
