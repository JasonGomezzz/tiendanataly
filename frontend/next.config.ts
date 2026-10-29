import type { NextConfig } from "next";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Django exige la barra final en sus URLs; sin esto Next la quita y se forma un bucle de redirecciones.
  skipTrailingSlashRedirect: true,
  images: {
    // Las fotos viven en el backend (/media) y se piden a través de Next.
    localPatterns: [{ pathname: "/media/**" }],
    remotePatterns: [{ protocol: "https", hostname: "res.cloudinary.com" }],
    formats: ["image/avif", "image/webp"],
    qualities: [60, 75],
  },
  // El navegador habla solo con Next; así las cookies de sesión de Django quedan same-site.
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
