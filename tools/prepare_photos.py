"""Prepara las fotos propias del negocio para el catálogo.

Qué hace: corrige la rotación EXIF, recorta alrededor del producto (quita barras de capturas
de pantalla y gente de fondo), lleva la imagen a proporción 4:5, mejora luz/color/nitidez y
exporta JPG optimizados a seed/images/<slug>[-N].jpg.

Qué NO hace: no descarga fotos de internet ni usa imágenes oficiales de marcas. Una foto
tomada en tienda no se vuelve foto de estudio con un script; para el mejor resultado ver
docs/guia-fotos.md.

Uso:  python tools/prepare_photos.py "C:\\ruta\\a\\productos nataly"
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

OUT = Path(__file__).resolve().parent.parent / "seed" / "images"
RATIO = 4 / 5
MAX_W = 1200

# archivo (parte del nombre) -> (slug destino, n.º de foto, caja del producto en fracciones x0,y0,x1,y1)
# Las cajas se ajustaron mirando cada foto; "region" delimita el área válida (sin barras negras).
PHOTOS = [
    ("2.48.02 PM", "bandolero-cuadrado", 1, (0.12, 0.19, 0.97, 0.66), None),
    ("9.00.41 PM", "bandolero-cuadrado", 2, (0.03, 0.38, 0.97, 0.66), (0, 0.19, 1, 0.81)),
    ("5.35.24 PM", "bolso-corazon-rojo", 1, (0.03, 0.36, 0.97, 0.68), (0, 0.225, 1, 0.78)),
    ("8.16.05 PM (4)", "bolso-corazon-negro-brillos", 1, (0.12, 0.12, 0.95, 0.72), None),
    ("8.16.05 PM (5)", "bolso-corazon-plateado-monograma", 1, (0.28, 0.0, 0.92, 0.66), None),
    ("9.01.28 PM", "mochila-negra-acolchada", 1, (0.25, 0.05, 0.82, 0.78), None),
    ("2.48.43 PM", "mochila-pink-deportiva", 1, (0.15, 0.20, 0.95, 0.72), None),
    ("8.16.05 PM (2)", "set-mini-eau-de-parfum-bombshell", 1, (0.20, 0.06, 0.94, 0.74), None),
    ("2.48.42 PM.jpeg", "set-4-splash", 1, (0.02, 0.20, 0.96, 0.68), None),
    ("8.16.05 PM (3)", "splash-clasica", 1, (0.0, 0.04, 1.0, 0.78), None),
    ("9.02.59 PM", "set-reloj-aeropostale-rosado", 1, (0.05, 0.06, 0.98, 0.78), None),
    ("9.03.10 PM", "reloj-bebe-plateado", 1, (0.02, 0.2, 0.98, 0.8), (0, 0.14, 1, 0.86)),
    ("9.03.16 PM", "panalero-rosado-juicy", 1, (0.02, 0.08, 0.98, 0.78), None),
]


def fit_ratio(box, size, region):
    """Expande la caja (con margen) a proporción 4:5 sin salirse de la región válida."""
    w, h = size
    rx0, ry0, rx1, ry1 = (region or (0, 0, 1, 1))
    rx0, rx1, ry0, ry1 = rx0 * w, rx1 * w, ry0 * h, ry1 * h
    x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = (x1 - x0) * 1.10, (y1 - y0) * 1.10
    if bw / bh > RATIO:
        bh = bw / RATIO
    else:
        bw = bh * RATIO
    bw = min(bw, rx1 - rx0)
    bh = min(bh, ry1 - ry0)
    if bw / bh > RATIO:
        bw = bh * RATIO
    else:
        bh = bw / RATIO
    left = min(max(cx - bw / 2, rx0), rx1 - bw)
    top = min(max(cy - bh / 2, ry0), ry1 - bh)
    return int(left), int(top), int(left + bw), int(top + bh)


def enhance(img):
    img = ImageOps.autocontrast(img, cutoff=0.6)
    img = ImageEnhance.Color(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.04)
    img = ImageEnhance.Brightness(img).enhance(1.03)
    return img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=70, threshold=3))


def main(src):
    src = Path(src)
    files = list(src.glob("*.jp*g"))
    OUT.mkdir(parents=True, exist_ok=True)
    for token, slug, n, box, region in PHOTOS:
        match = [f for f in files if token in f.name and (token != "2.48.42 PM.jpeg" or "(1)" not in f.name)]
        if not match:
            print(f"  falta: {token}")
            continue
        img = ImageOps.exif_transpose(Image.open(match[0])).convert("RGB")
        img = img.crop(fit_ratio(box, img.size, region))
        if img.width > MAX_W:
            img = img.resize((MAX_W, int(MAX_W / RATIO)), Image.LANCZOS)
        name = f"{slug}.jpg" if n == 1 else f"{slug}-{n}.jpg"
        enhance(img).save(OUT / name, "JPEG", quality=86, optimize=True, progressive=True)
        print(f"  {name}: {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
