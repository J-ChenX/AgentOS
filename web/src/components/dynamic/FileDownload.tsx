export default function FileDownload({ filename, url }: { filename: string; url: string }) {
  return (
    <a href={url} download={filename}
      className="inline-flex items-center gap-2 rounded px-3 py-2 text-xs hover:opacity-80"
      style={{ background: 'var(--color-bg-raised)', color: 'var(--color-accent)', border: '1px solid var(--color-border-default)' }}>
      <span>📥</span>
      <span>{filename}</span>
    </a>
  );
}
