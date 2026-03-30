import { useState, useCallback, useRef } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }, []);

  return (
    <div
      style={{
        borderTop: '1px solid var(--color-border-subtle)',
        padding: '10px 14px',
        display: 'flex', gap: '8px', alignItems: 'flex-end',
        background: 'var(--color-bg-surface)', flexShrink: 0,
      }}
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="输入任务..."
        disabled={disabled}
        style={{
          flex: 1, resize: 'none', overflow: 'hidden',
          minHeight: '34px', maxHeight: '120px',
          padding: '7px 11px',
          background: 'var(--color-bg-sunken)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)',
          color: 'var(--color-ink-primary)', fontWeight: 400,
          outline: 'none',
          transition: 'border-color 0.15s',
        }}
        onFocus={(e) => { e.target.style.borderColor = 'var(--color-border-strong)'; }}
        onBlur={(e) => { e.target.style.borderColor = 'var(--color-border-default)'; }}
      />
      <button
        onClick={handleSubmit}
        disabled={!value.trim() || disabled}
        aria-label="发送"
        style={{
          height: '34px', minWidth: '60px', padding: '0 14px',
          background: 'var(--color-accent)', color: 'var(--color-ink-inverse)',
          border: 'none', borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', fontWeight: 500,
          cursor: 'pointer', letterSpacing: '0.01em',
          transition: 'background 0.15s', flexShrink: 0,
          opacity: (!value.trim() || disabled) ? 0.35 : 1,
        }}
        onMouseEnter={(e) => {
          if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-accent-hover)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-accent)';
        }}
      >
        发送
      </button>
    </div>
  );
}
