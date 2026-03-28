from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from pyembroidery import (
    STITCH,
    JUMP,
    COLOR_CHANGE,
    COMMAND_MASK,
    EmbPattern,
)


def _thread_to_rgb(thread) -> tuple[int, int, int]:
    """Convert pyembroidery thread-like values to an RGB tuple."""
    if thread is None:
        return (255, 255, 255)

    color = getattr(thread, "color", None)
    if color is None and isinstance(thread, dict):
        color = thread.get("color", thread.get("rgb"))

    if isinstance(color, int):
        return ((color >> 16) & 255, (color >> 8) & 255, color & 255)

    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return (int(color[0]) & 255, int(color[1]) & 255, int(color[2]) & 255)

    if isinstance(color, str):
        hex_color = color.lstrip("#")
        if len(hex_color) in (3, 4):
            hex_color = "".join(ch * 2 for ch in hex_color[:3])
        if len(hex_color) >= 6:
            try:
                return (
                    int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16),
                )
            except ValueError:
                pass

    return (255, 255, 255)


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
    # Coletar trilhas por cor usando coordenadas absolutas.
    points_by_color: list[list[list[tuple[float, float]]]] = [[[]]]

    for stitch in pattern.stitches:
        cmd = stitch[2] & COMMAND_MASK
        if cmd == COLOR_CHANGE:
            points_by_color.append([[]])
            continue
        if cmd == JUMP:
            if points_by_color[-1][-1]:
                points_by_color[-1].append([])
            points_by_color[-1][-1].append((float(stitch[0]), float(stitch[1])))
            continue
        if cmd != STITCH:
            continue
        x = float(stitch[0])
        y = float(stitch[1])
        points_by_color[-1][-1].append((x, y))

    all_points = [p for layer in points_by_color for path in layer for p in path]
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
        thread_colors.append(_thread_to_rgb(th))

    def map_pt(px, py):
        X = int((px - minx) * scale_auto) + pad
        Y = int((py - miny) * scale_auto) + pad
        return (X, Y)

    for i, layer in enumerate(points_by_color):
        color = thread_colors[i] if i < len(thread_colors) else (90, 160, 255)
        for path in layer:
            if len(path) < 2:
                continue
            mapped = [map_pt(px, py) for (px, py) in path]
            draw.line(mapped, fill=color, width=2)

    img.save(out_path)