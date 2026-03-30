import { createContext, useContext } from 'react';

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
