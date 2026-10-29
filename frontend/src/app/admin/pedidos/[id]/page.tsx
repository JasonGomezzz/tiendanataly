"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { ESTADO_PEDIDO, dateTime, type AdminOrder } from "@/lib/admin";
import { api, ApiError, messageFrom } from "@/lib/client";
import { money } from "@/lib/format";

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAdmin();
  const [o, setO] = useState<AdminOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api<AdminOrder>(`/admin/orders/${id}/`).then(setO).catch(() => setError("No pudimos cargar el pedido.")), [id]);
  useEffect(() => {
    void load();
  }, [load]);

  async function act(path: string, json: unknown, confirmText?: string) {
    if (confirmText && !confirm(confirmText)) return;
    setBusy(true);
    setError(null);
    try {
      setO(await api<AdminOrder>(path, { json }));
    } catch (e) {
      setError(e instanceof ApiError ? messageFrom(e.data) : "No pudimos completar la acción.");
    } finally {
      setBusy(false);
    }
  }

  if (!o) return <p className="text-umber">{error ?? "Cargando…"}</p>;

  const dir = o.direccion;
  const wa = `https://wa.me/${o.cliente.telefono.replace(/\D/g, "")}?text=${encodeURIComponent(`Hola ${o.cliente.nombre}, te escribo por tu pedido #${o.id}.`)}`;

  return (
    <div className="space-y-6">
      <Link href="/admin/pedidos" className="text-xs uppercase tracking-widest text-umber underline underline-offset-4">← Pedidos</Link>
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-rose-text">{o.tipo_venta === "por_encargo" ? "Por encargo" : "Stock en Lima"}</p>
        <h1 className="font-serif text-3xl sm:text-4xl">Pedido #{o.id}</h1>
        <p className="mt-1 text-sm"><strong>{ESTADO_PEDIDO[o.estado]}</strong> · {dateTime(o.creado_en)}</p>
      </div>
      {error && <p role="alert" className="border border-rose bg-blush px-4 py-3 text-sm">{error}</p>}

      {can("orders.change_order") && o.siguientes.length > 0 && (
        <section aria-labelledby="mover" className="border border-stone/40 bg-white p-4">
          <h2 id="mover" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Mover pedido a</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {o.siguientes.map((s) => (
              <button key={s} disabled={busy} onClick={() => act(`/admin/orders/${o.id}/transition/`, { estado: s }, s === "CANCELADO" ? "¿Cancelar este pedido? Se liberará o devolverá el stock." : `¿Pasar el pedido a «${ESTADO_PEDIDO[s]}»? La clienta recibirá un aviso.`)}
                className={`min-h-12 px-5 text-xs font-medium uppercase tracking-[0.16em] ${s === "CANCELADO" ? "border border-rose text-rose-text" : "bg-ink text-white"}`}>
                {ESTADO_PEDIDO[s]}
              </button>
            ))}
          </div>
        </section>
      )}

      {o.pagos && (
        <section aria-labelledby="pagos" className="border border-stone/40 bg-white p-4">
          <h2 id="pagos" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Pagos</h2>
          {o.pagos.length === 0 ? <p className="mt-2 text-sm text-umber">Aún no hay pagos.</p> : (
            <ul className="mt-3 space-y-4">
              {o.pagos.map((p) => (
                <li key={p.id} className="border-t border-stone/30 pt-3 first:border-0 first:pt-0">
                  <p className="flex justify-between text-sm"><span>{p.proveedor === "culqi" ? "Culqi" : p.metodo.toUpperCase()} {p.es_adelanto ? "(adelanto)" : ""}</span><strong>{money(p.monto)}</strong></p>
                  <p className="text-xs text-umber">{p.estado.replace("_", " ")} · {dateTime(p.creado_en)} {p.nota && `· ${p.nota}`}</p>
                  {p.comprobante && <a href={p.comprobante} target="_blank" rel="noopener noreferrer"><img src={p.comprobante} alt="Comprobante de pago" className="mt-2 max-h-72 border border-stone/40" /></a>}
                  {can("payments.change_payment") && (p.estado === "en_revision" || p.estado === "pendiente") && (
                    <div className="mt-3 flex gap-2">
                      <button disabled={busy} onClick={() => act(`/admin/payments/${p.id}/approve/`, {}, `¿Confirmas que recibiste ${money(p.monto)}?`)} className="min-h-12 flex-1 bg-ink text-xs font-medium uppercase tracking-[0.16em] text-white">Aprobar pago</button>
                      <button disabled={busy} onClick={() => act(`/admin/payments/${p.id}/reject/`, { nota: prompt("Motivo del rechazo (se muestra internamente):") ?? "" }, undefined)} className="min-h-12 flex-1 border border-rose text-xs font-medium uppercase tracking-[0.16em] text-rose-text">Rechazar</button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section aria-labelledby="cli" className="border border-stone/40 bg-white p-4 text-sm">
        <h2 id="cli" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Clienta y entrega</h2>
        <p className="mt-2 font-medium">{o.cliente.nombre}</p>
        <p><a href={`tel:${o.cliente.telefono}`} className="underline underline-offset-4">{o.cliente.telefono}</a> · <a href={wa} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">WhatsApp</a></p>
        {o.cliente.email && <p className="text-umber">{o.cliente.email}</p>}
        <p className="mt-3 text-umber">{o.metodo_entrega.replace("_", " ")}</p>
        {dir.direccion && <p>{dir.direccion}, {dir.distrito}, {dir.provincia}, {dir.departamento}{dir.referencia ? ` (${dir.referencia})` : ""}</p>}
        {o.notas && <p className="mt-2 italic">“{o.notas}”</p>}
      </section>

      <section aria-labelledby="items" className="border border-stone/40 bg-white p-4 text-sm">
        <h2 id="items" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Productos</h2>
        <ul className="mt-2 divide-y divide-stone/30">
          {o.items.map((i) => <li key={i.sku} className="flex justify-between py-2"><span>{i.cantidad} × {i.nombre}</span><span>{money(Number(i.precio) * i.cantidad)}</span></li>)}
        </ul>
        <dl className="mt-3 space-y-1 border-t border-stone/30 pt-3">
          {Number(o.descuento_pen) > 0 && <div className="flex justify-between text-rose-text"><dt>Oferta aplicada</dt><dd>− {money(o.descuento_pen)}</dd></div>}
          <div className="flex justify-between"><dt>Envío</dt><dd>{money(o.envio_pen)}</dd></div>
          <div className="flex justify-between font-medium"><dt>Total</dt><dd>{money(o.total_pen)}</dd></div>
          {o.tipo_venta === "por_encargo" && <div className="flex justify-between text-umber"><dt>Saldo pendiente</dt><dd>{money(o.saldo_pen)}</dd></div>}
        </dl>
      </section>

      <section aria-labelledby="hist" className="text-sm">
        <h2 id="hist" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Historial</h2>
        <ol className="mt-2 space-y-1 text-xs text-umber">
          {o.historial.map((h, i) => <li key={i}>{dateTime(h.fecha)} · <strong className="text-ink">{ESTADO_PEDIDO[h.estado] ?? h.estado}</strong>{h.usuario ? ` · ${h.usuario}` : ""}{h.nota ? ` · ${h.nota}` : ""}</li>)}
        </ol>
      </section>
    </div>
  );
}
