"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import { api, ApiError, messageFrom } from "@/lib/client";

export default function ComplaintsBook() {
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [minor, setMinor] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const d = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    try {
      const res = await api<{ correlativo: string }>("/complaints/", {
        json: { ...d, es_menor: minor, monto_reclamado: d.monto_reclamado || null },
      });
      setDone(res.correlativo);
    } catch (err) {
      setError(err instanceof ApiError ? messageFrom(err.data) || "Revisa los datos del formulario." : "No pudimos enviar tu hoja. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="font-serif text-4xl">Recibimos tu hoja de reclamación</h1>
        <p className="mt-4 text-umber">Tu código es <strong className="text-ink">{done}</strong>. Guárdalo: lo necesitarás para cualquier consulta. Te responderemos al correo que indicaste.</p>
      </div>
    );
  }

  const field = (id: string, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div><label htmlFor={id} className={labelClass}>{label}</label><input id={id} name={id} required {...props} className={inputClass} /></div>
  );

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-8">
      <h1 className="font-serif text-4xl sm:text-5xl">Libro de reclamaciones</h1>
      <p className="mt-3 text-sm text-umber">Completa la hoja de reclamación. Reclamo: disconformidad con el producto o servicio. Queja: malestar no relacionado con el producto o servicio.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <h2 className="font-serif text-2xl">1. Tus datos</h2>
        {field("nombre", "Nombre completo")}
        <div className="grid gap-4 sm:grid-cols-2">
          <div><label htmlFor="doc_tipo" className={labelClass}>Documento</label><select id="doc_tipo" name="doc_tipo" required className={inputClass}><option>DNI</option><option value="CE">CE</option><option value="PAS">Pasaporte</option><option>RUC</option></select></div>
          {field("doc_numero", "Número de documento", { inputMode: "numeric", maxLength: 15 })}
        </div>
        {field("domicilio", "Domicilio")}
        <div className="grid gap-4 sm:grid-cols-2">
          {field("telefono", "Teléfono", { inputMode: "tel" })}
          {field("email", "Correo", { type: "email" })}
        </div>
        <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={minor} onChange={(e) => setMinor(e.target.checked)} /> Soy menor de edad</label>
        {minor && field("apoderado", "Nombre del padre, madre o apoderado")}

        <h2 className="pt-4 font-serif text-2xl">2. Producto contratado</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div><label htmlFor="bien" className={labelClass}>Tipo</label><select id="bien" name="bien" className={inputClass}><option value="producto">Producto</option><option value="servicio">Servicio</option></select></div>
          <div><label htmlFor="monto_reclamado" className={labelClass}>Monto reclamado (S/, opcional)</label><input id="monto_reclamado" name="monto_reclamado" type="number" step="0.01" min="0" className={inputClass} /></div>
        </div>
        {field("descripcion_bien", "Descripción del producto")}
        <div><label htmlFor="pedido_ref" className={labelClass}>N.º de pedido (opcional)</label><input id="pedido_ref" name="pedido_ref" className={inputClass} /></div>

        <h2 className="pt-4 font-serif text-2xl">3. Detalle del reclamo o queja</h2>
        <div><label htmlFor="tipo" className={labelClass}>Tipo</label><select id="tipo" name="tipo" required className={inputClass}><option value="reclamo">Reclamo</option><option value="queja">Queja</option></select></div>
        <div><label htmlFor="detalle" className={labelClass}>Detalle</label><textarea id="detalle" name="detalle" required rows={4} className={inputClass} /></div>
        <div><label htmlFor="pedido_consumidor" className={labelClass}>Pedido del consumidor</label><textarea id="pedido_consumidor" name="pedido_consumidor" required rows={2} className={inputClass} /></div>
        {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
        <button disabled={busy} className={btnPrimary}>{busy ? "Enviando…" : "Enviar hoja de reclamación"}</button>
      </form>
    </div>
  );
}
