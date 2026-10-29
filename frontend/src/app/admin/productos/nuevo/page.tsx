"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAdmin } from "@/components/admin/AdminShell";
import { EMPTY_DRAFT, PhotoPicker, ProductFields, toPayload, type ProductDraft } from "@/components/admin/ProductFields";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import type { AdminProduct } from "@/lib/admin";
import { api, ApiError, messageFrom } from "@/lib/client";

type VariantDraft = { nombre: string; atributo: string; stock: string };

export default function NewProduct() {
  const router = useRouter();
  const { meta, can } = useAdmin();
  const [draft, setDraft] = useState<ProductDraft>(EMPTY_DRAFT);
  const [files, setFiles] = useState<File[]>([]);
  const [variants, setVariants] = useState<VariantDraft[]>([{ nombre: "Única", atributo: "unico", stock: "1" }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setVariant = (i: number, patch: Partial<VariantDraft>) => setVariants(variants.map((v, j) => (j === i ? { ...v, ...patch } : v)));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const product = await api<AdminProduct>("/admin/products/", {
        json: { ...toPayload(draft, can("catalog.ver_finanzas")), variantes: variants.map((v) => ({ nombre: v.nombre, atributo: v.atributo, stock: Number(v.stock || 0) })) },
      });
      if (files.length > 0 && can("catalog.add_productimage")) {
        const form = new FormData();
        files.forEach((f) => form.append("imagen", f));
        await api(`/admin/products/${product.id}/images/`, { form });
      }
      router.push(`/admin/productos/${product.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? messageFrom(err.data) : "No pudimos guardar el producto.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-8 pb-10">
      <Link href="/admin/productos" className="text-xs uppercase tracking-widest text-umber underline underline-offset-4">← Productos</Link>
      <h1 className="font-serif text-3xl sm:text-4xl">Nuevo producto</h1>
      {error && <p role="alert" className="border border-rose bg-blush px-4 py-3 text-sm">{error}</p>}

      <section className="space-y-3"><h2 className="font-serif text-2xl">Fotos</h2><PhotoPicker files={files} onChange={setFiles} /></section>
      <section className="space-y-3"><h2 className="font-serif text-2xl">Datos</h2><ProductFields draft={draft} onChange={setDraft} /></section>

      <section className="space-y-3">
        <h2 className="font-serif text-2xl">Variantes y stock inicial</h2>
        <p className="text-xs text-umber">Si el producto es único, deja “Única”. Para colores o fragancias agrega una fila por cada una.</p>
        {variants.map((v, i) => (
          <div key={i} className="grid grid-cols-[1fr_6rem_5rem_auto] items-end gap-2">
            <div><label className={labelClass} htmlFor={`vn${i}`}>Nombre</label><input id={`vn${i}`} value={v.nombre} onChange={(e) => setVariant(i, { nombre: e.target.value })} className={inputClass} /></div>
            <div><label className={labelClass} htmlFor={`vt${i}`}>Tipo</label>
              <select id={`vt${i}`} value={v.atributo} onChange={(e) => setVariant(i, { atributo: e.target.value })} className={inputClass}>{meta.tipos_variante.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></div>
            <div><label className={labelClass} htmlFor={`vs${i}`}>Stock</label><input id={`vs${i}`} inputMode="numeric" value={v.stock} onChange={(e) => setVariant(i, { stock: e.target.value.replace(/\D/g, "") })} className={inputClass} /></div>
            <button type="button" aria-label="Quitar variante" disabled={variants.length === 1} onClick={() => setVariants(variants.filter((_, j) => j !== i))} className="h-12 w-10 text-xl disabled:opacity-30">×</button>
          </div>
        ))}
        <button type="button" onClick={() => setVariants([...variants, { nombre: "", atributo: "color", stock: "1" }])} className="text-xs uppercase tracking-widest underline underline-offset-4">+ Agregar variante</button>
      </section>

      <p className="text-xs text-umber">El producto se guarda como <strong>borrador</strong>. Cuando tenga precio y foto podrás publicarlo.</p>
      <button disabled={busy} className={btnPrimary}>{busy ? "Guardando…" : "Guardar producto"}</button>
    </form>
  );
}
