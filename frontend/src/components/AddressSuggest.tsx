"use client";

import { useEffect, useId, useRef, useState } from "react";
import { api } from "@/lib/client";
import { inputClass } from "./ui";

export type PickedAddress = { direccion: string; distrito: string; provincia: string; departamento: string };
type Suggestion = { id: string; texto: string; principal: string; secundario: string };

const MIN_CHARS = 4;
const DEBOUNCE_MS = 450;

/**
 * Campo «Dirección» con sugerencias de Google (a través de nuestro servidor, nunca desde el navegador).
 * - Una sesión de búsqueda (UUID) por dirección: Google cobra la sesión completa y no cada tecla.
 * - Si el buscador falla, se acaba el tope diario o no está activo, el campo es un input normal y la clienta escribe a mano.
 */
export function AddressSuggest({ id, value, onChange, onPick, enabled }: {
  id: string;
  value: string;
  onChange: (text: string) => void;
  onPick: (address: PickedAddress) => void;
  enabled: boolean;
}) {
  const listId = useId();
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const session = useRef<string>("");
  const typed = useRef(false); // solo se busca cuando la clienta escribe, no cuando se rellena sola
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!enabled || !typed.current) return;
    const q = value.trim();
    if (q.length < MIN_CHARS) {
      setItems([]);
      return;
    }
    if (!session.current) session.current = crypto.randomUUID();
    let cancelled = false;
    const timer = setTimeout(() => {
      api<{ sugerencias: Suggestion[] }>(`/places/autocomplete/?q=${encodeURIComponent(q)}&session=${session.current}`)
        .then((r) => {
          if (cancelled) return;
          setItems(r.sugerencias);
          setOpen(r.sugerencias.length > 0);
          setActive(-1);
        })
        .catch(() => !cancelled && setItems([]));
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [value, enabled]);

  useEffect(() => {
    const away = (e: PointerEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, []);

  async function pick(s: Suggestion) {
    setOpen(false);
    typed.current = false;
    onChange(s.principal);
    try {
      const place = await api<PickedAddress>(`/places/detail/?id=${encodeURIComponent(s.id)}&session=${session.current}`);
      onPick({ direccion: place.direccion || s.principal, distrito: place.distrito, provincia: place.provincia, departamento: place.departamento });
    } catch {
      /* si falla el detalle queda la dirección escrita y la clienta completa el resto */
    }
    session.current = ""; // la sesión terminó con la consulta del lugar: la próxima búsqueda empieza otra
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      void pick(items[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={box} className="relative">
      <input
        id={id}
        required
        autoComplete={enabled ? "off" : "street-address"}
        value={value}
        onChange={(e) => {
          typed.current = true;
          onChange(e.target.value);
        }}
        onKeyDown={onKeyDown}
        className={inputClass}
        role={enabled ? "combobox" : undefined}
        aria-expanded={enabled ? open : undefined}
        aria-controls={enabled ? listId : undefined}
        aria-autocomplete={enabled ? "list" : undefined}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
      />
      {enabled && open && items.length > 0 && (
        <ul id={listId} role="listbox" className="absolute z-30 mt-1 max-h-64 w-full overflow-auto border border-stone/60 bg-white shadow-lg">
          {items.map((s, i) => (
            <li
              key={s.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onPointerDown={(e) => {
                e.preventDefault();
                void pick(s);
              }}
              className={`cursor-pointer px-4 py-3 text-sm ${i === active ? "bg-blush" : "hover:bg-paper"}`}
            >
              <span className="block text-ink">{s.principal}</span>
              {s.secundario && <span className="block text-xs text-umber">{s.secundario}</span>}
            </li>
          ))}
          <li className="px-4 py-2 text-[10px] uppercase tracking-widest text-umber" aria-hidden="true">Sugerencias de Google</li>
        </ul>
      )}
    </div>
  );
}
