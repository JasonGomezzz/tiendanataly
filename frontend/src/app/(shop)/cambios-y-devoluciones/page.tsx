import type { Metadata } from "next";
import { LegalPage } from "@/components/Legal";

export const metadata: Metadata = { title: "Cambios y devoluciones" };

export default function Returns() {
  return (
    <LegalPage title="Cambios y devoluciones">
      <section>
        <h2>Cuándo puedes pedir un cambio</h2>
        <ul>
          <li>Si el producto llegó con una falla de fábrica o distinto a lo que compraste.</li>
          <li>Dentro de los <strong>[7] días calendario</strong> desde que recibes tu pedido (plazo por confirmar).</li>
          <li>Sin uso, con sus etiquetas y empaque originales.</li>
        </ul>
      </section>
      <section>
        <h2>Fragancias y cuidado corporal</h2>
        <p>Por higiene, las fragancias y cremas solo tienen cambio si llegaron dañadas o derramadas y se reportan con fotos al recibirlas.</p>
      </section>
      <section>
        <h2>Pedidos por encargo</h2>
        <p>El adelanto confirma el encargo. Si cancelas antes de que compremos el producto, devolvemos el adelanto descontando comisiones de pago. Una vez comprado, el adelanto no es reembolsable salvo falla del producto.</p>
      </section>
      <section>
        <h2>Cómo solicitarlo</h2>
        <p>Escríbenos por WhatsApp con tu número de pedido y fotos del producto. Te responderemos con los pasos a seguir. También puedes usar el Libro de reclamaciones.</p>
      </section>
    </LegalPage>
  );
}
