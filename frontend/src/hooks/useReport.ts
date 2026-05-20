import { useQuery } from "@tanstack/react-query";
import { get } from "@/lib/api";
import type { Report } from "@/types";

export function useReport(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["reports", sessionId],
    queryFn:  () => get<Report>(`/reports/${sessionId}`),
    enabled:  !!sessionId,
  });
}
