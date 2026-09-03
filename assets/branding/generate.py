#!/usr/bin/env python3
"""Regenerate every Converge branding asset from the original source logo.

    cd assets/branding && python generate.py

Requires Pillow. Everything under icons/, favicons/ and pwa/ is derived output --
the only inputs are source/converge-logo-original-1024.png and this file.

Two stages:

  1. MATTE REMOVAL. The source logo is the mark composited over an opaque black
     backing. The branding set uses transparent-background masters (matching the
     amplifier set), so the backing is removed:
       - flood fill the near-black region inward from the canvas border -> exterior
       - any remaining enclosed near-black component above MIN_HOLE px is a hole
         (here: the mark's central diamond), and is cleared too
       - alpha ramps with luminance across the anti-aliased edge rather than being
         hard-cut, then RGB is un-premultiplied so edges stay clean on light backdrops
     The backing is not pure #000 -- it carries encoder noise at luminance 1-7 --
     so the ramp floors above that noise instead of smearing a haze over the canvas.

  2. RESIZE. Downscaling happens in halving stages rather than one 1024->16 jump,
     with a light unsharp pass at or below 22px. Without it the mark's central
     opening dissolves at small sizes. The menu-bar stencils skip the unsharp pass:
     sharpening is tuned for the colour icon and would only ring a 1-bit silhouette.
"""

import struct
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).parent
SOURCE = HERE / "source" / "converge-logo-original-1024.png"

# --- matte removal ---
T_DARK = 20  # max-channel value at or below which a pixel is candidate backing
RAMP_LO = 8  # luminance at or below which backing is fully clear
RAMP_HI = 56  # luminance at or above which backing is fully opaque
MIN_HOLE = 200  # ignore enclosed dark specks smaller than this

# --- output inventory ---
ICON_SIZES = [1024, 512, 256, 128, 64, 48, 44, 32, 22, 16]
SHARPEN_AT_OR_BELOW = 22
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]
WINDOWS_ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
FAVICON_ICO_SIZES = [16, 32, 48]


def build_master() -> Image.Image:
    """Stage 1: lift the mark off its black backing into a transparent RGBA master."""
    rgb = np.array(Image.open(SOURCE).convert("RGB")).astype(np.float32)
    h, w = rgb.shape[:2]
    lum = rgb.max(axis=2)
    dark = lum <= T_DARK

    exterior = np.zeros((h, w), dtype=bool)
    q: deque = deque()
    for y, x in (
        [(0, x) for x in range(w)]
        + [(h - 1, x) for x in range(w)]
        + [(y, 0) for y in range(h)]
        + [(y, w - 1) for y in range(h)]
    ):
        if dark[y, x] and not exterior[y, x]:
            exterior[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not exterior[ny, nx]:
                exterior[ny, nx] = True
                q.append((ny, nx))

    remaining = dark & ~exterior
    holes = np.zeros((h, w), dtype=bool)
    seen = np.zeros((h, w), dtype=bool)
    for sy, sx in zip(*np.nonzero(remaining)):
        if seen[sy, sx]:
            continue
        comp = []
        seen[sy, sx] = True
        q = deque([(sy, sx)])
        while q:
            y, x = q.popleft()
            comp.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and remaining[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if len(comp) >= MIN_HOLE:
            for y, x in comp:
                holes[y, x] = True

    background = exterior | holes
    ramp = np.clip((lum - RAMP_LO) / (RAMP_HI - RAMP_LO), 0.0, 1.0)
    alpha = np.where(background, ramp, 1.0).astype(np.float32)

    out_rgb = np.clip(rgb / np.maximum(alpha, 1e-4)[..., None], 0, 255)
    out_rgb = np.where(alpha[..., None] > 0.004, out_rgb, 0.0)
    out = np.dstack([out_rgb, alpha * 255.0]).round().astype(np.uint8)

    a = out[..., 3]
    print(
        f"master: opaque={(a == 255).sum():,} clear={(a == 0).sum():,} "
        f"partial={((a > 0) & (a < 255)).sum():,}"
    )
    return Image.fromarray(out, "RGBA")


MASTER = build_master()


def scaled(size: int, sharpen: bool = True) -> Image.Image:
    """Stage 2: halving-stage downscale, light unsharp at the smallest sizes."""
    im, cur = MASTER, MASTER.width
    while cur // 2 > size:
        cur //= 2
        im = im.resize((cur, cur), Image.LANCZOS)
    im = im.resize((size, size), Image.LANCZOS)
    if sharpen and size <= SHARPEN_AT_OR_BELOW:
        im = im.filter(ImageFilter.UnsharpMask(radius=0.6, percent=90, threshold=0))
    return im


def save(im: Image.Image, rel: str) -> None:
    path = HERE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)
    print(f"  {rel}  {im.size[0]}x{im.size[1]}  {path.stat().st_size:,} B")


def save_ico(rel: str, sizes: list[int]) -> None:
    """Write a genuinely multi-frame ICO, then read the directory back to prove it."""
    path = HERE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    scaled(max(sizes)).save(path, format="ICO", sizes=[(s, s) for s in sorted(sizes)])
    data = path.read_bytes()
    count = struct.unpack("<H", data[4:6])[0]
    got = sorted((data[6 + i * 16] or 256) for i in range(count))
    assert got == sorted(sizes), f"{rel}: wrote {got}, wanted {sorted(sizes)}"
    print(f"  {rel}  frames={got}  {path.stat().st_size:,} B")


def save_icns(rel: str) -> None:
    path = HERE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    MASTER.save(path, format="ICNS", sizes=[(s, s) for s in ICNS_SIZES])
    with Image.open(path) as im:
        print(f"  {rel}  slots={sorted(im.info['sizes'])}  {path.stat().st_size:,} B")


def menu_bar_icon(size: int) -> Image.Image:
    """macOS template image: pure black RGB, the mark's alpha as the stencil."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    im.putalpha(scaled(size, sharpen=False).getchannel("A"))
    return im


print("icons/")
for s in ICON_SIZES:
    save(scaled(s), f"icons/converge-icon-{s}.png")
save(menu_bar_icon(18), "icons/MenuBarIcon.png")
save(menu_bar_icon(36), "icons/MenuBarIcon@2x.png")
save_ico("icons/converge-windows.ico", WINDOWS_ICO_SIZES)
save_icns("icons/Converge.icns")

print("favicons/")
save(scaled(32), "favicons/favicon-32.png")
save(scaled(180), "favicons/apple-touch-icon.png")
save_ico("favicons/favicon.ico", FAVICON_ICO_SIZES)

print("pwa/")
save(scaled(192), "pwa/pwa-192.png")
save(scaled(512), "pwa/pwa-512.png")

print("\nre-opening every emitted file")
n = 0
for p in sorted(HERE.rglob("*")):
    if p.suffix.lower() in {".png", ".ico", ".icns"} and "source" not in p.parts:
        with Image.open(p) as im:
            im.load()
        n += 1
print(f"  {n} files re-open cleanly")
