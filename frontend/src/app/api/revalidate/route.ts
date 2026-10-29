import { revalidatePath } from "next/cache";
import { timingSafeEqual } from "node:crypto";

// Django llama aquí al guardar un producto (ISR on-demand). Protegido con un secreto compartido.
export async function POST(request: Request) {
  const expected = process.env.REVALIDATE_SECRET ?? "";
  const received = request.headers.get("x-revalidate-secret") ?? "";
  const a = Buffer.from(expected);
  const b = Buffer.from(received);
  if (!expected || a.length !== b.length || !timingSafeEqual(a, b)) {
    return Response.json({ detail: "forbidden" }, { status: 403 });
  }
  revalidatePath("/", "layout");
  return Response.json({ revalidated: true });
}
