import type {
  AgentAdapter, StreamEvent, Session, Turn, TaskStatus,
  Skill, FileNode, AgentConfig, Annotation, AnnotationCreate,
} from '../types';

function delay(ms: number): Promise<void> {
  const isTest = import.meta.env['MODE'] === 'test';
  return new Promise((resolve) => setTimeout(resolve, isTest ? 0 : ms));
}

function createTurnEvents(turnId: string, userMessage: string): StreamEvent[] {
  let seq = 1;
  return [
    { type: 'task_started', task_id: turnId, seq: seq++ },
    { type: 'thinking', content: `正在分析: ${userMessage}`, seq: seq++ },
    { type: 'text', content: `处理: ${userMessage}`, seq: seq++ },
    { type: 'done', task_id: turnId, summary: '完成', seq: seq++ },
  ];
}

const mockSkills: Skill[] = [
  { name: 'fetch_image', description: '抓取图片', enabled: true, file: 'builtin' },
  { name: 'match_template', description: '匹配模板', enabled: true, file: 'builtin' },
  { name: 'generate_chart', description: '生成图表', enabled: false, file: 'builtin' },
];

const mockFiles: FileNode[] = [
  { name: 'agent.toml', path: './agent.toml', is_dir: false },
  { name: 'skills', path: './skills', is_dir: true, children: [] },
];

const mockConfig: AgentConfig = {
  project: { name: 'my-fashion-agent', version: '0.1.0' },
  llm: { model: 'gemini-2.0-flash', base_url: '' },
  agent: { type: 'react', max_iterations: 20 },
  scope: { allow: ['./'], deny: ['.env'] },
};

export class MockAdapter implements AgentAdapter {
  private sessions: Map<string, Session> = new Map();
  private actionResolvers = new Map<string, (payload: unknown) => void>();
  private _turnCounter = 0;

  private _makeId(prefix: string): string {
    return `${prefix}_${(++this._turnCounter).toString().padStart(4, '0')}`;
  }

  async createSession(userMessage: string): Promise<{ session_id: string; turn_id: string }> {
    const session_id = this._makeId('sess');
    const turn_id = this._makeId('turn');
    const now = new Date().toISOString();
    const turn: Turn = {
      turn_id,
      user_message: userMessage,
      created_at: now,
      status: 'running',
      events: [],
      annotations: [],
    };
    const session: Session = {
      session_id,
      title: userMessage.slice(0, 60),
      created_at: now,
      updated_at: now,
      turns: [turn],
    };
    this.sessions.set(session_id, session);
    return { session_id, turn_id };
  }

  async addTurn(
    sessionId: string,
    userMessage: string,
    turnId?: string,
  ): Promise<{ turn_id: string }> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    const turn_id = turnId ?? this._makeId('turn');
    const turn: Turn = {
      turn_id,
      user_message: userMessage,
      created_at: new Date().toISOString(),
      status: 'running',
      events: [],
      annotations: [],
    };
    session.turns.push(turn);
    session.updated_at = new Date().toISOString();
    return { turn_id };
  }

  async *streamTurn(sessionId: string, turnId: string): AsyncIterable<StreamEvent> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    const turn = session.turns.find((t) => t.turn_id === turnId);
    if (!turn) throw new Error(`Turn ${turnId} not found`);

    const events = createTurnEvents(turnId, turn.user_message);
    for (const event of events) {
      await delay(100);
      turn.events.push(event);
      if (event.type === 'text') turn.status = 'done' as TaskStatus;
      yield event;
    }
    turn.status = 'done';
    session.updated_at = new Date().toISOString();
  }

  async getSessions(
    limit = 50,
    offset = 0,
  ): Promise<{ items: Session[]; total: number }> {
    const all = [...this.sessions.values()].sort(
      (a, b) => b.updated_at.localeCompare(a.updated_at),
    );
    return { items: all.slice(offset, offset + limit), total: all.length };
  }

  async getSession(sessionId: string): Promise<Session> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    return session;
  }

  async cancelTurn(_sessionId: string, _turnId: string): Promise<void> {}

  async deleteSession(sessionId: string): Promise<void> {
    this.sessions.delete(sessionId);
  }

  async deleteTurn(sessionId: string, turnId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    session.turns = session.turns.filter((t) => t.turn_id !== turnId);
    if (session.turns.length === 0) this.sessions.delete(sessionId);
  }

  async addAnnotation(
    sessionId: string,
    turnId: string,
    payload: AnnotationCreate,
  ): Promise<Annotation> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    const turn = session.turns.find((t) => t.turn_id === turnId);
    if (!turn) throw new Error(`Turn ${turnId} not found`);
    const ann: Annotation = {
      annotation_id: `ann_${Math.random().toString(36).slice(2, 10)}`,
      ...payload,
    };
    turn.annotations.push(ann);
    return ann;
  }

  async removeAnnotation(
    sessionId: string,
    turnId: string,
    annotationId: string,
  ): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    const turn = session.turns.find((t) => t.turn_id === turnId);
    if (!turn) throw new Error(`Turn ${turnId} not found`);
    turn.annotations = turn.annotations.filter(
      (a) => a.annotation_id !== annotationId,
    );
  }

  async submitComponentAction(actionId: string, _payload: unknown): Promise<void> {
    const resolver = this.actionResolvers.get(actionId);
    if (resolver) {
      resolver(undefined);
      this.actionResolvers.delete(actionId);
    }
  }

  async getSkills(): Promise<Skill[]> { return mockSkills; }

  async toggleSkill(name: string, enabled: boolean): Promise<void> {
    const skill = mockSkills.find((s) => s.name === name);
    if (skill) skill.enabled = enabled;
  }

  async listFiles(_path?: string): Promise<FileNode[]> { return mockFiles; }
  async getConfig(): Promise<AgentConfig> { return mockConfig; }
  async updateConfig(patch: Partial<AgentConfig>): Promise<void> { Object.assign(mockConfig, patch); }
}
