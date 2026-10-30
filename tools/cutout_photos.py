"""Quita el fondo de fotos PROPIAS de productos sobre mesa/sofá y las deja en un fondo limpio de catálogo.

Funciona con productos fotografiados solos (cajas, bolsos sobre una superficie). NO es para fotos donde una mano
sostiene el producto: ahí la mano queda dentro del recorte. No usa imágenes de internet.

Requiere:  pip install rembg onnxruntime   (la primera vez descarga el modelo u2net, ~170 MB)
Uso:       python tools/cutout_photos.py "C:\\ruta\\a\\productos nataly" [slug ...]
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_photos import MAX_W, OUT, PHOTOS, RATIO, enhance  # noqa: E402

BG = (245, 241, 238)  # blanco cálido, combina con el tono rosado de la marca
DEFAULT = ["set-guess-red", "reloj-bebe-plateado", "set-reloj-aeropostale-rosado", "panalero-rosado-juicy"]
FILL = 0.84  # el producto ocupa ~84 % del ancho/alto del cuadro


def compose(cut: Image.Image) -> Image.Image:
    """Centra el recorte en un lienzo 4:5 con fondo liso."""
    bbox = cut.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    cut = cut.crop(bbox)
    w, h = MAX_W, int(MAX_W / RATIO)
    scale = min(w * FILL / cut.width, h * FILL / cut.height)
    cut = cut.resize((max(1, int(cut.width * scale)), max(1, int(cut.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), BG)
    x, y = (w - cut.width) // 2, int((h - cut.height) * 0.46)
    canvas.paste(cut, (x, y), cut)
    return canvas


def main(src, slugs):
    from rembg import new_session, remove  # import tardío: es pesado

    session = new_session("u2net")
    src = Path(src)
    originales = Path(__file__).resolve().parent.parent / "seed" / "originales"
    files = list(src.glob("*.jp*g")) + list(src.glob("*.jfif")) + list(originales.glob("*.*"))
    for token, slug, n, box, _region, *_ in PHOTOS:
        if slug not in slugs or n != 1:
            continue
        match = [f for f in files if token in f.name]
        if not match:
            print(f"  falta original: {token}")
            continue
        img = ImageOps.exif_transpose(Image.open(match[0])).convert("RGB")
        m = 0.06
        crop = img.crop((
            int(max(0, box[0] - m) * img.width), int(max(0, box[1] - m) * img.height),
            int(min(1, box[2] + m) * img.width), int(min(1, box[3] + m) * img.height),
        ))
        cut = remove(crop, session=session, alpha_matting=False)
        out = enhance(compose(cut))
        out.save(OUT / f"{slug}.jpg", "JPEG", quality=88, optimize=True, progressive=True)
        print(f"  {slug}.jpg: fondo quitado")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], set(sys.argv[2:]) or set(DEFAULT))
