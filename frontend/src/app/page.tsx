import { getProducts } from "@/lib/api";

export default async function Home() {
  const data = await getProducts();
  const products = data?.results ?? [];

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-8">
      <h1 className="font-serif text-4xl sm:text-5xl">Nuevas llegadas</h1>
      {products.length === 0 ? (
        <p className="mt-6 text-umber">Pronto publicaremos nuestros productos.</p>
      ) : (
        <ul className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {products.map((p) => (
            <li key={p.slug} className="bg-paper p-4">
              <p className="text-sm font-medium uppercase tracking-wide">{p.nombre}</p>
              <p className="mt-1 text-sm text-umber">S/ {p.precio_venta_pen}</p>
              {p.ultimas_unidades && <p className="mt-2 text-[11px] uppercase tracking-widest text-rose">Últimas unidades</p>}
              {p.agotado && <p className="mt-2 text-[11px] uppercase tracking-widest text-umber">Agotado</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
