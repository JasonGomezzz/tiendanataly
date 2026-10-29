"use client";

import { useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import type { PriceResult } from "@/lib/admin";
import { api, ApiError, messageFrom } from "@/lib/client";
import { money } from "@/lib/format";

export default function Calculator() {
  const { can } = useAdmin();
  const [f, setF] = useState({ precio_usd: "", margen: "", envio_usd: "", impuestos_pct: "", comision_pct: "", tipo_cambio: "" });
  const [res, setRes] = useState<PriceResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!can("catalog.ver_finanzas")) return <p className="text-umber">No tienes acceso a esta sección.</p>;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body = Object.fromEntries(Object.entries(f).filter(([, v]) => v !== ""));
    try {
      setRes(await api<PriceResult>("/admin/pricing/calculate/", { json: body }));
    } catch (err) {
      setRes(null);
      setError(err instanceof ApiError ? messageFrom(err.data) : "No pudimos calcular.");
    }
  }

  const field = (k: keyof typeof f, label: string, hint: string) => (
    <div><label className={labelClass} htmlFor={k}>{label}</label><input id={k} inputMode="decimal" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={hint} className={inputClass} /></div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl sm:text-4xl">Calculadora de precio</h1>
        <p className="mt-1 text-sm text-umber">(Costo US$ + envío + impuestos) × tipo de cambio + margen, con la comisión de la pasarela incluida y redondeo comercial. Lo que dejes vacío usa lo configurado en Ajustes.</p>
      </div>
      <form onSubmit={submit} className="space-y-4">
        {field("precio_usd", "Costo del producto (US$)", "Ej: 30")}
        <div className="grid gap-4 sm:grid-cols-2">
          {field("margen", "Margen (S/)", "Por defecto de Ajustes")}
          {field("tipo_cambio", "Tipo de cambio", "Vigente")}
          {field("envio_usd", "Envío estimado (US$)", "Por defecto de Ajustes")}
          {field("impuestos_pct", "Impuestos estimados (%)", "Por defecto de Ajustes")}
          {field("comision_pct", "Comisión de pasarela (%)", "Por defecto de Ajustes")}
        </div>
        {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
        <button className={btnPrimary} disabled={!f.precio_usd}>Calcular</button>
      </form>
      {res && (
        <section aria-live="polite" className="border border-ink bg-white p-5">
          <p className="text-[11px] uppercase tracking-[0.18em] text-umber">Precio de venta sugerido</p>
          <p className="mt-1 font-serif text-5xl">{money(res.precio_final)}</p>
          <dl className="mt-4 space-y-1 text-sm">
            <div className="flex justify-between"><dt>Costo total</dt><dd>S/ {res.costo_pen} (US$ {res.costo_usd} × {res.tipo_cambio})</dd></div>
            <div className="flex justify-between"><dt>Margen</dt><dd>S/ {res.margen_pen}</dd></div>
            <div className="flex justify-between"><dt>Comisión pasarela</dt><dd>S/ {res.comision_pen}</dd></div>
            <div className="flex justify-between"><dt>Antes de redondear</dt><dd>S/ {res.precio_sin_redondeo}</dd></div>
            <div className="flex justify-between border-t border-stone/40 pt-2 font-medium"><dt>Ganancia neta</dt><dd>S/ {res.ganancia_neta}</dd></div>
          </dl>
        </section>
      )}
    </div>
  );
}
