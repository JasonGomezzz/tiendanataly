export type Me = { id: number; email: string; nombre: string; rol: "administradora" | "staff" | "superusuario"; permisos: Record<string, boolean> };

export type Option = { id: number; nombre: string };
export type Choice = { value: string; label: string };

export type Meta = {
  marcas: Option[];
  categorias: Option[];
  colecciones: Option[];
  estados_producto: Choice[];
  tipos_venta: Choice[];
  estados_pedido: Choice[];
  tipos_variante: Choice[];
  transiciones: Record<string, string[]>;
};

export type AdminVariant = {
  id: number;
  sku: string;
  nombre: string;
  atributo: string;
  activo: boolean;
  stock_disponible: number;
  stock_reservado: number;
  libre: number;
};

export type AdminImage = { id: number; url: string; alt: string; orden: number };

export type AdminProduct = {
  id: number;
  nombre: string;
  slug: string;
  marca: number;
  marca_nombre: string;
  categoria: number;
  categoria_nombre: string;
  linea: string;
  descripcion: string;
  detalles: string;
  estado: "borrador" | "publicado" | "agotado";
  tipo_venta: "stock_local" | "por_encargo";
  orden: number;
  notas_internas: string;
  precio_compra_usd?: string | null;
  margen?: string | null;
  precio_venta_pen?: string | null;
  stock_total: number;
  variantes: AdminVariant[];
  imagenes: AdminImage[];
};

export type AdminOrderRow = { id: number; estado: string; tipo_venta: string; total_pen: string; cliente: string; telefono: string; creado_en: string; items: number };

export type AdminOrder = {
  id: number;
  token: string;
  estado: string;
  tipo_venta: string;
  creado_en: string;
  total_pen: string;
  envio_pen: string;
  subtotal_pen: string;
  adelanto_pen: string;
  saldo_pen: string;
  metodo_entrega: string;
  cliente: { nombre: string; telefono: string; email: string };
  direccion: Record<string, string>;
  notas: string;
  items: { nombre: string; sku: string; precio: string; cantidad: number }[];
  historial: { estado: string; nota: string; fecha: string; usuario: string | null }[];
  siguientes: string[];
  pagos?: { id: number; proveedor: string; metodo: string; monto: string; estado: string; es_adelanto: boolean; nota: string; comprobante: string | null; creado_en: string }[];
};

export type Dashboard = {
  pedidos_hoy: number;
  por_estado: Record<string, number>;
  por_comprar: number;
  por_entregar: number;
  stock_bajo: { id: number; producto_id: number; producto: string; variante: string; libre: number }[];
  pagos_en_revision?: number;
  ventas_hoy?: string;
  ventas_semana?: { fecha: string; total: string }[];
  ventas_mes?: string;
};

export type PriceResult = {
  tipo_cambio: string;
  costo_usd: string;
  costo_pen: string;
  margen_pen: string;
  comision_pen: string;
  precio_sin_redondeo: string;
  precio_final: string;
  ganancia_neta: string;
};

export const ESTADO_PEDIDO: Record<string, string> = {
  PENDIENTE_PAGO: "Pendiente de pago",
  PAGADO: "Pagado",
  COMPRADO: "Comprado",
  EN_CAMINO: "En camino",
  EN_LIMA: "En Lima",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
  EXPIRADO: "Expirado",
};

export function dateTime(value: string): string {
  return new Date(value).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short", timeZone: "America/Lima" });
}
