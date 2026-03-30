import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// Mock echarts-for-react to avoid canvas/jsdom incompatibility.
// The real ECharts requires a browser canvas context that jsdom doesn't support.
vi.mock('echarts-for-react', () => ({
  default: ({ style }: { style?: React.CSSProperties }) =>
    React.createElement('div', {
      className: 'chart-container',
      style,
      'data-testid': 'echarts-mock',
    }),
}));
