/**
 * Imagen de referencia de cada medio de pago. Son insignias propias con el color de cada marca
 * (no los logos oficiales). Si la dueña consigue los logos oficiales, basta reemplazar este componente.
 */
export type PayKind = "yape" | "plin" | "bcp" | "interbank" | "tarjeta" | "otro";

const STYLE: Record<PayKind, { bg: string; text: string }> = {
  yape: { bg: "#742284", text: "Yape" },
  plin: { bg: "linear-gradient(135deg,#00c9e0,#2d6df6)", text: "plin" },
  bcp: { bg: "#002a8d", text: "BCP" },
  interbank: { bg: "#00a651", text: "Interbank" },
  tarjeta: { bg: "#1c1410", text: "" },
  otro: { bg: "#605b51", text: "Banco" },
};

export function PayLogo({ kind, size = 56, label }: { kind: PayKind; size?: number; label?: string }) {
  const s = STYLE[kind];
  return (
    <span
      role="img"
      aria-label={label ?? s.text ?? kind}
      className="relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-xl font-semibold text-white"
      style={{ width: size, height: size, background: s.bg, fontSize: size * (s.text.length > 5 ? 0.17 : 0.27) }}
    >
      {kind === "tarjeta" ? (
        <svg viewBox="0 0 32 24" width={size * 0.62} aria-hidden="true" fill="none">
          <rect x="1" y="2" width="30" height="20" rx="3" stroke="#fff" strokeWidth="2" />
          <rect x="1" y="7" width="30" height="4" fill="#fff" />
          <rect x="5" y="15" width="8" height="2" rx="1" fill="#fff" />
        </svg>
      ) : (
        <span className={kind === "plin" ? "lowercase tracking-tight" : ""}>{s.text}</span>
      )}
      {kind === "bcp" && <span className="absolute inset-x-0 bottom-0 h-[10%] bg-[#ff7800]" />}
    </span>
  );
}
