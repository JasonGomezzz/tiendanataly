"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui";
import { api, ApiError, messageFrom } from "@/lib/client";

function Form() {
  const params = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"idle" | "sent" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (uid && token) {
        await api("/auth/password/reset/confirm/", { json: { uid, token, password } });
        setState("done");
      } else {
        await api("/auth/password/reset/", { json: { email } });
        setState("sent");
      }
    } catch (err) {
      setError(err instanceof ApiError ? messageFrom(err.data) : "No pudimos completar la solicitud.");
    } finally {
      setBusy(false);
    }
  }

  if (state === "sent") return <p className="mt-8 text-umber">Si el correo tiene una cuenta, te enviamos un enlace para elegir una nueva contraseña. Revisa también tu carpeta de spam.</p>;
  if (state === "done") return <p className="mt-8">Listo, tu contraseña se actualizó. <Link href="/cuenta" className="underline underline-offset-4">Ingresar</Link></p>;

  return (
    <form onSubmit={submit} className="mt-8 space-y-4">
      {uid && token ? (
        <div><label htmlFor="p" className={labelClass}>Nueva contraseña</label><input id="p" type="password" required minLength={10} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} /><p className="mt-1 text-xs text-umber">Mínimo 10 caracteres.</p></div>
      ) : (
        <div><label htmlFor="e" className={labelClass}>Tu correo</label><input id="e" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} /></div>
      )}
      {error && <p role="alert" className="text-sm text-rose-text">{error}</p>}
      <button disabled={busy} className={btnPrimary}>{busy ? "Un momento…" : uid && token ? "Guardar contraseña" : "Enviar enlace"}</button>
    </form>
  );
}

export default function ResetPage() {
  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="font-serif text-4xl">Recuperar contraseña</h1>
      <Suspense fallback={null}><Form /></Suspense>
    </div>
  );
}
