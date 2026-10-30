import Image from "next/image";
import type { ProductImage } from "@/lib/types";
import { ImagePlaceholder } from "./ui";

/**
 * Galería de la página de producto.
 * Escritorio: 2 fotos grandes arriba + miniaturas en 3 columnas (como la referencia).
 * Móvil: carrusel horizontal con scroll-snap.
 * Es un solo bloque de fotos para los dos tamaños: así la foto principal se descarga una sola vez y con prioridad alta.
 */
export function Gallery({ images, name }: { images: ProductImage[]; name: string }) {
  if (images.length === 0) {
    return (
      <div className="aspect-4/5 bg-paper">
        <ImagePlaceholder label={name} />
      </div>
    );
  }

  const span = (i: number) => (i >= 2 ? "lg:col-span-2" : images.length === 1 ? "lg:col-span-6" : "lg:col-span-3");

  return (
    <div
      role="group"
      aria-label={`Fotos de ${name}`}
      className="flex snap-x snap-mandatory gap-2 overflow-x-auto lg:grid lg:grid-cols-6 lg:snap-none lg:overflow-visible"
    >
      {images.map((img, i) => (
        <div key={img.url} className={`relative aspect-4/5 shrink-0 snap-center bg-paper lg:w-auto lg:shrink ${images.length === 1 ? "w-full" : "w-[88%]"} ${span(i)}`}>
          <Image
            src={img.url}
            alt={img.alt || name}
            fill
            priority={i === 0}
            fetchPriority={i === 0 ? "high" : undefined}
            sizes={i < 2 ? "(min-width: 1280px) 400px, (min-width: 1024px) 33vw, 88vw" : "(min-width: 1024px) 260px, 88vw"}
            className="object-cover"
          />
        </div>
      ))}
    </div>
  );
}
