"use client";

import { useState } from "react";
import { api, ApiError, messageFrom } from "@/lib/client";
import { money } from "@/lib/format";
import type { PriceResult } from "@/lib/admin";
import { inputClass, labelClass } from "../ui";
import { useAdmin } from "./AdminShell";

export type ProductDraft = {
  nombre: string;
  marca: string;
  categoria: string;
  tipo_venta: string;
  linea: string;
  descripcion: string;
  detalles: string;
  notas_internas: string;
  precio_compra_usd: string;
  margen: string;
  precio_venta_pen: string;
  oferta_cantidad: string;
  oferta_precio: string;
};

export const EMPTY_DRAFT: ProductDraft = {
  nombre: "", marca: "", categoria: "", tipo_venta: "stock_local", linea: "", descripcion: "", detalles: "", notas_internas: "",
  precio_compra_usd: "", margen: "", precio_venta_pen: "", oferta_cantidad: "", oferta_precio: "",
};

/** Campos del producto + ayuda de precio (solo si el rol puede ver finanzas). */
export function ProductFields({ draft, onChange }: { draft: ProductDraft; onChange: (d: ProductDraft) => void }) {
  const { meta, can } = useAdmin();
  const finance = can("catalog.ver_finanzas");
  const [calc, setCalc] = useState<PriceResult | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);
  const set = (k: keyof ProductDraft) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => onChange({ ...draft, [k]: e.target.value });

  async function calculate() {
    setCalcError(null);
    try {
      const res = await api<PriceResult>("/admin/pricing/calculate/", { json: { precio_usd: draft.precio_compra_usd || "0", ...(draft.margen ? { margen: draft.margen } : {}) } });
      setCalc(res);
    } catch (e) {
      setCalc(null);
      setCalcError(e instanceof ApiError ? messageFrom(e.data) : "No pudimos calcular el precio.");
    }
  }

  return (
    <div className="space-y-4">
      <div><label className={labelClass} htmlFor="nombre">Nombre</label><input id="nombre" required value={draft.nombre} onChange={set("nombre")} className={inputClass} /></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className={labelClass} htmlFor="marca">Marca</label>
          <select id="marca" required value={draft.marca} onChange={set("marca")} className={inputClass}><option value="">Elegir…</option>{meta.marcas.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}</select></div>
        <div><label className={labelClass} htmlFor="categoria">Categoría</label>
          <select id="categoria" required value={draft.categoria} onChange={set("categoria")} className={inputClass}><option value="">Elegir…</option>{meta.categorias.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}</select></div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className={labelClass} htmlFor="linea">Línea / presentación</label><input id="linea" value={draft.linea} onChange={set("linea")} className={inputClass} placeholder="Ej: Fragrance mist 250 ml" /></div>
        <div><label className={labelClass} htmlFor="tipo">Tipo de venta</label>
          <select id="tipo" value={draft.tipo_venta} onChange={set("tipo_venta")} className={inputClass}>{meta.tipos_venta.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></div>
      </div>
      <div><label className={labelClass} htmlFor="desc">Descripción</label><textarea id="desc" rows={3} value={draft.descripcion} onChange={set("descripcion")} className={inputClass} /></div>
      <div><label className={labelClass} htmlFor="det">Detalles (material, medidas…)</label><textarea id="det" rows={2} value={draft.detalles} onChange={set("detalles")} className={inputClass} /></div>

      {finance && (
        <fieldset className="space-y-4 border border-stone/40 bg-white p-4">
          <legend className="px-1 text-[11px] font-medium uppercase tracking-[0.16em] text-umber">Precio</legend>
          <div className="grid gap-4 sm:grid-cols-3">
            <div><label className={labelClass} htmlFor="usd">Costo en US$</label><input id="usd" inputMode="decimal" value={draft.precio_compra_usd} onChange={set("precio_compra_usd")} className={inputClass} /></div>
            <div><label className={labelClass} htmlFor="mar">Margen (S/)</label><input id="mar" inputMode="decimal" value={draft.margen} onChange={set("margen")} className={inputClass} placeholder="Usa el de Ajustes" /></div>
            <div><label className={labelClass} htmlFor="pv">Precio de venta (S/)</label><input id="pv" inputMode="decimal" value={draft.precio_venta_pen} onChange={set("precio_venta_pen")} className={inputClass} /></div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className={labelClass} htmlFor="oc">Oferta: llevando (unidades)</label><input id="oc" inputMode="numeric" value={draft.oferta_cantidad} onChange={set("oferta_cantidad")} className={inputClass} placeholder="Ej: 2" /></div>
            <div><label className={labelClass} htmlFor="op">Oferta: precio por esas unidades (S/)</label><input id="op" inputMode="decimal" value={draft.oferta_precio} onChange={set("oferta_precio")} className={inputClass} placeholder="Ej: 90" /></div>
          </div>
          <p className="text-xs text-umber">Déjalos vacíos si no hay oferta. Las variantes del mismo producto suman para la oferta (por ejemplo, dos fragancias distintas).</p>
          <button type="button" onClick={calculate} disabled={!draft.precio_compra_usd} className="min-h-12 w-full border border-ink text-xs font-medium uppercase tracking-[0.16em] disabled:opacity-40">Calcular precio sugerido</button>
          {calcError && <p role="alert" className="text-sm text-rose-text">{calcError}</p>}
          {calc && (
            <div className="bg-paper p-3 text-sm">
              <p>Costo S/ {calc.costo_pen} + margen S/ {calc.margen_pen}{Number(calc.comision_pen) > 0 ? ` + comisión S/ ${calc.comision_pen}` : ""}</p>
              <p className="mt-1">Precio sugerido: <strong>{money(calc.precio_final)}</strong> · Ganancia neta {money(calc.ganancia_neta)}</p>
              <button type="button" onClick={() => onChange({ ...draft, precio_venta_pen: calc.precio_final })} className="mt-2 text-xs uppercase tracking-widest underline underline-offset-4">Usar este precio</button>
            </div>
          )}
        </fieldset>
      )}

      <div><label className={labelClass} htmlFor="notas">Notas internas (no se muestran a clientas)</label><textarea id="notas" rows={2} value={draft.notas_internas} onChange={set("notas_internas")} className={inputClass} /></div>
    </div>
  );
}

/** Selector de fotos: cámara trasera del celular o galería. */
export function PhotoPicker({ files, onChange }: { files: File[]; onChange: (f: File[]) => void }) {
  const add = (list: FileList | null) => list && onChange([...files, ...Array.from(list)]);
  const btn = "flex min-h-14 flex-1 cursor-pointer items-center justify-center border border-ink text-xs font-medium uppercase tracking-[0.16em]";
  return (
    <div>
      <div className="flex gap-2">
        <label className={btn}>
          📷 Tomar foto
          <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        </label>
        <label className={btn}>
          Galería
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="sr-only" onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        </label>
      </div>
      {files.length > 0 && (
        <ul className="mt-3 grid grid-cols-3 gap-2">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="relative aspect-4/5 bg-paper">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={URL.createObjectURL(f)} alt={`Foto ${i + 1}`} className="h-full w-full object-cover" />
              <button type="button" aria-label={`Quitar foto ${i + 1}`} onClick={() => onChange(files.filter((_, j) => j !== i))} className="absolute right-1 top-1 h-8 w-8 bg-white/90 text-lg leading-none">×</button>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-umber">Fondo liso, luz de ventana, producto centrado. Máx. 5 MB por foto.</p>
    </div>
  );
}

export function toPayload(d: ProductDraft, finance: boolean) {
  const base: Record<string, unknown> = {
    nombre: d.nombre, marca: Number(d.marca), categoria: Number(d.categoria), tipo_venta: d.tipo_venta, linea: d.linea,
    descripcion: d.descripcion, detalles: d.detalles, notas_internas: d.notas_internas,
  };
  if (finance) {
    base.precio_compra_usd = d.precio_compra_usd || null;
    base.margen = d.margen || null;
    base.precio_venta_pen = d.precio_venta_pen || null;
    base.oferta_cantidad = d.oferta_cantidad ? Number(d.oferta_cantidad) : null;
    base.oferta_precio = d.oferta_precio || null;
  }
  return base;
}
