"use client";

import Link from "next/link";
import { useEffect } from "react";
import { money } from "@/lib/format";
import { CartLines } from "./CartLines";
import { useCart } from "./CartProvider";

export function CartDrawer() {
  const { cart, open, setOpen } = useCart();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, setOpen]);

  if (!open) return null;
  const blocked = cart.items.some((i) => !i.ok);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Tu bolsa">
      <button type="button" aria-label="Cerrar bolsa" className="absolute inset-0 bg-ink/40" onClick={() => setOpen(false)} />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-stone/30 px-6 py-5">
          <h2 className="font-serif text-2xl">Tu bolsa ({cart.count})</h2>
          <button type="button" onClick={() => setOpen(false)} aria-label="Cerrar" className="h-10 w-10 text-2xl leading-none">
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6">
          <CartLines onNavigate={() => setOpen(false)} />
        </div>
        {cart.items.length > 0 && (
          <div className="border-t border-stone/30 px-6 py-5">
            {Number(cart.descuento) > 0 && (
              <p className="flex justify-between text-xs text-rose-text"><span>Oferta aplicada</span><span>− {money(cart.descuento)}</span></p>
            )}
            <p className="flex justify-between text-sm uppercase tracking-widest">
              <span>Subtotal</span>
              <span>{money(cart.total)}</span>
            </p>
            <p className="mt-1 text-xs text-umber">El envío se calcula en el siguiente paso.</p>
            <Link
              href="/checkout"
              onClick={() => setOpen(false)}
              aria-disabled={blocked}
              className={`mt-4 block bg-ink py-4 text-center text-xs font-medium uppercase tracking-[0.2em] text-white ${blocked ? "pointer-events-none opacity-40" : "hover:bg-umber-dark"}`}
            >
              Finalizar compra
            </Link>
            <Link href="/bolsa" onClick={() => setOpen(false)} className="mt-3 block text-center text-xs uppercase tracking-widest text-umber underline underline-offset-4">
              Ver bolsa completa
            </Link>
          </div>
        )}
      </aside>
    </div>
  );
}
