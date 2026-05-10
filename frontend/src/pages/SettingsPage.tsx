import { useState } from "react";
import { Check, Copy, Eye, EyeOff, Key, Moon, Sun, Monitor } from "lucide-react";
import { getApiKey, setApiKey } from "../api";
import PageHeader from "../components/PageHeader";
import { useTheme } from "../theme";

const DEMO_KEY = "cp_demo_fnb_business_key_do_not_use_in_prod";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [key, setKey] = useState(getApiKey());
  const [saved, setSaved] = useState(false);
  const [reveal, setReveal] = useState(false);
  const [copied, setCopied] = useState(false);

  const save = () => {
    setApiKey(key);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const copy = async () => {
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="p-10 max-w-3xl">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Manage API credentials and dashboard preferences."
      />

      <div className="card p-8 mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-brand-gradient-soft dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20 flex items-center justify-center text-brand-600 dark:text-brand-300">
            <Key size={18} />
          </div>
          <div>
            <h2 className="font-bold heading">API credentials</h2>
            <p className="text-xs muted mt-0.5">Used for every request to the CreditPulse backend.</p>
          </div>
        </div>

        <div>
          <label className="label">API key</label>
          <div className="relative">
            <input
              type={reveal ? "text" : "password"}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="input font-mono pr-24"
              spellCheck={false}
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
              <button
                onClick={() => setReveal(!reveal)}
                className="p-1.5 rounded-lg text-ink-500 hover:bg-ink-100 dark:hover:bg-ink-800 transition"
                aria-label="Toggle reveal"
                type="button"
              >
                {reveal ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
              <button
                onClick={copy}
                className="p-1.5 rounded-lg text-ink-500 hover:bg-ink-100 dark:hover:bg-ink-800 transition"
                aria-label="Copy"
                type="button"
              >
                {copied ? <Check size={15} className="text-emerald-500" /> : <Copy size={15} />}
              </button>
            </div>
          </div>
          <p className="text-xs muted mt-2">
            Default demo key: <code className="kbd font-mono">{DEMO_KEY}</code>
          </p>
        </div>

        <div className="flex items-center justify-between mt-6 pt-6 border-t divider">
          <div className="text-xs muted">
            Stored locally in your browser · never transmitted.
          </div>
          <button onClick={save} className="btn-primary">
            {saved ? (
              <>
                <Check size={16} /> Saved
              </>
            ) : (
              "Save key"
            )}
          </button>
        </div>
      </div>

      <div className="card p-8">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-brand-gradient-soft dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20 flex items-center justify-center text-brand-600 dark:text-brand-300">
            {theme === "dark" ? <Moon size={18} /> : <Sun size={18} />}
          </div>
          <div>
            <h2 className="font-bold heading">Appearance</h2>
            <p className="text-xs muted mt-0.5">Choose a theme for your dashboard.</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <ThemeChoice
            active={theme === "light"}
            onClick={() => setTheme("light")}
            icon={<Sun size={16} />}
            label="Light"
            preview="bg-white border-ink-200"
          />
          <ThemeChoice
            active={theme === "dark"}
            onClick={() => setTheme("dark")}
            icon={<Moon size={16} />}
            label="Dark"
            preview="bg-ink-900 border-ink-800"
          />
        </div>
      </div>
    </div>
  );
}

function ThemeChoice({
  active,
  onClick,
  icon,
  label,
  preview,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  preview: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-xl border-2 transition ${
        active
          ? "border-brand-500 bg-brand-50 dark:bg-brand-500/10"
          : "border-ink-200 hover:border-ink-300 dark:border-ink-700 dark:hover:border-ink-600"
      }`}
    >
      <div className={`h-16 rounded-lg border ${preview} mb-3 relative overflow-hidden`}>
        <div className={`absolute top-2 left-2 right-8 h-1.5 rounded-full ${active ? "bg-brand-gradient" : "bg-ink-300 dark:bg-ink-700"}`} />
        <div className="absolute top-5 left-2 right-16 h-1 rounded-full bg-ink-200 dark:bg-ink-800" />
        <div className="absolute top-7.5 left-2 right-12 h-1 rounded-full bg-ink-200 dark:bg-ink-800" style={{ top: "1.875rem" }} />
      </div>
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-semibold heading">
          {icon} {label}
        </span>
        {active && (
          <span className="text-[10px] font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400">
            Active
          </span>
        )}
      </div>
    </button>
  );
}
