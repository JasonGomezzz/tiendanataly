// Prueba de carga con k6. Dos escenarios:
//  1) navegación: 40 visitantes simultáneos viendo home, catálogo y productos
//  2) ultima_unidad: 30 compradoras intentan comprar LA ÚLTIMA unidad del mismo producto a la vez
//
// Ejecutar (con la tienda levantada; BASE sin barra final):
//   docker run --rm -i -e BASE=https://host.docker.internal:8443 -e SLUG=mochila-negra-acolchada \
//     grafana/k6 run - < loadtest/k6-tienda.js
//
// IMPORTANTE: subir los límites por IP solo en el entorno de prueba (THROTTLE_CHECKOUT=1000/min, etc.),
// porque todas las visitas de k6 salen de la misma IP.
import http from "k6/http";
import { check, group, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE = __ENV.BASE || "https://localhost:8443";
const SLUG = __ENV.SLUG || "mochila-negra-acolchada";
export const options = {
  insecureSkipTLSVerify: true,
  scenarios: {
    navegacion: { executor: "constant-vus", vus: 40, duration: "30s", exec: "browse" },
    ultima_unidad: { executor: "per-vu-iterations", vus: 30, iterations: 1, exec: "lastUnit", startTime: "5s", maxDuration: "30s" },
  },
  thresholds: {
    "http_req_duration{scenario:navegacion}": ["p(95)<800"],
    "http_req_failed{scenario:navegacion}": ["rate<0.01"],
    checkout_ok: ["count<=1"], // jamás más de una venta de la última unidad
  },
};

const checkoutOk = new Counter("checkout_ok");
const checkoutSinStock = new Counter("checkout_sin_stock");
const checkoutOtro = new Counter("checkout_otro");

const jsonHeaders = (csrf) => ({
  "Content-Type": "application/json",
  "X-CSRFToken": csrf,
  Referer: `${BASE}/`,
  Origin: BASE,
});

export function browse() {
  group("home", () => check(http.get(`${BASE}/`), { "home 200": (r) => r.status === 200 }));
  group("catalogo", () => check(http.get(`${BASE}/api/v1/products/`), { "api 200": (r) => r.status === 200 }));
  group("tienda", () => check(http.get(`${BASE}/tienda`), { "tienda 200": (r) => r.status === 200 }));
  group("producto", () => check(http.get(`${BASE}/producto/${SLUG}`), { "producto 200": (r) => r.status === 200 }));
  group("detalle api", () => check(http.get(`${BASE}/api/v1/products/${SLUG}/`), { "detalle 200": (r) => r.status === 200 }));
  sleep(1);
}

export function lastUnit() {
  const product = http.get(`${BASE}/api/v1/products/${SLUG}/`).json();
  const variant = product.variantes[0].id;
  const zone = http.get(`${BASE}/api/v1/shipping/zones/`).json()[0];
  const csrf = http.get(`${BASE}/api/v1/auth/csrf/`).json().csrfToken;

  http.post(`${BASE}/api/v1/cart/items/`, JSON.stringify({ variante_id: variant, cantidad: 1 }), { headers: jsonHeaders(csrf) });
  sleep(Math.random() * 0.5); // las 30 llegan casi a la vez

  const res = http.post(
    `${BASE}/api/v1/checkout/`,
    JSON.stringify({
      nombre: "Prueba de carga", telefono: "987654321", metodo_entrega: zone.metodo, zona_id: zone.id,
      direccion: { departamento: "Lima", provincia: "Lima", distrito: "Miraflores", direccion: "Av. Prueba 123" },
      acepta_privacidad: true, acepta_terminos: true,
    }),
    { headers: jsonHeaders(csrf) },
  );
  if (res.status === 201) checkoutOk.add(1);
  else if (res.status === 409) checkoutSinStock.add(1);
  else checkoutOtro.add(1);
}
