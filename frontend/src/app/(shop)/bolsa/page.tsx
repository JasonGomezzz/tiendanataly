"use client";

import Link from "next/link";
import { CartLines } from "@/components/CartLines";
import { useCart } from "@/components/CartProvider";
import { btnPrimary } from "@/components/ui";
import { money } from "@/lib/format";

export default function BagPage() {
  const { cart } = useCart();
  const blocked = cart.items.some((i) => !i.ok);

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-8">
      <h1 className="font-serif text-4xl sm:text-5xl">Tu bolsa</h1>
      <CartLines />
      {cart.items.length > 0 ? (
        <div className="mt-6 border-t border-stone/40 pt-6">
          {Number(cart.descuento) > 0 && (
            <p className="flex justify-between text-sm text-rose-text"><span>Oferta aplicada</span><span>− {money(cart.descuento)}</span></p>
          )}
          <p className="flex justify-between text-sm uppercase tracking-widest">
            <span>Subtotal</span>
            <span>{money(cart.total)}</span>
          </p>
          <p className="mt-1 text-xs text-umber">El costo de envío se calcula en el siguiente paso.</p>
          <Link href="/checkout" aria-disabled={blocked} className={`${btnPrimary} mt-6 ${blocked ? "pointer-events-none opacity-40" : ""}`}>
            Finalizar compra
          </Link>
        </div>
      ) : (
        <Link href="/tienda" className={`${btnPrimary} mx-auto mt-4 max-w-xs`}>Ir a la tienda</Link>
      )}
    </div>
  );
}
