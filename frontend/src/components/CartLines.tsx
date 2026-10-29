"use client";

import Image from "next/image";
import Link from "next/link";
import { money } from "@/lib/format";
import { useCart } from "./CartProvider";

/** Líneas de la bolsa; se reutilizan en el drawer y en la página /bolsa. */
export function CartLines({ onNavigate }: { onNavigate?: () => void }) {
  const { cart, setQty, remove } = useCart();

  if (cart.items.length === 0) {
    return <p className="py-10 text-center text-sm text-umber">Tu bolsa está vacía.</p>;
  }

  // Cantidad total por producto (las variantes del mismo producto suman para la oferta).
  const qtyByProduct = cart.items.reduce<Record<string, number>>((acc, l) => ({ ...acc, [l.producto_slug]: (acc[l.producto_slug] ?? 0) + l.cantidad }), {});
  const seen = new Set<string>();

  return (
    <ul className="divide-y divide-stone/30">
      {cart.items.map((line) => {
        const total = qtyByProduct[line.producto_slug];
        const first = !seen.has(line.producto_slug);
        seen.add(line.producto_slug);
        const missing = line.oferta ? line.oferta.cantidad - (total % line.oferta.cantidad) : 0;
        const hint = line.oferta && first && line.ok && missing !== line.oferta.cantidad ? `Agrega ${missing} más y llévalas ${line.oferta.cantidad} por ${money(line.oferta.precio)}` : null;
        return (
        <li key={line.id} className="flex gap-4 py-5">
          <Link href={`/producto/${line.producto_slug}`} onClick={onNavigate} className="relative h-28 w-22 shrink-0 bg-paper">
            {line.imagen && <Image src={line.imagen} alt={line.nombre} fill sizes="88px" className="object-cover" />}
          </Link>
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="text-sm font-medium uppercase tracking-wide">{line.nombre}</p>
            {line.variante && <p className="text-xs text-umber">{line.variante}</p>}
            <p className="mt-1 text-sm">{money(line.precio_unitario)}</p>
            {hint && <p className="mt-1 text-xs text-rose-text">{hint}</p>}
            {!line.ok && (
              <p role="alert" className="mt-1 text-xs text-rose">
                {line.disponible > 0 ? `Solo quedan ${line.disponible}.` : "Ya no está disponible."}
              </p>
            )}
            <div className="mt-auto flex items-center justify-between pt-3">
              <div className="flex items-center border border-stone/60">
                <button
                  type="button"
                  aria-label={`Quitar una unidad de ${line.nombre}`}
                  className="h-9 w-9 text-lg leading-none disabled:opacity-30"
                  disabled={line.cantidad <= 1}
                  onClick={() => void setQty(line.id, line.cantidad - 1)}
                >
                  −
                </button>
                <span className="w-8 text-center text-sm" aria-live="polite">
                  {line.cantidad}
                </span>
                <button
                  type="button"
                  aria-label={`Agregar una unidad de ${line.nombre}`}
                  className="h-9 w-9 text-lg leading-none disabled:opacity-30"
                  disabled={line.cantidad >= line.disponible}
                  onClick={() => void setQty(line.id, line.cantidad + 1)}
                >
                  +
                </button>
              </div>
              <button type="button" onClick={() => void remove(line.id)} className="text-xs uppercase tracking-widest text-umber underline underline-offset-4 hover:text-ink">
                Quitar
              </button>
            </div>
          </div>
        </li>
        );
      })}
    </ul>
  );
}
