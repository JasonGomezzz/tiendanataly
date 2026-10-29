# Guía rápida para fotos de producto

Las fotos tomadas dentro de la tienda (gente al fondo, luz mixta, mano sosteniendo el producto) se ven "caseras" aunque se recorten. Con 10 minutos de preparación se consigue una foto de catálogo usando solo un celular.

## Montaje (sin gastar)
1. **Fondo liso y claro**: una cartulina blanca o beige apoyada en la pared y extendida sobre la mesa (que no se vea la unión).
2. **Luz de ventana**, de lado, sin sol directo. Sin flash y sin focos amarillos encendidos.
3. **Celular fijo**: sobre una pila de libros o un trípode barato, a la altura del producto, con la cámara limpia.

## Qué fotos tomar por producto
1. Frente completo, centrado, con espacio alrededor (la tienda recorta en proporción 4:5).
2. Detalle del herraje / textura / etiqueta de la fragancia.
3. De costado o por dentro (bolsos y mochilas).
4. Producto en uso (opcional), con fondo ordenado.

## Reglas
- Una foto = un producto. Si hay varios colores, una foto por color.
- Orientación vertical.
- No usar capturas de pantalla ni historias de otras cuentas: se ven los bordes del teléfono y son contenido ajeno.
- No usar fotos oficiales de marcas ni de otras tiendas: tienen derechos de autor, y la tienda declara que es independiente.

## Cómo subirlas
Admin → Productos → elegir el producto → sección *Imágenes* → subir. La primera (orden 0) es la principal. Se aceptan JPG, PNG y WEBP de hasta 5 MB.

## Mejora automática de las fotos que ya existen
`python tools/prepare_photos.py "<carpeta con las fotos originales>"` recorta, corrige luz/color/nitidez y deja los archivos listos en `seed/images/`. No inventa fondos nuevos: mejora lo que hay.
