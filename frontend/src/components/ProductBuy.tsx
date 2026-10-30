"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/client";
import type { ProductDetail, Variant } from "@/lib/types";
import { useCart } from "./CartProvider";
import { StockBadge, btnOutline, btnPrimary } from "./ui";

type Props = {
  slug: string;
  productName: string;
  preorder: boolean;
  initial: Variant[];
  whatsappUrl: string | null;
  advancePct: string;
};

/** Selector de variante, botón de bolsa y pedido por WhatsApp. Refresca el stock real al cargar. */
export function ProductBuy({ slug, productName, preorder, initial, whatsappUrl, advancePct }: Props) {
  const { add } = useCart();
  const [variants, setVariants] = useState(initial);
  const [selectedId, setSelectedId] = useState<number | null>(initial.length === 1 ? initial[0].id : null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [alertSent, setAlertSent] = useState<"idle" | "form" | "done">("idle");
  const [contact, setContact] = useState("");

  useEffect(() => {
    // La página es estática; aquí traemos la disponibilidad real (otra clienta pudo reservar).
    api<ProductDetail>(`/products/${slug}/`)
      .then((p) => setVariants(p.variantes))
      .catch(() => undefined);
  }, [slug]);

  const selected = variants.find((v) => v.id === selectedId) ?? null;
  const unavailable = !preorder && selected?.agotado;
  const allSoldOut = !preorder && variants.length > 0 && variants.every((v) => v.agotado);

  async function onAdd() {
    if (!selected) {
      setError("Elige una opción antes de añadir a la bolsa.");
      return;
    }
    setBusy(true);
    setError(await add(selected.id, 1));
    setBusy(false);
  }

  async function onNotify(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    const isEmail = contact.includes("@");
    try {
      await api(`/variants/${selected.id}/stock-alerts/`, { json: isEmail ? { email: contact } : { telefono: contact } });
      setAlertSent("done");
    } catch {
      setError("No pudimos registrar tu aviso. Revisa el dato e inténtalo otra vez.");
    }
  }

  const waText = `Hola, quiero pedir: ${productName}${selected && variants.length > 1 ? ` (${selected.nombre})` : ""}`;
  const wa = whatsappUrl ? `${whatsappUrl}${encodeURIComponent(waText)}` : null;

  return (
    <div>
      {variants.length > 1 && (
        <fieldset className="mt-6">
          <legend className="mb-2 flex w-full justify-between text-[11px] font-medium uppercase tracking-[0.18em]">
            <span>{variants[0].atributo === "fragancia" ? "Fragancia" : variants[0].atributo === "talla" ? "Talla" : "Color"}</span>
            {selected && <span className="normal-case tracking-normal text-umber">{selected.nombre}</span>}
          </legend>
          <div className="flex flex-wrap gap-2">
            {variants.map((v) => {
              const sold = !preorder && v.agotado;
              return (
                <button
                  key={v.id}
                  type="button"
                  aria-pressed={selectedId === v.id}
                  onClick={() => {
                    setSelectedId(v.id);
                    setError(null);
                    setAlertSent("idle");
                  }}
                  className={`min-h-11 border px-4 text-xs uppercase tracking-wide transition-colors ${
                    selectedId === v.id ? "border-ink bg-ink text-white" : "border-stone/70 hover:border-ink"
                  } ${sold ? "text-umber line-through decoration-stone" : ""}`}
                >
                  {v.nombre}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}

      {selected && !preorder && !selected.agotado && selected.disponible <= 2 && (
        <p className="mt-4">
          <StockBadge agotado={false} ultimas stock={selected.disponible} />
        </p>
      )}

      {preorder && (
        <p className="mt-4 bg-blush px-3 py-2 text-xs text-umber-dark">
          Producto por encargo: pagas un adelanto del {Number(advancePct)}% y el saldo cuando llegue a Lima.
        </p>
      )}

      <div className="mt-6 space-y-3">
        {unavailable || allSoldOut ? (
          <>
            <button type="button" disabled className={btnPrimary}>
              Agotado
            </button>
            {alertSent === "done" ? (
              <p role="status" className="text-sm text-umber">¡Listo! Te avisaremos cuando vuelva.</p>
            ) : alertSent === "form" ? (
              <form onSubmit={onNotify} className="flex gap-2">
                <label className="sr-only" htmlFor="notify">Correo o teléfono</label>
                <input id="notify" required value={contact} onChange={(e) => setContact(e.target.value)} placeholder="Correo o teléfono" className="w-full border border-stone/70 px-3 py-3 text-sm" />
                <button className="bg-ink px-5 text-xs uppercase tracking-widest text-white">Avísame</button>
              </form>
            ) : (
              <button type="button" className={btnOutline} onClick={() => (selected ? setAlertSent("form") : setError("Elige la opción que quieres que te avisemos."))}>
                Avísame cuando vuelva
              </button>
            )}
          </>
        ) : (
          <button type="button" onClick={onAdd} disabled={busy} className={btnPrimary}>
            {busy ? "Añadiendo…" : "Añadir a la bolsa"}
          </button>
        )}
        {wa && (
          <a href={wa} target="_blank" rel="noopener noreferrer" className={btnOutline}>
            Pedir por WhatsApp
          </a>
        )}
        {error && (
          <p role="alert" className="text-sm text-rose-text">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
