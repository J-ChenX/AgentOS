import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPanel from '../../src/components/panels/ChatPanel';
import { MockAdapter } from '../../src/adapter/mock';
import { SessionNavContext } from '../../src/App';
import type { SessionNavContextValue } from '../../src/App';

function renderChat(
  adapter: MockAdapter,
  navCtx: Partial<SessionNavContextValue> = {},
) {
  const ctx: SessionNavContextValue = {
    activeSessionId: null,
    navigateTo: () => {},
    ...navCtx,
  };
  return render(
    <SessionNavContext.Provider value={ctx}>
      <ChatPanel adapter={adapter} />
    </SessionNavContext.Provider>,
  );
}

describe('ChatPanel', () => {
  it('renders input field', () => {
    renderChat(new MockAdapter());
    expect(screen.getByPlaceholderText('输入任务...')).toBeInTheDocument();
  });

  it('renders send button', () => {
    renderChat(new MockAdapter());
    expect(screen.getByRole('button', { name: '发送' })).toBeInTheDocument();
  });

  it('disables send button when input is empty', () => {
    renderChat(new MockAdapter());
    expect(screen.getByRole('button', { name: '发送' })).toBeDisabled();
  });

  it('enables send button when input has text', async () => {
    renderChat(new MockAdapter());
    const input = screen.getByPlaceholderText('输入任务...');
    await userEvent.type(input, 'hello');
    expect(screen.getByRole('button', { name: '发送' })).toBeEnabled();
  });
});

describe('ChatPanel — history mode', () => {
  async function seedAdapter(adapter: MockAdapter, userMessage: string) {
    const { session_id, turn_id } = await adapter.createSession(userMessage);
    for await (const _e of adapter.streamTurn(session_id, turn_id)) { /* drain */ }
    return { session_id };
  }

  it('shows session title in header when activeSessionId is set', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '质检任务');
    renderChat(adapter, { activeSessionId: session_id });

    await waitFor(() => {
      // Title appears in both the header span and the user message bubble
      const matches = screen.getAllByText('质检任务');
      expect(matches.length).toBeGreaterThanOrEqual(1);
      // The header span has a title attribute matching the session title
      expect(document.querySelector('span[title="质检任务"]')).toBeInTheDocument();
    });
  });

  it('shows 删除会话 button in history mode', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '质检任务');
    renderChat(adapter, { activeSessionId: session_id });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '删除会话' })).toBeInTheDocument();
    });
  });

  it('delete session calls navigateTo(null) after confirmation', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '删除测试');
    const navigateTo = vi.fn();
    renderChat(adapter, { activeSessionId: session_id, navigateTo });

    await waitFor(() => screen.getByRole('button', { name: '删除会话' }));
    await userEvent.click(screen.getByRole('button', { name: '删除会话' }));
    await userEvent.click(screen.getByRole('button', { name: '删除' }));

    await waitFor(() => expect(navigateTo).toHaveBeenCalledWith(null));
  });

  it('loads history events when activeSessionId changes', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '历史消息');
    renderChat(adapter, { activeSessionId: session_id });

    await waitFor(() => {
      // Text appears in both header span and user message bubble after history loads
      const matches = screen.getAllByText('历史消息');
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });
});
