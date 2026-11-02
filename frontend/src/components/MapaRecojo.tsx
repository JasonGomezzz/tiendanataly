import type { StoreInfo } from "@/lib/types";

/**
 * Punto de recojo con mapa de Google. Sin llave solo muestra el enlace «Abrir en Google Maps» (no cuesta nada);
 * con la llave pública del Maps Embed API (restringida por dominio) muestra también el mapa incrustado.
 */
export function MapaRecojo({ store }: { store: Pick<StoreInfo, "punto_recojo_nombre" | "punto_recojo_direccion" | "mapa_embed_key"> | null }) {
  const direccion = store?.punto_recojo_direccion?.trim();
  if (!store || !direccion) return null;

  const abrir = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(direccion)}`;
  const embed = store.mapa_embed_key
    ? `https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(store.mapa_embed_key)}&q=${encodeURIComponent(direccion)}&language=es&region=PE`
    : null;

  return (
    <section className="space-y-3" aria-labelledby="mapa-recojo">
      <h3 id="mapa-recojo" className="font-serif text-xl">Dónde recoger tu pedido</h3>
      <p className="text-sm text-umber">
        {store.punto_recojo_nombre ? <strong className="text-ink">{store.punto_recojo_nombre}</strong> : null}
        {store.punto_recojo_nombre ? " · " : ""}{direccion}
      </p>
      {embed && (
        <iframe
          title={`Mapa: ${store.punto_recojo_nombre || direccion}`}
          src={embed}
          loading="lazy"
          allowFullScreen
          referrerPolicy="no-referrer-when-downgrade"
          className="h-64 w-full border border-stone/40 bg-paper sm:h-72"
        />
      )}
      <a href={abrir} target="_blank" rel="noopener noreferrer" className="inline-block text-xs uppercase tracking-[0.18em] text-umber underline underline-offset-4">
        Abrir en Google Maps
      </a>
    </section>
  );
}
