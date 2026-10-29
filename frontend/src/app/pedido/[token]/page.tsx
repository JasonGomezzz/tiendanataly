import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { OrderLive, ProofUploader } from "@/components/OrderClient";
import { getOrder, getStore } from "@/lib/api";
import { STATE_LABEL, money, whatsappLink } from "@/lib/format";
import type { OrderState } from "@/lib/types";

export const metadata: Metadata = { title: "Tu pedido", robots: { index: false, follow: false } };

const STEPS: OrderState[] = ["PENDIENTE_PAGO", "PAGADO", "COMPRADO", "EN_CAMINO", "EN_LIMA", "ENTREGADO"];

export default async function OrderPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const [order, store] = await Promise.all([getOrder(token), getStore()]);
  if (!order) notFound();

  const preorder = order.tipo_venta === "por_encargo";
  const steps = preorder ? STEPS : STEPS.filter((s) => s !== "COMPRADO" && s !== "EN_CAMINO");
  const currentIndex = steps.indexOf(order.estado);
  const closed = order.estado === "CANCELADO" || order.estado === "EXPIRADO";
  const inReview = order.pagos.some((p) => p.estado === "en_revision");
  const rejected = order.pagos.some((p) => p.estado === "rechazado") && !inReview;
  const waText = `Hola, te escribo por mi pedido #${order.numero}.`;
  const wa = order.whatsapp?.url ?? whatsappLink(store?.whatsapp, waText);
  const canPay = order.estado === "PENDIENTE_PAGO" && !inReview;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-8">
      <OrderLive active={order.estado === "PENDIENTE_PAGO" || order.estado === "PAGADO"} />
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-rose-text">Pedido #{order.numero}</p>
      <h1 className="mt-2 font-serif text-4xl sm:text-5xl">
        {closed ? STATE_LABEL[order.estado] : order.estado === "PENDIENTE_PAGO" ? "Falta tu pago" : "¡Gracias por tu compra!"}
      </h1>

      {!closed && (
        <ol className="mt-8 grid gap-2 text-xs uppercase tracking-wider" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }} aria-label="Estado del pedido">
          {steps.map((s, i) => (
            <li key={s} aria-current={i === currentIndex ? "step" : undefined} className={`border-t-2 pt-2 ${i <= currentIndex ? "border-ink text-ink" : "border-stone/50 text-umber"}`}>
              {STATE_LABEL[s]}
            </li>
          ))}
        </ol>
      )}

      {order.estado === "EXPIRADO" && (
        <p className="mt-6 border border-stone/50 bg-paper p-4 text-sm">La reserva de tus productos venció. Si ya pagaste, escríbenos por WhatsApp con tu captura y lo resolvemos.</p>
      )}

      {canPay && (
        <section className="mt-10 border border-ink p-6" aria-labelledby="pagar">
          <h2 id="pagar" className="font-serif text-2xl">Paga {money(order.monto_a_cobrar)} por Yape o Plin</h2>
          {rejected && <p role="alert" className="mt-3 text-sm text-rose-text">Tu comprobante anterior no pudo verificarse. Sube uno nuevo o escríbenos.</p>}
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            {store?.yape_numero && (
              <div className="bg-paper p-4"><dt className="text-[11px] uppercase tracking-[0.16em] text-umber">Yape</dt><dd className="mt-1 text-lg">{store.yape_numero}</dd><dd className="text-xs text-umber">{store.yape_titular}</dd></div>
            )}
            {store?.plin_numero && (
              <div className="bg-paper p-4"><dt className="text-[11px] uppercase tracking-[0.16em] text-umber">Plin</dt><dd className="mt-1 text-lg">{store.plin_numero}</dd><dd className="text-xs text-umber">{store.plin_titular}</dd></div>
            )}
            {!store?.yape_numero && !store?.plin_numero && <p className="text-umber">Escríbenos por WhatsApp y te enviamos los datos de pago.</p>}
          </dl>
          {preorder && <p className="mt-3 text-sm text-umber">Este pedido es por encargo: hoy pagas el adelanto. El saldo de {money(order.saldo_pen)} se paga cuando llegue a Lima.</p>}
          {order.expira_en && !preorder && <p className="mt-3 text-xs text-umber">Tus productos están reservados hasta las {new Date(order.expira_en).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Lima" })} (hora de Lima). Sube tu captura antes.</p>}
          <ProofUploader token={order.token} />
        </section>
      )}

      {inReview && <p role="status" className="mt-8 border border-stone/50 bg-blush p-4 text-sm">Recibimos tu comprobante. Lo estamos verificando y te avisaremos por WhatsApp.</p>}

      <section className="mt-10" aria-labelledby="detalle">
        <h2 id="detalle" className="font-serif text-2xl">Detalle</h2>
        <ul className="mt-4 divide-y divide-stone/30 text-sm">
          {order.items.map((i) => (
            <li key={i.sku_snapshot} className="flex justify-between py-3"><span>{i.cantidad} × {i.nombre_snapshot}</span><span>{money(Number(i.precio_unitario) * i.cantidad)}</span></li>
          ))}
        </ul>
        <dl className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between"><dt>Envío</dt><dd>{Number(order.envio_pen) === 0 ? "Gratis" : money(order.envio_pen)}</dd></div>
          <div className="flex justify-between text-base font-medium"><dt>Total</dt><dd>{money(order.total_pen)}</dd></div>
        </dl>
      </section>

      <div className="mt-10 flex flex-col gap-3 sm:flex-row">
        {wa && <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-12 items-center justify-center border border-ink px-6 text-xs font-medium uppercase tracking-[0.2em] hover:bg-ink hover:text-white">Escribir por WhatsApp</a>}
        <Link href="/tienda" className="inline-flex min-h-12 items-center justify-center px-6 text-xs uppercase tracking-[0.2em] text-umber underline underline-offset-4">Seguir comprando</Link>
      </div>
      <p className="mt-6 text-xs text-umber">Guarda este enlace: es tu seguimiento del pedido.</p>
    </div>
  );
}
