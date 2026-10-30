"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { ESTADO_PEDIDO, type Dashboard } from "@/lib/admin";
import { api } from "@/lib/client";
import { money } from "@/lib/format";

function Card({ title, value, href, tone }: { title: string; value: React.ReactNode; href?: string; tone?: "alert" }) {
  const body = (
    <div className={`h-full border bg-white p-4 ${tone === "alert" ? "border-rose" : "border-stone/40"}`}>
      <p className="text-[11px] uppercase tracking-[0.16em] text-umber">{title}</p>
      <p className="mt-2 font-serif text-3xl">{value}</p>
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function AdminHome() {
  const { me, can } = useAdmin();
  const [d, setD] = useState<Dashboard | null>(null);

  useEffect(() => {
    api<Dashboard>("/admin/dashboard/").then(setD).catch(() => undefined);
  }, []);

  if (!d) return <p className="text-umber">Cargando…</p>;
  const max = Math.max(1, ...(d.ventas_semana ?? []).map((v) => Number(v.total)));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-3xl sm:text-4xl">Hola, {me.nombre.split(" ")[0]}</h1>
        <p className="text-sm text-umber">Resumen de hoy</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card title="Pedidos hoy" value={d.pedidos_hoy} href="/admin/pedidos" />
        {d.pagos_en_revision !== undefined && <Card title="Pagos por verificar" value={d.pagos_en_revision} href="/admin/pedidos?estado=PENDIENTE_PAGO" tone={d.pagos_en_revision > 0 ? "alert" : undefined} />}
        <Card title="Por comprar (encargos)" value={d.por_comprar} href="/admin/pedidos?estado=PAGADO" />
        <Card title="Por entregar" value={d.por_entregar} href="/admin/pedidos?estado=PAGADO" />
        {d.ventas_hoy !== undefined && <Card title="Ventas hoy" value={money(d.ventas_hoy)} />}
        {d.ventas_mes !== undefined && <Card title="Ventas del mes" value={money(d.ventas_mes)} />}
      </div>

      {d.ventas_semana && (
        <section aria-labelledby="sem" className="border border-stone/40 bg-white p-4">
          <h2 id="sem" className="text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Ventas de los últimos 7 días</h2>
          <ul className="mt-4 flex h-32 items-end gap-2">
            {d.ventas_semana.map((v) => (
              <li key={v.fecha} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${v.fecha}: ${money(v.total)}`}>
                <span className="w-full bg-rose" style={{ height: `${Math.max(3, (Number(v.total) / max) * 100)}%` }} />
                <span className="text-[10px] text-umber">{v.fecha.slice(8)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="est">
        <h2 id="est" className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Pedidos por estado</h2>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Object.entries(ESTADO_PEDIDO).map(([k, label]) => (
            <li key={k}>
              <Link href={`/admin/pedidos?estado=${k}`} className="flex justify-between border border-stone/40 bg-white px-3 py-3 text-sm">
                <span>{label}</span>
                <strong>{d.por_estado[k] ?? 0}</strong>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="low">
        <h2 id="low" className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Stock bajo</h2>
        {d.stock_bajo.length === 0 ? (
          <p className="text-sm text-umber">Todo en orden.</p>
        ) : (
          <ul className="divide-y divide-stone/30 border border-stone/40 bg-white">
            {d.stock_bajo.map((s) => (
              <li key={s.id}>
                <Link href={`/admin/productos/${s.producto_id}`} className="flex items-center justify-between px-4 py-3 text-sm">
                  <span>{s.producto}{s.variante !== "Única" ? ` · ${s.variante}` : ""}</span>
                  <span className={s.libre === 0 ? "text-rose-text" : ""}>{s.libre === 0 ? "Agotado" : `Quedan ${s.libre}`}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {can("catalog.add_product") && (
        <Link href="/admin/productos/nuevo" className="fixed bottom-20 right-4 z-30 inline-flex h-14 items-center gap-2 bg-ink px-6 text-xs font-medium uppercase tracking-[0.18em] text-white shadow-lg md:static md:h-12 md:w-fit">
          + Nuevo producto
        </Link>
      )}
    </div>
  );
}
