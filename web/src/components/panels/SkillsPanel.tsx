import { useState, useEffect, useCallback } from 'react';
import type { AgentAdapter, Skill } from '../../types';

export default function SkillsPanel({ adapter }: { adapter: AgentAdapter }) {
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    adapter.getSkills().then(setSkills);
  }, [adapter]);

  const handleToggle = useCallback(
    async (name: string, enabled: boolean) => {
      await adapter.toggleSkill(name, enabled);
      setSkills((prev) => prev.map((s) => (s.name === name ? { ...s, enabled } : s)));
    },
    [adapter],
  );

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          fontWeight: 400,
          color: 'var(--color-ink-tertiary)',
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}
      >
        Skills ({skills.filter((s) => s.enabled).length}/{skills.length} 已启用)
      </div>
      {skills.map((skill) => (
        <div
          key={skill.name}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderRadius: 'var(--radius-md)',
            padding: '8px 12px',
            background: 'var(--color-bg-raised)',
            border: '1px solid var(--color-border-subtle)',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--color-ink-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {skill.name}
            </div>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 300,
                color: 'var(--color-ink-tertiary)',
                fontFamily: 'var(--font-body)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                marginTop: '1px',
              }}
            >
              {skill.description}
            </div>
          </div>
          <label
            style={{
              position: 'relative',
              display: 'inline-flex',
              alignItems: 'center',
              cursor: 'pointer',
              marginLeft: '12px',
              flexShrink: 0,
            }}
          >
            <input
              type="checkbox"
              checked={skill.enabled}
              onChange={(e) => handleToggle(skill.name, e.target.checked)}
              style={{ position: 'absolute', width: 0, height: 0, opacity: 0 }}
            />
            <div
              style={{
                width: '36px',
                height: '20px',
                borderRadius: '10px',
                background: skill.enabled ? 'var(--color-accent)' : 'var(--color-border-default)',
                transition: 'background 0.2s',
                position: 'relative',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: '2px',
                  left: skill.enabled ? '18px' : '2px',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  background: 'white',
                  transition: 'left 0.2s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                }}
              />
            </div>
          </label>
        </div>
      ))}
    </div>
  );
}
