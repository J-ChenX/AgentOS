import { useState, useEffect, useCallback } from 'react';
import type { AgentAdapter, AgentConfig } from '../../types';

export default function ConfigPanel({ adapter }: { adapter: AgentAdapter }) {
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adapter.getConfig().then(setConfig);
  }, [adapter]);

  const handleChange = useCallback((section: string, key: string, value: string) => {
    setConfig((prev) => {
      if (!prev) return prev;
      return { ...prev, [section]: { ...(prev as unknown as Record<string, Record<string, string>>)[section], [key]: value } };
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (!config) return;
    setSaving(true);
    try { await adapter.updateConfig(config); } finally { setSaving(false); }
  }, [adapter, config]);

  if (!config) {
    return (
      <div style={{ padding: '16px', fontSize: 'var(--text-xs)', color: 'var(--color-ink-tertiary)', fontWeight: 300 }}>
        加载中...
      </div>
    );
  }

  const sections = [
    { key: 'project', label: '项目', fields: [{ key: 'name', value: config.project.name }, { key: 'version', value: config.project.version }] },
    { key: 'llm', label: 'LLM', fields: [{ key: 'model', value: config.llm.model }, { key: 'base_url', value: config.llm.base_url }] },
    { key: 'agent', label: 'Agent', fields: [{ key: 'type', value: config.agent.type }, { key: 'max_iterations', value: String(config.agent.max_iterations) }] },
  ];

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {sections.map((section) => (
        <div key={section.key}>
          <div
            style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 400,
              color: 'var(--color-ink-tertiary)', letterSpacing: '0.07em',
              textTransform: 'uppercase', marginBottom: '8px',
            }}
          >
            [{section.label}]
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {section.fields.map((field) => (
              <div key={field.key} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <label
                  style={{
                    fontSize: 'var(--text-xs)', width: '112px', flexShrink: 0,
                    color: 'var(--color-ink-secondary)', fontFamily: 'var(--font-body)', fontWeight: 400,
                  }}
                >
                  {field.key}
                </label>
                <input
                  type="text"
                  value={field.value}
                  onChange={(e) => handleChange(section.key, field.key, e.target.value)}
                  style={{
                    flex: 1, padding: '5px 8px', borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)',
                    color: 'var(--color-ink-primary)',
                    background: 'var(--color-bg-sunken)',
                    border: '1px solid var(--color-border-default)',
                    outline: 'none',
                  }}
                  onFocus={(e) => { e.target.style.borderColor = 'var(--color-border-strong)'; }}
                  onBlur={(e) => { e.target.style.borderColor = 'var(--color-border-default)'; }}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
      <button
        onClick={handleSave}
        disabled={saving}
        style={{
          padding: '6px 16px', borderRadius: 'var(--radius-sm)',
          fontFamily: 'var(--font-body)', fontSize: 'var(--text-xs)', fontWeight: 500,
          background: 'var(--color-accent)', color: 'var(--color-ink-inverse)',
          border: 'none', cursor: 'pointer', opacity: saving ? 0.4 : 1,
          alignSelf: 'flex-start',
        }}
      >
        {saving ? '保存中...' : '保存配置'}
      </button>
    </div>
  );
}
