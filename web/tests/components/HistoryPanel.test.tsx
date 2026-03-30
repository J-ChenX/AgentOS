import { render, screen, waitFor } from '@testing-library/react';
import { within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HistoryPanel from '../../src/components/panels/HistoryPanel';
import { MockAdapter } from '../../src/adapter/mock';
import { SessionNavContext } from '../../src/contexts/SessionNavContext';
import type { SessionNavContextValue } from '../../src/contexts/SessionNavContext';

async function seedAdapter(adapter: MockAdapter, userMessage: string) {
  const { session_id, turn_id } = await adapter.createSession(userMessage);
  // Drain the stream so events and status are recorded
  for await (const _e of adapter.streamTurn(session_id, turn_id)) {
    // consume
  }
  return { session_id, turn_id };
}

function renderHistory(adapter: MockAdapter, navCtx: Partial<SessionNavContextValue> = {}) {
  const ctx: SessionNavContextValue = {
    activeSessionId: null,
    navigateTo: () => {},
    ...navCtx,
  };
  return render(
    <SessionNavContext.Provider value={ctx}>
      <HistoryPanel adapter={adapter} />
    </SessionNavContext.Provider>,
  );
}

describe('HistoryPanel', () => {
  it('renders history list from adapter', async () => {
    const adapter = new MockAdapter();
    await seedAdapter(adapter, '分析 ABT 数据并匹配模板');
    renderHistory(adapter);
    await waitFor(() => {
      expect(screen.getByText('分析 ABT 数据并匹配模板')).toBeInTheDocument();
    });
  });

  it('shows task status badges', async () => {
    const adapter = new MockAdapter();
    await seedAdapter(adapter, '分析 ABT 数据并匹配模板');
    renderHistory(adapter);
    await waitFor(() => {
      const badges = screen.getAllByText('done');
      expect(badges.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('clicking a session row calls navigateTo with the session id', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '分析数据');
    const navigateTo = vi.fn();
    renderHistory(adapter, { navigateTo });

    await waitFor(() => expect(screen.getByText('分析数据')).toBeInTheDocument());
    await userEvent.click(screen.getByText('分析数据'));

    expect(navigateTo).toHaveBeenCalledWith(session_id);
  });

  it('active session row is highlighted', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '高亮测试');
    renderHistory(adapter, { activeSessionId: session_id });

    await waitFor(() => expect(screen.getByText('高亮测试')).toBeInTheDocument());
    const row = screen.getByText('高亮测试').closest('[data-testid="session-row"]') as HTMLElement;
    expect(row.getAttribute('data-active')).toBe('true');
  });

  it('delete session button shows confirm modal', async () => {
    const adapter = new MockAdapter();
    await seedAdapter(adapter, '会话A');
    renderHistory(adapter);

    await waitFor(() => expect(screen.getByText('会话A')).toBeInTheDocument());

    const row = screen.getByText('会话A').closest('[data-testid="session-row"]') as HTMLElement;
    await userEvent.hover(row);
    const trashBtn = within(row).getByRole('button', { name: '删除会话' });
    await userEvent.click(trashBtn);

    expect(screen.getByText(/确定删除此会话/)).toBeInTheDocument();
  });

  it('confirming delete removes session from list', async () => {
    const adapter = new MockAdapter();
    await seedAdapter(adapter, '会话B');
    renderHistory(adapter);

    await waitFor(() => expect(screen.getByText('会话B')).toBeInTheDocument());

    const row = screen.getByText('会话B').closest('[data-testid="session-row"]') as HTMLElement;
    await userEvent.hover(row);
    await userEvent.click(within(row).getByRole('button', { name: '删除会话' }));
    await userEvent.click(screen.getByRole('button', { name: '删除' }));

    await waitFor(() => expect(screen.queryByText('会话B')).not.toBeInTheDocument());
  });

  it('deleting the active session calls navigateTo(null)', async () => {
    const adapter = new MockAdapter();
    const { session_id } = await seedAdapter(adapter, '活跃会话');
    const navigateTo = vi.fn();
    renderHistory(adapter, { activeSessionId: session_id, navigateTo });

    await waitFor(() => expect(screen.getByText('活跃会话')).toBeInTheDocument());
    const row = screen.getByText('活跃会话').closest('[data-testid="session-row"]') as HTMLElement;
    await userEvent.hover(row);
    await userEvent.click(within(row).getByRole('button', { name: '删除会话' }));
    await userEvent.click(screen.getByRole('button', { name: '删除' }));

    await waitFor(() => expect(navigateTo).toHaveBeenCalledWith(null));
  });

  it('does not show any detail view or turn content when row is clicked', async () => {
    const adapter = new MockAdapter();
    await seedAdapter(adapter, '导航测试');
    renderHistory(adapter);

    await waitFor(() => expect(screen.getByText('导航测试')).toBeInTheDocument());
    await userEvent.click(screen.getByText('导航测试'));

    // No "返回" button, no turn detail view
    expect(screen.queryByRole('button', { name: '返回' })).not.toBeInTheDocument();
    expect(screen.queryByText('任务完成')).not.toBeInTheDocument();
  });
});
