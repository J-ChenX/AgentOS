import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DynamicComponent from '../../src/components/dynamic/DynamicComponent';
import type { ComponentState } from '../../src/hooks/useEventReducer';

describe('DynamicComponent', () => {
  it('renders data_table with columns and rows', () => {
    const component: ComponentState = {
      id: 'c1', component_type: 'data_table',
      data: { columns: ['Name', 'Score'], rows: [{ Name: 'A', Score: 0.9 }] },
    };
    render(<DynamicComponent component={component} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('0.9')).toBeInTheDocument();
  });

  it('renders progress_bar with current/total', () => {
    const component: ComponentState = {
      id: 'c2', component_type: 'progress_bar',
      data: { current: 3, total: 10, label: '处理中' },
    };
    render(<DynamicComponent component={component} />);
    expect(screen.getByText('处理中')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument();
  });

  it('renders chart component', () => {
    const component: ComponentState = {
      id: 'c3', component_type: 'chart',
      data: { option: { series: [{ data: [1, 2, 3], type: 'bar' }] } },
    };
    const { container } = render(<DynamicComponent component={component} />);
    expect(container.querySelector('.chart-container') || container.firstChild).toBeTruthy();
  });

  it('renders confirm_dialog with options', () => {
    const component: ComponentState = {
      id: 'c4', component_type: 'confirm_dialog',
      data: { message: '确认继续？', options: ['确认', '取消'] },
    };
    const onAction = vi.fn();
    render(<DynamicComponent component={component} onAction={onAction} />);
    expect(screen.getByText('确认继续？')).toBeInTheDocument();
    expect(screen.getByText('确认')).toBeInTheDocument();
    expect(screen.getByText('取消')).toBeInTheDocument();
  });

  it('confirm_dialog triggers onAction when clicked', async () => {
    const component: ComponentState = {
      id: 'c4', component_type: 'confirm_dialog',
      data: { message: '确认？', options: ['Yes', 'No'] },
    };
    const onAction = vi.fn();
    render(<DynamicComponent component={component} onAction={onAction} />);
    await userEvent.click(screen.getByText('Yes'));
    expect(onAction).toHaveBeenCalledWith({ choice: 'Yes' });
  });

  it('renders file_download with link', () => {
    const component: ComponentState = {
      id: 'c5', component_type: 'file_download',
      data: { filename: 'report.xlsx', url: '/files/report.xlsx' },
    };
    render(<DynamicComponent component={component} />);
    expect(screen.getByText('report.xlsx')).toBeInTheDocument();
  });

  it('renders unknown component_type as fallback', () => {
    const component: ComponentState = {
      id: 'c6', component_type: 'custom_widget',
      data: { foo: 'bar' },
    };
    render(<DynamicComponent component={component} />);
    expect(screen.getByText('[custom_widget]')).toBeInTheDocument();
  });
});
