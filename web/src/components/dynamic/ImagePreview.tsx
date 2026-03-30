export default function ImagePreview({ src, alt }: { src: string; alt?: string }) {
  return (
    <div
      className="overflow-hidden rounded"
      style={{ border: '1px solid var(--color-border-default)' }}
    >
      <img src={src} alt={alt || ''} className="h-auto max-w-full" />
    </div>
  );
}
