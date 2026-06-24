import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";

// Pages — lazy loaded for better perf
import { LandingPage }          from "@/pages/LandingPage";
import { DashboardPage }        from "@/pages/DashboardPage";
import { UploadPage }           from "@/pages/UploadPage";
import { WorkspacePage }        from "@/pages/WorkspacePage";
import { AgentTimelinePage }    from "@/pages/AgentTimelinePage";
import { VisualizationPage }    from "@/pages/VisualizationPage";
import { ReportPage }           from "@/pages/ReportPage";
import { TraceViewerPage }      from "@/pages/TraceViewerPage";
import { SettingsPage }         from "@/pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public landing page — no shell */}
        <Route path="/" element={<LandingPage />} />

        {/* App shell wraps all authenticated routes */}
        <Route element={<AppLayout />}>
          <Route path="/dashboard"             element={<DashboardPage />} />
          <Route path="/upload"                element={<UploadPage />} />
          <Route path="/workspace/:datasetId"  element={<WorkspacePage />} />
          <Route path="/session/:sessionId/timeline"    element={<AgentTimelinePage />} />
          <Route path="/session/:sessionId/visualizations" element={<VisualizationPage />} />
          <Route path="/session/:sessionId/report"      element={<ReportPage />} />
          <Route path="/session/:sessionId/traces/:agentRunId" element={<TraceViewerPage />} />
          <Route path="/settings"              element={<SettingsPage />} />

          {/* Fallback redirect */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
