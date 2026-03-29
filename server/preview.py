from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from pyembroidery import (
    STITCH,
    JUMP,
    TRIM,
    COLOR_CHANGE,
    COMMAND_MASK,
    EmbPattern,
)


def _thread_to_rgb(thread) -> tuple[int, int, int]:
    """Convert pyembroidery thread-like values to an RGB tuple."""
    if thread is None:
        return (80, 80, 80)

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

    return (80, 80, 80)


def _darken(color: tuple[int, int, int], factor: float = 0.65) -> tuple[int, int, int]:
    return tuple(max(0, int(c * factor)) for c in color)  # type: ignore[return-value]


def _lighten(color: tuple[int, int, int], amount: int = 55) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in color)  # type: ignore[return-value]


def render_preview(
    pattern: EmbPattern,
    out_path: Path,
    scale: float = 5.0,
    max_size_px: int = 1600,
):
    """
    Renderiza uma previa de bordado realista:
    - Linhas com espessura proporcional ao diametro real do fio (~0.4 mm)
    - JUMP/TRIM nao sao desenhados (ficam invisiveis, como no tecido real)
    - Dupla passada: sombra + cor + highlight simulam o brilho do fio
    - Fundo creme com textura sutil de tecido
    """
    # Coleta de caminhos por cor
    # JUMP atualiza o cursor mas NAO conecta visualmente - nao e costurado.
    LayerType = list[list[tuple[float, float]]]
    points_by_color: list[LayerType] = [[[]]]
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    has_cursor = False

    for stitch in pattern.stitches:
        cmd = stitch[2] & COMMAND_MASK

        if cmd == COLOR_CHANGE:
            points_by_color.append([[]])
            continue

        if cmd == JUMP:
            # Avanca cursor mas quebra o caminho visivel - JUMP nao e costurado.
            if points_by_color[-1][-1]:
                points_by_color[-1].append([])
            cursor_x = float(stitch[0])
            cursor_y = float(stitch[1])
            has_cursor = True
            continue

        if cmd == TRIM:
            # TRIM apenas corta o fio; mantemos o cursor atual para evitar artefatos.
            if points_by_color[-1][-1]:
                points_by_color[-1].append([])
            continue

        if cmd != STITCH:
            continue

        x = float(stitch[0])
        y = float(stitch[1])

        # O primeiro STITCH define o cursor real do desenho.
        if not has_cursor:
            cursor_x, cursor_y = x, y
            has_cursor = True
            points_by_color[-1][-1].append((x, y))
            continue

        # Se o trecho atual esta vazio, adiciona o cursor como ponto de partida
        if not points_by_color[-1][-1]:
            points_by_color[-1][-1].append((cursor_x, cursor_y))

        points_by_color[-1][-1].append((x, y))
        cursor_x, cursor_y = x, y

    # Bounding box global
    all_points = [p for layer in points_by_color for path in layer for p in path]
    if len(all_points) < 2:
        img = Image.new("RGB", (900, 700), (245, 242, 235))
        img.save(out_path)
        return

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)

    span_x = max(1e-6, maxx - minx)
    span_y = max(1e-6, maxy - miny)

    pad = 30

    scale_limit_x = (max_size_px - 2 * pad) / span_x
    scale_limit_y = (max_size_px - 2 * pad) / span_y
    scale_auto = max(0.05, min(scale, scale_limit_x, scale_limit_y))

    w = max(500, min(int(span_x * scale_auto) + pad * 2, max_size_px))
    h = max(400, min(int(span_y * scale_auto) + pad * 2, max_size_px))

    # Fundo estilo tecido (creme com linhas finas de trama)
    FABRIC_BG = (245, 242, 235)
    img = Image.new("RGB", (w, h), FABRIC_BG)
    draw_bg = ImageDraw.Draw(img)
    grid_step = max(4, int(1.0 * scale_auto))
    for gx in range(0, w, grid_step):
        draw_bg.line([(gx, 0), (gx, h)], fill=(238, 235, 228), width=1)
    for gy in range(0, h, grid_step):
        draw_bg.line([(0, gy), (w, gy)], fill=(238, 235, 228), width=1)

    draw = ImageDraw.Draw(img)

    thread_colors = []
    for th in getattr(pattern, "threadlist", []) or []:
        thread_colors.append(_thread_to_rgb(th))

    def map_pt(px, py):
        X = int((px - minx) * scale_auto) + pad
        Y = int((py - miny) * scale_auto) + pad
        return (X, Y)

    # Espessura do fio: fio real ~0.4 mm
    THREAD_DIAM_MM = 0.40
    thread_w = max(2, int(THREAD_DIAM_MM * scale_auto))

    # Passada 1: sombra (escurecimento) - da profundidade
    for i, layer in enumerate(points_by_color):
        color = thread_colors[i] if i < len(thread_colors) else (90, 90, 200)
        shadow = _darken(color, 0.55)
        for path in layer:
            if len(path) < 2:
                continue
            mapped = [map_pt(px, py) for px, py in path]
            draw.line(mapped, fill=shadow, width=thread_w + 2)

    # Passada 2: cor principal do fio
    for i, layer in enumerate(points_by_color):
        color = thread_colors[i] if i < len(thread_colors) else (90, 90, 200)
        for path in layer:
            if len(path) < 2:
                continue
            mapped = [map_pt(px, py) for px, py in path]
            draw.line(mapped, fill=color, width=thread_w)

    # Passada 3: highlight central - simula brilho do fio sintetico
    for i, layer in enumerate(points_by_color):
        color = thread_colors[i] if i < len(thread_colors) else (90, 90, 200)
        highlight = _lighten(color, 65)
        hl_w = max(1, thread_w - 2)
        for path in layer:
            if len(path) < 2:
                continue
            mapped = [map_pt(px, py) for px, py in path]
            draw.line(mapped, fill=highlight, width=hl_w)

    # Passada 4: pontinhos de brilho nos pontos de ancoragem
    dot_r = max(1, thread_w // 2)
    for i, layer in enumerate(points_by_color):
        color = thread_colors[i] if i < len(thread_colors) else (90, 90, 200)
        bright = _lighten(color, 90)
        for path in layer:
            step = max(3, len(path) // 80 + 1)
            for pi in range(0, len(path), step):
                px, py = map_pt(*path[pi])
                draw.ellipse(
                    (px - dot_r, py - dot_r, px + dot_r, py + dot_r),
                    fill=bright,
                )

    # Suavizacao leve para reduzir aliasing
    img = img.filter(ImageFilter.SMOOTH)
    img.save(out_path)
