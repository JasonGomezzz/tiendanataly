# Dónde alojar la tienda: VPS o Vercel

La tienda tiene dos partes que se alojan distinto:

| Parte | Qué necesita | ¿Corre en Vercel? |
|---|---|---|
| Frontend (Next.js) | Node, ISR y optimizador de imágenes | Sí |
| Backend (Django) | Proceso permanente, PostgreSQL, Redis, **worker y beat de Celery** (expiran reservas de stock y envían eventos), disco para fotos y comprobantes | **No**: Vercel no ejecuta procesos permanentes ni bases de datos propias |

Por eso Vercel **nunca es la solución completa**: aun usándolo, el backend, la base y Redis van en otro servidor.

## Opción A (recomendada): todo en un VPS con Docker

Es lo que está probado en este repositorio (`docker-compose.prod.yml`, Caddy con HTTPS, respaldos diarios, prueba de carga). Una sola factura, un solo lugar donde mirar si algo falla. Guía paso a paso: [despliegue.md](despliegue.md).

Costo aproximado: el VPS (2 vCPU / 2 GB) más el dominio al año. Verifica los precios vigentes del proveedor que elijas antes de comprar.

## Opción B: frontend en Vercel + backend en otro lado

Solo conviene si se quiere el CDN de Vercel o sus despliegues automáticos. Implica:

1. **Plan de pago.** El plan gratuito (Hobby) de Vercel es solo para uso personal y no comercial; una tienda que cobra no cumple. El plan Pro cuesta US$ 20 al mes (precio publicado en [vercel.com/pricing](https://vercel.com/pricing); condiciones en [vercel.com/docs/plans](https://vercel.com/docs/plans)). Ese costo se suma al del servidor del backend.
2. **Backend aparte**, con la misma pila del VPS (Django + PostgreSQL + Redis + worker + beat), en un VPS o en un servicio que ejecute Docker. Es el 100 % de la complejidad operativa de la opción A, más Vercel.
3. **Configuración que hay que revisar** (no está probada en Vercel):
   - `API_INTERNAL_URL` debe apuntar a la URL pública del backend; las reescrituras de `/api/v1` y `/media` del frontend la usan, y así las cookies de sesión siguen siendo del mismo sitio.
   - Django llama a `/api/revalidate` en `FRONTEND_URL` con el secreto `REVALIDATE_SECRET`: `FRONTEND_URL` debe ser el dominio público del frontend en Vercel, con el mismo secreto en ambos lados.
   - `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` y `DJANGO_ALLOWED_HOSTS` del backend deben incluir el dominio del frontend y el del backend.
   - Las fotos se siguen sirviendo desde el backend; el optimizador de imágenes de Vercel tiene su propia cuota.
4. **Quién hace qué.** Para publicar hay que iniciar sesión en Vercel (lo haces tú en el navegador del panel; yo no creo cuentas ni escribo contraseñas) y tener ya el backend en línea.

## Recomendación

Lanzar con la **opción A**. Si más adelante se quiere Vercel, el cambio se limita al frontend y a las variables de arriba, sin tocar el backend. Antes de decidir hace falta tener el dominio y saber qué servidor tendrá el backend.
