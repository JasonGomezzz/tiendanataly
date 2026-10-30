"use client";

import { useEffect, useState } from "react";
import { api, ApiError, messageFrom } from "@/lib/client";
import { inputClass, labelClass } from "../ui";

type Account = { id?: number; banco: string; etiqueta: string; numero: string; cci: string; titular: string; activa: boolean; orden: number };

const BANKS = [
  ["bcp", "BCP"],
  ["interbank", "Interbank"],
  ["bbva", "BBVA"],
  ["scotiabank", "Scotiabank"],
  ["otro", "Otro"],
];
const EMPTY: Account = { banco: "bcp", etiqueta: "", numero: "", cci: "", titular: "", activa: true, orden: 0 };

/** Cuentas para transferencias: la administradora las agrega, edita o desactiva sin pedir ayuda. */
export function BankAccounts() {
  const [rows, setRows] = useState<Account[] | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = () => api<Account[]>("/admin/bank-accounts/").then(setRows).catch(() => setRows([]));
  useEffect(() => {
    void load();
  }, []);

  const set = (i: number, patch: Partial<Account>) => setRows((r) => (r ?? []).map((a, j) => (j === i ? { ...a, ...patch } : a)));

  async function save(a: Account) {
    try {
      if (a.id) await api(`/admin/bank-accounts/${a.id}/`, { method: "PATCH", json: a });
      else await api("/admin/bank-accounts/", { json: a });
      setMsg({ ok: true, text: "Cuenta guardada." });
      await load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? messageFrom(e.data) || "Revisa los datos de la cuenta." : "No pudimos guardar." });
    }
  }

  async function remove(a: Account) {
    if (!a.id) return setRows((r) => (r ?? []).filter((x) => x !== a));
    if (!confirm("¿Eliminar esta cuenta? Dejará de mostrarse a las clientas.")) return;
    await api(`/admin/bank-accounts/${a.id}/`, { method: "DELETE" }).catch(() => undefined);
    await load();
  }

  if (rows === null) return <p className="text-umber">Cargando…</p>;

  return (
    <section className="space-y-4" aria-labelledby="cuentas">
      <h2 id="cuentas" className="font-serif text-2xl">Cuentas para transferencias</h2>
      <p className="text-sm text-umber">Se muestran a la clienta cuando elige pagar por transferencia. Incluye el CCI para quien transfiere desde otro banco.</p>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`border px-4 py-3 text-sm ${msg.ok ? "border-stone/50 bg-paper" : "border-rose bg-blush"}`}>{msg.text}</p>}
      {rows.map((a, i) => (
        <div key={a.id ?? `n${i}`} className="space-y-3 border border-stone/40 bg-white p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className={labelClass} htmlFor={`b${i}`}>Banco</label>
              <select id={`b${i}`} value={a.banco} onChange={(e) => set(i, { banco: e.target.value })} className={inputClass}>{BANKS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
            <div><label className={labelClass} htmlFor={`e${i}`}>Descripción</label><input id={`e${i}`} value={a.etiqueta} onChange={(e) => set(i, { etiqueta: e.target.value })} className={inputClass} placeholder="Cuenta de ahorros soles" /></div>
            <div><label className={labelClass} htmlFor={`n${i}`}>Número de cuenta</label><input id={`n${i}`} inputMode="numeric" value={a.numero} onChange={(e) => set(i, { numero: e.target.value })} className={inputClass} /></div>
            <div><label className={labelClass} htmlFor={`c${i}`}>CCI</label><input id={`c${i}`} inputMode="numeric" value={a.cci} onChange={(e) => set(i, { cci: e.target.value })} className={inputClass} /></div>
            <div className="sm:col-span-2"><label className={labelClass} htmlFor={`t${i}`}>Titular</label><input id={`t${i}`} value={a.titular} onChange={(e) => set(i, { titular: e.target.value })} className={inputClass} /></div>
          </div>
          <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={a.activa} onChange={(e) => set(i, { activa: e.target.checked })} /> Mostrar a las clientas</label>
          <div className="flex gap-2">
            <button type="button" onClick={() => save(a)} className="min-h-12 flex-1 bg-ink text-xs font-medium uppercase tracking-[0.16em] text-white">Guardar</button>
            <button type="button" onClick={() => remove(a)} className="min-h-12 px-4 text-xs uppercase tracking-widest text-umber underline underline-offset-4">Eliminar</button>
          </div>
        </div>
      ))}
      <button type="button" onClick={() => setRows((r) => [...(r ?? []), { ...EMPTY, orden: (r ?? []).length + 1 }])} className="min-h-12 w-full border border-ink text-xs font-medium uppercase tracking-[0.16em]">+ Agregar cuenta</button>
    </section>
  );
}
