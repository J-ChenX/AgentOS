export default function ImagePreview({ src, alt }: { src: string; alt?: string }) {
  return (
    <div className="rounded overflow-hidden" style={{ border: '1px solid var(--color-border-default)' }}>
      <img src={src} alt={alt || ''} className="max-w-full h-auto" />
    </div>
  );
}
