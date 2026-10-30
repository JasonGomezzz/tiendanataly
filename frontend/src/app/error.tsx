"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-28 text-center">
      <h1 className="font-serif text-4xl">Algo salió mal</h1>
      <p className="mt-3 text-umber">Inténtalo de nuevo en unos segundos.</p>
      <button onClick={reset} className="mt-8 inline-flex min-h-12 items-center justify-center bg-ink px-8 text-xs font-medium uppercase tracking-[0.2em] text-white">Reintentar</button>
    </div>
  );
}
