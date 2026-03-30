import { Allotment } from 'allotment';
import 'allotment/dist/style.css';
import type { AgentAdapter } from '../../types';
import type { ViewportNode, ViewportType } from '../../types/layout';
import ViewportContainer from './ViewportContainer';

interface LayoutHandlers {
  onUpdateType: (id: string, type: ViewportType) => void;
  onSplit: (id: string, direction: 'horizontal' | 'vertical') => void;
  onClose: (id: string) => void;
}

interface LayoutRootProps extends LayoutHandlers {
  node: ViewportNode;
  adapter: AgentAdapter;
  isRoot?: boolean;
}

export default function LayoutRoot({ node, adapter, isRoot = true, ...handlers }: LayoutRootProps) {
  // Leaf node -> render viewport
  if (!node.children) {
    return <ViewportContainer node={node} adapter={adapter} canClose={!isRoot} {...handlers} />;
  }

  // Split node -> render Allotment
  // allotment vertical={true} = stack top-to-bottom = "horizontal" split line
  // allotment vertical={false} = stack left-to-right = "vertical" split line
  const allotmentVertical = node.split === 'horizontal';
  return (
    <Allotment vertical={allotmentVertical} defaultSizes={node.sizes}>
      {node.children.map((child) => (
        <Allotment.Pane key={child.id}>
          <LayoutRoot node={child} adapter={adapter} isRoot={false} {...handlers} />
        </Allotment.Pane>
      ))}
    </Allotment>
  );
}
