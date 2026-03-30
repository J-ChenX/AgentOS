// ── Stream Events ────────────────────────────────────────────────

export interface TaskStartedEvent {
  type: 'task_started';
  task_id: string;
  seq: number;
}

export interface ThinkingEvent {
  type: 'thinking';
  content: string;
  seq: number;
}

export interface SkillCallEvent {
  type: 'skill_call';
  id: string;
  skill: string;
  args: Record<string, unknown>;
  status: 'running';
  seq: number;
}

export interface SkillResultEvent {
  type: 'skill_result';
  id: string;
  skill: string;
  status: 'done' | 'failed';
  result?: string;
  /** Populated by the reducer when merging with the matching skill_call event */
  args?: Record<string, unknown>;
  error?: { message: string; code: string; retryable: boolean };
  duration_ms?: number;
  seq: number;
}

export interface TextEvent {
  type: 'text';
  content: string;
  seq: number;
}

export interface TextDeltaEvent {
  type: 'text_delta';
  content: string; // single token or chunk fragment
  seq: number;
}

export type DeltaOp = 'append' | 'set' | 'merge' | 'replace';

export type ComponentType =
  | 'image_preview'
  | 'image_grid'
  | 'match_result'
  | 'inspection_report'
  | 'chart'
  | 'data_table'
  | 'file_download'
  | 'progress_bar'
  | 'confirm_dialog'
  | 'form'
  | (string & {}); // extensible via custom_*

export interface ComponentEvent {
  type: 'component';
  id: string;
  component_type: ComponentType;
  data: Record<string, unknown>;
  seq: number;
}

export interface ComponentDeltaEvent {
  type: 'component_delta';
  id: string;
  op: DeltaOp;
  path: string;
  value: unknown;
  seq: number;
}

export interface ActionRequiredEvent {
  type: 'action_required';
  action_id: string;
  component_type: string;
  data: Record<string, unknown>;
  blocking: boolean;
  timeout_ms: number;
  seq: number;
}

export interface ErrorEvent {
  type: 'error';
  level: 'fatal' | 'warning';
  message: string;
  task_id: string;
  recoverable: boolean;
  seq: number;
}

export interface DoneEvent {
  type: 'done';
  task_id: string;
  summary: string;
  seq: number;
}

export interface CancelledEvent {
  type: 'cancelled';
  task_id: string;
  seq: number;
}

export interface UserMessageEvent {
  type: 'user_message';
  content: string;
  turn_id: string;
  seq: number;
}

export interface ContextTruncatedEvent {
  type: 'context_truncated';
  turns_dropped: number;
  remaining_turns: number;
  seq: number;
}

export type StreamEvent =
  | TaskStartedEvent
  | ThinkingEvent
  | SkillCallEvent
  | SkillResultEvent
  | TextEvent
  | TextDeltaEvent
  | ComponentEvent
  | ComponentDeltaEvent
  | ActionRequiredEvent
  | ErrorEvent
  | DoneEvent
  | CancelledEvent
  | UserMessageEvent
  | ContextTruncatedEvent;

// ── Data Models ──────────────────────────────────────────────────

export type TaskStatus = 'running' | 'done' | 'error' | 'cancelled';

export interface TaskRecord {
  task_id: string;
  created_at: string;
  task: string;
  status: TaskStatus;
  events: StreamEvent[];
  summary?: string;
}

export interface Turn {
  turn_id: string;
  user_message: string;
  created_at: string;
  status: TaskStatus;
  events: StreamEvent[];
  assistant_message?: string;
  annotations: Annotation[];
}

export type AnnotationType = 'deleted' | 'emphasized' | 'replaced';

export interface Annotation {
  annotation_id: string;
  target: 'user' | 'assistant';
  start: number;
  end: number;
  original: string;
  type: AnnotationType;
  replacement?: string;
}

export interface AnnotationCreate {
  target: 'user' | 'assistant';
  start: number;
  end: number;
  original: string;
  type: AnnotationType;
  replacement?: string;
}

export interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turns: Turn[];
}

export interface Skill {
  name: string;
  description: string;
  enabled: boolean;
  file: string;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  children?: FileNode[];
}

export interface AgentConfig {
  project: { name: string; version: string };
  llm: { model: string; base_url: string };
  agent: { type: string; max_iterations: number };
  scope: { allow: string[]; deny: string[] };
}

// ── Panel Types ──────────────────────────────────────────────────

export type PanelType = 'chat' | 'skills' | 'files' | 'history' | 'results' | 'config';

// ── Adapter Interface ────────────────────────────────────────────

export interface AgentAdapter {
  // Session/Turn API (new)
  createSession(userMessage: string): Promise<{ session_id: string; turn_id: string }>;
  addTurn(sessionId: string, userMessage: string, turnId?: string): Promise<{ turn_id: string }>;
  streamTurn(sessionId: string, turnId: string): AsyncIterable<StreamEvent>;
  getSessions(limit?: number, offset?: number): Promise<{ items: Session[]; total: number }>;
  getSession(sessionId: string): Promise<Session>;
  cancelTurn(sessionId: string, turnId: string): Promise<void>;
  deleteSession(sessionId: string): Promise<void>;
  deleteTurn(sessionId: string, turnId: string): Promise<void>;
  addAnnotation(sessionId: string, turnId: string, payload: AnnotationCreate): Promise<Annotation>;
  removeAnnotation(sessionId: string, turnId: string, annotationId: string): Promise<void>;

  // Shared utility methods (retained)
  submitComponentAction(actionId: string, payload: unknown): Promise<void>;
  getSkills(): Promise<Skill[]>;
  toggleSkill(name: string, enabled: boolean): Promise<void>;
  listFiles(path?: string): Promise<FileNode[]>;
  getConfig(): Promise<AgentConfig>;
  updateConfig(patch: Partial<AgentConfig>): Promise<void>;
}
