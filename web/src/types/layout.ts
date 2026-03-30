export type ViewportType =
  | 'chat'
  | 'files'
  | 'config'
  | 'skills'
  | 'history'
  | `plugin:${string}`;

export interface ViewportNode {
  id: string;
  type?: ViewportType;
  split?: 'horizontal' | 'vertical';
  sizes?: number[];
  children?: ViewportNode[];
}

export const DEFAULT_LAYOUT: ViewportNode = {
  id: 'root',
  split: 'vertical',
  sizes: [25, 75],
  children: [
    { id: 'v1', type: 'files' },
    { id: 'v2', type: 'chat' },
  ],
};
