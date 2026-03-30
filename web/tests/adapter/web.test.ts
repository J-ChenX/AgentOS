import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WebAdapter } from '../../src/adapter/web';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('WebAdapter', () => {
  let adapter: WebAdapter;

  beforeEach(() => {
    adapter = new WebAdapter('http://localhost:8000');
    mockFetch.mockReset();
  });

  it('createSession posts to /api/sessions', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: 'sess_1', turn_id: 'turn_1' }),
    });
    const result = await adapter.createSession('hello');
    expect(result.session_id).toBe('sess_1');
    expect(result.turn_id).toBe('turn_1');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/sessions',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('streamTurn streams SSE from /api/sessions/{id}/turns/{id}/stream', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"task_started","task_id":"turn_1","seq":1}\n\n'));
        controller.enqueue(encoder.encode('data: {"type":"done","task_id":"turn_1","summary":"ok","seq":2}\n\n'));
        controller.close();
      },
    });
    mockFetch.mockResolvedValueOnce({ ok: true, body: stream });

    const events = [];
    for await (const event of adapter.streamTurn('sess_1', 'turn_1')) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(events[0].type).toBe('task_started');
    expect(events[1].type).toBe('done');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/sessions/sess_1/turns/turn_1/stream',
      expect.any(Object),
    );
  });

  it('cancelTurn calls POST /api/sessions/{id}/turns/{id}/cancel', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
    await adapter.cancelTurn('sess_1', 'turn_1');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/sessions/sess_1/turns/turn_1/cancel',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('submitComponentAction calls POST /api/actions/{id}', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
    await adapter.submitComponentAction('act_1', { choice: 'confirm' });
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/actions/act_1',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ payload: { choice: 'confirm' } }),
      }),
    );
  });
});
