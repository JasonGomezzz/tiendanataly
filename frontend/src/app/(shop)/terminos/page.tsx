import type { Metadata } from "next";
import { LegalPage } from "@/components/Legal";

export const metadata: Metadata = { title: "Términos y condiciones" };

export default function Terms() {
  return (
    <LegalPage title="Términos y condiciones">
      <section>
        <h2>Quiénes somos</h2>
        <p>Tienda independiente de importación y venta de bolsos, mochilas y fragancias con entrega en Lima, Perú. No estamos afiliados a Victoria&apos;s Secret ni a otras marcas; sus nombres se usan solo para identificar los productos que vendemos. Titular: <strong>[nombre completo de la titular]</strong>, persona natural sin RUC, Lima, Perú.</p>
      </section>
      <section>
        <h2>Precios y pagos</h2>
        <p>Los precios están en soles (S/). Aceptamos Yape, Plin y transferencia bancaria (BCP e Interbank) y, cuando esté habilitado, tarjeta. El total, incluido el envío, se confirma al crear tu pedido. Un pedido se considera pagado cuando verificamos tu comprobante.</p>
      </section>
      <section>
        <h2>Reserva de productos</h2>
        <p>Al confirmar tu pedido reservamos las unidades por un tiempo limitado. Si no recibimos tu pago en ese plazo, la reserva se libera y el pedido vence. Si pagaste después de que venciera, te avisaremos si aún hay stock o te devolveremos tu dinero.</p>
      </section>
      <section>
        <h2>Disponibilidad</h2>
        <p>Trabajamos con pocas unidades por modelo. Si por un error de inventario no pudiéramos entregar un producto pagado, te ofreceremos una alternativa o la devolución total.</p>
      </section>
      <section>
        <h2>Entrega</h2>
        <p>Entregamos en Lima por delivery o recojo y a provincias mediante courier. Los plazos y costos se muestran al elegir la entrega.</p>
      </section>
      <section>
        <h2>Cambios, devoluciones y reclamos</h2>
        <p>Consulta la política de cambios y devoluciones y el Libro de reclamaciones virtual disponibles en el pie de página.</p>
      </section>
    </LegalPage>
  );
}
