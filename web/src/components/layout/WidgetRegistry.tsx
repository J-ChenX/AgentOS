import type { AgentAdapter } from '../../types';
import type { ViewportType } from '../../types/layout';
import ChatPanel from '../panels/ChatPanel';
import FilesPanel from '../panels/FilesPanel';
import ConfigPanel from '../panels/ConfigPanel';
import SkillsPanel from '../panels/SkillsPanel';
import HistoryPanel from '../panels/HistoryPanel';

const REGISTRY: Record<string, React.FC<{ adapter: AgentAdapter }>> = {
  chat: ChatPanel,
  files: FilesPanel,
  config: ConfigPanel,
  skills: SkillsPanel,
  history: HistoryPanel,
};

export function renderWidget(
  type: ViewportType,
  adapter: AgentAdapter,
): React.ReactNode {
  const Widget = REGISTRY[type];
  if (Widget) return <Widget adapter={adapter} />;

  if (type.startsWith('plugin:')) {
    const pluginId = type.slice(7);
    return (
      <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--color-ink-secondary)' }}>
        Plugin "{pluginId}" not installed
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--color-ink-secondary)' }}>
      Unknown: {type}
    </div>
  );
}
