import path from "node:path";
import type { NextConfig } from "next";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const isProd = process.env.NODE_ENV === "production";

// CSP solo en producción (el modo desarrollo de Next necesita eval). Culqi Checkout y su API se permiten
// por dominio; 'unsafe-inline' es necesario para los scripts en línea de Next sin nonces.
const csp = [
  "default-src 'self'",
  "img-src 'self' data: blob: https://res.cloudinary.com https://*.culqi.com",
  "script-src 'self' 'unsafe-inline' https://checkout.culqi.com https://*.culqi.com",
  "style-src 'self' 'unsafe-inline' https://*.culqi.com",
  "font-src 'self' data: https://*.culqi.com",
  "connect-src 'self' https://*.culqi.com",
  "frame-src https://*.culqi.com",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  ...(isProd ? [{ key: "Content-Security-Policy", value: csp }] : []),
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname),
  // Django exige la barra final en sus URLs; sin esto Next la quita y se forma un bucle de redirecciones.
  skipTrailingSlashRedirect: true,
  images: {
    // Las fotos viven en el backend (/media) y se piden a través de Next.
    localPatterns: [{ pathname: "/media/**" }, { pathname: "/brand/**" }],
    remotePatterns: [{ protocol: "https", hostname: "res.cloudinary.com" }],
    formats: ["image/avif", "image/webp"],
    qualities: [60, 75],
  },
  // En desarrollo el navegador habla solo con Next y este lo reenvía a Django (cookies same-site).
  // En producción Caddy enruta /api, /media y /static directo al backend.
  async rewrites() {
    return [
      // Con barra final (Django la exige) y sin ella.
      { source: "/api/v1/:path*/", destination: `${API}/api/v1/:path*/` },
      { source: "/api/v1/:path*", destination: `${API}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
