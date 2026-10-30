/** Nombre de la marca en texto, junto al logo oficial (frontend/public/brand/logo.png). */
export function Logo({ name }: { name: string }) {
  const [first, ...rest] = name.split(" ");
  return (
    <span className="inline-flex flex-col items-center leading-none" aria-label={name}>
      <span className="font-serif text-2xl font-semibold tracking-[0.18em] sm:text-4xl">{first.toUpperCase()}</span>
      {rest.length > 0 && <span className="mt-1 text-[9px] font-medium uppercase tracking-[0.5em] text-umber sm:text-[10px]">{rest.join(" ")}</span>}
    </span>
  );
}
