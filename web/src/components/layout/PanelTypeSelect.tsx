import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Clock, Folder, Settings, Plug, ChevronDown, Check } from 'lucide-react';
import type { ViewportType } from '../../types/layout';

const TYPE_CONFIG: Record<
  string,
  { label: string; Icon: React.FC<{ size?: number; strokeWidth?: number }> }
> = {
  chat: { label: '对话', Icon: MessageSquare },
  history: { label: '历史记录', Icon: Clock },
  files: { label: '项目文件', Icon: Folder },
  config: { label: '配置', Icon: Settings },
  skills: { label: 'Skills', Icon: Plug },
};

const ORDERED_TYPES: ViewportType[] = ['chat', 'history', 'files', 'config', 'skills'];

interface PanelTypeSelectProps {
  value: ViewportType;
  onChange: (type: ViewportType) => void;
}

export default function PanelTypeSelect({ value, onChange }: PanelTypeSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const config = TYPE_CONFIG[value] ?? TYPE_CONFIG['chat'];
  const { label, Icon } = config;

  useEffect(() => {
    if (!open) return;
    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [open]);

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          padding: '3px 7px 3px 6px',
          borderRadius: 'var(--radius-sm)',
          background: open ? 'var(--color-bg-sunken)' : 'transparent',
          border: open ? '1px solid var(--color-border-strong)' : '1px solid transparent',
          cursor: 'pointer',
          transition: 'background 0.15s, border-color 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!open) {
            (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-bg-sunken)';
            (e.currentTarget as HTMLButtonElement).style.borderColor =
              'var(--color-border-default)';
          }
        }}
        onMouseLeave={(e) => {
          if (!open) {
            (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            (e.currentTarget as HTMLButtonElement).style.borderColor = 'transparent';
          }
        }}
      >
        <Icon size={13} strokeWidth={1.8} />
        <span
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: '11.5px',
            fontWeight: 500,
            color: 'var(--color-ink-secondary)',
            letterSpacing: '0.01em',
          }}
        >
          {label}
        </span>
        <ChevronDown
          size={11}
          strokeWidth={2}
          style={{
            color: 'var(--color-ink-tertiary)',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.15s',
          }}
        />
      </button>

      {/* Dropdown menu */}
      {open && (
        <div
          role="menu"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            minWidth: '152px',
            zIndex: 100,
            background: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border-default)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
          }}
        >
          {ORDERED_TYPES.map((type, i) => {
            const item = TYPE_CONFIG[type];
            if (!item) return null;
            const isActive = type === value;
            const isLast = i === ORDERED_TYPES.length - 1;
            const showDivider = type === 'config'; // divider before config/skills section
            return (
              <div key={type}>
                {showDivider && (
                  <div style={{ height: '1px', background: 'var(--color-border-subtle)' }} />
                )}
                <button
                  role="menuitem"
                  aria-checked={isActive}
                  onClick={() => {
                    onChange(type);
                    setOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '7px 12px',
                    fontFamily: 'var(--font-body)',
                    fontSize: '12px',
                    fontWeight: isActive ? 500 : 400,
                    color: isActive ? 'var(--color-ink-primary)' : 'var(--color-ink-secondary)',
                    background: isActive ? 'var(--color-bg-raised)' : 'transparent',
                    border: 'none',
                    borderBottom: isLast ? 'none' : '1px solid var(--color-border-subtle)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.1s, color 0.1s',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background =
                      'var(--color-bg-raised)';
                    (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-ink-primary)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background = isActive
                      ? 'var(--color-bg-raised)'
                      : 'transparent';
                    (e.currentTarget as HTMLButtonElement).style.color = isActive
                      ? 'var(--color-ink-primary)'
                      : 'var(--color-ink-secondary)';
                  }}
                >
                  <item.Icon size={13} strokeWidth={1.8} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {isActive && (
                    <Check
                      size={12}
                      strokeWidth={2}
                      style={{ color: 'var(--color-ink-secondary)' }}
                    />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
