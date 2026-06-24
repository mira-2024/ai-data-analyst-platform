import { useNavigate } from "react-router-dom";
import {
  Sparkles, Upload, BarChart3, Brain, FileText,
  ArrowRight, CheckCircle, Zap, Shield, Eye
} from "lucide-react";
import { Button } from "@/components/ui/Button";

const FEATURES = [
  {
    icon: Brain,
    title: "Multi-Agent Intelligence",
    description:
      "Four specialised AI agents work in sequence — cleaning, analysing, visualising, and narrating your data.",
  },
  {
    icon: Eye,
    title: "Full Transparency",
    description:
      "Watch every agent decision in real time. See tool calls, reasoning steps, and intermediate outputs as they happen.",
  },
  {
    icon: BarChart3,
    title: "Auto-Generated Visuals",
    description:
      "The Visualizer Agent selects the best chart types for your data and generates publication-ready Plotly figures.",
  },
  {
    icon: FileText,
    title: "Executive Reports",
    description:
      "The Storyteller Agent synthesises all findings into a board-ready narrative with actionable recommendations.",
  },
  {
    icon: Zap,
    title: "Real-Time Streaming",
    description:
      "SSE-powered live updates. No page refreshes — see agent progress, insights, and charts as they're generated.",
  },
  {
    icon: Shield,
    title: "Production Architecture",
    description:
      "PostgreSQL persistence, event audit log, storage abstraction, structured logging, and typed API contracts throughout.",
  },
];

const STEPS = [
  { n: "01", title: "Upload Your Dataset", desc: "CSV, Excel, JSON, Parquet, or PDF. Profiled automatically." },
  { n: "02", title: "Launch Analysis",      desc: "Start the 4-agent pipeline with one click." },
  { n: "03", title: "Watch Agents Work",    desc: "Follow the workflow timeline in real time." },
  { n: "04", title: "Explore & Export",     desc: "Charts, insights, and executive report — ready to share." },
];

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface-0 text-zinc-100">
      {/* ── Nav ──────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-surface-4 bg-surface-0/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center shadow-glow">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold tracking-tight">DataFlow</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              Sign In
            </Button>
            <Button size="sm" onClick={() => navigate("/dashboard")}>
              Get Started
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Grid background */}
        <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none" />
        {/* Glow orb */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-6">
            <Sparkles className="w-3 h-3" />
            Multi-Agent AI Data Analyst · Final Year Project 2025
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight mb-5">
            Talk to Your Data.{" "}
            <span className="text-gradient">Watch it Think.</span>
          </h1>

          <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-8 leading-relaxed">
            Upload any dataset. A team of specialised AI agents autonomously cleans, analyses,
            visualises, and narrates your data — while you watch every decision unfold in real time.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button size="lg" onClick={() => navigate("/upload")}>
              <Upload className="w-4 h-4" />
              Upload a Dataset
            </Button>
            <Button variant="outline" size="lg" onClick={() => navigate("/dashboard")}>
              View Dashboard
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>

          <p className="mt-4 text-xs text-zinc-600">
            CSV · Excel · JSON · Parquet · PDF · No account required
          </p>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-zinc-100 mb-2">From upload to insight in minutes</h2>
          <p className="text-sm text-zinc-500">No configuration. No code. Just upload and go.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((step) => (
            <div key={step.n} className="card p-5 relative overflow-hidden group hover:shadow-card-hover transition-shadow duration-200">
              <div className="text-3xl font-black text-surface-3 mb-3 group-hover:text-brand-500/20 transition-colors">
                {step.n}
              </div>
              <h3 className="text-sm font-semibold text-zinc-100 mb-1">{step.title}</h3>
              <p className="text-xs text-zinc-500 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section className="bg-surface-1 border-y border-surface-4">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-zinc-100 mb-2">Enterprise-grade under the hood</h2>
            <p className="text-sm text-zinc-500">Built for transparency, scalability, and trust.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <div key={title} className="card-elevated p-5 hover:shadow-card-hover transition-shadow duration-200">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 mb-3">
                  <Icon className="w-4 h-4 text-brand-400" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-100 mb-1.5">{title}</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Agent pipeline visual ─────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h2 className="text-2xl font-bold text-zinc-100 mb-2">The Agent Pipeline</h2>
        <p className="text-sm text-zinc-500 mb-10">Four specialised agents. One seamless workflow.</p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-2">
          {[
            { name: "Cleaner",     color: "text-info",      bg: "bg-info/10     border-info/30" },
            { name: "Analyst",     color: "text-brand-400", bg: "bg-brand-500/10 border-brand-500/30" },
            { name: "Visualizer",  color: "text-success",   bg: "bg-success/10  border-success/30" },
            { name: "Storyteller", color: "text-warning",   bg: "bg-warning/10  border-warning/30" },
          ].map((agent, i) => (
            <div key={agent.name} className="flex items-center gap-2">
              <div className={`px-4 py-2.5 rounded-xl border text-xs font-semibold ${agent.bg} ${agent.color}`}>
                {agent.name}
              </div>
              {i < 3 && (
                <ArrowRight className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
              )}
            </div>
          ))}
        </div>

        <p className="mt-6 text-xs text-zinc-600">
          Each agent produces typed, structured outputs passed to the next stage via a shared state graph.
        </p>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <section className="max-w-2xl mx-auto px-6 pb-20 text-center">
        <div className="card p-8 glow-brand">
          <Sparkles className="w-8 h-8 text-brand-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-zinc-100 mb-2">Ready to analyse your data?</h2>
          <p className="text-sm text-zinc-500 mb-5">Upload a CSV and see the agents in action within seconds.</p>
          <Button size="lg" onClick={() => navigate("/upload")}>
            <Upload className="w-4 h-4" />
            Start Now — It's Free
          </Button>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-surface-4 px-6 py-6 text-center text-xs text-zinc-600">
        DataFlow · Multi-Agent AI Data Analyst Platform · Final Year Project 2025
      </footer>
    </div>
  );
}
