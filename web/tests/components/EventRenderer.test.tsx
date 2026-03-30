import { render, screen } from '@testing-library/react';
import EventRenderer from '../../src/components/events/EventRenderer';
import type { StreamEvent } from '../../src/types';

const mockAdapter = {
  submitComponentAction: vi.fn(),
} as any;

describe('EventRenderer', () => {
  it('renders thinking event as animated bubble', () => {
    const event: StreamEvent = { type: 'thinking', content: '正在分析...', seq: 1 };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('正在分析...')).toBeInTheDocument();
  });

  it('renders text event as markdown', () => {
    const event: StreamEvent = { type: 'text', content: '**bold text**', seq: 1 };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('bold text')).toBeInTheDocument();
  });

  it('renders error event with error styling', () => {
    const event: StreamEvent = {
      type: 'error', level: 'fatal', message: 'LLM 崩溃',
      task_id: 't1', recoverable: false, seq: 1,
    };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('LLM 崩溃')).toBeInTheDocument();
  });

  it('renders done event with summary', () => {
    const event: StreamEvent = { type: 'done', task_id: 't1', summary: '分析完毕', seq: 1 };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('分析完毕')).toBeInTheDocument();
    expect(screen.getByText('任务完成')).toBeInTheDocument();
  });

  it('renders cancelled event', () => {
    const event: StreamEvent = { type: 'cancelled', task_id: 't1', seq: 1 };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('任务已取消')).toBeInTheDocument();
  });

  it('skips task_started event (no visible UI)', () => {
    const event: StreamEvent = { type: 'task_started', task_id: 't1', seq: 1 };
    const { container } = render(
      <EventRenderer event={event} components={{}} adapter={mockAdapter} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders skill_call as running', () => {
    const event: StreamEvent = {
      type: 'skill_call', id: 'call_1', skill: 'fetch_image',
      args: { url: 'http://...' }, status: 'running', seq: 1,
    };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('fetch_image')).toBeInTheDocument();
    expect(screen.getByText('调用中')).toBeInTheDocument();
  });

  it('renders skill_result done with duration', () => {
    const event: StreamEvent = {
      type: 'skill_result', id: 'call_1', skill: 'fetch_image',
      status: 'done', result: {}, duration_ms: 1240, seq: 2,
    };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('完成')).toBeInTheDocument();
    expect(screen.getByText('1240ms')).toBeInTheDocument();
  });

  it('renders skill_result failed with error message', () => {
    const event: StreamEvent = {
      type: 'skill_result', id: 'call_2', skill: 'match_template',
      status: 'failed',
      error: { message: '文件未找到', code: 'FILE_NOT_FOUND', retryable: true },
      seq: 3,
    };
    render(<EventRenderer event={event} components={{}} adapter={mockAdapter} />);
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.getByText('文件未找到')).toBeInTheDocument();
  });
});
