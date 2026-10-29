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
- [ ] Datos reales: WhatsApp, Yape/Plin (número y titular), tipo de cambio, margen, zonas y costos de envío, precios de todos los productos y reparto de los splash por fragancia.
- [ ] Fotos finales de producto (ver `docs/guia-fotos.md`) y logo oficial (`frontend/public/brand/logo.png`, ver `docs/marca.md`).
- [ ] **Textos legales** revisados con un asesor: términos, privacidad (Ley 29733), cambios y devoluciones, **Libro de Reclamaciones** (verificar los requisitos vigentes de Indecopi para venta online y completar razón social/RUC en Ajustes).
- [ ] Definir si la dueña vende con RUC o como persona natural y qué comprobante emite (la facturación electrónica queda fuera de alcance; los campos RUC/DNI ya existen).
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
