import { MockAdapter } from '../../src/adapter/mock';
import type { AgentAdapter, StreamEvent } from '../../src/types';

describe('MockAdapter', () => {
  let adapter: AgentAdapter;

  beforeEach(() => {
    adapter = new MockAdapter();
  });

  it('implements AgentAdapter interface', () => {
    expect(typeof adapter.createSession).toBe('function');
    expect(typeof adapter.addTurn).toBe('function');
    expect(typeof adapter.streamTurn).toBe('function');
    expect(typeof adapter.getSessions).toBe('function');
    expect(typeof adapter.getSession).toBe('function');
    expect(typeof adapter.cancelTurn).toBe('function');
    expect(typeof adapter.submitComponentAction).toBe('function');
    expect(typeof adapter.getSkills).toBe('function');
    expect(typeof adapter.toggleSkill).toBe('function');
    expect(typeof adapter.listFiles).toBe('function');
    expect(typeof adapter.getConfig).toBe('function');
    expect(typeof adapter.updateConfig).toBe('function');
  });

  it('getSkills returns Skill[]', async () => {
    const skills = await adapter.getSkills();
    expect(Array.isArray(skills)).toBe(true);
    expect(skills[0].name).toBeDefined();
    expect(typeof skills[0].enabled).toBe('boolean');
  });

  it('toggleSkill updates enabled state', async () => {
    const skills = await adapter.getSkills();
    const name = skills[0].name;
    const original = skills[0].enabled;
    await adapter.toggleSkill(name, !original);
    const updated = await adapter.getSkills();
    expect(updated.find(s => s.name === name)!.enabled).toBe(!original);
  });

  it('listFiles returns FileNode[]', async () => {
    const files = await adapter.listFiles();
    expect(Array.isArray(files)).toBe(true);
    expect(files[0].name).toBeDefined();
    expect(typeof files[0].is_dir).toBe('boolean');
  });

  it('getConfig returns AgentConfig', async () => {
    const config = await adapter.getConfig();
    expect(config.project.name).toBeDefined();
    expect(config.llm.model).toBeDefined();
  });

  describe('session methods', () => {
    it('createSession returns session_id and turn_id', async () => {
      const result = await adapter.createSession('hello world');
      expect(result.session_id).toBeTruthy();
      expect(result.turn_id).toBeTruthy();
    });

    it('addTurn returns turn_id', async () => {
      const { session_id, turn_id } = await adapter.createSession('first');
      // drain first turn
      for await (const _ of adapter.streamTurn(session_id, turn_id)) { /* drain */ }
      const result = await adapter.addTurn(session_id, 'second');
      expect(result.turn_id).toBeTruthy();
    });

    it('getSessions returns items array', async () => {
      await adapter.createSession('test session');
      const result = await adapter.getSessions();
      expect(Array.isArray(result.items)).toBe(true);
    });

    it('getSession returns session with turns', async () => {
      const { session_id } = await adapter.createSession('my session');
      const session = await adapter.getSession(session_id);
      expect(session.session_id).toBe(session_id);
      expect(Array.isArray(session.turns)).toBe(true);
    });

    it('streamTurn yields events', async () => {
      const { session_id, turn_id } = await adapter.createSession('stream test');
      const events = [];
      for await (const event of adapter.streamTurn(session_id, turn_id)) {
        events.push(event);
      }
      expect(events.length).toBeGreaterThan(0);
    });
  });
});
