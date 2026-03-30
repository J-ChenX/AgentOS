import ReactMarkdown from 'react-markdown';

export default function TextBlock({ content }: { content: string }) {
  return (
    <div
      className="prose max-w-none"
      style={{
        fontFamily: 'var(--font-body)',
        fontSize: 'var(--text-sm)',
        lineHeight: 'var(--leading-loose)',
        color: 'var(--color-ink-primary)',
      }}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
