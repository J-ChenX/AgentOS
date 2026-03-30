import { useState, useEffect, useCallback, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import DOMPurify from 'dompurify';
import type { AgentAdapter, Session } from '../../types';
import { useSessionNav } from '../../App';
import ConfirmModal from '../common/ConfirmModal';

function StatusBadge({ status }: { status: string }) {
  const isDone = status === 'done';
  const isError = status === 'error' || status === 'failed';
  const bg = isDone
    ? 'rgba(74,124,92,0.1)'
    : isError
    ? 'rgba(155,58,46,0.08)'
    : 'var(--color-bg-sunken)';
  const color = isDone
    ? 'var(--color-success)'
    : isError
    ? 'var(--color-error)'
    : 'var(--color-ink-secondary)';
  return (
    <span
      style={{
        fontFamily: 'var(--font-mono)', fontSize: '9.5px', fontWeight: 400,
        padding: '2px 6px', borderRadius: 'var(--radius-sm)',
        background: bg, color, flexShrink: 0, letterSpacing: '0.04em',
      }}
    >
      {status}
    </span>
  );
}

function SessionRow({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      data-testid="session-row"
      data-active={isActive ? 'true' : undefined}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '10px 14px', cursor: 'pointer',
        borderBottom: '1px solid var(--color-border-subtle)',
        background: isActive
          ? 'var(--color-bg-sunken)'
          : hovered
          ? 'var(--color-bg-raised)'
          : 'transparent',
        transition: 'background 0.1s', position: 'relative',
      }}
    >
      <div
        onClick={onSelect}
        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
      >
        <span
          style={{
            flex: 1, fontFamily: 'var(--font-body)', fontSize: '12.5px',
            fontWeight: isActive ? 500 : 400,
            color: 'var(--color-ink-primary)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}
        >
          {DOMPurify.sanitize(session.title)}
        </span>
        <StatusBadge status={session.turns?.at(-1)?.status ?? 'done'} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
        <span
          style={{
            flex: 1, fontFamily: 'var(--font-mono)', fontSize: '10px',
            color: 'var(--color-ink-tertiary)',
          }}
        >
          {new Date(session.updated_at).toLocaleString('zh-CN')}
        </span>
        {hovered && (
          <button
            aria-label="删除会话"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            style={{
              background: 'transparent', border: 'none',
              color: 'var(--color-ink-tertiary)', cursor: 'pointer', padding: '2px',
              display: 'flex', alignItems: 'center',
            }}
          >
            <Trash2 size={13} strokeWidth={1.6} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function HistoryPanel({ adapter }: { adapter: AgentAdapter }) {
  const { activeSessionId, navigateTo } = useSessionNav();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const offset = useRef(0);
  const loadingRef = useRef(false);

  const loadMore = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    try {
      const result = await adapter.getSessions(50, offset.current);
      setSessions((prev) => [...prev, ...result.items]);
      setTotal(result.total);
      offset.current += result.items.length;
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [adapter]);

  useEffect(() => {
    loadMore();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDeleteId) return;
    const sessionId = pendingDeleteId;
    setPendingDeleteId(null);
    setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    setTotal((t) => Math.max(0, t - 1));
    offset.current = Math.max(0, offset.current - 1);
    if (activeSessionId === sessionId) {
      navigateTo(null);
    }
    try {
      await adapter.deleteSession(sessionId);
    } catch {
      offset.current = 0;
      setSessions([]);
      setTotal(0);
      loadMore();
    }
  }, [pendingDeleteId, adapter, activeSessionId, navigateTo, loadMore]);

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {pendingDeleteId && (
        <ConfirmModal
          message="确定删除此会话？删除后不可恢复。"
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDeleteId(null)}
        />
      )}
      {sessions.length === 0 && !loading ? (
        <div
          className="flex-1 flex items-center justify-center"
          style={{
            color: 'var(--color-ink-tertiary)',
            fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', fontWeight: 300,
          }}
        >
          暂无历史记录
        </div>
      ) : (
        <>
          {sessions.map((session) => (
            <SessionRow
              key={session.session_id}
              session={session}
              isActive={session.session_id === activeSessionId}
              onSelect={() => navigateTo(session.session_id)}
              onDelete={() => setPendingDeleteId(session.session_id)}
            />
          ))}
          {sessions.length < total && (
            <button
              onClick={loadMore}
              disabled={loading}
              style={{
                padding: '10px', textAlign: 'center',
                color: 'var(--color-ink-secondary)',
                fontFamily: 'var(--font-body)', fontSize: 'var(--text-xs)',
                background: 'none', border: 'none', cursor: 'pointer',
              }}
            >
              {loading ? '加载中...' : '加载更多'}
            </button>
          )}
        </>
      )}
    </div>
  );
}
