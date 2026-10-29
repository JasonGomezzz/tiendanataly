export function money(value: string | number): string {
  const n = Number(value);
  return `S/ ${Number.isInteger(n) ? n.toString() : n.toFixed(2)}`;
}

export const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export function absolute(path: string): string {
  return path.startsWith("http") ? path : `${SITE}${path}`;
}

export function whatsappLink(number: string | undefined, text: string): string | null {
  const n = (number ?? "").replace(/\D/g, "");
  return n ? `https://wa.me/${n}?text=${encodeURIComponent(text)}` : null;
}

export const STATE_LABEL: Record<string, string> = {
  PENDIENTE_PAGO: "Pendiente de pago",
  PAGADO: "Pagado",
  COMPRADO: "Comprado en EE. UU.",
  EN_CAMINO: "En camino",
  EN_LIMA: "En Lima",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
  EXPIRADO: "Expirado",
};
