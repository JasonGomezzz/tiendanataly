"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, messageFrom } from "@/lib/client";
import { btnPrimary } from "./ui";

declare global {
  interface Window {
    Culqi?: {
      publicKey: string;
      settings: (s: Record<string, unknown>) => void;
      options: (o: Record<string, unknown>) => void;
      open: () => void;
      close: () => void;
      token?: { id: string; email?: string };
      error?: { user_message?: string };
    };
    culqi?: () => void;
  }
}

// Script oficial de Culqi Checkout v4 (la documentación avisa que se reemplazará por Checkout Custom: ver docs/pagos-culqi.md).
const SCRIPT = "https://checkout.culqi.com/js/v4";

/** Pago con tarjeta: el navegador habla con Culqi y solo el token llega a nuestro servidor (SAQ-A). */
export function CulqiPay({ token, publicKey, amount, storeName }: { token: string; publicKey: string; amount: string; storeName: string }) {
  const router = useRouter();
  const key = useRef(crypto.randomUUID());
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const el = document.createElement("script");
    el.src = SCRIPT;
    el.async = true;
    el.onload = () => setReady(true);
    el.onerror = () => setError("No pudimos cargar el pago con tarjeta. Usa Yape o Plin.");
    document.body.appendChild(el);

    window.culqi = async () => {
      const culqi = window.Culqi;
      if (culqi?.token) {
        culqi.close();
        setBusy(true);
        setError(null);
        try {
          await api(`/orders/${token}/payments/culqi/charge/`, { json: { token_id: culqi.token.id, email: culqi.token.email ?? "", idempotency_key: key.current } });
          router.refresh();
        } catch (e) {
          key.current = crypto.randomUUID(); // un nuevo intento = nueva clave
          setError(e instanceof ApiError ? messageFrom(e.data) || "No pudimos procesar el pago." : "No pudimos procesar el pago.");
        } finally {
          setBusy(false);
        }
      } else if (culqi?.error) {
        setError(culqi.error.user_message ?? "No pudimos procesar el pago.");
      }
    };
    return () => {
      delete window.culqi;
      el.remove();
    };
  }, [token, router]);

  function open() {
    const culqi = window.Culqi;
    if (!culqi) return;
    culqi.publicKey = publicKey;
    culqi.settings({ title: storeName, currency: "PEN", amount: Math.round(Number(amount) * 100) }); // céntimos
    culqi.options({ lang: "auto", installments: false, paymentMethods: { tarjeta: true } });
    culqi.open();
  }

  return (
    <div className="mt-4">
      <button type="button" disabled={!ready || busy} onClick={open} className={btnPrimary}>
        {busy ? "Procesando…" : "Pagar con tarjeta"}
      </button>
      {error && <p role="alert" className="mt-3 text-sm text-rose-text">{error}</p>}
    </div>
  );
}
