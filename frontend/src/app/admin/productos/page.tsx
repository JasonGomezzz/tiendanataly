"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { inputClass } from "@/components/ui";
import type { AdminProduct } from "@/lib/admin";
import { api } from "@/lib/client";
import { money } from "@/lib/format";

const STATE: Record<string, string> = { borrador: "Borrador", publicado: "Publicado", agotado: "Agotado" };

export default function ProductsAdmin() {
  const { can } = useAdmin();
  const [rows, setRows] = useState<AdminProduct[] | null>(null);
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");

  useEffect(() => {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (estado) qs.set("estado", estado);
    const t = setTimeout(() => api<AdminProduct[]>(`/admin/products/?${qs}`).then(setRows).catch(() => setRows([])), 250);
    return () => clearTimeout(t);
  }, [q, estado]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-serif text-3xl sm:text-4xl">Productos</h1>
        {can("catalog.add_product") && <Link href="/admin/productos/nuevo" className="inline-flex min-h-12 items-center bg-ink px-5 text-xs font-medium uppercase tracking-[0.16em] text-white">+ Nuevo</Link>}
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="q">Buscar producto</label>
        <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por nombre o código" className={inputClass} />
        <select aria-label="Filtrar por estado" value={estado} onChange={(e) => setEstado(e.target.value)} className={`${inputClass} sm:w-48`}>
          <option value="">Todos</option>{Object.entries(STATE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      {rows === null ? <p className="text-umber">Cargando…</p> : rows.length === 0 ? <p className="text-umber">No hay productos.</p> : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {rows.map((p) => (
            <li key={p.id}>
              <Link href={`/admin/productos/${p.id}`} className="flex gap-3 border border-stone/40 bg-white p-3 hover:border-ink">
                <span className="relative h-24 w-20 shrink-0 bg-paper">
                  {p.imagenes[0] ? <Image src={p.imagenes[0].url} alt="" fill sizes="80px" className="object-cover" /> : <span className="flex h-full items-center justify-center p-1 text-center text-[10px] text-umber">Sin foto</span>}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium uppercase tracking-wide">{p.nombre}</span>
                  <span className="block text-xs text-umber">{p.marca_nombre} · {p.categoria_nombre}</span>
                  <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                    <span className={`px-2 py-0.5 uppercase tracking-widest ${p.estado === "publicado" ? "bg-ink text-white" : "bg-paper text-umber"}`}>{STATE[p.estado]}</span>
                    <span>{p.tipo_venta === "por_encargo" ? "Por encargo" : `Stock ${p.stock_total}`}</span>
                    {p.precio_venta_pen !== undefined && <span>{p.precio_venta_pen ? money(p.precio_venta_pen) : <em className="text-rose-text">Sin precio</em>}</span>}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
