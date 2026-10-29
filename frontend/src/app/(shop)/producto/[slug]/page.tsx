import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Gallery } from "@/components/Gallery";
import { ProductBuy } from "@/components/ProductBuy";
import { Accordion, PayBadges, ProductCard, StockBadge } from "@/components/ui";
import { getProduct, getProducts, getRelated, getStore } from "@/lib/api";
import { absolute, money } from "@/lib/format";

type Params = { params: Promise<{ slug: string }> };

export const revalidate = 120;

// Los productos existentes se generan al compilar; los nuevos, bajo demanda (ISR) y se regeneran al editar.
export async function generateStaticParams() {
  const data = await getProducts({ page_size: "200" });
  return (data?.results ?? []).map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const p = await getProduct(slug);
  if (!p) return { title: "Producto no encontrado", robots: { index: false } };
  const description = (p.descripcion || `${p.nombre} de ${p.marca.nombre}.`).slice(0, 160);
  const image = p.imagenes[0]?.url;
  const title = `${p.nombre} · ${money(p.precio_venta_pen)}`;
  return {
    title,
    description,
    alternates: { canonical: `/producto/${p.slug}` },
    openGraph: { title, description, type: "website", url: `/producto/${p.slug}`, images: image ? [{ url: absolute(image), width: 900, height: 1125, alt: p.nombre }] : undefined },
    twitter: { card: image ? "summary_large_image" : "summary", title, description, images: image ? [absolute(image)] : undefined },
  };
}

export default async function ProductPage({ params }: Params) {
  const { slug } = await params;
  const [product, related, store] = await Promise.all([getProduct(slug), getRelated(slug), getStore()]);
  if (!product) notFound();

  const preorder = product.tipo_venta === "por_encargo";
  const waNumber = (store?.whatsapp ?? "").replace(/\D/g, "");
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.nombre,
    description: product.descripcion,
    image: product.imagenes.map((i) => absolute(i.url)),
    sku: product.variantes[0]?.sku,
    brand: { "@type": "Brand", name: product.marca.nombre },
    offers: {
      "@type": "Offer",
      url: absolute(`/producto/${product.slug}`),
      priceCurrency: "PEN",
      price: product.precio_venta_pen,
      availability: product.agotado ? "https://schema.org/OutOfStock" : preorder ? "https://schema.org/PreOrder" : "https://schema.org/InStock",
    },
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8 sm:py-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />
      <nav aria-label="Ruta" className="mb-6 text-[11px] uppercase tracking-[0.16em] text-umber">
        <Link href="/tienda" className="hover:text-ink">Tienda</Link> / <Link href={`/tienda?categoria=${product.categoria.slug}`} className="hover:text-ink">{product.categoria.nombre}</Link>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[1.45fr_1fr] lg:gap-12">
        <Gallery images={product.imagenes} name={product.nombre} />

        <div className="lg:sticky lg:top-6 lg:self-start">
          <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-rose-text">
            {product.agotado ? "Agotado" : product.ultimas_unidades ? "Últimas unidades" : preorder ? "Por encargo" : "Nueva llegada"}
          </p>
          <h1 className="mt-2 text-2xl font-semibold uppercase leading-snug tracking-wide">{product.nombre}</h1>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-umber">{product.marca.nombre}{product.linea ? ` · ${product.linea}` : ""}</p>
          <p className="mt-4 text-2xl">{money(product.precio_venta_pen)}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="text-xs text-umber">Paga con</span>
            <PayBadges />
          </div>

          <ProductBuy
            slug={product.slug}
            productName={product.nombre}
            preorder={preorder}
            initial={product.variantes}
            whatsappUrl={waNumber ? `https://wa.me/${waNumber}?text=` : null}
            advancePct={store?.pct_adelanto ?? "50"}
          />

          <ul className="mt-6 space-y-2 border-t border-stone/40 pt-5 text-xs text-umber">
            <li>Entrega en Lima por delivery o recojo. Envíos a provincias con courier.</li>
            <li>Tu pedido se reserva {store?.minutos_reserva ?? 15} minutos mientras pagas.</li>
          </ul>

          <div className="mt-6 border-t border-stone/40">
            <Accordion title="Descripción" open>
              <p>{product.descripcion || "Pronto agregaremos más detalles de este producto."}</p>
            </Accordion>
            {product.detalles && (
              <Accordion title="Detalles del producto">
                <p className="whitespace-pre-line">{product.detalles}</p>
              </Accordion>
            )}
            <Accordion title="Nuestro compromiso">
              <p>Productos importados y seleccionados uno por uno. Revisa nuestra política de <Link href="/cambios-y-devoluciones" className="underline underline-offset-4">cambios y devoluciones</Link>.</p>
              <p className="mt-2">{store?.aviso_legal}</p>
            </Accordion>
          </div>
          <p className="mt-4"><StockBadge agotado={false} ultimas={false} /></p>
        </div>
      </div>

      {related && related.length > 0 && (
        <section className="mt-20" aria-labelledby="look">
          <h2 id="look" className="font-serif text-3xl">Completa tu look</h2>
          <ul className="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-4">
            {related.map((p) => (
              <li key={p.slug}><ProductCard product={p} /></li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
