interface UserBubbleProps {
  content: string;
}

export default function UserBubble({ content }: UserBubbleProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '4px' }}>
      <div
        style={{
          maxWidth: '72%',
          background: 'var(--color-bg-raised)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '8px 12px',
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
          fontWeight: 400,
          color: 'var(--color-ink-primary)',
          lineHeight: 1.5,
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
        }}
      >
        {content}
      </div>
    </div>
  );
}
