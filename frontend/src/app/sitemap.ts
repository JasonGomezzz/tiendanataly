import type { MetadataRoute } from "next";
import { getProducts } from "@/lib/api";
import { SITE } from "@/lib/format";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const data = await getProducts({ page_size: "200" });
  const products = (data?.results ?? []).map((p) => ({
    url: `${SITE}/producto/${p.slug}`,
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));
  const pages = ["", "/tienda", "/cambios-y-devoluciones", "/terminos", "/privacidad", "/libro-de-reclamaciones"].map((path) => ({
    url: `${SITE}${path}`,
    priority: path === "" ? 1 : 0.5,
  }));
  return [...pages, ...products];
}
