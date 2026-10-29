import type { Metadata } from "next";
import { Cormorant_Garamond, Jost } from "next/font/google";
import "./globals.css";
import { getStore } from "@/lib/api";

const serif = Cormorant_Garamond({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-cormorant", display: "swap" });
const sans = Jost({ subsets: ["latin"], variable: "--font-jost", display: "swap" });

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const NAME = process.env.NEXT_PUBLIC_STORE_NAME ?? "Tienda Nataly";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: NAME, template: `%s · ${NAME}` },
  description: "Bolsos, mochilas y fragancias importadas, con entrega en Lima.",
};

const NAV = ["Bolsos", "Mochilas", "Fragancias", "Regalos"];

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await getStore();
  const aviso = store?.aviso_legal ?? "Tienda independiente de importación, no afiliada a Victoria's Secret.";

  return (
    <html lang="es-PE" className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-screen bg-white text-ink">
        <header className="border-b border-stone/30">
          <div className="mx-auto grid max-w-7xl grid-cols-[1fr_auto_1fr] items-center px-4 py-4 sm:px-8">
            <nav aria-label="Categorías" className="hidden gap-6 text-[11px] font-medium uppercase tracking-[0.18em] text-umber sm:flex">
              {NAV.map((item) => (
                <a key={item} href={`/${item.toLowerCase()}`} className="hover:text-ink">
                  {item}
                </a>
              ))}
            </nav>
            <a href="/" className="col-start-2 font-serif text-3xl tracking-wide sm:text-4xl">
              {store?.nombre_tienda ?? NAME}
            </a>
            <div className="col-start-3 flex justify-end gap-5 text-[11px] font-medium uppercase tracking-[0.18em] text-umber">
              <a href="/buscar">Buscar</a>
              <a href="/bolsa">Bolsa</a>
            </div>
          </div>
          <p className="bg-paper py-2 text-center text-[11px] uppercase tracking-[0.14em] text-umber">
            Envíos en Lima · Paga con Yape, Plin o tarjeta
          </p>
        </header>
        <main>{children}</main>
        <footer className="mt-24 border-t border-stone/30 bg-paper px-4 py-10 text-center text-xs text-umber">
          <p>{aviso}</p>
        </footer>
      </body>
    </html>
  );
}
