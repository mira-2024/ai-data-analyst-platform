import { useState } from "react";
import { Settings, Key, Palette, Bell, Database, Info, Check } from "lucide-react";
import { PageHeader }     from "@/components/ui/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button }         from "@/components/ui/Button";
import { toast }          from "@/components/ui/Toaster";

interface SettingRowProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

function SettingRow({ label, description, children }: SettingRowProps) {
  return (
    <div className="flex items-start justify-between gap-6 py-4 border-b border-surface-4 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function SectionHeader({ icon: Icon, title }: { icon: typeof Settings; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-1">
      <Icon className="w-4 h-4 text-zinc-500" />
      <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{title}</h2>
    </div>
  );
}

export function SettingsPage() {
  const [apiKey, setApiKey] = useState("sk-ant-••••••••••••••••••••••••••••••");
  const [showKey, setShowKey] = useState(false);
  const [maxCharts, setMaxCharts] = useState("6");
  const [model, setModel] = useState("claude-opus-4-6");

  const handleSave = () => {
    toast.success("Settings saved", "Your configuration has been updated.");
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <PageHeader
        title="Settings"
        description="Configure your DataFlow platform preferences."
      />

      {/* AI Configuration */}
      <div>
        <SectionHeader icon={Key} title="AI Configuration" />
        <Card>
          <CardContent className="pt-4">
            <SettingRow
              label="Anthropic API Key"
              description="Used by all agents to call Claude. Set via ANTHROPIC_API_KEY environment variable in production."
            >
              <div className="flex items-center gap-2">
                <input
                  type={showKey ? "text" : "password"}
                  className="input-base w-48 font-mono text-xs"
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                />
                <Button variant="ghost" size="sm" onClick={() => setShowKey(v => !v)}>
                  {showKey ? "Hide" : "Show"}
                </Button>
              </div>
            </SettingRow>

            <SettingRow
              label="Model"
              description="Claude model used by all agents. Opus = highest quality, Haiku = fastest."
            >
              <select
                className="input-base w-52 text-xs"
                value={model}
                onChange={e => setModel(e.target.value)}
              >
                <option value="claude-opus-4-6">Claude Opus 4.6</option>
                <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option>
              </select>
            </SettingRow>
          </CardContent>
        </Card>
      </div>

      {/* Analysis defaults */}
      <div>
        <SectionHeader icon={Database} title="Analysis Defaults" />
        <Card>
          <CardContent className="pt-4">
            <SettingRow
              label="Max Charts per Session"
              description="Maximum number of charts the VisualizerAgent will generate per analysis run."
            >
              <input
                type="number"
                min="1"
                max="20"
                className="input-base w-24 text-center"
                value={maxCharts}
                onChange={e => setMaxCharts(e.target.value)}
              />
            </SettingRow>

            <SettingRow
              label="Default Agents"
              description="Which agents run when you start analysis. All are enabled by default."
            >
              <div className="flex flex-col gap-1.5">
                {["Cleaner", "Analyst", "Visualizer", "Storyteller"].map(name => (
                  <label key={name} className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                    <input type="checkbox" className="accent-brand-500" defaultChecked />
                    {name}
                  </label>
                ))}
              </div>
            </SettingRow>
          </CardContent>
        </Card>
      </div>

      {/* Appearance */}
      <div>
        <SectionHeader icon={Palette} title="Appearance" />
        <Card>
          <CardContent className="pt-4">
            <SettingRow
              label="Theme"
              description="DataFlow uses dark mode exclusively for optimal data readability."
            >
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-4 h-4 rounded-full bg-surface-0 border border-brand-500" />
                Dark (default)
              </div>
            </SettingRow>

            <SettingRow
              label="Brand Colour"
              description="Primary accent colour used throughout the UI."
            >
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-md bg-brand-500 border border-brand-400" />
                <span className="text-xs text-zinc-500 font-mono">#6366f1</span>
              </div>
            </SettingRow>
          </CardContent>
        </Card>
      </div>

      {/* About */}
      <div>
        <SectionHeader icon={Info} title="About" />
        <Card>
          <CardContent className="pt-4 space-y-3">
            {[
              ["Platform",   "DataFlow — Multi-Agent AI Data Analyst"],
              ["Version",    "1.0.0"],
              ["Backend",    "FastAPI + LangGraph + Claude API"],
              ["Frontend",   "React 18 + TypeScript + Tailwind CSS"],
              ["Database",   "PostgreSQL + SQLAlchemy (async)"],
              ["Built by",   "Mira · Final Year Project 2025"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between text-xs">
                <span className="text-zinc-500">{k}</span>
                <span className="text-zinc-300 font-medium">{v}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Check className="w-3.5 h-3.5" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}
