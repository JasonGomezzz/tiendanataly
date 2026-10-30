"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useCart } from "@/components/CartProvider";
import { btnOutline, btnPrimary, inputClass, labelClass } from "@/components/ui";
import { api, ApiError, messageFrom, resetCsrf } from "@/lib/client";
import { STATE_LABEL, money } from "@/lib/format";
import type { Order, Paginated } from "@/lib/types";

type Me = { nombre: string; telefono: string; email: string };

export default function AccountPage() {
  const { refresh } = useCart();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [orders, setOrders] = useState<Order[]>([]);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ email: "", password: "", nombre: "", telefono: "", privacy: false, terms: false, marketing: false });

  const load = useCallback(async () => {
    try {
      setMe(await api<Me>("/me/"));
      setOrders((await api<Paginated<Order>>("/me/orders/")).results);
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await api("/auth/login/", { json: { email: f.email, password: f.password } });
      } else {
        await api("/auth/register/", { json: { email: f.email, password: f.password, nombre: f.nombre, telefono: f.telefono, acepta_privacidad: f.privacy, acepta_terminos: f.terms, acepta_marketing: f.marketing } });
      }
      resetCsrf(); // Django rota el token CSRF al iniciar sesión
      await api("/cart/merge/", { method: "POST", json: {} }).catch(() => undefined);
      await refresh();
      await load();
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(status === 429 ? "Demasiados intentos. Espera unos minutos." : err instanceof ApiError ? messageFrom(err.data) : "No pudimos conectar. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api("/auth/logout/", { method: "POST", json: {} }).catch(() => undefined);
    resetCsrf();
    setMe(null);
    setOrders([]);
    await refresh();
  }

  async function deleteAccount() {
    if (!confirm("Se borrarán tus datos personales y no podrás volver a entrar con esta cuenta. Tus pedidos se conservan de forma anónima. ¿Continuar?")) return;
    await api("/me/", { method: "DELETE" });
    resetCsrf();
    setMe(null);
    setOrders([]);
  }

  if (me === undefined) return <div className="mx-auto max-w-md px-4 py-24 text-center text-umber">Cargando…</div>;

  if (me) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-8">
        <h1 className="font-serif text-4xl sm:text-5xl">Hola, {me.nombre.split(" ")[0]}</h1>
        <p className="mt-1 text-sm text-umber">{me.email}</p>
        <h2 className="mt-10 font-serif text-2xl">Mis pedidos</h2>
        {orders.length === 0 ? (
          <p className="mt-4 text-sm text-umber">Aún no tienes pedidos. <Link href="/tienda" className="underline underline-offset-4">Ir a la tienda</Link></p>
        ) : (
          <ul className="mt-4 divide-y divide-stone/30">
            {orders.map((o) => (
              <li key={o.token}>
                <Link href={`/pedido/${o.token}`} className="flex items-center justify-between py-4 text-sm hover:bg-paper">
                  <span>#{o.numero} · {new Date(o.creado_en).toLocaleDateString("es-PE")}</span>
                  <span className="text-umber">{STATE_LABEL[o.estado]}</span>
                  <span>{money(o.total_pen)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-12 flex flex-col gap-3 sm:flex-row">
          <button onClick={logout} className={`${btnOutline} sm:w-auto`}>Cerrar sesión</button>
          <button onClick={deleteAccount} className="min-h-12 px-6 text-xs uppercase tracking-[0.18em] text-umber underline underline-offset-4">Eliminar mi cuenta y mis datos</button>
        </div>
      </div>
    );
  }

  const set = (k: "email" | "password" | "nombre" | "telefono") => (e: React.ChangeEvent<HTMLInputElement>) => setF((s) => ({ ...s, [k]: e.target.value }));

  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <h1 className="font-serif text-4xl sm:text-5xl">{mode === "login" ? "Ingresar" : "Crear cuenta"}</h1>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {mode === "register" && (
          <>
            <div><label htmlFor="n" className={labelClass}>Nombre y apellido</label><input id="n" required autoComplete="name" value={f.nombre} onChange={set("nombre")} className={inputClass} /></div>
            <div><label htmlFor="t" className={labelClass}>Celular</label><input id="t" required inputMode="tel" autoComplete="tel" value={f.telefono} onChange={set("telefono")} className={inputClass} /></div>
          </>
        )}
        <div><label htmlFor="e" className={labelClass}>Correo</label><input id="e" type="email" required autoComplete="email" value={f.email} onChange={set("email")} className={inputClass} /></div>
        <div><label htmlFor="p" className={labelClass}>Contraseña</label><input id="p" type="password" required minLength={mode === "register" ? 10 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={f.password} onChange={set("password")} className={inputClass} />{mode === "register" && <p className="mt-1 text-xs text-umber">Mínimo 10 caracteres.</p>}</div>
        {mode === "register" && (
          <div className="space-y-2 text-sm">
            <label className="flex items-start gap-3"><input type="checkbox" required checked={f.privacy} onChange={(e) => setF((s) => ({ ...s, privacy: e.target.checked }))} className="mt-1" /><span>Acepto la <Link href="/privacidad" target="_blank" className="underline underline-offset-4">política de privacidad</Link>.</span></label>
            <label className="flex items-start gap-3"><input type="checkbox" required checked={f.terms} onChange={(e) => setF((s) => ({ ...s, terms: e.target.checked }))} className="mt-1" /><span>Acepto los <Link href="/terminos" target="_blank" className="underline underline-offset-4">términos y condiciones</Link>.</span></label>
            <label className="flex items-start gap-3 text-umber"><input type="checkbox" checked={f.marketing} onChange={(e) => setF((s) => ({ ...s, marketing: e.target.checked }))} className="mt-1" /><span>Quiero recibir novedades (opcional).</span></label>
          </div>
        )}
        {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
        <button disabled={busy} className={btnPrimary}>{busy ? "Un momento…" : mode === "login" ? "Ingresar" : "Crear cuenta"}</button>
      </form>
      {mode === "login" && <Link href="/restablecer" className="mt-4 block text-center text-xs uppercase tracking-[0.18em] text-umber underline underline-offset-4">¿Olvidaste tu contraseña?</Link>}
      <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }} className="mt-6 w-full text-center text-xs uppercase tracking-[0.18em] text-umber underline underline-offset-4">
        {mode === "login" ? "¿Primera vez? Crear cuenta" : "Ya tengo cuenta"}
      </button>
      <p className="mt-6 text-center text-xs text-umber">También puedes comprar sin cuenta: te damos un enlace para seguir tu pedido.</p>
    </div>
  );
}
