# src/optees/core/make_icons_from_png.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple, Iterable
import argparse
import subprocess
import sys
import os

from PIL import Image, ImageDraw, ImageFilter, ImageChops

# ---------------- helpers ----------------
def linear_gradient(size: Tuple[int, int], c1, c2, direction="trbl") -> Image.Image:
    """Semplice gradiente lineare. direction: 'tb','lr','tlbr','trbl'."""
    w, h = size
    base = Image.new("RGB", size, c1)
    top = Image.new("RGB", size, c2)
    mask = Image.new("L", size, 0)
    px = mask.load()

    if direction == "tb":
        for y in range(h):
            v = int(255 * (y / (h - 1)))
            for x in range(w): px[x, y] = v
    elif direction == "lr":
        for x in range(w):
            v = int(255 * (x / (w - 1)))
            for y in range(h): px[x, y] = v
    elif direction == "tlbr":
        for y in range(h):
            for x in range(w):
                t = (x + y) / (w + h - 2)
                px[x, y] = int(255 * t)
    else:  # 'trbl'
        for y in range(h):
            for x in range(w):
                t = (w - 1 - x + y) / (w + h - 2)
                px[x, y] = int(255 * t)

    return Image.composite(top, base, mask)

def radial_glow(size: Tuple[int, int], color=(0, 0, 0), strength=0.45) -> Image.Image:
    w, h = size
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    r = int(min(w, h) * 0.60)
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((w//2 - r//2, h//2 - r//2, w//2 + r//2, h//2 + r//2), fill=int(255 * strength))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=int(r * 0.45)))
    g = Image.new("RGBA", size, (*color, 255))
    return Image.composite(g, glow, mask)

def rounded_mask(size: Tuple[int, int], radius_ratio=0.22) -> Image.Image:
    w, h = size
    r = int(min(w, h) * radius_ratio)
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w, h], radius=r, fill=255)
    return m

def paste_center(bg: Image.Image, fg: Image.Image, scale=0.82) -> None:
    """Incolla fg centrato su bg con scala relativa (mantiene alpha)."""
    W, H = bg.size
    max_side = int(min(W, H) * scale)
    ratio = fg.width / fg.height
    if fg.width >= fg.height:
        nw = max_side
        nh = int(nw / ratio)
    else:
        nh = max_side
        nw = int(nh * ratio)
    fg_resized = fg.resize((nw, nh), Image.LANCZOS)
    x = (W - nw) // 2
    y = (H - nh) // 2
    bg.alpha_composite(fg_resized, (x, y))

# ---------------- pipeline ----------------
def build_master(
    fg_path: Path,
    out_dir: Path,
    *,
    variant: str = "dark",   # 'dark' | 'light'
    scale: float = 0.82,     # dimensione del logo dentro la card
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    size = (1024, 1024)

    # background gradiente per variante
    if variant == "dark":
        c1, c2 = (10, 26, 64), (28, 71, 190)     # blu scuri
        tint_fg = (255, 255, 255)
        border_alpha = 30
    else:
        c1, c2 = (230, 242, 255), (200, 220, 255)  # chiaro
        tint_fg = (20, 20, 20)
        border_alpha = 60

    grad = linear_gradient(size, c1, c2, direction="trbl").convert("RGBA")
    glow = radial_glow(size, color=(0, 0, 0), strength=0.50)
    canvas = Image.alpha_composite(grad, glow)

    # squircle + bordino
    mask = rounded_mask(size, radius_ratio=0.22)
    canvas = Image.composite(canvas, Image.new("RGBA", size, (0, 0, 0, 0)), mask)

    ring_outer = mask
    ring_inner = mask.filter(ImageFilter.GaussianBlur(1))
    ring = ImageChops.difference(ring_outer, ring_inner)
    border = Image.new("RGBA", size, (255, 255, 255, border_alpha))
    canvas = Image.alpha_composite(canvas, Image.composite(border, Image.new("RGBA", size, 0), ring))

    # foreground
    fg = Image.open(fg_path).convert("RGBA")
    # re-tinta solo i pixel visibili (mantiene alpha)
    r, g, b, a = fg.split()
    solid = Image.new("RGBA", fg.size, (*tint_fg, 255))
    fg = Image.composite(solid, Image.new("RGBA", fg.size, (0, 0, 0, 0)), a)
    fg.putalpha(a)

    paste_center(canvas, fg, scale=scale)

    master = out_dir / f"appicon_1024.png"
    canvas.save(master)
    return master

def save_resizes(master: Path, out_dir: Path, sizes: Iterable[int] = (512, 256, 128, 64, 32)) -> None:
    img = Image.open(master)
    for s in sizes:
        img.resize((s, s), Image.LANCZOS).save(out_dir / f"appicon_{s}.png")

def make_iconset_and_icns(master: Path, out_dir: Path) -> None:
    """Crea iconset .iconset e, se possibile, compila un .icns (macOS)."""
    iconset = out_dir / "appicon.iconset"
    iconset.mkdir(exist_ok=True)

    def save(size: int, name: str):
        Image.open(master).resize((size, size), Image.LANCZOS).save(iconset / name)

    # set completo Apple
    save(16, "icon_16x16.png")
    save(32, "icon_16x16@2x.png")
    save(32, "icon_32x32.png")
    save(64, "icon_32x32@2x.png")
    save(128, "icon_128x128.png")
    save(256, "icon_128x128@2x.png")
    save(256, "icon_256x256.png")
    save(512, "icon_256x256@2x.png")
    save(512, "icon_512x512.png")
    Image.open(master).save(iconset / "icon_512x512@2x.png")  # 1024

    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset), "-o", str(out_dir / "optees.icns")],
                check=True
            )
        except Exception as e:
            print("icns generation skipped:", e)

def make_ico(master: Path, out_dir: Path) -> None:
    img = Image.open(master)
    sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    img.save(out_dir / "optees.ico", format="ICO", sizes=sizes)

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description="Generate app icons (dark/light) from a transparent PNG.")
    ap.add_argument("foreground", type=str, help="Percorso PNG trasparente (logo).")
    ap.add_argument("--out-dir", type=str, default=None,
                    help="Cartella di output (default: <foreground_dir>/logo).")
    ap.add_argument("--variant", choices=["dark", "light", "both"], default="both",
                    help="Quale set generare.")
    ap.add_argument("--scale", type=float, default=0.82,
                    help="Scala del logo dentro l'icona (0-1).")
    args = ap.parse_args()

    fg_path = Path(args.foreground).resolve()
    if not fg_path.exists():
        print("Foreground non trovato:", fg_path)
        sys.exit(1)

    # OUT BASE: se non specificato, mette in <dir_del_logo>/logo
    out_base = Path(args.out_dir).resolve() if args.out_dir else fg_path.parent / "logo"

    variants = ["dark", "light"] if args.variant == "both" else [args.variant]
    for var in variants:
        out_dir = out_base / var
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{var}] building 1024… -> {out_dir}")
        master = build_master(fg_path, out_dir, variant=var, scale=args.scale)

        print(f"[{var}] resizes…")
        save_resizes(master, out_dir)

        print(f"[{var}] iconset + icns…")
        make_iconset_and_icns(master, out_dir)

        print(f"[{var}] ico…")
        make_ico(master, out_dir)

        print(f"[{var}] DONE -> {out_dir}")

if __name__ == "__main__":
    main()
