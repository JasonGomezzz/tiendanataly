export function LegalPage({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="mx-auto max-w-2xl px-4 py-12 sm:px-8">
      <h1 className="font-serif text-4xl sm:text-5xl">{title}</h1>
      <p role="note" className="mt-6 border border-stone/50 bg-blush px-4 py-3 text-xs text-umber-dark">
        Texto base. La administradora debe confirmar los datos marcados y se recomienda revisarlo con un asesor legal antes del lanzamiento.
      </p>
      <div className="mt-8 space-y-6 text-sm leading-relaxed text-umber [&_h2]:mb-2 [&_h2]:font-serif [&_h2]:text-2xl [&_h2]:text-ink [&_li]:ml-5 [&_li]:list-disc">
        {children}
      </div>
    </article>
  );
}
