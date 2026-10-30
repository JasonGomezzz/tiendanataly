import Image from "next/image";
import Link from "next/link";
import { CartDrawer } from "@/components/CartDrawer";
import { CartProvider } from "@/components/CartProvider";
import { Header } from "@/components/Header";
import { getStore } from "@/lib/api";

const NAME = process.env.NEXT_PUBLIC_STORE_NAME ?? "Marle Fashion";

/** Vitrina pública: cabecera, bolsa y pie de página. El panel /admin usa su propio diseño. */
export default async function ShopLayout({ children }: { children: React.ReactNode }) {
  const store = await getStore();
  const name = store?.nombre_tienda ?? NAME;
  const aviso = store?.aviso_legal ?? "Tienda independiente de importación, no afiliada a Victoria's Secret.";

  return (
    <>
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:p-3">
        Saltar al contenido
      </a>
      <CartProvider>
        <p className="bg-paper py-2 text-center text-[11px] uppercase tracking-[0.14em] text-umber">Envíos en Lima · Paga con Yape, Plin o transferencia{store?.payments_provider === "culqi" ? " o tarjeta" : ""}</p>
        <Header name={name} />
        <main id="contenido">{children}</main>
        <CartDrawer />
      </CartProvider>
      <footer className="mt-24 border-t border-stone/30 bg-paper px-4 py-12 text-sm text-umber sm:px-8">
        <div className="mx-auto grid max-w-7xl gap-8 sm:grid-cols-3">
          <div>
            <Image src="/brand/logo-640.png" alt={name} width={96} height={96} className="mb-3 h-24 w-24 rounded-full" />
            <p className="font-serif text-2xl text-ink">{name}</p>
            <p className="mt-1 text-xs italic">Tu estilo, nuestra inspiración ♡</p>
            <p className="mt-3 max-w-xs text-xs leading-relaxed">{aviso}</p>
          </div>
          <nav aria-label="Ayuda" className="flex flex-col gap-2 text-xs uppercase tracking-[0.14em]">
            <Link href="/cambios-y-devoluciones" className="hover:text-ink">Cambios y devoluciones</Link>
            <Link href="/terminos" className="hover:text-ink">Términos y condiciones</Link>
            <Link href="/privacidad" className="hover:text-ink">Política de privacidad</Link>
            <Link href="/libro-de-reclamaciones" className="hover:text-ink">Libro de reclamaciones</Link>
          </nav>
          <div className="text-xs leading-relaxed">
            <p className="uppercase tracking-[0.14em]">Pagos</p>
            <p className="mt-2">Yape, Plin y transferencia bancaria{store?.payments_provider === "culqi" ? ", y tarjeta" : ""}.</p>
            {store?.whatsapp && (
              <a href={`https://wa.me/${store.whatsapp}`} className="mt-3 inline-block underline underline-offset-4 hover:text-ink">
                Escríbenos por WhatsApp
              </a>
            )}
          </div>
        </div>
      </footer>
    </>
  );
}
