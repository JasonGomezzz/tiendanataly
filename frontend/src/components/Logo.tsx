/** Marca provisional de Marle Fashion: percha con corazón + nombre. Se reemplaza por el archivo oficial del logo. */
export function LogoMark({ className = "h-8 w-auto" }: { className?: string }) {
  return (
    <svg viewBox="0 0 126 74" className={className} fill="none" aria-hidden="true">
      <path d="M57 24c-1-12 15-13 15-3 0 5-9 6-9 12" stroke="#1a1a1a" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M64 38 25 56c-8 4-6 9 1 8" stroke="#1a1a1a" strokeWidth="3.2" strokeLinecap="round" />
      <path d="m64 38 39 18c8 4 6 9-1 8" stroke="#1a1a1a" strokeWidth="3.2" strokeLinecap="round" />
      <path d="M64 49c-9-5-13-9-13-14 0-4 3-6 7-6 3 0 5 2 6 4 1-2 3-4 6-4 4 0 7 2 7 6 0 5-4 9-13 14Z" fill="#cc8a84" transform="translate(0 -4) scale(1 .9) translate(0 5)" />
    </svg>
  );
}

export function Logo({ name }: { name: string }) {
  const [first, ...rest] = name.split(" ");
  return (
    <span className="inline-flex flex-col items-center leading-none" aria-label={name}>
      <span className="font-serif text-3xl font-semibold tracking-[0.18em] sm:text-4xl">{first.toUpperCase()}</span>
      {rest.length > 0 && <span className="mt-1 text-[9px] font-medium uppercase tracking-[0.5em] text-umber sm:text-[10px]">{rest.join(" ")}</span>}
    </span>
  );
}
