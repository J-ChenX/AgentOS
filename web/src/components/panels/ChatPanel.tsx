import { useReducer, useCallback, useRef, useState, useEffect, useMemo } from 'react';
import { Trash2 } from 'lucide-react';
import DOMPurify from 'dompurify';
import ChatInput from '../chat/ChatInput';
import MessageList from '../chat/MessageList';
import ReconnectionBanner from '../chat/ReconnectionBanner';
import ConfirmModal from '../common/ConfirmModal';
import { chatReducer, initialChatState } from '../../hooks/useEventReducer';
import type { AgentAdapter, UserMessageEvent, Annotation, AnnotationCreate } from '../../types';
import { useSessionNav } from '../../contexts/SessionNavContext';

export default function ChatPanel({ adapter }: { adapter: AgentAdapter }) {
  const { activeSessionId, navigateTo } = useSessionNav();
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const abortRef = useRef<AbortController | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [annotationMap, setAnnotationMap] = useState<Map<string, Annotation[]>>(new Map());

  // Track latest requested session to guard against race conditions
  const latestRequestedIdRef = useRef<string | null>(null);

  // Load history when activeSessionId changes
  useEffect(() => {
    if (!activeSessionId) {
      // Navigated to new chat — reset
      abortRef.current?.abort();
      setSessionId(null);
      setSessionTitle(null);
      setSendError(null);
      setReconnecting(false);
      setAnnotationMap(new Map());
      dispatch({ type: 'RESET' });
      return;
    }

    const requestedId = activeSessionId;
    latestRequestedIdRef.current = requestedId;

    adapter.getSession(requestedId).then((session) => {
      // Race condition guard: discard if a newer navigation happened
      if (latestRequestedIdRef.current !== requestedId) return;

      dispatch({ type: 'BULK_LOAD', session });
      setSessionId(session.session_id);
      setSessionTitle(session.title);
      setSendError(null);
      setReconnecting(false);

      // Populate annotation map from all turns
      const map = new Map<string, Annotation[]>();
      for (const turn of session.turns) {
        if (turn.annotations?.length) {
          map.set(turn.turn_id, turn.annotations);
        }
      }
      setAnnotationMap(map);
    }).catch((err) => {
      if (latestRequestedIdRef.current !== requestedId) return;
      console.error('Failed to load session:', err);
      setSendError('无法加载历史对话，请重试或开启新对话');
      dispatch({ type: 'RESET' });
    });
  }, [activeSessionId, adapter]);

  const handleSend = useCallback(
    async (userMessage: string) => {
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      setSendError(null);
      setReconnecting(false);

      const turnId = crypto.randomUUID();
      const userEvent: UserMessageEvent = {
        type: 'user_message',
        content: userMessage,
        turn_id: turnId,
        seq: 0,
      };
      dispatch({ type: 'PUSH_EVENT', event: userEvent });

      let resolvedSessionId = sessionId;
      let resolvedTurnId: string = turnId;

      try {
        if (!resolvedSessionId) {
          const result = await adapter.createSession(userMessage);
          resolvedSessionId = result.session_id;
          resolvedTurnId = result.turn_id;
          setSessionId(resolvedSessionId);
        } else {
          const result = await adapter.addTurn(resolvedSessionId, userMessage, turnId);
          resolvedTurnId = result.turn_id;
        }
      } catch (err) {
        setSendError((err as Error).message || '发送失败，请重试');
        return;
      }

      try {
        for await (const event of adapter.streamTurn(resolvedSessionId, resolvedTurnId)) {
          if (abortRef.current?.signal.aborted) break;
          setReconnecting(false);
          dispatch({ type: 'PUSH_EVENT', event });
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          try {
            const session = await adapter.getSession(resolvedSessionId!);
            const turn = session.turns.find((t) => t.turn_id === resolvedTurnId);
            if (turn?.status === 'done') {
              if (turn.assistant_message) {
                dispatch({
                  type: 'PUSH_EVENT',
                  event: { type: 'text', content: turn.assistant_message, seq: Date.now() },
                });
              }
              dispatch({
                type: 'PUSH_EVENT',
                event: { type: 'done', task_id: resolvedTurnId, summary: '', seq: Date.now() + 1 },
              });
              return;
            }
          } catch {
            // fall through
          }
          setReconnecting(true);
          console.error('Stream error:', err);
        }
      }
    },
    [adapter, sessionId],
  );

  const handleCancel = useCallback(async () => {
    abortRef.current?.abort();
    if (sessionId) {
      const runningTurn = state.events.filter((e) => e.type === 'user_message').at(-1);
      if (runningTurn && 'turn_id' in runningTurn) {
        await adapter.cancelTurn(sessionId, runningTurn.turn_id as string);
      }
    }
  }, [adapter, sessionId, state.events]);

  const handleNewChat = useCallback(() => {
    abortRef.current?.abort();
    navigateTo(null);
  }, [navigateTo]);

  const handleDeleteSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await adapter.deleteSession(sessionId);
      navigateTo(null);
    } catch {
      setSendError('删除失败，请重试');
    }
  }, [adapter, sessionId, navigateTo]);

  const annotationContext = useMemo(() => {
    if (!sessionId) return undefined;
    return {
      sessionId,
      turnAnnotations: annotationMap,
      onAdd: async (turnId: string, payload: AnnotationCreate) => {
        const ann = await adapter.addAnnotation(sessionId, turnId, payload);
        setAnnotationMap((prev) => {
          const next = new Map(prev);
          next.set(turnId, [...(next.get(turnId) ?? []), ann]);
          return next;
        });
      },
      onRemove: async (turnId: string, annotationId: string) => {
        await adapter.removeAnnotation(sessionId, turnId, annotationId);
        setAnnotationMap((prev) => {
          const next = new Map(prev);
          next.set(turnId, (next.get(turnId) ?? []).filter((a) => a.annotation_id !== annotationId));
          return next;
        });
      },
    };
  }, [sessionId, annotationMap, adapter]);

  const isRunning = state.status === 'running';

  return (
    <div className="flex flex-col h-full">
      {showDeleteConfirm && (
        <ConfirmModal
          message="确定删除此会话？删除后不可恢复。"
          onConfirm={async () => {
            setShowDeleteConfirm(false);
            await handleDeleteSession();
          }}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '4px 12px', flexShrink: 0,
          borderBottom: '1px solid var(--color-border-subtle)',
        }}
      >
        <button
          onClick={handleNewChat}
          style={{
            fontSize: 'var(--text-xs)', padding: '3px 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border-default)',
            background: 'transparent',
            color: 'var(--color-ink-secondary)',
            cursor: 'pointer', fontFamily: 'var(--font-body)',
          }}
        >
          新对话
        </button>
        {sessionTitle && (
          <span
            title={sessionTitle}
            style={{
              flex: 1, fontSize: 'var(--text-xs)', color: 'var(--color-ink-secondary)',
              fontFamily: 'var(--font-body)', fontWeight: 400,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              textAlign: 'center',
            }}
          >
            {DOMPurify.sanitize(sessionTitle)}
          </span>
        )}
        {sessionId && (
          <button
            aria-label="删除会话"
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              fontSize: 'var(--text-xs)', padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(155,58,46,0.2)',
              background: 'rgba(155,58,46,0.06)',
              color: 'var(--color-error)',
              cursor: 'pointer', fontFamily: 'var(--font-body)',
              display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0,
            }}
          >
            <Trash2 size={11} strokeWidth={1.8} />
            删除会话
          </button>
        )}
      </div>
      <MessageList
        events={state.events}
        components={state.components}
        adapter={adapter}
        isRunning={isRunning}
        annotationContext={annotationContext}
      />
      {sendError && (
        <div
          style={{
            padding: '6px 14px', flexShrink: 0,
            fontSize: 'var(--text-xs)', color: 'var(--color-error)',
            fontFamily: 'var(--font-body)',
          }}
        >
          {sendError}
        </div>
      )}
      {isRunning && (
        <div style={{ padding: '4px 14px', flexShrink: 0 }}>
          <button
            onClick={handleCancel}
            style={{
              fontSize: 'var(--text-xs)', padding: '3px 10px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border-default)',
              background: 'transparent',
              color: 'var(--color-ink-secondary)',
              cursor: 'pointer', fontFamily: 'var(--font-body)',
              transition: 'background 0.15s, border-color 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              const btn = e.currentTarget;
              btn.style.background = 'rgba(155,58,46,0.08)';
              btn.style.borderColor = 'rgba(155,58,46,0.2)';
              btn.style.color = 'var(--color-error)';
            }}
            onMouseLeave={(e) => {
              const btn = e.currentTarget;
              btn.style.background = 'transparent';
              btn.style.borderColor = 'var(--color-border-default)';
              btn.style.color = 'var(--color-ink-secondary)';
            }}
          >
            取消
          </button>
        </div>
      )}
      <ReconnectionBanner visible={reconnecting} />
      <ChatInput onSend={handleSend} disabled={isRunning} />
    </div>
  );
}
