"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { PhotoPicker, ProductFields, toPayload, type ProductDraft } from "@/components/admin/ProductFields";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import type { AdminProduct, AdminVariant } from "@/lib/admin";
import { api, ApiError, messageFrom } from "@/lib/client";

const toDraft = (p: AdminProduct): ProductDraft => ({
  nombre: p.nombre, marca: String(p.marca), categoria: String(p.categoria), tipo_venta: p.tipo_venta, linea: p.linea, descripcion: p.descripcion,
  detalles: p.detalles, notas_internas: p.notas_internas, precio_compra_usd: p.precio_compra_usd ?? "", margen: p.margen ?? "", precio_venta_pen: p.precio_venta_pen ?? "",
  oferta_cantidad: p.oferta_cantidad ? String(p.oferta_cantidad) : "", oferta_precio: p.oferta_precio ?? "",
});

export default function EditProduct() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAdmin();
  const [p, setP] = useState<AdminProduct | null>(null);
  const [draft, setDraft] = useState<ProductDraft | null>(null);
  const [newFiles, setNewFiles] = useState<File[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [adjust, setAdjust] = useState<{ v: AdminVariant; tipo: "entrada" | "ajuste"; cantidad: string; motivo: string } | null>(null);
  const [newVariant, setNewVariant] = useState("");

  const load = useCallback(async () => {
    const data = await api<AdminProduct>(`/admin/products/${id}/`);
    setP(data);
    setDraft(toDraft(data));
  }, [id]);

  useEffect(() => {
    load().catch(() => setMsg({ ok: false, text: "No pudimos cargar el producto." }));
  }, [load]);

  async function run(fn: () => Promise<unknown>, okText: string) {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      await load();
      setMsg({ ok: true, text: okText });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? messageFrom(e.data) : "No pudimos completar la acción." });
    } finally {
      setBusy(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  if (!p || !draft) return <p className="text-umber">{msg?.text ?? "Cargando…"}</p>;

  const finance = can("catalog.ver_finanzas");

  return (
    <div className="space-y-8 pb-10">
      <Link href="/admin/productos" className="text-xs uppercase tracking-widest text-umber underline underline-offset-4">← Productos</Link>
      <div>
        <h1 className="font-serif text-3xl sm:text-4xl">{p.nombre}</h1>
        <p className="mt-1 text-sm text-umber">{p.estado === "publicado" ? "Publicado en la tienda" : p.estado === "agotado" ? "Publicado · agotado" : "Borrador (no se ve en la tienda)"} · /producto/{p.slug}</p>
      </div>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`border px-4 py-3 text-sm ${msg.ok ? "border-stone/50 bg-paper" : "border-rose bg-blush"}`}>{msg.text}</p>}

      {can("catalog.change_product") && (
        <div className="flex gap-2">
          {p.estado === "borrador" ? (
            <button disabled={busy} onClick={() => run(() => api(`/admin/products/${p.id}/publish/`, { json: {} }), "¡Publicado! Ya se ve en la tienda.")} className={btnPrimary}>Publicar en la tienda</button>
          ) : (
            <button disabled={busy} onClick={() => run(() => api(`/admin/products/${p.id}/hide/`, { json: {} }), "Ocultado: ahora es un borrador.")} className="inline-flex min-h-12 w-full items-center justify-center border border-ink text-xs font-medium uppercase tracking-[0.2em]">Ocultar de la tienda</button>
          )}
        </div>
      )}

      <section className="space-y-3">
        <h2 className="font-serif text-2xl">Fotos</h2>
        <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {p.imagenes.map((img) => (
            <li key={img.id} className="relative aspect-4/5 bg-paper">
              <Image src={img.url} alt={img.alt || p.nombre} fill sizes="160px" className="object-cover" />
              {can("catalog.delete_productimage") && <button aria-label="Eliminar foto" disabled={busy} onClick={() => confirm("¿Eliminar esta foto?") && run(() => api(`/admin/products/${p.id}/images/?imagen=${img.id}`, { method: "DELETE" }), "Foto eliminada.")} className="absolute right-1 top-1 h-8 w-8 bg-white/90 text-lg leading-none">×</button>}
            </li>
          ))}
        </ul>
        {can("catalog.add_productimage") && (
          <>
            <PhotoPicker files={newFiles} onChange={setNewFiles} />
            {newFiles.length > 0 && (
              <button disabled={busy} className={btnPrimary} onClick={() => run(async () => {
                const form = new FormData();
                newFiles.forEach((f) => form.append("imagen", f));
                await api(`/admin/products/${p.id}/images/`, { form });
                setNewFiles([]);
              }, "Fotos subidas.")}>Subir {newFiles.length} {newFiles.length === 1 ? "foto" : "fotos"}</button>
            )}
          </>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl">Variantes y stock</h2>
        <ul className="divide-y divide-stone/30 border border-stone/40 bg-white">
          {p.variantes.map((v) => (
            <li key={v.id} className="p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className={`font-medium ${v.activo ? "" : "text-umber line-through"}`}>{v.nombre}</p>
                  <p className="text-xs text-umber">{v.sku} · en Lima {v.stock_disponible} · reservadas {v.stock_reservado} · libres <strong className="text-ink">{v.libre}</strong></p>
                </div>
                {can("catalog.change_productvariant") && (
                  <div className="flex shrink-0 gap-2">
                    <button disabled={busy} onClick={() => setAdjust({ v, tipo: "entrada", cantidad: "1", motivo: "" })} className="min-h-11 border border-ink px-3 text-xs uppercase tracking-widest">Stock</button>
                    <button disabled={busy} onClick={() => run(() => api(`/admin/variants/${v.id}/`, { method: "PATCH", json: { activo: !v.activo } }), v.activo ? "Variante desactivada." : "Variante activada.")} className="min-h-11 px-2 text-xs uppercase tracking-widest text-umber underline underline-offset-4">{v.activo ? "Ocultar" : "Mostrar"}</button>
                  </div>
                )}
              </div>
              {adjust?.v.id === v.id && (
                <form className="mt-3 space-y-3 bg-paper p-3" onSubmit={(e) => { e.preventDefault(); void run(async () => { await api(`/admin/variants/${v.id}/adjust-stock/`, { json: { tipo: adjust.tipo, cantidad: Number(adjust.cantidad), motivo: adjust.motivo } }); setAdjust(null); }, "Stock actualizado."); }}>
                  <div className="grid grid-cols-2 gap-2">
                    <div><label className={labelClass} htmlFor="ad-tipo">Tipo</label>
                      <select id="ad-tipo" value={adjust.tipo} onChange={(e) => setAdjust({ ...adjust, tipo: e.target.value as "entrada" | "ajuste" })} className={inputClass}><option value="entrada">Ingreso (suma)</option><option value="ajuste">Corrección (+/−)</option></select></div>
                    <div><label className={labelClass} htmlFor="ad-cant">Cantidad</label><input id="ad-cant" required inputMode="numeric" value={adjust.cantidad} onChange={(e) => setAdjust({ ...adjust, cantidad: e.target.value.replace(/[^\d-]/g, "") })} className={inputClass} /></div>
                  </div>
                  <div><label className={labelClass} htmlFor="ad-mot">Motivo (obligatorio)</label><input id="ad-mot" required minLength={3} value={adjust.motivo} onChange={(e) => setAdjust({ ...adjust, motivo: e.target.value })} className={inputClass} placeholder="Ej: llegó pedido, conteo físico" /></div>
                  <div className="flex gap-2"><button disabled={busy} className="min-h-12 flex-1 bg-ink text-xs font-medium uppercase tracking-[0.16em] text-white">Aplicar</button><button type="button" onClick={() => setAdjust(null)} className="min-h-12 px-4 text-xs uppercase tracking-widest text-umber">Cancelar</button></div>
                </form>
              )}
            </li>
          ))}
        </ul>
        {can("catalog.add_productvariant") && (
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void run(async () => { await api(`/admin/products/${p.id}/variants/`, { json: { nombre: newVariant, atributo: "color" } }); setNewVariant(""); }, "Variante agregada. Ahora súmale stock."); }}>
            <label className="sr-only" htmlFor="nv">Nueva variante</label>
            <input id="nv" required value={newVariant} onChange={(e) => setNewVariant(e.target.value)} placeholder="Nueva variante (color, fragancia…)" className={inputClass} />
            <button disabled={busy} className="shrink-0 border border-ink px-5 text-xs uppercase tracking-widest">Agregar</button>
          </form>
        )}
      </section>

      {can("catalog.change_product") && (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); void run(() => api(`/admin/products/${p.id}/`, { method: "PATCH", json: toPayload(draft, finance) }), "Cambios guardados."); }}>
          <h2 className="font-serif text-2xl">Datos</h2>
          <ProductFields draft={draft} onChange={setDraft} />
          <button disabled={busy} className={btnPrimary}>{busy ? "Guardando…" : "Guardar cambios"}</button>
        </form>
      )}
    </div>
  );
}
