import type {
  StreamEvent,
  TaskStartedEvent,
  ThinkingEvent,
  SkillCallEvent,
  SkillResultEvent,
  TextEvent,
  ComponentEvent,
  ComponentDeltaEvent,
  ActionRequiredEvent,
  ErrorEvent,
  DoneEvent,
  CancelledEvent,
  TaskRecord,
  Skill,
  FileNode,
  AgentConfig,
  AgentAdapter,
  PanelType,
  ComponentType,
  DeltaOp,
} from '../src/types';

describe('StreamEvent types', () => {
  it('task_started event is type-safe', () => {
    const event: TaskStartedEvent = {
      type: 'task_started',
      task_id: 'task_001',
      seq: 1,
    };
    expect(event.type).toBe('task_started');
    expect(event.task_id).toBe('task_001');
  });

  it('StreamEvent union accepts all event types', () => {
    const events: StreamEvent[] = [
      { type: 'task_started', task_id: 't1', seq: 1 },
      { type: 'thinking', content: '...', seq: 2 },
      { type: 'text', content: 'hello', seq: 3 },
      { type: 'done', task_id: 't1', summary: 'ok', seq: 4 },
    ];
    expect(events).toHaveLength(4);
  });

  it('DeltaOp covers all operations', () => {
    const ops: DeltaOp[] = ['append', 'set', 'merge', 'replace'];
    expect(ops).toHaveLength(4);
  });

  it('PanelType covers all panel kinds', () => {
    const panels: PanelType[] = ['chat', 'skills', 'files', 'history', 'results', 'config'];
    expect(panels).toHaveLength(6);
  });

  it('TaskRecord has required fields', () => {
    const record: TaskRecord = {
      task_id: 'task_001',
      created_at: '2026-03-23T10:00:00Z',
      task: 'test task',
      status: 'done',
      events: [],
      summary: 'done',
    };
    expect(record.status).toBe('done');
  });
});
