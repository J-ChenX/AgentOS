export default function ProgressBar({
  current,
  total,
  label,
}: {
  current: number;
  total: number;
  label?: string;
}) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="space-y-1">
      {label && (
        <div className="text-xs" style={{ color: 'var(--color-ink-secondary)' }}>
          {label}
        </div>
      )}
      <div
        className="h-2 overflow-hidden rounded-full"
        style={{ background: 'var(--color-bg-raised)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: 'var(--color-accent)' }}
        />
      </div>
      <div className="text-xs" style={{ color: 'var(--color-ink-secondary)' }}>
        {current} / {total}
      </div>
    </div>
  );
}
