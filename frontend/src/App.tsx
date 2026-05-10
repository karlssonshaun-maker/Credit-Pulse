import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Activity,
  BarChart3,
  FileText,
  History,
  Moon,
  Settings,
  Sun,
  Sparkles,
} from "lucide-react";
import ScorePage from "./pages/ScorePage";
import ResultPage from "./pages/ResultPage";
import HistoryPage from "./pages/HistoryPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import SettingsPage from "./pages/SettingsPage";
import { useTheme } from "./theme";

const navItems = [
  { to: "/score", label: "New Score", icon: FileText, group: "Assess" },
  { to: "/history", label: "History", icon: History, group: "Assess" },
  { to: "/analytics", label: "Analytics", icon: BarChart3, group: "Insights" },
  { to: "/settings", label: "Settings", icon: Settings, group: "Account" },
];

export default function App() {
  const { theme, toggle } = useTheme();
  const grouped = navItems.reduce<Record<string, typeof navItems>>((acc, item) => {
    (acc[item.group] = acc[item.group] || []).push(item);
    return acc;
  }, {});

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 flex flex-col border-r border-ink-200 bg-white/80 backdrop-blur
                        dark:border-ink-800 dark:bg-ink-950/70">
        <div className="px-5 py-5 flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center shadow-card">
            <Activity className="text-white" size={20} strokeWidth={2.5} />
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 ring-2 ring-white dark:ring-ink-950" />
          </div>
          <div className="leading-tight">
            <div className="font-bold text-ink-900 dark:text-ink-50 tracking-tight">CreditPulse</div>
            <div className="text-[11px] muted">South Africa · Lender</div>
          </div>
        </div>

        <div className="px-3">
          <div className="h-px bg-gradient-to-r from-transparent via-ink-200 to-transparent dark:via-ink-800" />
        </div>

        <nav className="flex-1 px-3 py-4 space-y-5 overflow-auto">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 mb-2 text-[10px] font-semibold tracking-[0.14em] uppercase text-ink-400 dark:text-ink-500">
                {group}
              </div>
              <div className="space-y-0.5">
                {items.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      `group relative flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition ${
                        isActive
                          ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                          : "text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-800/60"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span
                          className={`absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full transition ${
                            isActive ? "bg-brand-gradient" : "bg-transparent"
                          }`}
                        />
                        <Icon size={17} strokeWidth={isActive ? 2.4 : 2} />
                        <span>{label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 space-y-2 border-t border-ink-200 dark:border-ink-800">
          <div className="p-3 rounded-xl bg-brand-gradient-soft dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={14} className="text-brand-600 dark:text-brand-300" />
              <span className="text-[11px] font-semibold text-brand-700 dark:text-brand-200 uppercase tracking-wider">
                Demo Build
              </span>
            </div>
            <p className="text-[11px] text-ink-600 dark:text-ink-300 leading-snug">
              Synthetic data only. Swap integrations before production.
            </p>
          </div>

          <button
            onClick={toggle}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm
                       text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-800/60 transition"
            aria-label="Toggle theme"
          >
            <span className="flex items-center gap-2">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </span>
            <span className="kbd">⌘ ·</span>
          </button>

          <div className="px-3 py-1 text-[10px] text-ink-400 dark:text-ink-500">
            v0.1.0 · 2026
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="animate-fade-in">
          <Routes>
            <Route path="/" element={<Navigate to="/score" replace />} />
            <Route path="/score" element={<ScorePage />} />
            <Route path="/score/:id" element={<ResultPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
