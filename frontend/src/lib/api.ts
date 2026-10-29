const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export type ProductCard = {
  slug: string;
  nombre: string;
  precio_venta_pen: string;
  imagen_principal: string | null;
  ultimas_unidades: boolean;
  agotado: boolean;
};

export type StoreInfo = { nombre_tienda: string; whatsapp: string; aviso_legal: string };

async function get<T>(path: string, tag: string): Promise<T | null> {
  try {
    const res = await fetch(`${API}/api/v1${path}`, { next: { tags: [tag], revalidate: 300 } });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null; // el backend puede no estar listo; la página se muestra igual
  }
}

export const getStore = () => get<StoreInfo>("/store-settings/public/", "store");
export const getProducts = () => get<{ results: ProductCard[] }>("/products/", "products");
