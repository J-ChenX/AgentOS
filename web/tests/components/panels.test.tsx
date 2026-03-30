import { render, screen, waitFor } from '@testing-library/react';
import SkillsPanel from '../../src/components/panels/SkillsPanel';
import FilesPanel from '../../src/components/panels/FilesPanel';
import ConfigPanel from '../../src/components/panels/ConfigPanel';
import { MockAdapter } from '../../src/adapter/mock';

describe('SkillsPanel', () => {
  it('renders skill list from adapter', async () => {
    render(<SkillsPanel adapter={new MockAdapter()} />);
    await waitFor(() => {
      expect(screen.getByText('fetch_image')).toBeInTheDocument();
    });
  });

  it('renders toggle switches for each skill', async () => {
    render(<SkillsPanel adapter={new MockAdapter()} />);
    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThanOrEqual(3);
    });
  });
});

describe('FilesPanel', () => {
  it('renders file tree from adapter', async () => {
    render(<FilesPanel adapter={new MockAdapter()} />);
    await waitFor(() => {
      expect(screen.getByText('skills')).toBeInTheDocument();
      expect(screen.getByText('agent.toml')).toBeInTheDocument();
    });
  });
});

describe('ConfigPanel', () => {
  it('renders config sections from adapter', async () => {
    render(<ConfigPanel adapter={new MockAdapter()} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue('my-fashion-agent')).toBeInTheDocument();
      expect(screen.getByDisplayValue('gemini-2.0-flash')).toBeInTheDocument();
    });
  });

  it('renders save button', async () => {
    render(<ConfigPanel adapter={new MockAdapter()} />);
    await waitFor(() => {
      expect(screen.getByText('保存配置')).toBeInTheDocument();
    });
  });
});
