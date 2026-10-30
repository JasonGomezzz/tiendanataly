"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ESTADO_PEDIDO, dateTime, type AdminOrderRow } from "@/lib/admin";
import { api } from "@/lib/client";
import { inputClass } from "@/components/ui";
import { money } from "@/lib/format";

const COLUMNS = ["PENDIENTE_PAGO", "PAGADO", "COMPRADO", "EN_CAMINO", "EN_LIMA", "ENTREGADO"];

function Board() {
  const params = useSearchParams();
  const [rows, setRows] = useState<AdminOrderRow[] | null>(null);
  const [q, setQ] = useState("");
  const [only, setOnly] = useState(params.get("estado") ?? "");

  useEffect(() => {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    const t = setTimeout(() => api<AdminOrderRow[]>(`/admin/orders/?${qs}`).then(setRows).catch(() => setRows([])), 250);
    return () => clearTimeout(t);
  }, [q]);

  const visible = (estado: string) => (rows ?? []).filter((r) => r.estado === estado);
  const columns = only ? [only] : COLUMNS;
  const closed = (rows ?? []).filter((r) => r.estado === "CANCELADO" || r.estado === "EXPIRADO");

  return (
    <div className="space-y-5">
      <h1 className="font-serif text-3xl sm:text-4xl">Pedidos</h1>
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="q">Buscar pedido</label>
        <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre, teléfono o n.º de pedido" className={inputClass} />
        <select aria-label="Filtrar por estado" value={only} onChange={(e) => setOnly(e.target.value)} className={`${inputClass} sm:w-56`}>
          <option value="">Todos los estados</option>
          {Object.entries(ESTADO_PEDIDO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {rows === null ? (
        <p className="text-umber">Cargando…</p>
      ) : (
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-4 sm:mx-0 sm:px-0">
          {columns.map((estado) => (
            <section key={estado} aria-label={ESTADO_PEDIDO[estado]} className="w-72 shrink-0 snap-start sm:w-64">
              <h2 className="mb-2 flex justify-between text-[11px] font-medium uppercase tracking-[0.16em] text-umber">
                {ESTADO_PEDIDO[estado]} <span>{visible(estado).length}</span>
              </h2>
              <ul className="space-y-2">
                {visible(estado).map((o) => (
                  <li key={o.id}>
                    <Link href={`/admin/pedidos/${o.id}`} className="block border border-stone/40 bg-white p-3 hover:border-ink">
                      <p className="flex justify-between text-sm font-medium"><span>#{o.id} · {o.cliente}</span><span>{money(o.total_pen)}</span></p>
                      <p className="mt-1 text-xs text-umber">{o.items} {o.items === 1 ? "producto" : "productos"} · {dateTime(o.creado_en)}</p>
                      {o.tipo_venta === "por_encargo" && <p className="mt-1 text-[10px] uppercase tracking-widest text-rose-text">Por encargo</p>}
                    </Link>
                  </li>
                ))}
                {visible(estado).length === 0 && <li className="border border-dashed border-stone/50 p-3 text-xs text-umber">Sin pedidos</li>}
              </ul>
            </section>
          ))}
        </div>
      )}

      {!only && closed.length > 0 && (
        <details className="border border-stone/40 bg-white p-4">
          <summary className="cursor-pointer text-xs uppercase tracking-[0.16em] text-umber">Cancelados y expirados ({closed.length})</summary>
          <ul className="mt-3 divide-y divide-stone/30 text-sm">
            {closed.map((o) => (
              <li key={o.id}><Link href={`/admin/pedidos/${o.id}`} className="flex justify-between py-2"><span>#{o.id} · {o.cliente}</span><span className="text-umber">{ESTADO_PEDIDO[o.estado]}</span></Link></li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export default function OrdersPage() {
  return <Suspense fallback={<p className="text-umber">Cargando…</p>}><Board /></Suspense>;
}
