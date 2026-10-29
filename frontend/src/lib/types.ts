export type Brand = { nombre: string; slug: string };
export type Category = { nombre: string; slug: string };

export type ProductCard = {
  slug: string;
  nombre: string;
  marca: Brand;
  categoria: Category;
  linea: string;
  tipo_venta: "stock_local" | "por_encargo";
  precio_venta_pen: string;
  imagen_principal: string | null;
  stock: number;
  ultimas_unidades: boolean;
  agotado: boolean;
};

export type Variant = {
  id: number;
  sku: string;
  nombre: string;
  atributo: "unico" | "color" | "fragancia" | "talla";
  disponible: number;
  agotado: boolean;
};

export type ProductImage = { url: string; alt: string; orden: number };

export type ProductDetail = ProductCard & {
  descripcion: string;
  detalles: string;
  imagenes: ProductImage[];
  variantes: Variant[];
  puntaje_promedio: number | null;
};

export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type StoreInfo = {
  nombre_tienda: string;
  whatsapp: string;
  aviso_legal: string;
  costo_envio_default: string;
  pct_adelanto: string;
  minutos_reserva: number;
  yape_numero: string;
  yape_titular: string;
  plin_numero: string;
  plin_titular: string;
};

export type Zone = {
  id: number;
  nombre: string;
  metodo: "delivery_lima" | "recojo" | "courier_provincia";
  costo: string;
  courier: string;
  instrucciones: string;
};

export type CartLine = {
  id: number;
  variante_id: number;
  producto_slug: string;
  nombre: string;
  variante: string;
  sku: string;
  imagen: string | null;
  precio_unitario: string;
  cantidad: number;
  subtotal: string;
  disponible: number;
  ok: boolean;
};

export type Cart = { items: CartLine[]; count: number; subtotal: string };

export type OrderState = "PENDIENTE_PAGO" | "PAGADO" | "COMPRADO" | "EN_CAMINO" | "EN_LIMA" | "ENTREGADO" | "CANCELADO" | "EXPIRADO";

export type Order = {
  numero: number;
  token: string;
  estado: OrderState;
  tipo_venta: "stock_local" | "por_encargo";
  subtotal_pen: string;
  envio_pen: string;
  total_pen: string;
  adelanto_pen: string;
  saldo_pen: string;
  monto_a_cobrar: string;
  metodo_entrega: string;
  expira_en: string | null;
  creado_en: string;
  items: { nombre_snapshot: string; sku_snapshot: string; precio_unitario: string; cantidad: number }[];
  historial: { estado_nuevo: OrderState; creado_en: string }[];
  pagos: { metodo: string; monto: string; estado: string; es_adelanto: boolean; creado_en: string }[];
  whatsapp?: { text: string; url: string | null };
};
