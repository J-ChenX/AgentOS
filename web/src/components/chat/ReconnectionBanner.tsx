interface ReconnectionBannerProps {
  visible: boolean;
}

export default function ReconnectionBanner({ visible }: ReconnectionBannerProps) {
  if (!visible) return null;

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '7px 14px',
        background: 'rgba(138,106,28,0.07)',
        borderTop: '1px solid rgba(138,106,28,0.2)',
        fontFamily: 'var(--font-body)', fontSize: '12px',
        color: 'var(--color-warning)', fontWeight: 400,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          display: 'inline-block', width: '6px', height: '6px',
          borderRadius: '50%', background: 'var(--color-warning)',
          animation: 'warning-blink 1s ease-in-out infinite',
          flexShrink: 0,
        }}
      />
      连接中断，正在重连…
      <style>{`
        @keyframes warning-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
