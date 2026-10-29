"use client";

import { useEffect, useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import { dateTime } from "@/lib/admin";
import { api, ApiError, messageFrom } from "@/lib/client";

type Settings = Record<string, string | number>;
type Rate = { id: number; usd_pen: string; vigente_desde: string };
type AuditRow = { id: number; fecha: string; usuario: string | null; accion: string; modelo: string; objeto: string };

const FIELDS: { key: string; label: string; hint?: string; group: string }[] = [
  { key: "nombre_tienda", label: "Nombre de la tienda", group: "Tienda" },
  { key: "whatsapp", label: "WhatsApp para pedidos", hint: "Con código de país, sin +. Ej: 51999999999", group: "Tienda" },
  { key: "razon_social", label: "Razón social / titular", group: "Tienda" },
  { key: "ruc", label: "RUC (si tiene)", group: "Tienda" },
  { key: "yape_numero", label: "Número de Yape", group: "Pagos" },
  { key: "yape_titular", label: "Titular de Yape", group: "Pagos" },
  { key: "plin_numero", label: "Número de Plin", group: "Pagos" },
  { key: "plin_titular", label: "Titular de Plin", group: "Pagos" },
  { key: "minutos_reserva", label: "Minutos que se reserva una unidad", group: "Pedidos" },
  { key: "pct_adelanto", label: "% de adelanto en pedidos por encargo", group: "Pedidos" },
  { key: "margen_default", label: "Margen por defecto (S/)", group: "Precios" },
  { key: "envio_estimado_usd", label: "Envío estimado por producto (US$)", group: "Precios" },
  { key: "impuestos_estimados_pct", label: "Impuestos estimados (%)", group: "Precios" },
  { key: "pct_comision", label: "Comisión de pasarela (%)", hint: "Aprox. 3.3% a 4.2% + IGV; confirmar con el contrato", group: "Precios" },
  { key: "redondeo_multiplo", label: "Redondear precios a múltiplos de (S/)", group: "Precios" },
];

export default function SettingsPage() {
  const { can } = useAdmin();
  const [s, setS] = useState<Settings | null>(null);
  const [rates, setRates] = useState<Rate[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [rate, setRate] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    api<Settings>("/admin/store-settings/").then(setS).catch(() => undefined);
    api<Rate[]>("/admin/exchange-rates/").then(setRates).catch(() => undefined);
    api<AuditRow[]>("/admin/audit-log/").then(setAudit).catch(() => undefined);
  }, []);

  const fail = (e: unknown) => setMsg({ ok: false, text: e instanceof ApiError ? messageFrom(e.data) : "No pudimos guardar." });

  if (!can("core.change_storesettings")) return <p className="text-umber">No tienes acceso a esta sección.</p>;
  if (!s) return <p className="text-umber">Cargando…</p>;

  const groups = [...new Set(FIELDS.map((f) => f.group))];

  return (
    <div className="space-y-10 pb-10">
      <h1 className="font-serif text-3xl sm:text-4xl">Ajustes</h1>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`border px-4 py-3 text-sm ${msg.ok ? "border-stone/50 bg-paper" : "border-rose bg-blush"}`}>{msg.text}</p>}

      <section className="space-y-3" aria-labelledby="tc">
        <h2 id="tc" className="font-serif text-2xl">Tipo de cambio</h2>
        <p className="text-sm text-umber">Vigente: <strong className="text-ink">{rates[0] ? `S/ ${Number(rates[0].usd_pen).toFixed(4)} por US$ 1` : "sin configurar"}</strong>{rates[0] && ` (desde ${rates[0].vigente_desde})`}</p>
        <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); try { await api("/admin/exchange-rates/", { json: { usd_pen: rate } }); setRates(await api<Rate[]>("/admin/exchange-rates/")); setRate(""); setMsg({ ok: true, text: "Tipo de cambio actualizado." }); } catch (err) { fail(err); } }}>
          <label className="sr-only" htmlFor="rate">Nuevo tipo de cambio</label>
          <input id="rate" required inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="Ej: 3.75" className={inputClass} />
          <button className="shrink-0 bg-ink px-6 text-xs font-medium uppercase tracking-widest text-white">Guardar</button>
        </form>
      </section>

      <form className="space-y-8" onSubmit={async (e) => { e.preventDefault(); try { setS(await api<Settings>("/admin/store-settings/", { method: "PATCH", json: s })); setMsg({ ok: true, text: "Ajustes guardados." }); } catch (err) { fail(err); } }}>
        {groups.map((g) => (
          <fieldset key={g} className="space-y-3">
            <legend className="font-serif text-2xl">{g}</legend>
            {FIELDS.filter((f) => f.group === g).map((f) => (
              <div key={f.key}>
                <label className={labelClass} htmlFor={f.key}>{f.label}</label>
                <input id={f.key} value={String(s[f.key] ?? "")} onChange={(e) => setS({ ...s, [f.key]: e.target.value })} className={inputClass} />
                {f.hint && <p className="mt-1 text-xs text-umber">{f.hint}</p>}
              </div>
            ))}
          </fieldset>
        ))}
        <button className={btnPrimary}>Guardar ajustes</button>
      </form>

      {can("core.view_auditlog") && (
        <section aria-labelledby="aud" className="space-y-3">
          <h2 id="aud" className="font-serif text-2xl">Últimos cambios</h2>
          <ul className="divide-y divide-stone/30 border border-stone/40 bg-white text-sm">
            {audit.slice(0, 30).map((a) => (
              <li key={a.id} className="px-4 py-3">
                <p><strong>{a.accion}</strong> · {a.objeto || a.modelo}</p>
                <p className="text-xs text-umber">{a.usuario ?? "sistema"} · {dateTime(a.fecha)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
