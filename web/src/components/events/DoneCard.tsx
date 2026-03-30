import { CircleCheck } from 'lucide-react';

export default function DoneCard({ summary }: { summary: string }) {
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '7px 11px',
        background: 'rgba(74,124,92,0.05)',
        border: '1px solid rgba(74,124,92,0.18)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <CircleCheck size={15} strokeWidth={1.8} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
      <span
        style={{
          fontFamily: 'var(--font-body)', fontSize: '12px',
          fontWeight: 500, color: 'var(--color-success)',
        }}
      >
        任务完成
      </span>
      {summary && (
        <span
          style={{
            fontFamily: 'var(--font-body)', fontSize: '12px',
            fontWeight: 300, color: 'var(--color-ink-secondary)',
          }}
        >
          {'— '}<span>{summary}</span>
        </span>
      )}
    </div>
  );
}
