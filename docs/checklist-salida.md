# Checklist de salida a producción

## Resultados de las pruebas hechas (desarrollo local, mismo compose de producción)

| Prueba | Resultado |
|---|---|
| Tests automáticos (permisos, IDOR, stock, concurrencia, pagos, Culqi, webhooks, panel, seguridad) | 214 en verde sobre PostgreSQL, incluida la concurrencia de la última unidad |
| Carga: 40 visitantes simultáneos 30 s (home, tienda, producto, API) | 4 895 peticiones, 0 errores, p95 ≈ 166 ms, ≈ 160 req/s en una sola máquina local |
| Carga: 30 compradoras a la vez por la **última unidad** | exactamente **1** pedido creado, 29 "sin stock", `audit_stock` consistente |
| Respaldo y restauración | restauración en base de prueba con los mismos conteos |
| Bloqueo por intentos fallidos detrás del proxy | bloquea por IP real aunque el atacante falsifique `X-Forwarded-For` |
| `pip-audit` y `npm audit` | 0 vulnerabilidades conocidas |
| Lighthouse móvil (build de producción, local) | producto: rendimiento 98, LCP 2.3 s; accesibilidad 100, SEO 100, buenas prácticas 96. **Home: rendimiento 93–96, LCP 2.7–3.3 s (meta 2.5 s no alcanzada en laboratorio local)**: reevaluar ya desplegado con CDN/HTTP2 real |

## Antes de abrir al público (bloqueantes)

- [ ] Dominio comprado y DNS apuntando al VPS.
- [ ] `.env.prod` completo; `DJANGO_SECRET_KEY`, contraseñas y `ADMIN_URL_PATH` generados al azar; `DJANGO_DEBUG=false`.
- [ ] Superusuario técnico creado; administradora y staff **sin** superusuario; 2FA activado con `enroll_2fa` y códigos de respaldo entregados.
- [ ] Correo SMTP configurado (recuperar contraseña) y probado.
- [ ] Respaldo copiado fuera del servidor y restauración probada en el servidor real.
- [x] WhatsApp del negocio y titular de Yape/Plin y de las cuentas (la dueña), cargados en la base local desde `seed/negocio.local.yaml`.
- [ ] Datos reales que faltan: tipo de cambio, margen, zonas y costos de envío, reparto de los splash por fragancia y stock de pañalero, relojes, set de 4 splash y Peach.
- [x] El DNI de la dueña **no hace falta** para la tienda: no se muestra en el sitio ni se guarda en el sistema. Solo lo pedirían Culqi, el banco o SUNAT si ella abre una cuenta o un RUC, y lo escribe ella misma en esos formularios oficiales (nunca en un chat).
- [x] Precios de venta confirmados: corazón negro S/ 130, corazón rojo S/ 120, plateado S/ 120, pañalero rosado S/ 130, reloj plateado bebe S/ 80, set reloj Aéropostale rosado S/ 100 (cargados en `seed/inventory.yaml`; los 3 bolsos corazón quedan publicados, el resto en borrador hasta tener stock).
- [x] Más precios confirmados: mochila negra acolchada S/ 150, bandolero cuadrado S/ 130 (el negro; se asumió igual para el blanco), crema Cucumber S/ 40, splash clásica S/ 50 con **oferta 2 por S/ 90** (las dos unidades pueden ser de fragancias distintas) y set Guess Red S/ 180.
- [x] Set de 3 mini perfumes Bombshell S/ 90 y set de 4 splash S/ 75 (publicados / en borrador según stock).
- [x] Más precios: mochila rosa PINK S/ 85, bandolero cuadrado negro S/ 130 y **blanco S/ 120** (ahora son dos productos), splash vainilla y Midnight Marshmallow S/ 50, Piña Tropicale y PINK Pineapple S/ 45. La crema Cucumber (S/ 40) **no se promociona**: queda en borrador sin foto.
- [ ] Precio pendiente: Peach (marca/línea sin confirmar). Stock pendiente de todo lo que está en borrador.
- [x] Medios de pago cargados en la base local: Yape y Plin (mismo número), transferencia BCP e Interbank con su CCI. Los números **no están en el repositorio**: viven en `seed/negocio.local.yaml` (ignorado por git).
- [ ] En producción: copiar `seed/negocio.local.yaml` al servidor y correr `python manage.py load_business_data`, o escribirlos en `/admin` → Ajustes (Yape/Plin y *Cuentas para transferencias*). El archivo ya incluye WhatsApp y titulares; al guardar desde `/admin` la tienda se actualiza al instante.
- [ ] Fotos finales de producto (ver `docs/guia-fotos.md`) y logo oficial (`frontend/public/brand/logo.png`, ver `docs/marca.md`).
- [ ] **Textos legales** revisados con un asesor: términos, privacidad (Ley 29733), cambios y devoluciones, **Libro de Reclamaciones** (verificar los requisitos vigentes de Indecopi para venta online y completar razón social/RUC en Ajustes).
- [x] Decidido: la dueña vende como **persona natural sin RUC**. Pendiente: poner su nombre completo como titular en términos y privacidad (textos marcados con corchetes; ahí no va el DNI) y que un contador o abogado confirme qué datos del titular debe mostrar una persona natural. Ojo: una actividad comercial habitual suele requerir inscribirse en SUNAT (RUC y régimen), y es probable que Culqi y otras pasarelas lo pidan para abrir la cuenta; confírmalo con un contador antes de depender de la pasarela. La facturación electrónica sigue fuera de alcance (los campos RUC/DNI ya existen).
- [ ] Probar un pedido completo real: Yape/Plin con comprobante → aprobación en el panel → entrega.
- [ ] Alta en Google Search Console con el `sitemap.xml`; revisar la vista previa al compartir un producto en WhatsApp/Instagram.

## Para activar Culqi (después del lanzamiento)

- [ ] Cuenta de Culqi a nombre de la dueña, aprobada.
- [ ] Validar en sandbox los puntos NO verificados de `docs/pagos-culqi.md` (URL base, unidad del monto, campos, estados de orden, formato del webhook).
- [ ] Migrar de Checkout v4 (anunciado como próximo a retirarse) a Checkout Custom.
- [ ] Registrar el webhook en CulqiPanel y probar un cargo, un rechazo y un reintento.
- [ ] `PAYMENTS_PROVIDER=culqi` + llaves en `.env.prod`; configurar la comisión real en Ajustes y recalcular precios.

## Operación continua
- Activar la CI: copiar `infra/github-ci.yml.example` a `.github/workflows/ci.yml` (requiere permiso `workflow` en GitHub). Revisar semanalmente los PR de Dependabot y su resultado.
- Probar la restauración de respaldos cada mes.
- Rotar `CULQI_SECRET_KEY`, `REVALIDATE_SECRET`, `N8N_WEBHOOK_SECRET` si alguna vez se exponen.
