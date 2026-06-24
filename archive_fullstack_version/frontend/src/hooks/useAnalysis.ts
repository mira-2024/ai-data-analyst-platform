import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { get, post } from "@/lib/api";
import type {
  AnalysisSession,
  AnalysisSessionListResponse,
  StartAnalysisRequest,
} from "@/types";

// ── Query keys ─────────────────────────────────────────────────────
export const sessionKeys = {
  all:    ["sessions"] as const,
  list:   (datasetId?: string) => ["sessions", "list", datasetId] as const,
  detail: (id: string) => ["sessions", id] as const,
};

// ── Queries ─────────────────────────────────────────────────────────

export function useSessions(datasetId?: string) {
  return useQuery({
    queryKey: sessionKeys.list(datasetId),
    queryFn: () => {
      const params = datasetId ? `?dataset_id=${datasetId}` : "";
      return get<AnalysisSessionListResponse>(`/analysis${params}`);
    },
  });
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: sessionKeys.detail(id!),
    queryFn:  () => get<AnalysisSession>(`/analysis/${id}`),
    enabled:  !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll while running or pending
      return status === "running" || status === "pending" ? 3_000 : false;
    },
  });
}

// ── Mutations ────────────────────────────────────────────────────────

export function useStartAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: StartAnalysisRequest) =>
      post<AnalysisSession>("/analysis/start", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
}

export function useCancelSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      post<{ status: string }>(`/analysis/${sessionId}/cancel`),
    onSuccess: (_data, sessionId) => {
      qc.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
    },
  });
}
