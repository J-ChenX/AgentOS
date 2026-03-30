import { useState } from 'react';
import { Loader, Check, X, ChevronDown, ChevronUp } from 'lucide-react';
import type { SkillCallEvent, SkillResultEvent } from '../../types';

type SkillCallCardProps = {
  event: SkillCallEvent | SkillResultEvent;
};

/** Maximum characters shown in the inline result preview before "show more". */
const PREVIEW_CHARS = 400;

/** Priority keys to surface as the card subtitle. */
const PRIMARY_KEYS = ['file_path', 'path', 'command', 'query', 'question', 'pattern', 'content'];

function getPrimaryArg(args: Record<string, unknown> | undefined): string | null {
  if (!args) return null;
  for (const key of PRIMARY_KEYS) {
    if (typeof args[key] === 'string') {
      const v = args[key] as string;
      return v.length > 80 ? v.slice(0, 80) + '…' : v;
    }
  }
  // Fallback: first string value
  for (const v of Object.values(args)) {
    if (typeof v === 'string') return v.length > 80 ? v.slice(0, 80) + '…' : v;
  }
  return null;
}

function ResultPreview({ result }: { result: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = result.length > PREVIEW_CHARS;
  const text = expanded || !isLong ? result : result.slice(0, PREVIEW_CHARS);

  return (
    <div
      style={{
        borderTop: '1px solid var(--color-border-subtle)',
        padding: '7px 11px',
        background: 'var(--color-bg-sunken)',
      }}
    >
      <pre
        style={{
          margin: 0,
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          color: 'var(--color-ink-secondary)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          lineHeight: 1.55,
        }}
      >
        {text}
        {isLong && !expanded && '…'}
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded((v) => !v)}
          style={{
            marginTop: '5px',
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            background: 'none',
            border: 'none',
            fontFamily: 'var(--font-body)',
            fontSize: '10.5px',
            color: 'var(--color-ink-tertiary)',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          {expanded ? (
            <>
              <ChevronUp size={11} strokeWidth={2} /> 收起
            </>
          ) : (
            <>
              <ChevronDown size={11} strokeWidth={2} /> 显示全部 ({result.length} 字符)
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default function SkillCallCard({ event }: SkillCallCardProps) {
  const isResult = event.type === 'skill_result';
  const failed = isResult && event.status === 'failed';
  const success = isResult && event.status === 'done';
  const running = !isResult;

  const borderColor = failed
    ? 'var(--color-error)'
    : success
      ? 'var(--color-success)'
      : 'var(--color-border-strong)';

  const badgeColor = failed
    ? 'var(--color-error)'
    : success
      ? 'var(--color-success)'
      : 'var(--color-ink-tertiary)';

  const badgeText = failed ? '失败' : success ? '完成' : '调用中';

  // args is always present on skill_call; on skill_result it's enriched by reducer
  const args = isResult ? (event as SkillResultEvent).args : (event as SkillCallEvent).args;

  const primaryArg = getPrimaryArg(args);
  const result = isResult ? (event as SkillResultEvent).result : undefined;
  const hasResult = typeof result === 'string' && result.length > 0;

  return (
    <div
      style={{
        background: 'var(--color-bg-raised)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        borderLeft: `2.5px solid ${borderColor}`,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '9px',
          padding: '7px 11px',
        }}
      >
        <div style={{ flexShrink: 0, color: badgeColor }}>
          {failed && <X size={14} strokeWidth={2} />}
          {success && <Check size={14} strokeWidth={2} />}
          {running && <Loader size={14} strokeWidth={1.8} />}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Skill name */}
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11.5px',
              fontWeight: 400,
              color: 'var(--color-ink-secondary)',
            }}
          >
            {event.skill}
          </div>
          {/* Primary arg subtitle — always visible */}
          {primaryArg && (
            <div
              style={{
                marginTop: '2px',
                fontFamily: 'var(--font-mono)',
                fontSize: '10.5px',
                fontWeight: 300,
                color: 'var(--color-ink-tertiary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {primaryArg}
            </div>
          )}
          {/* Error detail */}
          {failed && 'error' in event && event.error && (
            <div
              style={{
                marginTop: '2px',
                fontSize: '11px',
                fontWeight: 300,
                color: 'var(--color-error)',
              }}
            >
              {event.error.message}
            </div>
          )}
        </div>

        {success && 'duration_ms' in event && event.duration_ms != null && (
          <span
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: '11px',
              fontWeight: 300,
              color: 'var(--color-ink-tertiary)',
              flexShrink: 0,
            }}
          >
            {event.duration_ms}ms
          </span>
        )}

        <span
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: badgeColor,
            flexShrink: 0,
          }}
        >
          {badgeText}
        </span>
      </div>

      {/* Result preview — always visible when available (Claude Code style) */}
      {hasResult && <ResultPreview result={result!} />}
    </div>
  );
}
