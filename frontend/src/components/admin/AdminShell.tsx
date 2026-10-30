"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { Me, Meta } from "@/lib/admin";
import { api, ApiError, messageFrom, resetCsrf } from "@/lib/client";
import { btnPrimary, inputClass, labelClass } from "../ui";

type Ctx = { me: Me; meta: Meta; can: (perm: string) => boolean };
const AdminContext = createContext<Ctx | null>(null);

export function useAdmin() {
  const ctx = useContext(AdminContext);
  if (!ctx) throw new Error("useAdmin debe usarse dentro de AdminShell");
  return ctx;
}

function Login({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState({ email: "", password: "", otp: "" });
  const [needOtp, setNeedOtp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/login/", { json: { email: f.email, password: f.password, otp_token: f.otp } });
      resetCsrf();
      onDone();
    } catch (err) {
      if (err instanceof ApiError && err.data.otp_required) setNeedOtp(true);
      setError(err instanceof ApiError ? (err.status === 429 ? "Demasiados intentos. Espera unos minutos." : messageFrom(err.data)) : "No pudimos conectar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-5">
      <Image src="/brand/logo-640.png" alt="Marle Fashion" width={96} height={96} priority className="mx-auto mb-4 h-24 w-24 rounded-full" />
      <p className="text-center text-[11px] font-medium uppercase tracking-[0.3em] text-rose-text">Panel de administración</p>
      <h1 className="mt-3 text-center font-serif text-4xl">Ingresar</h1>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <div><label htmlFor="e" className={labelClass}>Correo</label><input id="e" type="email" required autoComplete="username" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={inputClass} /></div>
        <div><label htmlFor="p" className={labelClass}>Contraseña</label><input id="p" type="password" required autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} className={inputClass} /></div>
        {needOtp && (
          <div>
            <label htmlFor="o" className={labelClass}>Código de tu app de autenticación</label>
            <input id="o" inputMode="numeric" autoComplete="one-time-code" maxLength={8} required value={f.otp} onChange={(e) => setF({ ...f, otp: e.target.value })} className={inputClass} />
          </div>
        )}
        {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
        <button disabled={busy} className={btnPrimary}>{busy ? "Verificando…" : "Entrar"}</button>
      </form>
    </main>
  );
}

const TABS = [
  { href: "/admin", label: "Inicio", icon: "◧", perm: null },
  { href: "/admin/pedidos", label: "Pedidos", icon: "▤", perm: "orders.change_order" },
  { href: "/admin/productos", label: "Productos", icon: "▣", perm: null },
  { href: "/admin/calculadora", label: "Precio", icon: "＄", perm: "catalog.ver_finanzas" },
  { href: "/admin/ajustes", label: "Ajustes", icon: "⚙", perm: "core.change_storesettings" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [state, setState] = useState<{ me: Me; meta: Meta } | null | undefined>(undefined);

  const load = useCallback(async () => {
    try {
      const [me, meta] = await Promise.all([api<Me>("/admin/me/"), api<Meta>("/admin/meta/")]);
      setState({ me, meta });
    } catch {
      setState(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function logout() {
    await api("/auth/logout/", { method: "POST", json: {} }).catch(() => undefined);
    resetCsrf();
    setState(null);
  }

  if (state === undefined) return <div className="flex min-h-screen items-center justify-center text-umber">Cargando…</div>;
  if (state === null) return <Login onDone={load} />;

  const { me, meta } = state;
  const can = (perm: string) => !!me.permisos[perm] || me.rol === "superusuario";
  const tabs = TABS.filter((t) => !t.perm || can(t.perm));

  return (
    <AdminContext.Provider value={{ me, meta, can }}>
      <div className="min-h-screen bg-paper pb-24 md:pb-0 md:pl-56">
        <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-stone/40 bg-white p-5 md:flex">
          <p className="font-serif text-2xl">Panel</p>
          <p className="mt-1 text-xs text-umber">{me.nombre} · {me.rol}</p>
          <nav className="mt-8 flex flex-col gap-1">
            {tabs.map((t) => (
              <Link key={t.href} href={t.href} className={`px-3 py-3 text-xs font-medium uppercase tracking-[0.16em] ${pathname === t.href || (t.href !== "/admin" && pathname.startsWith(t.href)) ? "bg-ink text-white" : "text-umber hover:bg-paper"}`}>
                {t.label}
              </Link>
            ))}
          </nav>
          <div className="mt-auto space-y-2 text-xs">
            <Link href="/" target="_blank" className="block text-umber underline underline-offset-4">Ver la tienda</Link>
            <button onClick={logout} className="text-umber underline underline-offset-4">Cerrar sesión</button>
          </div>
        </aside>

        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-stone/40 bg-white px-4 py-3 md:hidden">
          <span className="font-serif text-xl">Panel</span>
          <button onClick={logout} className="text-[11px] uppercase tracking-widest text-umber">Salir</button>
        </header>

        <main className="mx-auto max-w-5xl px-4 py-6 sm:px-8">{children}</main>

        <nav aria-label="Secciones" className="fixed inset-x-0 bottom-0 z-30 grid border-t border-stone/40 bg-white md:hidden" style={{ gridTemplateColumns: `repeat(${tabs.length}, 1fr)` }}>
          {tabs.map((t) => {
            const active = pathname === t.href || (t.href !== "/admin" && pathname.startsWith(t.href));
            return (
              <Link key={t.href} href={t.href} className={`flex min-h-16 flex-col items-center justify-center gap-0.5 text-[10px] uppercase tracking-wider ${active ? "text-ink" : "text-umber"}`}>
                <span aria-hidden className="text-lg leading-none">{t.icon}</span>
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </AdminContext.Provider>
  );
}
