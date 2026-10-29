"use client";

import Link from "next/link";
import { Logo } from "./Logo";
import { useCart } from "./CartProvider";

const NAV = [
  { label: "Bolsos", href: "/tienda?categoria=bolsos" },
  { label: "Mochilas", href: "/tienda?categoria=mochilas" },
  { label: "Fragancias", href: "/tienda?categoria=fragancias" },
  { label: "Últimas unidades", href: "/tienda?ultimas=true" },
];

const linkClass = "text-[11px] font-medium uppercase tracking-[0.18em] text-umber hover:text-ink";

export function Header({ name }: { name: string }) {
  const { cart, setOpen } = useCart();

  return (
    <header className="border-b border-stone/30 bg-white">
      <div className="mx-auto grid max-w-7xl grid-cols-[1fr_auto_1fr] items-center px-4 py-3 sm:px-8 sm:py-4">
        <nav aria-label="Categorías" className="hidden gap-6 xl:flex">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={linkClass}>
              {item.label}
            </Link>
          ))}
        </nav>
        <details className="relative xl:hidden">
          <summary className="flex h-11 w-11 cursor-pointer list-none items-center justify-center text-xl" aria-label="Menú">
            ☰
          </summary>
          <nav aria-label="Categorías" className="absolute left-0 top-11 z-40 flex w-56 flex-col gap-1 border border-stone/30 bg-white p-3 shadow-lg">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className="py-3 text-xs font-medium uppercase tracking-[0.18em]">
                {item.label}
              </Link>
            ))}
          </nav>
        </details>
        <Link href="/" className="col-start-2 px-2 text-center" aria-label={`${name}, ir al inicio`}>
          <Logo name={name} />
        </Link>
        <div className="col-start-3 flex items-center justify-end gap-1 sm:gap-5">
          <Link href="/buscar" className={`${linkClass} flex h-11 items-center px-2`}>
            Buscar
          </Link>
          <Link href="/cuenta" className={`${linkClass} hidden h-11 items-center px-2 sm:flex`}>
            Cuenta
          </Link>
          <button type="button" onClick={() => setOpen(true)} className={`${linkClass} flex h-11 items-center px-2`} aria-label={`Abrir bolsa, ${cart.count} productos`}>
            Bolsa{cart.count > 0 && <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-ink px-1 text-[10px] text-white">{cart.count}</span>}
          </button>
        </div>
      </div>
    </header>
  );
}
