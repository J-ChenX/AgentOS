import type { StreamEvent, AgentAdapter } from '../../types';
import type { ComponentState } from '../../hooks/useEventReducer';
import ThinkingBubble from './ThinkingBubble';
import TextBlock from './TextBlock';
import SkillCallCard from './SkillCallCard';
import ErrorCard from './ErrorCard';
import DoneCard from './DoneCard';
import CancelledCard from './CancelledCard';
import DynamicComponent from '../dynamic/DynamicComponent';

interface EventRendererProps {
  event: StreamEvent;
  components: Record<string, ComponentState>;
  adapter: AgentAdapter;
}

export default function EventRenderer({ event, components, adapter }: EventRendererProps) {
  switch (event.type) {
    case 'task_started':
      return null;
    case 'thinking':
      return <ThinkingBubble content={event.content} />;
    case 'text':
      return <TextBlock content={event.content} />;
    case 'skill_call':
      return <SkillCallCard event={event} />;
    case 'skill_result':
      return <SkillCallCard event={event} />;
    case 'component': {
      const comp = components[event.id];
      if (!comp) return null;
      return <DynamicComponent component={comp} />;
    }
    case 'component_delta':
      return null;
    case 'action_required':
      return (
        <DynamicComponent
          component={{
            id: event.action_id,
            component_type: event.component_type,
            data: { ...event.data, timeout_ms: event.timeout_ms },
          }}
          onAction={(payload) => adapter.submitComponentAction(event.action_id, payload)}
        />
      );
    case 'error':
      return <ErrorCard message={event.message} recoverable={event.recoverable} />;
    case 'done':
      return <DoneCard summary={event.summary} />;
    case 'cancelled':
      return <CancelledCard />;
    default:
      return null;
  }
}
