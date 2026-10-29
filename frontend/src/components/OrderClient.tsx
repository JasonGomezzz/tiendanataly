"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, messageFrom } from "@/lib/client";
import { btnPrimary, inputClass, labelClass } from "./ui";

/** Refresca el seguimiento cada 30 s mientras el pedido espera pago o verificación. */
export function OrderLive({ active }: { active: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => router.refresh(), 30000);
    return () => clearInterval(id);
  }, [active, router]);
  return null;
}

export function ProofUploader({ token }: { token: string }) {
  const router = useRouter();
  const key = useRef(crypto.randomUUID());
  const [metodo, setMetodo] = useState<"yape" | "plin">("yape");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("La imagen supera los 5 MB. Prueba con una captura más liviana.");
      return;
    }
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("comprobante", file);
    form.append("metodo", metodo);
    form.append("idempotency_key", key.current);
    try {
      await api(`/orders/${token}/payments/manual/`, { form });
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? messageFrom(err.data) : "No pudimos subir tu comprobante.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-6 space-y-4 border-t border-stone/40 pt-6">
      <fieldset>
        <legend className={labelClass}>¿Con qué pagaste?</legend>
        <div className="flex gap-3">
          {(["yape", "plin"] as const).map((m) => (
            <label key={m} className={`flex min-h-11 flex-1 cursor-pointer items-center justify-center border text-xs uppercase tracking-widest ${metodo === m ? "border-ink bg-ink text-white" : "border-stone/60"}`}>
              <input type="radio" name="metodo" value={m} checked={metodo === m} onChange={() => setMetodo(m)} className="sr-only" />
              {m}
            </label>
          ))}
        </div>
      </fieldset>
      <div>
        <label htmlFor="comprobante" className={labelClass}>Captura de tu pago</label>
        <input id="comprobante" type="file" accept="image/jpeg,image/png,image/webp" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} className={inputClass} />
        <p className="mt-1 text-xs text-umber">JPG, PNG o WEBP de hasta 5 MB.</p>
      </div>
      {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
      <button disabled={busy || !file} className={btnPrimary}>{busy ? "Subiendo…" : "Enviar comprobante"}</button>
    </form>
  );
}
