import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-28 text-center">
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-rose-text">Error 404</p>
      <h1 className="mt-3 font-serif text-5xl">No encontramos esa página</h1>
      <Link href="/tienda" className="mt-8 inline-flex min-h-12 items-center justify-center bg-ink px-8 text-xs font-medium uppercase tracking-[0.2em] text-white hover:bg-umber-dark">Ir a la tienda</Link>
    </div>
  );
}
