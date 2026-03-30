import { useState, useEffect, useRef, useCallback } from 'react';
import type { Annotation, AnnotationType } from '../../types';

// ── Utilities ────────────────────────────────────────────────────────────────

/** Convert a UTF-16 offset in `text` to a Unicode code-point offset. */
function utf16ToCodePointOffset(text: string, utf16Offset: number): number {
  return [...text.slice(0, Math.min(utf16Offset, text.length))].length;
}

interface Span {
  text: string;
  annotation: Annotation | null;
  cpOffset: number;
}

function buildSpans(text: string, annotations: Annotation[], target: 'user' | 'assistant'): Span[] {
  const relevant = [...annotations]
    .filter((a) => a.target === target)
    .sort((a, b) => a.start - b.start);

  if (relevant.length === 0) return [{ text, annotation: null, cpOffset: 0 }];

  const codePoints = [...text];
  const spans: Span[] = [];
  let pos = 0;

  for (const ann of relevant) {
    if (ann.start < pos) continue; // skip overlapping
    if (pos < ann.start) {
      spans.push({
        text: codePoints.slice(pos, ann.start).join(''),
        annotation: null,
        cpOffset: pos,
      });
    }
    spans.push({
      text: codePoints.slice(ann.start, ann.end).join(''),
      annotation: ann,
      cpOffset: ann.start,
    });
    pos = ann.end;
  }
  if (pos < codePoints.length) {
    spans.push({
      text: codePoints.slice(pos).join(''),
      annotation: null,
      cpOffset: pos,
    });
  }
  return spans;
}

// ── Selection info ────────────────────────────────────────────────────────────

export interface SelectionInfo {
  start: number;
  end: number;
  original: string;
  rect: DOMRect;
}

function getSelectionInfo(container: HTMLElement): SelectionInfo | null {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;

  const range = sel.getRangeAt(0);
  if (!container.contains(range.commonAncestorContainer)) return null;

  const findSpan = (node: Node): Element | null => {
    let el: Node | null = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    while (
      el &&
      el !== container &&
      !(el instanceof Element && el.hasAttribute('data-cp-offset'))
    ) {
      el = (el as Element).parentElement;
    }
    if (!el || el === container) return null;
    return el as Element;
  };

  const startSpan = findSpan(range.startContainer);
  const endSpan = findSpan(range.endContainer);
  if (!startSpan || !endSpan) return null;

  // Don't allow annotations on replaced spans — offsets are relative to replacement text,
  // not the stored original, which would produce wrong code-point coordinates.
  if (
    startSpan.hasAttribute('data-annotation-id') &&
    startSpan.getAttribute('data-annotation-type') === 'replaced'
  )
    return null;
  if (
    endSpan.hasAttribute('data-annotation-id') &&
    endSpan.getAttribute('data-annotation-type') === 'replaced'
  )
    return null;

  const cpBase = (span: Element) => parseInt(span.getAttribute('data-cp-offset') ?? '0', 10);
  const spanText = (span: Element) => span.textContent ?? '';

  const start = cpBase(startSpan) + utf16ToCodePointOffset(spanText(startSpan), range.startOffset);
  const end = cpBase(endSpan) + utf16ToCodePointOffset(spanText(endSpan), range.endOffset);

  if (start >= end) return null;

  return { start, end, original: sel.toString(), rect: range.getBoundingClientRect() };
}

// ── Main component ────────────────────────────────────────────────────────────

const BTN: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize: '11px',
  padding: '2px 8px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--color-border-default)',
  background: 'var(--color-bg-raised)',
  color: 'var(--color-ink-primary)',
  cursor: 'pointer',
};

export interface AnnotatedTextProps {
  text: string;
  annotations: Annotation[];
  target: 'user' | 'assistant';
  onAddAnnotation?: (payload: {
    target: 'user' | 'assistant';
    start: number;
    end: number;
    original: string;
    type: AnnotationType;
    replacement?: string;
  }) => Promise<void>;
  onRemoveAnnotation?: (annotationId: string) => Promise<void>;
}

export default function AnnotatedText({
  text,
  annotations,
  target,
  onAddAnnotation,
  onRemoveAnnotation,
}: AnnotatedTextProps) {
  const containerRef = useRef<HTMLSpanElement>(null);
  const [selInfo, setSelInfo] = useState<SelectionInfo | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [replacement, setReplacement] = useState('');
  const [busy, setBusy] = useState(false);

  const spans = buildSpans(text, annotations, target);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onMouseUp = () => {
      setTimeout(() => {
        const info = getSelectionInfo(container);
        setSelInfo(info);
        setEditMode(false);
        setReplacement('');
      }, 10);
    };
    const onDocMouseDown = (e: MouseEvent) => {
      if (!container.contains(e.target as Node)) {
        setSelInfo(null);
        setEditMode(false);
      }
    };
    container.addEventListener('mouseup', onMouseUp);
    document.addEventListener('mousedown', onDocMouseDown);
    return () => {
      container.removeEventListener('mouseup', onMouseUp);
      document.removeEventListener('mousedown', onDocMouseDown);
    };
  }, []);

  const act = useCallback(
    async (type: AnnotationType, rep?: string) => {
      if (!selInfo || !onAddAnnotation) return;
      setBusy(true);
      try {
        await onAddAnnotation({
          target,
          start: selInfo.start,
          end: selInfo.end,
          original: selInfo.original,
          type,
          replacement: rep,
        });
        setSelInfo(null);
      } finally {
        setBusy(false);
      }
    },
    [selInfo, onAddAnnotation, target],
  );

  let toolbarTop = 0;
  let toolbarLeft = 0;
  if (selInfo && containerRef.current) {
    const cRect = containerRef.current.getBoundingClientRect();
    toolbarTop = selInfo.rect.top - cRect.top - 38;
    toolbarLeft = selInfo.rect.left - cRect.left;
  }

  return (
    <span ref={containerRef} style={{ position: 'relative' }}>
      {spans.map((span, i) => {
        const ann = span.annotation;

        if (ann?.type === 'deleted') {
          return (
            <span
              key={i}
              data-cp-offset={span.cpOffset}
              data-annotation-id={ann.annotation_id}
              className="cursor-pointer line-through opacity-40"
              title={`原文: ${span.text} — 点击移除标注`}
              onClick={() => onRemoveAnnotation?.(ann.annotation_id)}
            >
              {span.text}
            </span>
          );
        }

        if (ann?.type === 'emphasized') {
          return (
            <span
              key={i}
              data-cp-offset={span.cpOffset}
              data-annotation-id={ann.annotation_id}
              className="cursor-pointer font-bold"
              style={{ background: 'rgba(253,224,71,0.35)' }}
              title="加重标注 — 点击移除"
              onClick={() => onRemoveAnnotation?.(ann.annotation_id)}
            >
              {span.text}
            </span>
          );
        }

        if (ann?.type === 'replaced') {
          return (
            <span
              key={i}
              data-cp-offset={span.cpOffset}
              data-annotation-id={ann.annotation_id}
              data-annotation-type="replaced"
              className="cursor-pointer"
              style={{ color: '#8a6a1c', borderBottom: '1.5px dotted #8a6a1c' }}
              title={`原文: ${span.text} — 点击移除标注`}
              onClick={() => onRemoveAnnotation?.(ann.annotation_id)}
            >
              {ann.replacement}
            </span>
          );
        }

        return (
          <span key={i} data-cp-offset={span.cpOffset}>
            {span.text}
          </span>
        );
      })}

      {selInfo && onAddAnnotation && (
        <span
          style={{
            position: 'absolute',
            top: Math.max(0, toolbarTop),
            left: Math.max(0, toolbarLeft),
            zIndex: 100,
            display: 'inline-flex',
            flexDirection: 'column',
            gap: '4px',
            background: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border-default)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
          }}
          onMouseDown={(e) => e.preventDefault()}
        >
          {!editMode ? (
            <span style={{ display: 'inline-flex', gap: '4px' }}>
              <button style={BTN} disabled={busy} onClick={() => act('deleted')}>
                删除
              </button>
              <button style={BTN} disabled={busy} onClick={() => act('emphasized')}>
                加重
              </button>
              <button style={BTN} disabled={busy} onClick={() => setEditMode(true)}>
                编辑
              </button>
              <button
                style={BTN}
                onClick={() => navigator.clipboard?.writeText(selInfo.original).catch(() => {})}
              >
                复制
              </button>
            </span>
          ) : (
            <span style={{ display: 'inline-flex', gap: '4px', alignItems: 'center' }}>
              <input
                autoFocus
                value={replacement}
                onChange={(e) => setReplacement(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') act('replaced', replacement);
                  if (e.key === 'Escape') setEditMode(false);
                }}
                placeholder="替换文本…"
                style={{
                  fontSize: '11px',
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-default)',
                  minWidth: '120px',
                }}
              />
              <button
                style={BTN}
                disabled={busy || !replacement.trim()}
                onClick={() => act('replaced', replacement)}
              >
                确认
              </button>
            </span>
          )}
        </span>
      )}
    </span>
  );
}
