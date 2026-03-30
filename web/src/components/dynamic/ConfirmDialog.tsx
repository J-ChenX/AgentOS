import { useState, useEffect } from 'react';

interface ConfirmDialogProps {
  message: string;
  options: string[];
  onAction?: (payload: unknown) => void;
  timeoutMs?: number;
}

export default function ConfirmDialog({ message, options, onAction, timeoutMs }: ConfirmDialogProps) {
  const [disabled, setDisabled] = useState(false);

  useEffect(() => {
    if (!timeoutMs || timeoutMs === 0) return;
    const timer = setTimeout(() => {
      setDisabled(true);
      onAction?.({ choice: '__timeout__' });
    }, timeoutMs);
    return () => clearTimeout(timer);
  }, [timeoutMs, onAction]);

  return (
    <div className="rounded p-4 space-y-3" style={{ background: 'var(--color-bg-raised)', border: '1px solid var(--color-border-default)' }}>
      <div className="text-sm" style={{ color: 'var(--color-ink-primary)' }}>{message}</div>
      <div className="flex gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => { if (!disabled) onAction?.({ choice: opt }); }}
            disabled={disabled}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-40"
            style={{ background: 'var(--color-accent)', color: '#fff' }}
          >
            {opt}
          </button>
        ))}
      </div>
      {disabled && (
        <div className="text-xs" style={{ color: 'var(--color-ink-secondary)' }}>操作超时，已采用默认行为</div>
      )}
    </div>
  );
}
