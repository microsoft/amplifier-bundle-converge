# Converge Branding Assets

Official Converge branding assets, for use across Converge surfaces. The layout and
file inventory mirror [`amplifier/assets/branding/`](https://github.com/microsoft/amplifier/tree/main/assets/branding)
so the two sets can be consumed interchangeably.

## Source

The mark is the Converge hexagon: three interlocking folded ribbons carrying a
purple-to-blue gradient, enclosing a diamond-shaped central opening.

`source/converge-logo-original-1024.png` is the original artwork as delivered — the
mark composited over an **opaque black backing**. Every shipped asset is derived from
it by `generate.py`, which lifts the mark off that backing onto transparency (matching
the amplifier set, whose masters are also transparent-background).

Because the black backing was contiguous with the mark's central diamond, that diamond
becomes **transparent negative space**, not a black fill. On a light surface the centre
reads light. This is intentional and matches how the amplifier mark behaves.

## Directory Structure

```
branding/
├── source/            # Original artwork (black-backed) — the only non-derived file
├── icons/             # App icons (all sizes)
├── favicons/          # Web favicons
├── pwa/               # Progressive Web App icons
└── generate.py        # Regenerates everything below source/
```

## Icons (`icons/`)

| File | Size | Purpose |
|------|------|---------|
| `converge-icon-1024.png` | 1024x1024 | Master (transparent background) |
| `converge-icon-512.png` | 512x512 | Large app icon, app stores |
| `converge-icon-256.png` | 256x256 | Large app icon |
| `converge-icon-128.png` | 128x128 | Medium app icon |
| `converge-icon-64.png` | 64x64 | Standard app icon |
| `converge-icon-48.png` | 48x48 | Medium-small icon |
| `converge-icon-44.png` | 44x44 | Small UI icon (2x retina) |
| `converge-icon-32.png` | 32x32 | Small app icon |
| `converge-icon-22.png` | 22x22 | Small UI icon (1x) |
| `converge-icon-16.png` | 16x16 | Tiny icon — see *Small-size legibility* |
| `Converge.icns` | Multi-size | macOS app icon bundle (16-1024px) |
| `converge-windows.ico` | Multi-size | Windows app icon (16, 24, 32, 48, 64, 128, 256) |
| `MenuBarIcon.png` | 18x18 | macOS menu bar template (1x) |
| `MenuBarIcon@2x.png` | 36x36 | macOS menu bar template (2x) |

## Favicons (`favicons/`)

| File | Size | Purpose |
|------|------|---------|
| `favicon.ico` | 16, 32, 48 | Multi-resolution favicon for browsers |
| `favicon-32.png` | 32x32 | Modern browser favicon |
| `apple-touch-icon.png` | 180x180 | iOS "Add to Home Screen" |

## PWA Icons (`pwa/`)

| File | Size | Purpose |
|------|------|---------|
| `pwa-192.png` | 192x192 | PWA manifest icon |
| `pwa-512.png` | 512x512 | PWA splash screen |

## Menu Bar Icons

`MenuBarIcon*.png` are **template images** — pure black RGB with the mark's silhouette
in the alpha channel. macOS tints them automatically for light and dark mode. Use these
for system tray / menu bar icons; do **not** use the colour icons there.

## Full Colour Icons

The `converge-icon-*.png` files are full colour with a transparent background. Use them
for app icons, in-app UI headers, documentation, README badges, and marketing.

## Small-size legibility

The mark's central opening starts to soften at 22px and is no longer distinct at 16px,
where the icon reads as a coloured hexagon rather than an open one. The 16px asset ships
for completeness (OS icon pickers and favicon fallbacks require it), but prefer 22px or
above wherever the surface allows a choice.

## Regenerating

All assets outside `source/` are derived. Never hand-edit them — change the source or
`generate.py`, then:

```bash
cd assets/branding
python generate.py        # requires Pillow and numpy
```

The script re-derives the transparent master, emits every size, asserts that each `.ico`
really contains the frames it claims, and re-opens every emitted file before exiting.

## Usage in a GitHub README

```markdown
![Converge](assets/branding/icons/converge-icon-64.png)
```

## HTML Favicon Setup

```html
<link rel="icon" href="/favicons/favicon.ico" sizes="any">
<link rel="icon" href="/favicons/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/favicons/apple-touch-icon.png">
```

## PWA Manifest

```json
{
  "icons": [
    { "src": "/pwa/pwa-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/pwa/pwa-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```
