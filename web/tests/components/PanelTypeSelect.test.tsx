import { render, screen, fireEvent } from '@testing-library/react';
import PanelTypeSelect from '../../src/components/layout/PanelTypeSelect';

describe('PanelTypeSelect', () => {
  it('displays current type label', () => {
    render(<PanelTypeSelect value="chat" onChange={() => {}} />);
    expect(screen.getByText('对话')).toBeInTheDocument();
  });

  it('opens menu on trigger click', () => {
    render(<PanelTypeSelect value="chat" onChange={() => {}} />);
    fireEvent.click(screen.getByText('对话'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  it('calls onChange with new type when item clicked', () => {
    const onChange = vi.fn();
    render(<PanelTypeSelect value="chat" onChange={onChange} />);
    fireEvent.click(screen.getByText('对话'));
    fireEvent.click(screen.getByRole('menuitem', { name: /历史记录/ }));
    expect(onChange).toHaveBeenCalledWith('history');
  });

  it('marks current type as active in menu', () => {
    render(<PanelTypeSelect value="files" onChange={() => {}} />);
    fireEvent.click(screen.getByText('项目文件'));
    const activeItem = screen.getByRole('menuitem', { name: /项目文件/ });
    expect(activeItem).toHaveAttribute('aria-checked', 'true');
  });

  it('closes menu when clicking outside', () => {
    render(
      <div>
        <PanelTypeSelect value="chat" onChange={() => {}} />
        <div data-testid="outside">outside</div>
      </div>,
    );
    fireEvent.click(screen.getByText('对话'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByTestId('outside'));
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
