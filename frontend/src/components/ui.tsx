import Image from "next/image";
import Link from "next/link";
import { money } from "@/lib/format";
import type { ProductCard as Card } from "@/lib/types";

export const btnPrimary =
  "inline-flex min-h-12 w-full items-center justify-center bg-ink px-6 text-xs font-medium uppercase tracking-[0.2em] text-white transition-colors hover:bg-umber-dark disabled:cursor-not-allowed disabled:bg-stone";
export const btnOutline =
  "inline-flex min-h-12 w-full items-center justify-center border border-ink px-6 text-xs font-medium uppercase tracking-[0.2em] text-ink transition-colors hover:bg-ink hover:text-white";
export const inputClass =
  "w-full border border-stone/70 bg-white px-3 py-3 text-sm outline-none focus:border-ink focus-visible:outline-2 focus-visible:outline-rose";
export const labelClass = "mb-1 block text-[11px] font-medium uppercase tracking-[0.16em] text-umber";

export const offerText = (p: { oferta_cantidad: number | null; oferta_precio: string | null }) =>
  p.oferta_cantidad && p.oferta_precio ? `${p.oferta_cantidad} por ${money(p.oferta_precio)}` : null;

export function StockBadge({ agotado, ultimas, stock }: { agotado: boolean; ultimas: boolean; stock?: number }) {
  if (agotado) return <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-umber">Agotado</span>;
  if (ultimas)
    return (
      <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-rose-text">
        {stock ? `Últimas unidades (${stock})` : "Últimas unidades"}
      </span>
    );
  return null;
}

export function ImagePlaceholder({ label }: { label?: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center bg-blush p-4 text-center font-serif text-lg text-umber-dark">
      {label ?? "Foto próximamente"}
    </div>
  );
}

export function ProductCard({ product, priority = false }: { product: Card; priority?: boolean }) {
  return (
    <Link href={`/producto/${product.slug}`} className="group block">
      <div className="relative aspect-4/5 overflow-hidden bg-paper">
        {product.imagen_principal ? (
          <Image
            src={product.imagen_principal}
            alt={product.nombre}
            fill
            priority={priority}
            fetchPriority={priority ? "high" : undefined}
            sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
            className={`object-cover transition-transform duration-500 group-hover:scale-[1.03] ${product.agotado ? "opacity-60" : ""}`}
          />
        ) : (
          <ImagePlaceholder label={product.nombre} />
        )}
        {(product.agotado || product.ultimas_unidades) && (
          <span className="absolute left-2 top-2 bg-white/90 px-2 py-1">
            <StockBadge agotado={product.agotado} ultimas={product.ultimas_unidades} />
          </span>
        )}
      </div>
      <div className="pt-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-umber">{product.marca.nombre}</p>
        <p className="mt-0.5 text-sm font-medium uppercase tracking-wide">{product.nombre}</p>
        <p className="mt-1 text-sm">{money(product.precio_venta_pen)}</p>
        {offerText(product) && <p className="mt-1 inline-block bg-blush px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.14em] text-rose-text">Oferta {offerText(product)}</p>}
      </div>
    </Link>
  );
}

export function Accordion({ title, children, open = false }: { title: string; children: React.ReactNode; open?: boolean }) {
  return (
    <details open={open} className="group border-b border-stone/40 py-4">
      <summary className="flex cursor-pointer list-none items-center justify-between text-[11px] font-medium uppercase tracking-[0.18em]">
        {title}
        <span aria-hidden className="text-lg leading-none transition-transform group-open:rotate-45">
          +
        </span>
      </summary>
      <div className="pt-3 text-sm leading-relaxed text-umber">{children}</div>
    </details>
  );
}

export function PayBadges({ card = false }: { card?: boolean }) {
  const methods = ["Yape", "Plin", "Transferencia", ...(card ? ["Tarjeta"] : [])];
  return (
    <ul className="flex flex-wrap items-center gap-2" aria-label="Medios de pago">
      {methods.map((m) => (
        <li key={m} className="border border-stone/60 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-umber">
          {m}
        </li>
      ))}
    </ul>
  );
}
