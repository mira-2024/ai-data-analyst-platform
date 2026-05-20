import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Database, Play, BarChart3, FileText,
  ChevronRight, Clock, Activity, AlertCircle,
  CheckCircle2, RefreshCw, Trash2, Table2,
  TrendingUp, Hash, Calendar
} from "lucide-react";
import { PageHeader }     from "@/components/ui/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button }         from "@/components/ui/Button";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { SkeletonCard }   from "@/components/ui/Skeleton";
import { EmptyState }     from "@/components/ui/EmptyState";
import { toast }          from "@/components/ui/Toaster";
import { useDataset, useDeleteDataset }     from "@/hooks/useDatasets";
import { useSessions, useStartAnalysis }    from "@/hooks/useAnalysis";
import { formatBytes, formatDate, timeAgo, formatNumber } from "@/lib/utils";
import type { ColumnProfile } from "@/types";

// ── Column type icon ──────────────────────────────────────────────────────────
function DtypeIcon({ dtype }: { dtype: string }) {
  if (dtype.includes("int") || dtype.includes("float") || dtype === "numeric")
    return <Hash className="w-3 h-3 text-brand-400" />;
  if (dtype.includes("date") || dtype.includes("time"))
    return <Calendar className="w-3 h-3 text-info" />;
  return <FileText className="w-3 h-3 text-zinc-500" />;
}

// ── Column preview table ──────────────────────────────────────────────────────
function ColumnTable({ columns }: { columns: ColumnProfile[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-surface-4 text-zinc-500">
            <th className="pb-2 text-left font-medium">Column</th>
            <th className="pb-2 text-left font-medium">Type</th>
            <th className="pb-2 text-right font-medium">Nulls</th>
            <th className="pb-2 text-right font-medium">Unique</th>
            <th className="pb-2 text-right font-medium">Sample</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((col) => (
            <tr key={col.name} className="border-b border-surface-4/50 last:border-0 hover:bg-surface-3/30 transition-colors">
              <td className="py-2 pr-3">
                <div className="flex items-center gap-1.5">
                  <DtypeIcon dtype={col.dtype} />
                  <span className="font-medium text-zinc-200 font-mono">{col.name}</span>
                </div>
              </td>
              <td className="py-2 pr-3">
                <span className="text-zinc-500 font-mono">{col.dtype}</span>
              </td>
              <td className="py-2 pr-3 text-right">
                <span className={(col.null_pct ?? 0) > 20 ? "text-warning" : (col.null_pct ?? 0) > 0 ? "text-zinc-400" : "text-success"}>
                  {(col.null_pct ?? 0).toFixed(1)}%
                </span>
              </td>
              <td className="py-2 pr-3 text-right text-zinc-500">
                {col.unique_count != null ? formatNumber(col.unique_count) : "—"}
              </td>
              <td className="py-2 text-right text-zinc-500 max-w-[120px]">
                <span className="truncate block">
                  {(col.sample_values ?? []).slice(0, 2).map(String).join(", ")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Workspace ─────────────────────────────────────────────────────────────────
export function WorkspacePage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const [isConfirmDelete, setIsConfirmDelete] = useState(false);

  const { data: dataset, isLoading, error } = useDataset(datasetId);
  const { data: sessionsResp } = useSessions(datasetId);
  const startAnalysis = useStartAnalysis();
  const deleteDataset = useDeleteDataset();

  const sessions = sessionsResp?.items ?? [];
  const schema = dataset?.schema_json ?? [];
  const stats = dataset?.statistics_json;

  const handleStartAnalysis = async () => {
    if (!datasetId || dataset?.status !== "ready") return;
    try {
      const session = await startAnalysis.mutateAsync({ dataset_id: datasetId });
      toast.success("Analysis started!", "Agents are now running.");
      navigate(`/session/${session.id}/timeline`);
    } catch (err) {
      toast.error("Failed to start analysis", err instanceof Error ? err.message : "Unknown error");
    }
  };

  const handleDelete = async () => {
    if (!datasetId) return;
    try {
      await deleteDataset.mutateAsync(datasetId);
      toast.success("Dataset deleted");
      navigate("/dashboard");
    } catch {
      toast.error("Failed to delete dataset");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Dataset not found"
        description="This dataset may have been deleted or doesn't exist."
        action={{ label: "Back to Dashboard", onClick: () => navigate("/dashboard") }}
      />
    );
  }

  const canAnalyse = dataset.status === "ready";

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title={dataset.name}
        description={dataset.description ?? "No description provided."}
        breadcrumb={
          <Link to="/dashboard" className="hover:text-zinc-300 transition-colors">
            Dashboard
          </Link>
        }
        actions={
          <div className="flex items-center gap-2">
            {isConfirmDelete ? (
              <>
                <span className="text-xs text-danger">Confirm delete?</span>
                <Button
                  variant="danger"
                  size="sm"
                  isLoading={deleteDataset.isPending}
                  onClick={handleDelete}
                >
                  Delete
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setIsConfirmDelete(false)}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsConfirmDelete(true)}
                >
                  <Trash2 className="w-3.5 h-3.5 text-danger" />
                </Button>
                <Button
                  onClick={handleStartAnalysis}
                  isLoading={startAnalysis.isPending}
                  disabled={!canAnalyse}
                  size="sm"
                >
                  <Play className="w-3.5 h-3.5" />
                  Run Analysis
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* Status + meta */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Status",  value: <Badge variant={statusVariant(dataset.status)}>{dataset.status}</Badge> },
          { label: "Rows",    value: stats?.row_count != null ? stats.row_count.toLocaleString() : "—" },
          { label: "Columns", value: stats?.column_count != null ? stats.column_count : "—" },
          { label: "Size",    value: formatBytes(dataset.file_size ?? 0) },
        ].map(({ label, value }) => (
          <Card key={label} className="p-4">
            <p className="text-2xs text-zinc-500 mb-1">{label}</p>
            <div className="text-sm font-semibold text-zinc-100">{value}</div>
          </Card>
        ))}
      </div>

      {dataset.status === "pending" && (
        <div className="flex items-center gap-2 text-xs text-zinc-400 card p-4">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-400" />
          Profiling dataset… This may take a few seconds.
        </div>
      )}

      {/* Schema */}
      {schema.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Schema</CardTitle>
            <CardDescription>{schema.length} columns detected</CardDescription>
          </CardHeader>
          <CardContent>
            <ColumnTable columns={schema} />
          </CardContent>
        </Card>
      )}

      {/* Data quality */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>Data Quality</CardTitle>
            <CardDescription>Auto-detected quality indicators</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-2xs text-zinc-500 mb-0.5">Quality Score</p>
                <p className={`text-lg font-bold ${(stats.quality_score ?? 0) >= 0.8 ? "text-success" : (stats.quality_score ?? 0) >= 0.6 ? "text-warning" : "text-danger"}`}>
                  {((stats.quality_score ?? 0) * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-2xs text-zinc-500 mb-0.5">Datetime Cols</p>
                <p className="text-lg font-bold text-zinc-100">{(stats.likely_datetime_columns ?? []).length}</p>
              </div>
              <div>
                <p className="text-2xs text-zinc-500 mb-0.5">ID Columns</p>
                <p className="text-lg font-bold text-zinc-100">{(stats.likely_id_columns ?? []).length}</p>
              </div>
              <div>
                <p className="text-2xs text-zinc-500 mb-0.5">Uploaded</p>
                <p className="text-sm font-medium text-zinc-300">{timeAgo(dataset.created_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analysis sessions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Analysis Sessions</CardTitle>
              <CardDescription>History of agent pipeline runs for this dataset</CardDescription>
            </div>
            <Button
              size="sm"
              onClick={handleStartAnalysis}
              isLoading={startAnalysis.isPending}
              disabled={!canAnalyse}
            >
              <Play className="w-3.5 h-3.5" />
              New Run
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No analysis sessions yet"
              description="Start a multi-agent analysis to discover insights from this dataset."
              action={canAnalyse ? { label: "Run Analysis", onClick: handleStartAnalysis } : undefined}
            />
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => {
                const completedAgents = session.agent_runs.filter(r => r.status === "completed").length;
                const totalAgents = session.agent_runs.length;
                return (
                  <div
                    key={session.id}
                    className="flex items-center justify-between p-3 rounded-xl border border-surface-4 bg-surface-3/20 hover:bg-surface-3/50 cursor-pointer transition-colors"
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
                      <div>
                        <p className="text-xs font-medium text-zinc-200">
                          {formatDate(session.created_at)} · {completedAgents}/{totalAgents} agents
                        </p>
                        <p className="text-2xs text-zinc-500">
                          {session.total_tokens_used.toLocaleString()} tokens · {session.id.slice(0, 8)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={statusVariant(session.status)}>{session.status}</Badge>
                      {session.status === "completed" && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={(e) => { e.stopPropagation(); navigate(`/session/${session.id}/visualizations`); }}
                            title="Visualizations"
                          >
                            <BarChart3 className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={(e) => { e.stopPropagation(); navigate(`/session/${session.id}/report`); }}
                            title="Report"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
