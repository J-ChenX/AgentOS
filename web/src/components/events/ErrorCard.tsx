import { AlertTriangle } from 'lucide-react';

export default function ErrorCard({
  message,
  recoverable,
}: {
  message: string;
  recoverable: boolean;
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: '10px',
        alignItems: 'flex-start',
        padding: '9px 12px',
        background: 'rgba(155,58,46,0.04)',
        border: '1px solid rgba(155,58,46,0.16)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <AlertTriangle
        size={15}
        strokeWidth={1.8}
        style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: '1px' }}
      />
      <div>
        <div
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: 'var(--text-sm)',
            fontWeight: 500,
            color: 'var(--color-error)',
          }}
        >
          错误
        </div>
        <div
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: 'var(--text-sm)',
            fontWeight: 300,
            color: 'var(--color-ink-secondary)',
            marginTop: '2px',
            lineHeight: 'var(--leading-normal)',
          }}
        >
          {message}
        </div>
        {recoverable && (
          <span
            style={{
              display: 'inline-block',
              marginTop: '4px',
              fontFamily: 'var(--font-body)',
              fontSize: '10px',
              fontWeight: 500,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              color: 'var(--color-error)',
              border: '1px solid rgba(155,58,46,0.3)',
              padding: '1px 6px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            可恢复
          </span>
        )}
      </div>
    </div>
  );
}
