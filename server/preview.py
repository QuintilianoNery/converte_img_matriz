from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pyembroidery import (
    STITCH,
    COLOR_CHANGE,
    EmbPattern,
)


def render_preview(
    pattern: EmbPattern,
    out_path: Path,
    scale: float = 4.0,
    max_size_px: int = 1400,
):
    """
    Render simples do caminho de pontos (linhas), com limite de tamanho para não estourar memória.
    - max_size_px limita largura/altura do preview
    """
    # Coletar pontos absolutos por cor
    x = 0.0
    y = 0.0
    points_by_color: list[list[tuple[float, float]]] = [[]]

    # pattern.stitches normalmente é lista de (dx, dy, cmd) em coordenadas relativas
    for stitch in pattern.stitches:
        cmd = stitch[2]
        if cmd == COLOR_CHANGE:
            points_by_color.append([])
            continue
        if cmd != STITCH:
            continue
        dx = float(stitch[0])
        dy = float(stitch[1])
        x += dx
        y += dy
        points_by_color[-1].append((x, y))

    all_points = [p for layer in points_by_color for p in layer]
    if len(all_points) < 2:
        img = Image.new("RGB", (800, 600), (11, 18, 32))
        img.save(out_path)
        return

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)

    # Evitar bbox degenerado
    span_x = max(1e-6, (maxx - minx))
    span_y = max(1e-6, (maxy - miny))

    pad = 20

    # Ajustar scale automaticamente para caber em max_size_px
    # w = span_x * scale + 2*pad <= max_size_px  => scale <= (max_size_px-2*pad)/span_x
    scale_limit_x = (max_size_px - 2 * pad) / span_x
    scale_limit_y = (max_size_px - 2 * pad) / span_y
    scale_auto = min(scale, scale_limit_x, scale_limit_y)

    # Garantir um scale mínimo para não zerar tudo
    scale_auto = max(scale_auto, 0.05)

    w = int(span_x * scale_auto) + pad * 2
    h = int(span_y * scale_auto) + pad * 2

    # Clamp final (dupla segurança)
    w = max(480, min(w, max_size_px))
    h = max(360, min(h, max_size_px))

    img = Image.new("RGB", (w, h), (11, 18, 32))
    draw = ImageDraw.Draw(img)

    # Tentar pegar cores do threadlist
    thread_colors = []
    for th in getattr(pattern, "threadlist", []) or []:
        c = th.get("color", 0xFFFFFF)
        r = (c >> 16) & 255
        g = (c >> 8) & 255
        b = c & 255
        thread_colors.append((r, g, b))

    def map_pt(px, py):
        X = int((px - minx) * scale_auto) + pad
        Y = int((py - miny) * scale_auto) + pad
        return (X, Y)

    for i, layer in enumerate(points_by_color):
        if len(layer) < 2:
            continue
        color = thread_colors[i] if i < len(thread_colors) else (90, 160, 255)
        mapped = [map_pt(px, py) for (px, py) in layer]
        draw.line(mapped, fill=color, width=2)

    img.save(out_path)