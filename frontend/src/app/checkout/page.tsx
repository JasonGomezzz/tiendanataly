"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useCart } from "@/components/CartProvider";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import { api, ApiError, messageFrom } from "@/lib/client";
import { money } from "@/lib/format";
import type { Order, StoreInfo, Zone } from "@/lib/types";

type Me = { nombre: string; telefono: string; email: string };

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, refresh } = useCart();
  const [zones, setZones] = useState<Zone[]>([]);
  const [store, setStore] = useState<StoreInfo | null>(null);
  const [zoneId, setZoneId] = useState<number | null>(null);
  const [form, setForm] = useState({ nombre: "", telefono: "", email: "", departamento: "Lima", provincia: "Lima", distrito: "", direccion: "", referencia: "", notas: "" });
  const [privacy, setPrivacy] = useState(false);
  const [terms, setTerms] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Zone[]>("/shipping/zones/").then((z) => {
      setZones(z);
      setZoneId((cur) => cur ?? z[0]?.id ?? null);
    }).catch(() => undefined);
    api<StoreInfo>("/store-settings/public/").then(setStore).catch(() => undefined);
    api<Me>("/me/").then((me) => setForm((f) => ({ ...f, nombre: me.nombre, telefono: me.telefono, email: me.email }))).catch(() => undefined);
  }, []);

  const zone = zones.find((z) => z.id === zoneId) ?? null;
  const needsAddress = zone?.metodo !== "recojo";
  const shipping = Number(zone?.costo ?? 0);
  const total = useMemo(() => Number(cart.subtotal) + shipping, [cart.subtotal, shipping]);
  const blocked = cart.items.length === 0 || cart.items.some((i) => !i.ok);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  function pickZone(z: Zone) {
    setZoneId(z.id);
    setForm((f) => (z.metodo === "delivery_lima" ? { ...f, departamento: "Lima", provincia: "Lima" } : z.metodo === "courier_provincia" ? { ...f, departamento: "", provincia: "" } : f));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!zone) return;
    setBusy(true);
    setError(null);
    try {
      const order = await api<Order>("/checkout/", {
        json: {
          nombre: form.nombre, telefono: form.telefono, email: form.email, metodo_entrega: zone.metodo, zona_id: zone.id, notas: form.notas,
          direccion: needsAddress ? { departamento: form.departamento, provincia: form.provincia, distrito: form.distrito, direccion: form.direccion, referencia: form.referencia } : undefined,
          acepta_privacidad: privacy, acepta_terminos: terms, acepta_marketing: marketing,
        },
      });
      await refresh();
      router.push(`/pedido/${order.token}`);
    } catch (err) {
      setError(err instanceof ApiError ? messageFrom(err.data) : "No pudimos crear tu pedido. Inténtalo de nuevo.");
      if (err instanceof ApiError && err.status === 409) await refresh();
      window.scrollTo({ top: 0, behavior: "smooth" });
      setBusy(false);
    }
  }

  if (cart.items.length === 0 && !busy) {
    return (
      <div className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="font-serif text-4xl">Tu bolsa está vacía</h1>
        <Link href="/tienda" className={`${btnPrimary} mx-auto mt-8 max-w-xs`}>Ir a la tienda</Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto grid max-w-6xl gap-12 px-4 py-10 sm:px-8 lg:grid-cols-[1fr_380px]">
      <div className="space-y-10">
        <h1 className="font-serif text-4xl sm:text-5xl">Finalizar compra</h1>
        {error && <p role="alert" className="border border-rose bg-blush px-4 py-3 text-sm text-umber-dark">{error}</p>}

        <fieldset className="space-y-4">
          <legend className="mb-2 font-serif text-2xl">1. Tus datos</legend>
          <div><label className={labelClass} htmlFor="nombre">Nombre y apellido</label><input id="nombre" required autoComplete="name" value={form.nombre} onChange={set("nombre")} className={inputClass} /></div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className={labelClass} htmlFor="telefono">Celular (WhatsApp)</label><input id="telefono" required inputMode="tel" autoComplete="tel" value={form.telefono} onChange={set("telefono")} className={inputClass} /></div>
            <div><label className={labelClass} htmlFor="email">Correo (opcional)</label><input id="email" type="email" autoComplete="email" value={form.email} onChange={set("email")} className={inputClass} /></div>
          </div>
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="mb-2 font-serif text-2xl">2. Entrega</legend>
          <div className="grid gap-3">
            {zones.map((z) => (
              <label key={z.id} className={`flex cursor-pointer items-center justify-between border p-4 text-sm ${zoneId === z.id ? "border-ink" : "border-stone/60"}`}>
                <span className="flex items-center gap-3">
                  <input type="radio" name="zona" checked={zoneId === z.id} onChange={() => pickZone(z)} />
                  <span>
                    <span className="block font-medium uppercase tracking-wide">{z.nombre}</span>
                    {(z.instrucciones || z.courier) && <span className="block text-xs text-umber">{z.instrucciones || `Courier: ${z.courier}`}</span>}
                  </span>
                </span>
                <span>{Number(z.costo) === 0 ? "Gratis" : money(z.costo)}</span>
              </label>
            ))}
          </div>
          {needsAddress && (
            <div className="space-y-4 pt-2">
              <div className="grid gap-4 sm:grid-cols-3">
                <div><label className={labelClass} htmlFor="dep">Departamento</label><input id="dep" required value={form.departamento} onChange={set("departamento")} className={inputClass} /></div>
                <div><label className={labelClass} htmlFor="prov">Provincia</label><input id="prov" required value={form.provincia} onChange={set("provincia")} className={inputClass} /></div>
                <div><label className={labelClass} htmlFor="dist">Distrito</label><input id="dist" required value={form.distrito} onChange={set("distrito")} className={inputClass} /></div>
              </div>
              <div><label className={labelClass} htmlFor="dir">Dirección</label><input id="dir" required autoComplete="street-address" value={form.direccion} onChange={set("direccion")} className={inputClass} /></div>
              <div><label className={labelClass} htmlFor="ref">Referencia (opcional)</label><input id="ref" value={form.referencia} onChange={set("referencia")} className={inputClass} /></div>
            </div>
          )}
          <div><label className={labelClass} htmlFor="notas">Notas para tu pedido (opcional)</label><textarea id="notas" rows={2} value={form.notas} onChange={set("notas")} className={inputClass} /></div>
        </fieldset>

        <fieldset className="space-y-3 text-sm">
          <legend className="mb-2 font-serif text-2xl">3. Pago</legend>
          <p className="text-umber">Al confirmar, reservamos tus productos por {store?.minutos_reserva ?? 15} minutos. En el siguiente paso pagas con <strong>Yape o Plin</strong> y subes tu captura; verificamos tu pago y te avisamos.</p>
          <label className="flex items-start gap-3"><input type="checkbox" required checked={privacy} onChange={(e) => setPrivacy(e.target.checked)} className="mt-1" /><span>Acepto la <Link href="/privacidad" target="_blank" className="underline underline-offset-4">política de privacidad</Link> y el uso de mis datos para gestionar mi pedido.</span></label>
          <label className="flex items-start gap-3"><input type="checkbox" required checked={terms} onChange={(e) => setTerms(e.target.checked)} className="mt-1" /><span>Acepto los <Link href="/terminos" target="_blank" className="underline underline-offset-4">términos y condiciones</Link>.</span></label>
          <label className="flex items-start gap-3 text-umber"><input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} className="mt-1" /><span>Quiero recibir novedades y ofertas por WhatsApp (opcional).</span></label>
        </fieldset>
      </div>

      <aside className="h-fit border border-stone/40 bg-paper p-6 lg:sticky lg:top-6" aria-label="Resumen del pedido">
        <h2 className="font-serif text-2xl">Resumen</h2>
        <ul className="mt-4 space-y-3 text-sm">
          {cart.items.map((i) => (
            <li key={i.id} className="flex justify-between gap-3">
              <span>{i.cantidad} × {i.nombre}{i.variante ? ` (${i.variante})` : ""}</span>
              <span>{money(i.subtotal)}</span>
            </li>
          ))}
        </ul>
        <dl className="mt-5 space-y-2 border-t border-stone/40 pt-4 text-sm">
          <div className="flex justify-between"><dt>Subtotal</dt><dd>{money(cart.subtotal)}</dd></div>
          <div className="flex justify-between"><dt>Envío</dt><dd>{zone ? (shipping === 0 ? "Gratis" : money(shipping)) : "—"}</dd></div>
          <div className="flex justify-between border-t border-stone/40 pt-3 text-base font-medium"><dt>Total</dt><dd>{money(total)}</dd></div>
        </dl>
        <button disabled={busy || blocked || !zone || !privacy || !terms} className={`${btnPrimary} mt-6`}>{busy ? "Creando pedido…" : "Confirmar pedido"}</button>
        <p className="mt-3 text-center text-xs text-umber">El total final lo confirma el sistema al crear tu pedido.</p>
      </aside>
    </form>
  );
}
