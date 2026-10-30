"use client";

import { useState } from "react";
import { money } from "@/lib/format";
import type { BankAccount, StoreInfo } from "@/lib/types";
import { CulqiPay } from "./CulqiPay";
import { ProofUploader } from "./OrderClient";
import { PayLogo, type PayKind } from "./PayLogo";

type Method =
  | { id: string; kind: "yape" | "plin"; label: string; subtitle: string; number: string; holder: string }
  | { id: string; kind: PayKind; label: string; subtitle: string; account: BankAccount }
  | { id: "tarjeta"; kind: "tarjeta"; label: string; subtitle: string };

const BANK_KIND: Record<string, PayKind> = { bcp: "bcp", interbank: "interbank" };
const BANK_NAME: Record<string, string> = { bcp: "BCP", interbank: "Interbank", bbva: "BBVA", scotiabank: "Scotiabank", otro: "Banco" };

function buildMethods(store: StoreInfo): Method[] {
  const list: Method[] = [];
  if (store.yape_numero) list.push({ id: "yape", kind: "yape", label: "Pagar con Yape", subtitle: "Desde tu celular", number: store.yape_numero, holder: store.yape_titular });
  if (store.plin_numero) list.push({ id: "plin", kind: "plin", label: "Pagar con Plin", subtitle: "Desde tu banco", number: store.plin_numero, holder: store.plin_titular });
  for (const account of store.cuentas ?? []) {
    list.push({ id: `bank-${account.id}`, kind: BANK_KIND[account.banco] ?? "otro", label: `Transferencia ${BANK_NAME[account.banco] ?? account.banco}`, subtitle: account.etiqueta || "Cuenta en soles", account });
  }
  if (store.payments_provider === "culqi" && store.culqi_public_key) list.push({ id: "tarjeta", kind: "tarjeta", label: "Pagar con tarjeta", subtitle: "Crédito o débito", });
  return list;
}

function Copy({ value, label }: { value: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      aria-label={`Copiar ${label}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value.replace(/\s/g, ""));
          setDone(true);
          setTimeout(() => setDone(false), 2000);
        } catch {
          /* sin permiso de portapapeles: la clienta puede copiar el número a mano */
        }
      }}
      className="min-h-11 shrink-0 border border-ink px-3 text-[11px] font-medium uppercase tracking-[0.14em] hover:bg-ink hover:text-white"
    >
      {done ? "Copiado ✓" : "Copiar"}
    </button>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 bg-paper px-4 py-3">
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-[0.16em] text-umber">{label}</p>
        <p className="mt-0.5 break-all text-lg tabular-nums">{value}</p>
      </div>
      <Copy value={value} label={label} />
    </div>
  );
}

/** «Elige cómo pagar»: una tarjeta por medio de pago con su imagen de referencia y las instrucciones. */
export function PayMethods({ token, store, amount, whatsappUrl }: { token: string; store: StoreInfo; amount: string; whatsappUrl: string | null }) {
  const methods = buildMethods(store);
  const [selected, setSelected] = useState<string | null>(methods.length === 1 ? methods[0].id : null);
  const current = methods.find((m) => m.id === selected) ?? null;

  if (methods.length === 0) {
    return (
      <p className="mt-4 text-sm text-umber">
        Escríbenos por WhatsApp y te enviamos los datos de pago.{" "}
        {whatsappUrl && <a href={whatsappUrl} className="underline underline-offset-4">Abrir WhatsApp</a>}
      </p>
    );
  }

  return (
    <div className="mt-5">
      <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-umber">Elige cómo quieres pagar</p>
      <div role="group" aria-label="Medios de pago" className="mt-3 grid gap-3 sm:grid-cols-2">
        {methods.map((m) => (
          <button
            key={m.id}
            type="button"
            aria-pressed={selected === m.id}
            onClick={() => setSelected(m.id)}
            className={`flex min-h-20 items-center gap-4 border p-3 text-left transition-colors ${selected === m.id ? "border-ink bg-paper" : "border-stone/60 hover:border-ink"}`}
          >
            <PayLogo kind={m.kind} label={m.label} />
            <span>
              <span className="block text-sm font-medium uppercase tracking-wide">{m.label}</span>
              <span className="block text-xs text-umber">{m.subtitle}</span>
            </span>
          </button>
        ))}
      </div>

      {current && (
        <div className="mt-6 space-y-3" aria-live="polite">
          <p className="text-sm">
            Monto exacto a pagar: <strong className="text-lg">{money(amount)}</strong>
          </p>

          {(current.kind === "yape" || current.kind === "plin") && "number" in current && (
            <>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-umber">
                <li>Abre {current.kind === "yape" ? "Yape" : "Plin"} y elige <em>Yapear</em>/<em>Enviar</em> a un número.</li>
                <li>Pega este número y envía {money(amount)}.</li>
                <li>Toma una captura del comprobante y súbela aquí abajo.</li>
              </ol>
              <Row label={`Número de ${current.kind === "yape" ? "Yape" : "Plin"}`} value={current.number} />
              {current.holder && <p className="text-xs text-umber">A nombre de {current.holder}</p>}
              <ProofUploader token={token} metodo={current.kind} />
            </>
          )}

          {"account" in current && (
            <>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-umber">
                <li>Desde tu app o banca por internet, transfiere {money(amount)} a la cuenta de abajo.</li>
                <li>Si transfieres desde otro banco, usa el <strong>CCI</strong>.</li>
                <li>Sube la captura de la operación aquí abajo.</li>
              </ol>
              <Row label={`Cuenta ${BANK_NAME[current.account.banco] ?? ""}`} value={current.account.numero} />
              {current.account.cci && <Row label="CCI (otros bancos)" value={current.account.cci} />}
              {current.account.titular && <p className="text-xs text-umber">Titular: {current.account.titular}</p>}
              <ProofUploader token={token} metodo="transferencia" banco={BANK_NAME[current.account.banco] ?? current.account.banco} />
            </>
          )}

          {current.id === "tarjeta" && <CulqiPay token={token} publicKey={store.culqi_public_key} amount={amount} storeName={store.nombre_tienda} />}
        </div>
      )}
    </div>
  );
}
