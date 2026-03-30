import { useState } from 'react';

interface FormField {
  name: string;
  label: string;
  type: string;
  required?: boolean;
}

export default function FormComponent({
  fields,
  submitLabel,
  onAction,
}: {
  fields: FormField[];
  submitLabel?: string;
  onAction?: (payload: unknown) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <div
      className="space-y-3 rounded p-4"
      style={{
        background: 'var(--color-bg-raised)',
        border: '1px solid var(--color-border-default)',
      }}
    >
      {fields.map((field) => (
        <div key={field.name} className="space-y-1">
          <label className="text-xs" style={{ color: 'var(--color-ink-secondary)' }}>
            {field.label}
          </label>
          <input
            type={field.type}
            value={values[field.name] || ''}
            onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
            className="w-full rounded px-2 py-1.5 text-sm outline-none"
            style={{
              background: 'var(--color-bg-surface)',
              color: 'var(--color-ink-primary)',
              border: '1px solid var(--color-border-default)',
            }}
          />
        </div>
      ))}
      <button
        onClick={() => onAction?.(values)}
        className="rounded px-4 py-1.5 text-xs font-medium"
        style={{ background: 'var(--color-accent)', color: '#fff' }}
      >
        {submitLabel || '提交'}
      </button>
    </div>
  );
}
