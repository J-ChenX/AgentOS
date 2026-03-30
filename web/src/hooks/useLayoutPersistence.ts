import { useState, useCallback } from 'react';
import { produce } from 'immer';
import type { ViewportNode, ViewportType } from '../types/layout';
import { DEFAULT_LAYOUT } from '../types/layout';

const STORAGE_KEY = 'agentos-layout-v2';
let nextId = 100;

function loadLayout(): ViewportNode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* intentionally empty */
  }
  return DEFAULT_LAYOUT;
}

function saveLayout(layout: ViewportNode) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch {
    /* intentionally empty */
  }
}

function findNode(draft: ViewportNode, id: string): ViewportNode | null {
  if (draft.id === id) return draft;
  if (draft.children) {
    for (const child of draft.children) {
      const found = findNode(child, id);
      if (found) return found;
    }
  }
  return null;
}

function findParent(
  draft: ViewportNode,
  id: string,
): { parent: ViewportNode; index: number } | null {
  if (draft.children) {
    for (let i = 0; i < draft.children.length; i++) {
      if (draft.children[i].id === id) return { parent: draft, index: i };
      const found = findParent(draft.children[i], id);
      if (found) return found;
    }
  }
  return null;
}

function usePersistentLayout() {
  const [layout, setLayoutState] = useState<ViewportNode>(loadLayout);

  const update = useCallback((recipe: (draft: ViewportNode) => void) => {
    setLayoutState((prev) => {
      const next = produce(prev, recipe);
      saveLayout(next);
      return next;
    });
  }, []);

  return { layout, update };
}

export function useLayoutPersistence() {
  const { layout, update } = usePersistentLayout();

  const updateViewportType = useCallback(
    (id: string, type: ViewportType) => {
      update((draft) => {
        const node = findNode(draft, id);
        if (node) node.type = type;
      });
    },
    [update],
  );

  const splitViewport = useCallback(
    (id: string, direction: 'horizontal' | 'vertical') => {
      update((draft) => {
        const node = findNode(draft, id);
        if (!node) return;
        const originalType = node.type;
        node.split = direction;
        node.sizes = [50, 50];
        node.children = [
          { id: `v${nextId++}`, type: originalType },
          { id: `v${nextId++}`, type: originalType },
        ];
        delete node.type;
      });
    },
    [update],
  );

  const closeViewport = useCallback(
    (id: string) => {
      update((draft) => {
        const result = findParent(draft, id);
        if (!result) return;
        const { parent, index } = result;
        const siblingIndex = index === 0 ? 1 : 0;
        const sibling = parent.children![siblingIndex];
        parent.id = sibling.id;
        parent.type = sibling.type;
        parent.split = sibling.split;
        parent.sizes = sibling.sizes;
        parent.children = sibling.children;
      });
    },
    [update],
  );

  return { layout, updateViewportType, splitViewport, closeViewport };
}
