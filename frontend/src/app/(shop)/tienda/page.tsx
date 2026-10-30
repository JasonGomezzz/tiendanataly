import type { Metadata } from "next";
import Link from "next/link";
import { ProductCard } from "@/components/ui";
import { getBrands, getCategories, getProducts } from "@/lib/api";

export const metadata: Metadata = { title: "Tienda", description: "Explora bolsos, mochilas y fragancias importadas." };

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

const PRICE_RANGES: [string, string, string][] = [
  ["Todos los precios", "", ""],
  ["Hasta S/ 100", "", "100"],
  ["S/ 100 – 200", "100", "200"],
  ["Más de S/ 200", "200", ""],
];

export default async function Shop({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const q = one(sp.q);
  const categoria = one(sp.categoria);
  const marca = one(sp.marca);
  const ultimas = one(sp.ultimas);
  const disponible = one(sp.disponible);
  const precio_min = one(sp.precio_min);
  const precio_max = one(sp.precio_max);
  const ordering = one(sp.ordering);

  const [data, categories, brands] = await Promise.all([
    getProducts({ search: q, categoria, marca, ultimas, disponible, precio_min, precio_max, ordering }),
    getCategories(),
    getBrands(),
  ]);
  const products = data?.results ?? [];

  const href = (patch: Record<string, string | undefined>) => {
    const next = { q, categoria, marca, ultimas, disponible, precio_min, precio_max, ordering, ...patch };
    const qs = new URLSearchParams(Object.entries(next).filter(([, v]) => v) as [string, string][]).toString();
    return `/tienda${qs ? `?${qs}` : ""}`;
  };
  const chip = (active: boolean) =>
    `block py-1.5 text-sm ${active ? "font-medium text-ink underline underline-offset-4" : "text-umber hover:text-ink"}`;

  const filters = (
    <div className="space-y-8 text-sm">
      <section aria-labelledby="f-cat">
        <h2 id="f-cat" className="mb-2 text-[11px] font-medium uppercase tracking-[0.18em]">Categoría</h2>
        <Link href={href({ categoria: undefined })} className={chip(!categoria)}>Todas</Link>
        {categories?.map((c) => (
          <Link key={c.slug} href={href({ categoria: c.slug })} className={chip(categoria === c.slug)}>{c.nombre}</Link>
        ))}
      </section>
      <section aria-labelledby="f-marca">
        <h2 id="f-marca" className="mb-2 text-[11px] font-medium uppercase tracking-[0.18em]">Marca</h2>
        <Link href={href({ marca: undefined })} className={chip(!marca)}>Todas</Link>
        {brands?.filter((b) => b.slug !== "por-confirmar").map((b) => (
          <Link key={b.slug} href={href({ marca: b.slug })} className={chip(marca === b.slug)}>{b.nombre}</Link>
        ))}
      </section>
      <section aria-labelledby="f-precio">
        <h2 id="f-precio" className="mb-2 text-[11px] font-medium uppercase tracking-[0.18em]">Precio</h2>
        {PRICE_RANGES.map(([label, min, max]) => (
          <Link key={label} href={href({ precio_min: min || undefined, precio_max: max || undefined })} className={chip((precio_min ?? "") === min && (precio_max ?? "") === max)}>
            {label}
          </Link>
        ))}
      </section>
      <section aria-labelledby="f-disp">
        <h2 id="f-disp" className="mb-2 text-[11px] font-medium uppercase tracking-[0.18em]">Disponibilidad</h2>
        <Link href={href({ disponible: undefined, ultimas: undefined })} className={chip(!disponible && !ultimas)}>Todo</Link>
        <Link href={href({ disponible: "true", ultimas: undefined })} className={chip(disponible === "true")}>Disponible ahora</Link>
        <Link href={href({ ultimas: "true", disponible: undefined })} className={chip(ultimas === "true")}>Últimas unidades</Link>
      </section>
    </div>
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-4xl sm:text-5xl">{q ? `Resultados para “${q}”` : "Tienda"}</h1>
          <p className="mt-1 text-sm text-umber">{products.length} {products.length === 1 ? "producto" : "productos"}</p>
        </div>
        <nav aria-label="Ordenar" className="flex gap-4 text-xs uppercase tracking-widest text-umber">
          <Link href={href({ ordering: undefined })} className={ordering ? "" : "text-ink underline underline-offset-4"}>Destacados</Link>
          <Link href={href({ ordering: "precio_venta_pen" })} className={ordering === "precio_venta_pen" ? "text-ink underline underline-offset-4" : ""}>Menor precio</Link>
          <Link href={href({ ordering: "-precio_venta_pen" })} className={ordering === "-precio_venta_pen" ? "text-ink underline underline-offset-4" : ""}>Mayor precio</Link>
        </nav>
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[220px_1fr]">
        <aside aria-label="Filtros">
          <details className="lg:hidden">
            <summary className="flex min-h-11 cursor-pointer items-center border border-stone/60 px-4 text-xs font-medium uppercase tracking-[0.18em]">Filtrar</summary>
            <div className="border border-t-0 border-stone/60 p-4">{filters}</div>
          </details>
          <div className="hidden lg:block">{filters}</div>
        </aside>

        {products.length === 0 ? (
          <div className="py-16 text-center">
            <p className="font-serif text-2xl">No encontramos productos con esos filtros</p>
            <Link href="/tienda" className="mt-4 inline-block text-sm text-umber underline underline-offset-4">Quitar filtros</Link>
          </div>
        ) : (
          <ul className="grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3">
            {products.map((p, i) => (
              <li key={p.slug}><ProductCard product={p} priority={i < 2} /></li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
