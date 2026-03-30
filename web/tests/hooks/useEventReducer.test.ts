import { chatReducer, initialChatState, type ChatState } from '../../src/hooks/useEventReducer';
import type {
  TaskStartedEvent,
  ThinkingEvent,
  TextEvent,
  TextDeltaEvent,
  ComponentEvent,
  ComponentDeltaEvent,
  SkillCallEvent,
  SkillResultEvent,
  ActionRequiredEvent,
  DoneEvent,
  ErrorEvent,
  CancelledEvent,
  UserMessageEvent,
  Session,
} from '../../src/types';

describe('chatReducer', () => {
  it('initializes with idle state', () => {
    expect(initialChatState.status).toBe('idle');
    expect(initialChatState.taskId).toBeNull();
    expect(initialChatState.events).toEqual([]);
    expect(initialChatState.components).toEqual({});
    expect(initialChatState.pendingAction).toBeNull();
  });

  it('handles task_started', () => {
    const event: TaskStartedEvent = { type: 'task_started', task_id: 'task_1', seq: 1 };
    const state = chatReducer(initialChatState, { type: 'PUSH_EVENT', event });
    expect(state.taskId).toBe('task_1');
    expect(state.status).toBe('running');
    expect(state.events).toHaveLength(1);
  });

  it('handles thinking event (appended, no status change)', () => {
    const started = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'task_started', task_id: 't1', seq: 1 },
    });
    const state = chatReducer(started, {
      type: 'PUSH_EVENT',
      event: { type: 'thinking', content: 'Analyzing...', seq: 2 },
    });
    expect(state.events).toHaveLength(2);
    expect(state.status).toBe('running');
  });

  it('handles component event (registers component)', () => {
    const event: ComponentEvent = {
      type: 'component',
      id: 'comp_1',
      component_type: 'data_table',
      data: { columns: ['A', 'B'], rows: [] },
      seq: 3,
    };
    const state = chatReducer(initialChatState, { type: 'PUSH_EVENT', event });
    expect(state.components['comp_1']).toBeDefined();
    expect(state.components['comp_1'].component_type).toBe('data_table');
    expect((state.components['comp_1'].data as any).rows).toEqual([]);
  });

  it('handles component_delta append', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'c1',
        component_type: 'data_table',
        data: { columns: ['A'], rows: [] },
        seq: 1,
      },
    });
    const delta: ComponentDeltaEvent = {
      type: 'component_delta',
      id: 'c1',
      op: 'append',
      path: '/rows',
      value: { A: 'hello' },
      seq: 2,
    };
    state = chatReducer(state, { type: 'PUSH_EVENT', event: delta });
    const rows = (state.components['c1'].data as any).rows;
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({ A: 'hello' });
  });

  it('handles component_delta set', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'c1',
        component_type: 'data_table',
        data: { title: 'old' },
        seq: 1,
      },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component_delta',
        id: 'c1',
        op: 'set',
        path: '/title',
        value: 'new',
        seq: 2,
      },
    });
    expect((state.components['c1'].data as any).title).toBe('new');
  });

  it('handles component_delta merge', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'c1',
        component_type: 'data_table',
        data: { meta: { total: 0, status: 'pending' } },
        seq: 1,
      },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component_delta',
        id: 'c1',
        op: 'merge',
        path: '/meta',
        value: { total: 24 },
        seq: 2,
      },
    });
    const meta = (state.components['c1'].data as any).meta;
    expect(meta.total).toBe(24);
    expect(meta.status).toBe('pending');
  });

  it('handles component_delta replace', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'c1',
        component_type: 'data_table',
        data: { old: true },
        seq: 1,
      },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component_delta',
        id: 'c1',
        op: 'replace',
        path: '/',
        value: { brand: 'new' },
        seq: 2,
      },
    });
    expect((state.components['c1'].data as any).brand).toBe('new');
    expect((state.components['c1'].data as any).old).toBeUndefined();
  });

  it('handles action_required (sets pendingAction)', () => {
    const event: ActionRequiredEvent = {
      type: 'action_required',
      action_id: 'act_1',
      component_type: 'confirm_dialog',
      data: { message: 'Continue?', options: ['Yes', 'No'] },
      blocking: true,
      timeout_ms: 120000,
      seq: 5,
    };
    const state = chatReducer(initialChatState, { type: 'PUSH_EVENT', event });
    expect(state.pendingAction).toBe(event);
  });

  it('handles done event', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'done', task_id: 't1', summary: 'Complete', seq: 10 },
    });
    expect(state.status).toBe('done');
  });

  it('handles error event', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'error',
        level: 'fatal',
        message: 'LLM crash',
        task_id: 't1',
        recoverable: false,
        seq: 10,
      },
    });
    expect(state.status).toBe('error');
  });

  it('handles cancelled event', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'cancelled', task_id: 't1', seq: 10 },
    });
    expect(state.status).toBe('cancelled');
  });

  it('RESET returns initial state', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'task_started', task_id: 't1', seq: 1 },
    });
    state = chatReducer(state, { type: 'RESET' });
    expect(state).toEqual(initialChatState);
  });

  it('ignores component_delta for unknown component id', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component_delta',
        id: 'nonexistent',
        op: 'set',
        path: '/foo',
        value: 'bar',
        seq: 1,
      },
    });
    expect(Object.keys(state.components)).toHaveLength(0);
  });

  it('supports batch replay (history rehydration)', () => {
    const events = [
      { type: 'task_started' as const, task_id: 't1', seq: 1 },
      { type: 'thinking' as const, content: '...', seq: 2 },
      { type: 'text' as const, content: 'Hello', seq: 3 },
      { type: 'done' as const, task_id: 't1', summary: 'Done', seq: 4 },
    ];
    let state = initialChatState;
    for (const event of events) {
      state = chatReducer(state, { type: 'PUSH_EVENT', event });
    }
    expect(state.taskId).toBe('t1');
    expect(state.status).toBe('done');
    expect(state.events).toHaveLength(4);
  });

  // component_delta pipeline tests
  it('append adds rows that DataTable would render', () => {
    let state = initialChatState;
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'tbl',
        component_type: 'data_table',
        data: { columns: ['A', 'B'], rows: [] },
        seq: 1,
      },
    });
    for (let i = 0; i < 5; i++) {
      state = chatReducer(state, {
        type: 'PUSH_EVENT',
        event: {
          type: 'component_delta',
          id: 'tbl',
          op: 'append',
          path: '/rows',
          value: { A: `row${i}`, B: i },
          seq: i + 2,
        },
      });
    }
    const rows = (state.components['tbl'].data as any).rows;
    expect(rows).toHaveLength(5);
    expect(rows[4]).toEqual({ A: 'row4', B: 4 });
  });

  it('merge updates progress_bar without losing other fields', () => {
    let state = initialChatState;
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component',
        id: 'pb',
        component_type: 'progress_bar',
        data: { current: 0, total: 10, label: 'Processing' },
        seq: 1,
      },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'component_delta',
        id: 'pb',
        op: 'merge',
        path: '/',
        value: { current: 7 },
        seq: 2,
      },
    });
    const data = state.components['pb'].data as any;
    expect(data.current).toBe(7);
    expect(data.total).toBe(10);
    expect(data.label).toBe('Processing');
  });

  it('text_delta appends content to last text event', () => {
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'text', content: 'Hello', seq: 1 },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: { type: 'text_delta', content: ' world', seq: 2 },
    });
    expect(state.events).toHaveLength(1);
    expect(state.events[0].type).toBe('text');
    expect((state.events[0] as TextEvent).content).toBe('Hello world');
  });

  it('text_delta before any text creates a new text event', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: { type: 'text_delta', content: 'Hi', seq: 1 },
    });
    expect(state.events).toHaveLength(1);
    expect(state.events[0].type).toBe('text');
    expect((state.events[0] as TextEvent).content).toBe('Hi');
  });

  it('text_delta is never stored as a raw event in events array', () => {
    let state = initialChatState;
    for (const char of ['A', 'B', 'C']) {
      state = chatReducer(state, {
        type: 'PUSH_EVENT',
        event: { type: 'text_delta', content: char, seq: 1 },
      });
    }
    expect(state.events).toHaveLength(1);
    expect(state.events.every((e) => e.type !== 'text_delta')).toBe(true);
    expect((state.events[0] as TextEvent).content).toBe('ABC');
  });

  it('error event with warning level still sets status to error', () => {
    const state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'error',
        level: 'warning',
        message: 'max iterations reached',
        task_id: 't1',
        recoverable: false,
        seq: 5,
      },
    });
    expect(state.status).toBe('error');
  });

  it('user_message event is stored in events array', () => {
    const event: UserMessageEvent = {
      type: 'user_message',
      content: 'hello',
      turn_id: 't1',
      seq: 0,
    };
    const state = chatReducer(initialChatState, { type: 'PUSH_EVENT', event });
    expect(state.events).toHaveLength(1);
    expect(state.events[0].type).toBe('user_message');
  });

  it('text_delta does NOT bleed into previous turn text event', () => {
    // Turn 1: user message + text event
    let state = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'user_message',
        content: 'turn1 question',
        turn_id: 't1',
        seq: 1,
      } as UserMessageEvent,
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: { type: 'text', content: 'Turn1 answer', seq: 2 },
    });
    // Turn 2: new user message, then text_delta
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: {
        type: 'user_message',
        content: 'turn2 question',
        turn_id: 't2',
        seq: 3,
      } as UserMessageEvent,
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: { type: 'text_delta', content: 'Turn2 ', seq: 4 },
    });
    state = chatReducer(state, {
      type: 'PUSH_EVENT',
      event: { type: 'text_delta', content: 'answer', seq: 5 },
    });

    // Turn1's text should be unchanged
    const turn1Text = state.events.find(
      (e, i) =>
        e.type === 'text' &&
        i <
          state.events.findIndex(
            (ev) => ev.type === 'user_message' && (ev as UserMessageEvent).turn_id === 't2',
          ),
    ) as TextEvent | undefined;
    expect(turn1Text?.content).toBe('Turn1 answer');

    // Turn2's text should be accumulated from deltas
    const turn2Text = state.events.findLast((e) => e.type === 'text') as TextEvent | undefined;
    expect(turn2Text?.content).toBe('Turn2 answer');
  });

  it('pendingAction is cleared when user_message event arrives', () => {
    const withAction = chatReducer(initialChatState, {
      type: 'PUSH_EVENT',
      event: {
        type: 'action_required',
        action_id: 'a1',
        component_type: 'confirm_dialog',
        data: {},
        blocking: true,
        timeout_ms: 60000,
        seq: 1,
      },
    });
    expect(withAction.pendingAction).not.toBeNull();

    const afterUser = chatReducer(withAction, {
      type: 'PUSH_EVENT',
      event: {
        type: 'user_message',
        content: 'next turn',
        turn_id: 't2',
        seq: 2,
      } as UserMessageEvent,
    });
    expect(afterUser.pendingAction).toBeNull();
  });

  it('skill_result merges into matching skill_call in PUSH_EVENT', () => {
    const call: SkillCallEvent = {
      type: 'skill_call',
      id: 'sc1',
      skill: 'shell',
      args: { command: 'ls' },
      status: 'running',
      seq: 1,
    };
    const result: SkillResultEvent = {
      type: 'skill_result',
      id: 'sc1',
      skill: 'shell',
      status: 'done',
      result: 'ok',
      seq: 2,
    };
    let state = chatReducer(initialChatState, { type: 'PUSH_EVENT', event: call });
    state = chatReducer(state, { type: 'PUSH_EVENT', event: result });
    // skill_call should be replaced by skill_result (with args preserved)
    expect(state.events).toHaveLength(1);
    expect(state.events[0].type).toBe('skill_result');
    expect((state.events[0] as SkillResultEvent).args).toEqual({ command: 'ls' });
  });
});

describe('BULK_LOAD', () => {
  const makeSession = (overrides: Partial<Session> = {}): Session => ({
    session_id: 's1',
    title: 'Test',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    turns: [
      {
        turn_id: 't1',
        user_message: 'hello',
        created_at: new Date().toISOString(),
        status: 'done',
        events: [
          { type: 'text', content: 'world', seq: 1 },
          { type: 'done', task_id: 't1', summary: '', seq: 2 },
        ],
        annotations: [],
      },
    ],
    ...overrides,
  });

  it('produces a single state with all events merged', () => {
    const session = makeSession();
    const state = chatReducer(initialChatState, { type: 'BULK_LOAD', session });
    // user_message + text + done = 3 events
    expect(state.events).toHaveLength(3);
    expect(state.events[0].type).toBe('user_message');
    expect(state.events[1].type).toBe('text');
    expect(state.events[2].type).toBe('done');
  });

  it('sets status to last turn status', () => {
    const session = makeSession();
    const state = chatReducer(initialChatState, { type: 'BULK_LOAD', session });
    expect(state.status).toBe('done');
  });

  it('merges text_delta events into text', () => {
    const session = makeSession({
      turns: [
        {
          turn_id: 't1',
          user_message: 'hi',
          created_at: new Date().toISOString(),
          status: 'done',
          annotations: [],
          events: [
            { type: 'text_delta', content: 'A', seq: 1 },
            { type: 'text_delta', content: 'B', seq: 2 },
            { type: 'done', task_id: 't1', summary: '', seq: 3 },
          ],
        },
      ],
    });
    const state = chatReducer(initialChatState, { type: 'BULK_LOAD', session });
    const textEvent = state.events.find((e) => e.type === 'text');
    expect((textEvent as { content: string }).content).toBe('AB');
  });

  it('merges skill_call + skill_result across multiple turns', () => {
    const session = makeSession({
      turns: [
        {
          turn_id: 't1',
          user_message: 'run',
          created_at: new Date().toISOString(),
          status: 'done',
          annotations: [],
          events: [
            {
              type: 'skill_call',
              id: 'sc1',
              skill: 'shell',
              args: { command: 'ls' },
              status: 'running',
              seq: 1,
            },
            {
              type: 'skill_result',
              id: 'sc1',
              skill: 'shell',
              status: 'done',
              result: 'ok',
              seq: 2,
            },
            { type: 'done', task_id: 't1', summary: '', seq: 3 },
          ],
        },
      ],
    });
    const state = chatReducer(initialChatState, { type: 'BULK_LOAD', session });
    const results = state.events.filter((e) => e.type === 'skill_result');
    expect(results).toHaveLength(1);
    // skill_call should be replaced, not duplicated
    const calls = state.events.filter((e) => e.type === 'skill_call');
    expect(calls).toHaveLength(0);
  });
});
