import type { Metadata } from "next";
import { LegalPage } from "@/components/Legal";

export const metadata: Metadata = { title: "Política de privacidad" };

export default function Privacy() {
  return (
    <LegalPage title="Política de privacidad">
      <section>
        <h2>Responsable del tratamiento</h2>
        <p>La tienda (titular: <strong>[nombre completo de la titular]</strong>, persona natural) trata tus datos personales conforme a la Ley N.° 29733, Ley de Protección de Datos Personales, y su reglamento.</p>
      </section>
      <section>
        <h2>Qué datos recogemos</h2>
        <ul>
          <li>Nombre, teléfono y, opcionalmente, correo electrónico.</li>
          <li>Dirección de entrega (solo si tu pedido se envía).</li>
          <li>Comprobantes de pago que tú subes (capturas de Yape/Plin).</li>
        </ul>
        <p>No recogemos más datos de los necesarios. Nunca recibimos ni guardamos datos de tu tarjeta: el pago con tarjeta lo procesa la pasarela.</p>
      </section>
      <section>
        <h2>Para qué los usamos</h2>
        <ul>
          <li>Gestionar tu pedido, la entrega y la atención posventa.</li>
          <li>Avisarte por WhatsApp sobre el estado de tu pedido.</li>
          <li>Enviarte novedades, solo si lo aceptaste expresamente (puedes retirarlo cuando quieras).</li>
        </ul>
      </section>
      <section>
        <h2>Tus derechos</h2>
        <p>Puedes acceder, rectificar, cancelar u oponerte al tratamiento de tus datos. Desde tu cuenta puedes eliminar tus datos personales; tus pedidos se conservan de forma anónima por obligaciones contables. También puedes escribirnos por WhatsApp.</p>
      </section>
      <section>
        <h2>Seguridad y conservación</h2>
        <p>Protegemos tus datos con medidas técnicas y de acceso restringido. Los conservamos mientras sean necesarios para las finalidades indicadas y las obligaciones legales.</p>
      </section>
    </LegalPage>
  );
}
