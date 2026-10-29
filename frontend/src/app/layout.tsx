import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Cormorant_Garamond, Jost } from "next/font/google";
import "./globals.css";
import { CartDrawer } from "@/components/CartDrawer";
import { CartProvider } from "@/components/CartProvider";
import { Header } from "@/components/Header";
import { getStore } from "@/lib/api";
import { SITE } from "@/lib/format";

const serif = Cormorant_Garamond({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-cormorant", display: "swap" });
const sans = Jost({ subsets: ["latin"], variable: "--font-jost", display: "swap" });

const NAME = process.env.NEXT_PUBLIC_STORE_NAME ?? "Marle Fashion";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: `${NAME} · Bolsos, mochilas y fragancias`, template: `%s · ${NAME}` },
  description: "Bolsos, mochilas y fragancias importadas, con entrega en Lima. Paga con Yape, Plin o tarjeta.",
  openGraph: { type: "website", locale: "es_PE", siteName: NAME },
};

export const viewport: Viewport = { themeColor: "#ffffff" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await getStore();
  const name = store?.nombre_tienda ?? NAME;
  const aviso = store?.aviso_legal ?? "Tienda independiente de importación, no afiliada a Victoria's Secret.";

  return (
    <html lang="es-PE" className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-screen bg-white text-ink">
        <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:p-3">
          Saltar al contenido
        </a>
        <CartProvider>
          <p className="bg-paper py-2 text-center text-[11px] uppercase tracking-[0.14em] text-umber">
            Envíos en Lima · Paga con Yape, Plin o tarjeta
          </p>
          <Header name={name} />
          <main id="contenido">{children}</main>
          <CartDrawer />
        </CartProvider>
        <footer className="mt-24 border-t border-stone/30 bg-paper px-4 py-12 text-sm text-umber sm:px-8">
          <div className="mx-auto grid max-w-7xl gap-8 sm:grid-cols-3">
            <div>
              <p className="font-serif text-2xl text-ink">{name}</p>
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
              <p className="mt-2">Yape, Plin y tarjeta.</p>
              {store?.whatsapp && (
                <a href={`https://wa.me/${store.whatsapp}`} className="mt-3 inline-block underline underline-offset-4 hover:text-ink">
                  Escríbenos por WhatsApp
                </a>
              )}
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
