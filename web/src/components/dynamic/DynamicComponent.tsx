import type { ComponentState } from '../../hooks/useEventReducer';
import DataTable from './DataTable';
import ProgressBar from './ProgressBar';
import ImagePreview from './ImagePreview';
import ImageGrid from './ImageGrid';
import ConfirmDialog from './ConfirmDialog';
import FormComponent from './FormComponent';
import FileDownload from './FileDownload';

interface DynamicComponentProps {
  component: ComponentState;
  onAction?: (payload: unknown) => void;
}

export default function DynamicComponent({ component, onAction }: DynamicComponentProps) {
  const { component_type, data } = component;

  switch (component_type) {
    case 'data_table':
      return (
        <DataTable
          columns={(data.columns as string[]) || []}
          rows={(data.rows as Record<string, unknown>[]) || []}
        />
      );
    case 'progress_bar':
      return (
        <ProgressBar
          current={data.current as number}
          total={data.total as number}
          label={data.label as string | undefined}
        />
      );
    case 'image_preview':
      return <ImagePreview src={data.src as string} alt={data.alt as string} />;
    case 'image_grid':
      return <ImageGrid images={(data.images as Array<{ src: string; alt?: string }>) || []} />;
    case 'confirm_dialog':
      return (
        <ConfirmDialog
          message={data.message as string}
          options={(data.options as string[]) || []}
          onAction={onAction}
          timeoutMs={data.timeout_ms as number | undefined}
        />
      );
    case 'form':
      return (
        <FormComponent
          fields={(data.fields as unknown as Parameters<typeof FormComponent>[0]['fields']) || []}
          submitLabel={data.submitLabel as string}
          onAction={onAction}
        />
      );
    case 'file_download':
      return <FileDownload filename={data.filename as string} url={data.url as string} />;
    default:
      return (
        <div
          className="rounded p-3 text-xs"
          style={{ background: 'var(--color-bg-raised)', color: 'var(--color-ink-secondary)' }}
        >
          [{component_type}]
          <pre className="mt-1 overflow-x-auto text-xs">{JSON.stringify(data, null, 2)}</pre>
        </div>
      );
  }
}
