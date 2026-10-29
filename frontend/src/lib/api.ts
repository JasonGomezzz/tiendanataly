import type { Brand, Category, Order, Paginated, ProductCard, ProductDetail, StoreInfo, Zone } from "./types";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

type Opts = { tags?: string[]; revalidate?: number | false; noStore?: boolean };

/** Lectura desde el servidor de Next. Si el backend no responde, devuelve null y la página se muestra igual. */
async function get<T>(path: string, { tags = [], revalidate = 300, noStore = false }: Opts = {}): Promise<T | null> {
  try {
    // Llamada interna a Django: el header evita su redirección a HTTPS (el TLS lo termina Caddy).
    const headers = { "X-Forwarded-Proto": "https" };
    const res = await fetch(`${API}/api/v1${path}`, noStore ? { cache: "no-store", headers } : { headers, next: { tags, revalidate } });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export const getStore = () => get<StoreInfo>("/store-settings/public/", { tags: ["store"] });
export const getZones = () => get<Zone[]>("/shipping/zones/", { tags: ["store"] });
export const getCategories = () => get<Category[]>("/categories/", { tags: ["catalog"] });
export const getBrands = () => get<Brand[]>("/brands/", { tags: ["catalog"] });

export function getProducts(params: Record<string, string | undefined> = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]).toString();
  return get<Paginated<ProductCard>>(`/products/${qs ? `?${qs}` : ""}`, { tags: ["catalog"], revalidate: 120 });
}

export const getProduct = (slug: string) => get<ProductDetail>(`/products/${encodeURIComponent(slug)}/`, { tags: ["catalog"], revalidate: 120 });
export const getRelated = (slug: string) => get<ProductCard[]>(`/products/${encodeURIComponent(slug)}/related/`, { tags: ["catalog"], revalidate: 120 });
export const getOrder = (token: string) => get<Order>(`/orders/track/${encodeURIComponent(token)}/`, { noStore: true });
