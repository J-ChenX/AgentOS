import { render, screen } from '@testing-library/react';
import App from '../../src/App';

describe('MosaicLayout', () => {
  it('renders default two-panel layout', () => {
    render(<App />);
    // Default layout has 'files' and 'chat' panels — labels come from PanelTypeSelect
    expect(screen.getAllByText('项目文件').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('对话').length).toBeGreaterThanOrEqual(1);
  });

  it('renders panel type selectors', () => {
    render(<App />);
    // PanelTypeSelect renders a button with aria-haspopup="menu" as the trigger
    const selectors = screen.getAllByRole('button', { expanded: false });
    // Filter to the panel type trigger buttons (aria-haspopup="menu")
    const typeButtons = selectors.filter((btn) => btn.getAttribute('aria-haspopup') === 'menu');
    expect(typeButtons.length).toBeGreaterThanOrEqual(2);
  });
});
