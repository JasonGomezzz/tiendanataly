import type { Metadata } from "next";

export const metadata: Metadata = { title: "Buscar", robots: { index: false } };

export default function Search() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-20 text-center sm:px-8">
      <h1 className="font-serif text-4xl sm:text-5xl">¿Qué estás buscando?</h1>
      <form action="/tienda" role="search" className="mt-8 flex gap-2">
        <label htmlFor="q" className="sr-only">Buscar productos</label>
        <input id="q" name="q" type="search" autoFocus placeholder="Bolso, mochila, fragancia…" className="w-full border border-stone/70 px-4 py-3.5 text-sm outline-none focus:border-ink" />
        <button className="bg-ink px-8 text-xs font-medium uppercase tracking-[0.2em] text-white hover:bg-umber-dark">Buscar</button>
      </form>
    </div>
  );
}
