import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { get, post, patch, del, api } from "@/lib/api";
import type {
  Dataset,
  DatasetListResponse,
} from "@/types";

// ── Query keys ─────────────────────────────────────────────────────
export const datasetKeys = {
  all:    ["datasets"] as const,
  list:   (page: number, size: number) => ["datasets", "list", page, size] as const,
  detail: (id: string) => ["datasets", id] as const,
};

// ── Queries ─────────────────────────────────────────────────────────

export function useDatasets(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: datasetKeys.list(page, pageSize),
    queryFn: () => get<DatasetListResponse>(`/datasets?page=${page}&page_size=${pageSize}`),
  });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: datasetKeys.detail(id!),
    queryFn:  () => get<Dataset>(`/datasets/${id}`),
    enabled:  !!id,
    refetchInterval: (query) => {
      // Poll every 2s while status is pending
      return query.state.data?.status === "pending" ? 2_000 : false;
    },
  });
}

// ── Mutations ────────────────────────────────────────────────────────

export function useUploadDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { file: File; name?: string; description?: string }) => {
      const form = new FormData();
      form.append("file", payload.file);
      if (payload.name)        form.append("name",        payload.name);
      if (payload.description) form.append("description", payload.description);

      const res = await api.post<Dataset>("/datasets/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}

export function useUpdateDataset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string }) =>
      patch<Dataset>(`/datasets/${id}`, body),
    onSuccess: (data) => {
      qc.setQueryData(datasetKeys.detail(id), data);
      qc.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => del(`/datasets/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}
