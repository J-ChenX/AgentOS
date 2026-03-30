import { PanelLeft, PanelTop, X } from 'lucide-react';
import type { AgentAdapter } from '../../types';
import type { ViewportType, ViewportNode } from '../../types/layout';
import { renderWidget } from './WidgetRegistry';
import PanelTypeSelect from './PanelTypeSelect';

interface ViewportContainerProps {
  node: ViewportNode;
  adapter: AgentAdapter;
  onUpdateType: (id: string, type: ViewportType) => void;
  onSplit: (id: string, direction: 'horizontal' | 'vertical') => void;
  onClose: (id: string) => void;
  canClose: boolean;
}

function PanelButton({
  onClick,
  title,
  isClose = false,
  children,
}: {
  onClick: () => void;
  title: string;
  isClose?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: '22px',
        height: '22px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--radius-sm)',
        background: 'transparent',
        border: '1px solid transparent',
        cursor: 'pointer',
        color: 'var(--color-ink-tertiary)',
        transition: 'background 0.15s, border-color 0.15s, color 0.15s',
      }}
      onMouseEnter={(e) => {
        const btn = e.currentTarget;
        if (isClose) {
          btn.style.background = 'rgba(155,58,46,0.08)';
          btn.style.borderColor = 'rgba(155,58,46,0.2)';
          btn.style.color = 'var(--color-error)';
        } else {
          btn.style.background = 'var(--color-bg-sunken)';
          btn.style.borderColor = 'var(--color-border-default)';
          btn.style.color = 'var(--color-ink-secondary)';
        }
      }}
      onMouseLeave={(e) => {
        const btn = e.currentTarget;
        btn.style.background = 'transparent';
        btn.style.borderColor = 'transparent';
        btn.style.color = 'var(--color-ink-tertiary)';
      }}
    >
      {children}
    </button>
  );
}

export default function ViewportContainer({
  node,
  adapter,
  onUpdateType,
  onSplit,
  onClose,
  canClose,
}: ViewportContainerProps) {
  return (
    <div className="flex h-full flex-col" style={{ background: 'var(--color-bg-surface)' }}>
      <header
        style={{
          height: '30px',
          display: 'flex',
          alignItems: 'center',
          padding: '0 8px',
          gap: '4px',
          flexShrink: 0,
          background: 'var(--color-bg-raised)',
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        <PanelTypeSelect
          value={node.type ?? 'chat'}
          onChange={(type) => onUpdateType(node.id, type)}
        />

        <div
          style={{
            width: '1px',
            height: '14px',
            background: 'var(--color-border-default)',
            margin: '0 4px',
          }}
        />
        <div style={{ flex: 1 }} />

        <PanelButton onClick={() => onSplit(node.id, 'vertical')} title="纵向分割">
          <PanelLeft size={13} strokeWidth={1.8} />
        </PanelButton>
        <PanelButton onClick={() => onSplit(node.id, 'horizontal')} title="横向分割">
          <PanelTop size={13} strokeWidth={1.8} />
        </PanelButton>
        {canClose && (
          <PanelButton onClick={() => onClose(node.id)} title="关闭面板" isClose>
            <X size={13} strokeWidth={2} />
          </PanelButton>
        )}
      </header>
      <div className="flex-1 overflow-hidden">{renderWidget(node.type ?? 'chat', adapter)}</div>
    </div>
  );
}
