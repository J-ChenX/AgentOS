interface ConfirmModalProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({ message, onConfirm, onCancel }: ConfirmModalProps) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.35)',
      }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div
        style={{
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          minWidth: '280px',
          display: 'flex', flexDirection: 'column', gap: '16px',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--font-body)', fontSize: '13px',
            color: 'var(--color-ink-primary)', margin: 0, lineHeight: 1.5,
          }}
        >
          {message}
        </p>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              fontFamily: 'var(--font-body)', fontSize: '12px',
              padding: '4px 14px', borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border-default)',
              background: 'transparent', color: 'var(--color-ink-secondary)',
              cursor: 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            style={{
              fontFamily: 'var(--font-body)', fontSize: '12px',
              padding: '4px 14px', borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: 'var(--color-error)', color: '#fff',
              cursor: 'pointer',
            }}
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}
