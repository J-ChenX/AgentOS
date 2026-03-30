import { CircleStop } from 'lucide-react';

export default function CancelledCard() {
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '7px 11px',
        background: 'var(--color-bg-raised)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <CircleStop size={14} strokeWidth={1.8} style={{ color: 'var(--color-ink-tertiary)' }} />
      <span
        style={{
          fontFamily: 'var(--font-body)', fontSize: '12px',
          fontWeight: 300, color: 'var(--color-ink-tertiary)',
        }}
      >
        任务已取消
      </span>
    </div>
  );
}
