import { useRef, useEffect } from 'react';
import EventRenderer from '../events/EventRenderer';
import AnnotatedText from './AnnotatedText';
import ThinkingBubble from '../events/ThinkingBubble';
import type { StreamEvent, UserMessageEvent, AgentAdapter, Annotation, AnnotationCreate } from '../../types';
import type { ComponentState } from '../../hooks/useEventReducer';

export interface AnnotationContext {
  sessionId: string;
  turnAnnotations: Map<string, Annotation[]>;
  onAdd: (turnId: string, payload: AnnotationCreate) => Promise<void>;
  onRemove: (turnId: string, annotationId: string) => Promise<void>;
}

interface MessageListProps {
  events: StreamEvent[];
  components: Record<string, ComponentState>;
  adapter: AgentAdapter;
  isRunning?: boolean;
  annotationContext?: AnnotationContext;
}

function TimeDivider({ timestamp }: { timestamp?: string }) {
  const d = timestamp ? new Date(timestamp) : new Date();
  const label = `今天 · ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '4px 0' }}>
      <div style={{ flex: 1, height: '1px', background: 'var(--color-border-subtle)' }} />
      <span
        style={{
          fontSize: 'var(--text-xs)', color: 'var(--color-ink-tertiary)',
          fontFamily: 'var(--font-body)', fontWeight: 300, letterSpacing: '0.04em',
        }}
      >
        {label}
      </span>
      <div style={{ flex: 1, height: '1px', background: 'var(--color-border-subtle)' }} />
    </div>
  );
}

const SKIP_EVENTS = new Set(['task_started', 'context_truncated']);

export default function MessageList({
  events,
  components,
  adapter,
  isRunning = false,
  annotationContext,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === 'function') {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]); // depend on array reference, not .length — text_delta mutates content without changing array length

  if (events.length === 0) {
    return (
      <div
        className="flex-1 flex items-center justify-center"
        style={{
          color: 'var(--color-ink-tertiary)',
          fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', fontWeight: 300,
        }}
      >
        发送任务以开始
      </div>
    );
  }

  // Find index of last user_message to determine if current turn is running
  const lastUserMsgIdx = events.reduce(
    (last, e, i) => (e.type === 'user_message' ? i : last),
    -1,
  );

  // Determine if the very last visible event is a user_message (no response yet)
  const lastVisibleEvent = [...events].reverse().find((e) => !SKIP_EVENTS.has(e.type));
  const isWaitingForResponse = isRunning && lastVisibleEvent?.type === 'user_message';

  return (
    <div
      className="flex-1 overflow-y-auto"
      style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}
    >
      {events.map((event, i) => {
        if (SKIP_EVENTS.has(event.type)) return null;

        if (event.type === 'user_message') {
          const msgEvent = event as UserMessageEvent;
          const isLastMsg = i === lastUserMsgIdx;
          // Disable annotation toolbar on the currently-running turn
          const enableAnnotation = !!annotationContext && !(isRunning && isLastMsg);

          return (
            <div key={i}>
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
                  {enableAnnotation ? (
                    <AnnotatedText
                      text={msgEvent.content}
                      annotations={annotationContext!.turnAnnotations.get(msgEvent.turn_id) ?? []}
                      target="user"
                      onAddAnnotation={(payload) =>
                        annotationContext!.onAdd(msgEvent.turn_id, payload)
                      }
                      onRemoveAnnotation={(annotationId) =>
                        annotationContext!.onRemove(msgEvent.turn_id, annotationId)
                      }
                    />
                  ) : (
                    msgEvent.content
                  )}
                </div>
              </div>
              <TimeDivider />
            </div>
          );
        }

        return (
          <EventRenderer key={i} event={event} components={components} adapter={adapter} />
        );
      })}
      {isWaitingForResponse && <ThinkingBubble content="思考中..." />}
      <div ref={endRef} />
    </div>
  );
}
