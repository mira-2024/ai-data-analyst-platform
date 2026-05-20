import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Settings,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", to: "/dashboard" },
  { icon: Upload,          label: "Upload",    to: "/upload" },
  { icon: Settings,        label: "Settings",  to: "/settings" },
];

export function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="flex flex-col w-[220px] min-w-[220px] h-full bg-surface-1 border-r border-surface-4">
      {/* Logo */}
      <div
        className="flex items-center gap-2.5 px-5 py-5 cursor-pointer group"
        onClick={() => navigate("/dashboard")}
      >
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-brand shadow-glow">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-zinc-100 tracking-tight">
          DataFlow
        </span>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-surface-4 mb-2" />

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {NAV_ITEMS.map(({ icon: Icon, label, to }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150",
                isActive
                  ? "bg-brand-500/15 text-brand-400"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-surface-3"
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn("w-4 h-4 shrink-0", isActive ? "text-brand-400" : "")} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight className="w-3 h-3 opacity-50" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-surface-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-gradient-brand flex items-center justify-center text-white text-xs font-bold">
            M
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-zinc-200 truncate">Mira</p>
            <p className="text-2xs text-zinc-500 truncate">Student</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
