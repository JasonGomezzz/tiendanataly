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

/** Sube la captura del pago. El medio (Yape, Plin o transferencia) lo define quien la usa. */
export function ProofUploader({ token, metodo, banco = "" }: { token: string; metodo: "yape" | "plin" | "transferencia"; banco?: string }) {
  const router = useRouter();
  const key = useRef(crypto.randomUUID());
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
    if (banco) form.append("banco", banco);
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
      <div>
        <label htmlFor="comprobante" className={labelClass}>Sube la captura de tu pago</label>
        <input id="comprobante" type="file" accept="image/jpeg,image/png,image/webp" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} className={inputClass} />
        <p className="mt-1 text-xs text-umber">JPG, PNG o WEBP de hasta 5 MB. Verificamos tu pago y te avisamos.</p>
      </div>
      {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
      <button disabled={busy || !file} className={btnPrimary}>{busy ? "Subiendo…" : "Enviar comprobante"}</button>
    </form>
  );
}
