import Image from "next/image";
import type { ProductImage } from "@/lib/types";
import { ImagePlaceholder } from "./ui";

/**
 * Galería de la página de producto.
 * Escritorio: 2 fotos grandes arriba + miniaturas en 3 columnas (como la referencia).
 * Móvil: carrusel horizontal con scroll-snap.
 */
export function Gallery({ images, name }: { images: ProductImage[]; name: string }) {
  if (images.length === 0) {
    return (
      <div className="aspect-4/5 bg-paper">
        <ImagePlaceholder label={name} />
      </div>
    );
  }

  const big = images.slice(0, 2);
  const rest = images.slice(2);

  return (
    <>
      <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto lg:hidden" aria-label={`Fotos de ${name}`}>
        {images.map((img, i) => (
          <div key={img.url} className="relative aspect-4/5 w-[88%] shrink-0 snap-center bg-paper first:ml-0">
            <Image src={img.url} alt={img.alt || name} fill priority={i === 0} sizes="88vw" className="object-cover" />
          </div>
        ))}
      </div>

      <div className="hidden lg:block">
        <div className={`grid gap-2 ${big.length === 1 ? "grid-cols-1" : "grid-cols-2"}`}>
          {big.map((img, i) => (
            <div key={img.url} className="relative aspect-4/5 bg-paper">
              <Image src={img.url} alt={img.alt || name} fill priority={i === 0} sizes="(min-width: 1280px) 400px, 33vw" className="object-cover" />
            </div>
          ))}
        </div>
        {rest.length > 0 && (
          <div className="mt-2 grid grid-cols-3 gap-2">
            {rest.map((img) => (
              <div key={img.url} className="relative aspect-4/5 bg-paper">
                <Image src={img.url} alt={img.alt || name} fill sizes="260px" className="object-cover" />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
