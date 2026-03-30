import type {
  AgentAdapter,
  StreamEvent,
  Session,
  Skill,
  FileNode,
  AgentConfig,
  Annotation,
  AnnotationCreate,
} from '../types';

export class WebAdapter implements AgentAdapter {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    return resp.json();
  }

  private async *streamSSE(path: string): AsyncIterable<StreamEvent> {
    const url = `${this.baseUrl}${path}`;
    let lastSeq = 0;
    const maxRetries = 5;
    let retries = 0;

    while (retries < maxRetries) {
      try {
        const headers: Record<string, string> = { Accept: 'text/event-stream' };
        if (lastSeq > 0) headers['Last-Event-ID'] = String(lastSeq);

        const resp = await fetch(url, { headers });
        if (!resp.ok || !resp.body) {
          throw new Error(`SSE connection failed: ${resp.status}`);
        }

        retries = 0;
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: StreamEvent = JSON.parse(line.slice(6));
                if ('seq' in event) lastSeq = (event as { seq: number }).seq;
                yield event;
                if (event.type === 'done' || event.type === 'error' || event.type === 'cancelled') {
                  return;
                }
              } catch {
                /* intentionally empty */
              }
            }
          }
        }
      } catch (err) {
        retries++;
        if (retries >= maxRetries) throw err;
        await new Promise((r) => setTimeout(r, 1000 * retries));
      }
    }
  }

  async createSession(userMessage: string): Promise<{ session_id: string; turn_id: string }> {
    return this.request('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ user_message: userMessage }),
    });
  }

  async addTurn(
    sessionId: string,
    userMessage: string,
    turnId?: string,
  ): Promise<{ turn_id: string }> {
    return this.request(`/api/sessions/${sessionId}/turns`, {
      method: 'POST',
      body: JSON.stringify({ user_message: userMessage, turn_id: turnId }),
    });
  }

  async *streamTurn(sessionId: string, turnId: string): AsyncIterable<StreamEvent> {
    yield* this.streamSSE(`/api/sessions/${sessionId}/turns/${turnId}/stream`);
  }

  async getSessions(limit = 50, offset = 0): Promise<{ items: Session[]; total: number }> {
    return this.request(`/api/sessions?limit=${limit}&offset=${offset}`);
  }

  async getSession(sessionId: string): Promise<Session> {
    return this.request(`/api/sessions/${sessionId}`);
  }

  async cancelTurn(sessionId: string, turnId: string): Promise<void> {
    await this.request(`/api/sessions/${sessionId}/turns/${turnId}/cancel`, {
      method: 'POST',
    });
  }

  async deleteSession(sessionId: string): Promise<void> {
    const resp = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    // 404 is treated as success (idempotent)
    if (!resp.ok && resp.status !== 404) {
      throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
    }
  }

  async deleteTurn(sessionId: string, turnId: string): Promise<void> {
    const resp = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/turns/${turnId}`, {
      method: 'DELETE',
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
  }

  async submitComponentAction(actionId: string, payload: unknown): Promise<void> {
    await this.request(`/api/actions/${actionId}`, {
      method: 'POST',
      body: JSON.stringify({ payload }),
    });
  }

  async getSkills(): Promise<Skill[]> {
    return this.request('/api/skills');
  }

  async toggleSkill(name: string, enabled: boolean): Promise<void> {
    await this.request(`/api/skills/${name}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    });
  }

  async listFiles(path?: string): Promise<FileNode[]> {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    return this.request(`/api/files${query}`);
  }

  async getConfig(): Promise<AgentConfig> {
    return this.request('/api/config');
  }

  async updateConfig(patch: Partial<AgentConfig>): Promise<void> {
    await this.request('/api/config', {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
  }

  async addAnnotation(
    sessionId: string,
    turnId: string,
    payload: AnnotationCreate,
  ): Promise<Annotation> {
    return this.request(`/api/sessions/${sessionId}/turns/${turnId}/annotations`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async removeAnnotation(sessionId: string, turnId: string, annotationId: string): Promise<void> {
    const resp = await fetch(
      `${this.baseUrl}/api/sessions/${sessionId}/turns/${turnId}/annotations/${annotationId}`,
      { method: 'DELETE' },
    );
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
  }
}
