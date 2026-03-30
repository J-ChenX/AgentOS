import { useReducer } from 'react';
import { produce } from 'immer';
import type {
  StreamEvent,
  ComponentDeltaEvent,
  TaskStatus,
  TextEvent,
  SkillCallEvent,
  SkillResultEvent,
  Session,
} from '../types';

// ── State ────────────────────────────────────────────────────────

export interface ComponentState {
  id: string;
  component_type: string;
  data: Record<string, unknown>;
}

export interface ChatState {
  taskId: string | null;
  status: TaskStatus | 'idle';
  events: StreamEvent[];
  components: Record<string, ComponentState>;
  pendingAction: StreamEvent | null;
}

export const initialChatState: ChatState = {
  taskId: null,
  status: 'idle',
  events: [],
  components: {},
  pendingAction: null,
};

// ── Actions ──────────────────────────────────────────────────────

export type ChatAction =
  | { type: 'PUSH_EVENT'; event: StreamEvent }
  | { type: 'BULK_LOAD'; session: Session }
  | { type: 'RESET' };

// ── Helpers ──────────────────────────────────────────────────────

function resolvePath(obj: Record<string, unknown>, path: string): unknown {
  if (path === '/') return obj;
  const parts = path.replace(/^\//, '').split('/');
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

function setAtPath(obj: Record<string, unknown>, path: string, value: unknown): void {
  const parts = path.replace(/^\//, '').split('/');
  let current: Record<string, unknown> = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const next = current[parts[i]];
    if (next == null || typeof next !== 'object') return;
    current = next as Record<string, unknown>;
  }
  current[parts[parts.length - 1]] = value;
}

// Mutations inside produce() are safe — they operate on Immer draft proxies
function applyDelta(components: Record<string, ComponentState>, event: ComponentDeltaEvent): void {
  const comp = components[event.id];
  if (!comp) return;

  switch (event.op) {
    case 'append': {
      const arr = resolvePath(comp.data, event.path);
      if (Array.isArray(arr)) arr.push(event.value);
      break;
    }
    case 'set': {
      setAtPath(comp.data, event.path, event.value);
      break;
    }
    case 'merge': {
      const target = resolvePath(comp.data, event.path);
      if (target && typeof target === 'object' && !Array.isArray(target)) {
        Object.assign(target, event.value as Record<string, unknown>);
      }
      break;
    }
    case 'replace': {
      comp.data = event.value as Record<string, unknown>;
      break;
    }
  }
}

// ── Reducer ──────────────────────────────────────────────────────

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'RESET':
      return initialChatState;

    case 'BULK_LOAD':
      return produce(initialChatState, (draft) => {
        for (const turn of action.session.turns) {
          draft.events.push({
            type: 'user_message',
            content: turn.user_message,
            turn_id: turn.turn_id,
            seq: 0,
          });
          for (const event of turn.events) {
            if (event.type === 'skill_result') {
              const callIdx = draft.events.findLastIndex(
                (e) => e.type === 'skill_call' && (e as SkillCallEvent).id === event.id,
              );
              if (callIdx >= 0) {
                const callArgs = (draft.events[callIdx] as SkillCallEvent).args;
                draft.events.splice(callIdx, 1, {
                  ...event,
                  args: callArgs,
                } as unknown as StreamEvent);
              } else {
                draft.events.push(event);
              }
              continue;
            }
            if (event.type === 'text_delta') {
              const lastUserMsgIdx = draft.events.findLastIndex((e) => e.type === 'user_message');
              const searchFrom = lastUserMsgIdx + 1;
              const relIdx = draft.events.slice(searchFrom).findLastIndex((e) => e.type === 'text');
              const absIdx = relIdx >= 0 ? relIdx + searchFrom : -1;
              if (absIdx >= 0) {
                (draft.events[absIdx] as TextEvent).content += event.content;
              } else {
                draft.events.push({ type: 'text', content: event.content, seq: event.seq });
              }
              continue;
            }
            draft.events.push(event);
            if (event.type === 'component') {
              draft.components[event.id] = {
                id: event.id,
                component_type: event.component_type,
                data: event.data,
              };
            }
            if (event.type === 'component_delta') {
              applyDelta(draft.components, event as ComponentDeltaEvent);
            }
          }
        }
        const lastTurn = action.session.turns.at(-1);
        if (lastTurn) {
          draft.status = lastTurn.status;
        }
      });

    case 'PUSH_EVENT':
      return produce(state, (draft) => {
        const event = action.event;

        // ── skill_result merge: replace matching skill_call with enriched result ─
        if (event.type === 'skill_result') {
          const callIdx = draft.events.findLastIndex(
            (e) => e.type === 'skill_call' && (e as SkillCallEvent).id === event.id,
          );
          if (callIdx >= 0) {
            const callArgs = (draft.events[callIdx] as SkillCallEvent).args;
            const enriched: SkillResultEvent = { ...event, args: callArgs };
            draft.events.splice(callIdx, 1, enriched as unknown as StreamEvent);
            return;
          }
          // No matching skill_call found — push as-is
          draft.events.push(event);
          return;
        }
        // ─────────────────────────────────────────────────────────────────────────

        // ── text_delta pre-intercept: scope search to current turn only ──────────
        if (event.type === 'text_delta') {
          // Search only after the last user_message event to prevent cross-turn bleed
          const lastUserMsgIdx = draft.events.findLastIndex((e) => e.type === 'user_message');
          const searchFrom = lastUserMsgIdx + 1; // 0 if no user_message found
          const sliced = draft.events.slice(searchFrom);
          const relIdx = sliced.findLastIndex((e) => e.type === 'text');
          const absIdx = relIdx >= 0 ? relIdx + searchFrom : -1;

          if (absIdx >= 0) {
            (draft.events[absIdx] as TextEvent).content += event.content;
          } else {
            draft.events.push({ type: 'text', content: event.content, seq: event.seq });
          }
          return;
        }
        // ─────────────────────────────────────────────────────────────────────────

        draft.events.push(event);

        switch (event.type) {
          case 'task_started':
            draft.taskId = event.task_id;
            draft.status = 'running';
            break;
          case 'component':
            draft.components[event.id] = {
              id: event.id,
              component_type: event.component_type,
              data: event.data,
            };
            break;
          case 'component_delta':
            applyDelta(draft.components, event);
            break;
          case 'action_required':
            draft.pendingAction = event;
            break;
          case 'user_message':
            draft.pendingAction = null;
            break;
          case 'done':
            draft.status = 'done';
            break;
          case 'error':
            draft.status = 'error';
            break;
          case 'cancelled':
            draft.status = 'cancelled';
            break;
        }
      });

    default:
      return state;
  }
}

// ── Hook ─────────────────────────────────────────────────────────

export function useEventReducer() {
  return useReducer(chatReducer, initialChatState);
}
