import { Brain } from 'lucide-react';

export default function ThinkingBubble({ content }: { content: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        background: 'var(--color-bg-raised)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <Brain
        size={14}
        strokeWidth={1.6}
        style={{ color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
      />
      <span
        style={{
          fontFamily: 'var(--font-body)',
          fontStyle: 'italic',
          fontWeight: 300,
          fontSize: 'var(--text-sm)',
          color: 'var(--color-ink-tertiary)',
          lineHeight: 'var(--leading-normal)',
        }}
      >
        {content}
      </span>
      <span style={{ display: 'inline-flex', gap: '2px', marginLeft: '2px' }}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              display: 'inline-block',
              width: '3px',
              height: '3px',
              borderRadius: '50%',
              background: 'var(--color-ink-tertiary)',
              animation: 'thinking-blink 1.4s ease-in-out infinite',
              animationDelay: `${i * 0.22}s`,
            }}
          />
        ))}
      </span>
      <style>{`
        @keyframes thinking-blink {
          0%, 80%, 100% { opacity: 0.2; }
          40% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
