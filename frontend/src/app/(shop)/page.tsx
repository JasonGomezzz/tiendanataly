import Image from "next/image";
import Link from "next/link";
import { ProductCard } from "@/components/ui";
import { getCategories, getProducts, getStore } from "@/lib/api";
import { btnOutline } from "@/components/ui";
import { whatsappLink } from "@/lib/format";

export default async function Home() {
  const [all, last, categories, store] = await Promise.all([
    getProducts({ ordering: "orden" }),
    getProducts({ ultimas: "true" }),
    getCategories(),
    getStore(),
  ]);
  const products = all?.results ?? [];
  const lastUnits = last?.results ?? [];
  const featured = products.find((p) => p.imagen_principal) ?? null;
  const wa = whatsappLink(store?.whatsapp, "Hola, quisiera más información sobre sus productos.");

  return (
    <>
      <section className="bg-blush">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-4 py-10 sm:px-8 lg:grid-cols-2 lg:py-16">
          <div className="order-2 lg:order-1">
            <p className="text-[11px] font-medium uppercase tracking-[0.24em] text-rose-text">Nuevas llegadas</p>
            <h1 className="mt-4 font-serif text-5xl leading-[1.05] text-umber-dark sm:text-6xl">
              Bolsos, mochilas y fragancias que enamoran
            </h1>
            <p className="mt-5 max-w-md text-umber">Importamos piezas seleccionadas y te las entregamos en Lima. Pocas unidades por modelo: cuando se acaban, se acaban.</p>
            <div className="mt-8 flex max-w-sm flex-col gap-3 sm:flex-row">
              <Link href="/tienda" className="inline-flex min-h-12 items-center justify-center bg-ink px-8 text-xs font-medium uppercase tracking-[0.2em] text-white hover:bg-umber-dark">
                Ver la tienda
              </Link>
              {wa && (
                <a href={wa} className={`${btnOutline} sm:w-auto`} target="_blank" rel="noopener noreferrer">
                  WhatsApp
                </a>
              )}
            </div>
          </div>
          <div className="order-1 lg:order-2">
            <div className="relative mx-auto aspect-4/5 max-w-md bg-paper">
              {featured?.imagen_principal && (
                <Image src={featured.imagen_principal} alt={featured.nombre} fill priority fetchPriority="high" quality={60} sizes="(min-width: 640px) 448px, 85vw" className="object-cover" />
              )}
            </div>
          </div>
        </div>
      </section>

      {categories && categories.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pt-16 sm:px-8" aria-labelledby="cats">
          <h2 id="cats" className="sr-only">Categorías</h2>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {categories.map((c) => {
              const sample = products.find((p) => p.categoria.slug === c.slug && p.imagen_principal);
              return (
                <li key={c.slug}>
                  <Link href={`/tienda?categoria=${c.slug}`} className="group relative block aspect-4/5 overflow-hidden bg-paper">
                    {sample?.imagen_principal && (
                      <Image src={sample.imagen_principal} alt="" fill sizes="(min-width: 640px) 25vw, 50vw" className="object-cover transition-transform duration-500 group-hover:scale-[1.04]" />
                    )}
                    <span className="absolute inset-x-0 bottom-0 bg-linear-to-t from-ink/60 to-transparent p-4 font-serif text-2xl text-white">{c.nombre}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {lastUnits.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pt-20 sm:px-8" aria-labelledby="ultimas">
          <div className="flex items-end justify-between">
            <h2 id="ultimas" className="font-serif text-3xl sm:text-4xl">Últimas unidades</h2>
            <Link href="/tienda?ultimas=true" className="text-xs uppercase tracking-widest text-umber underline underline-offset-4">Ver todas</Link>
          </div>
          <ul className="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-4">
            {lastUnits.slice(0, 4).map((p) => (
              <li key={p.slug}><ProductCard product={p} /></li>
            ))}
          </ul>
        </section>
      )}

      <section className="mx-auto max-w-7xl px-4 pt-20 sm:px-8" aria-labelledby="todo">
        <div className="flex items-end justify-between">
          <h2 id="todo" className="font-serif text-3xl sm:text-4xl">Toda la colección</h2>
          <Link href="/tienda" className="text-xs uppercase tracking-widest text-umber underline underline-offset-4">Ver todo</Link>
        </div>
        {products.length === 0 ? (
          <p className="mt-8 text-umber">Pronto publicaremos nuestros productos.</p>
        ) : (
          <ul className="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-4">
            {products.slice(0, 8).map((p, i) => (
              <li key={p.slug}><ProductCard product={p} priority={i < 2} /></li>
            ))}
          </ul>
        )}
      </section>

      <section className="mx-auto mt-24 max-w-7xl px-4 sm:px-8" aria-label="Por qué comprar aquí">
        <ul className="grid gap-px bg-stone/30 text-center sm:grid-cols-3">
          {[
            ["Paga fácil", "Yape, Plin o transferencia. Tu pedido queda reservado mientras pagas."],
            ["Entrega en Lima", "Delivery o recojo. Envíos a provincias con courier."],
            ["Atención personal", "Escríbenos por WhatsApp y te ayudamos a elegir."],
          ].map(([title, text]) => (
            <li key={title} className="bg-white px-6 py-8">
              <p className="font-serif text-2xl">{title}</p>
              <p className="mt-2 text-sm text-umber">{text}</p>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
