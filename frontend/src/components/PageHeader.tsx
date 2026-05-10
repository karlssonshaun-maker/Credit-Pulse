import type { ReactNode } from "react";

interface Props {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export default function PageHeader({ eyebrow, title, description, actions }: Props) {
  return (
    <header className="flex items-start justify-between gap-6 mb-8">
      <div>
        {eyebrow && (
          <div className="section-title mb-2 flex items-center gap-2">
            <span className="w-6 h-px bg-gradient-to-r from-brand-500 to-accent-500" />
            {eyebrow}
          </div>
        )}
        <h1 className="text-3xl font-bold tracking-tight heading">{title}</h1>
        {description && (
          <p className="body-text mt-1.5 max-w-2xl">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </header>
  );
}
