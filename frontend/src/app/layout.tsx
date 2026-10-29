import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Jost } from "next/font/google";
import "./globals.css";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-PE" className={`${serif.variable} ${sans.variable}`}>
      <body className="min-h-screen bg-white text-ink">{children}</body>
    </html>
  );
}
