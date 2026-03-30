export default function ImageGrid({ images }: { images: Array<{ src: string; alt?: string }> }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {images.map((img, i) => (
        <div
          key={i}
          className="cursor-pointer overflow-hidden rounded hover:opacity-80"
          style={{ border: '1px solid var(--color-border-default)' }}
        >
          <img src={img.src} alt={img.alt || ''} className="h-32 w-full object-cover" />
        </div>
      ))}
    </div>
  );
}
