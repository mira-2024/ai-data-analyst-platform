import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Toaster } from "@/components/ui/Toaster";

export function AppLayout() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-surface-0">
      {/* Fixed sidebar */}
      <Sidebar />

      {/* Main content area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="flex-1 p-6 lg:p-8 max-w-screen-2xl w-full mx-auto">
          <Outlet />
        </div>
      </main>

      {/* Toast notifications */}
      <Toaster />
    </div>
  );
}
