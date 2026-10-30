import type { MetadataRoute } from "next";
import { SITE } from "@/lib/format";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/checkout", "/bolsa", "/cuenta", "/pedido/", "/api/", "/admin"] }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
