
export function StatusPill({ tone, children }: { tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info'; children: React.ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}
