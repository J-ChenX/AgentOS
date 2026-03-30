import { useMemo, useState, useCallback, createContext, useContext } from 'react';
import LayoutRoot from './components/layout/LayoutRoot';
import { MockAdapter } from './adapter/mock';
import { WebAdapter } from './adapter/web';
import type { AgentAdapter } from './types';
import { useLayoutPersistence } from './hooks/useLayoutPersistence';

// ── Session Navigation Context ────────────────────────────────────

export interface SessionNavContextValue {
  activeSessionId: string | null;
  navigateTo: (id: string | null) => void;
}

export const SessionNavContext = createContext<SessionNavContextValue>({
  activeSessionId: null,
  navigateTo: () => {},
});

export function useSessionNav() {
  return useContext(SessionNavContext);
}

// ── Adapter factory ───────────────────────────────────────────────

function createAdapter(): AgentAdapter {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('adapter') || import.meta.env.VITE_ADAPTER || 'mock';

  switch (mode) {
    case 'web':
      return new WebAdapter(import.meta.env.VITE_API_URL || '');
    case 'mock':
    default:
      return new MockAdapter();
  }
}

// ── App ───────────────────────────────────────────────────────────

export default function App() {
  const adapter = useMemo(() => createAdapter(), []);
  const { layout, updateViewportType, splitViewport, closeViewport } =
    useLayoutPersistence();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const navigateTo = useCallback((id: string | null) => {
    setActiveSessionId(id);
  }, []);

  const navContext = useMemo<SessionNavContextValue>(
    () => ({ activeSessionId, navigateTo }),
    [activeSessionId, navigateTo],
  );

  return (
    <SessionNavContext.Provider value={navContext}>
      <div className="h-screen w-screen" style={{ background: 'var(--color-bg-canvas)' }}>
        <LayoutRoot
          node={layout}
          adapter={adapter}
          onUpdateType={updateViewportType}
          onSplit={splitViewport}
          onClose={closeViewport}
        />
      </div>
    </SessionNavContext.Provider>
  );
}
