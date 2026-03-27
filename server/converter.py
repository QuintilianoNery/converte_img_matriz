from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageFilter

from pyembroidery import (
    EmbPattern,
    STITCH,
    JUMP,
    COLOR_CHANGE,
    END,
)

from preview import render_preview


DetailLevel = Literal["low", "medium", "high"]

DETAIL_STEP_MM: dict[DetailLevel, float] = {
    "low": 0.8,
    "medium": 0.45,
    "high": 0.3,
}

SUPPORTED_FORMATS = {"PES", "DST", "JEF", "EXP", "HUS", "VP3"}  # E3D não

@dataclass
class ConvertMeta:
    width_px: int
    height_px: int
    size_cm: int
    mm_per_px: float
    num_colors: int
    detail: str
    out_format: str


def _kmeans_colors(pixels: np.ndarray, k: int, iters: int = 12, seed: int = 42):
    """
    pixels: (N,3) uint8
    Retorna: centers (k,3) float, labels (N,)
    """
    if pixels.size == 0:
        raise ValueError("Imagem sem pixels válidos para quantização.")

    k = max(1, min(int(k), int(pixels.shape[0])))

    rng = np.random.default_rng(seed)
    N = pixels.shape[0]
    # amostrar para performance (se imagem grande)
    sample_n = min(N, 120_000)
    idx = rng.choice(N, size=sample_n, replace=False)
    sample = pixels[idx].astype(np.float32)

    # init centers
    centers = sample[rng.choice(sample.shape[0], size=k, replace=False)]

    for _ in range(iters):
        # distâncias quadráticas
        d2 = ((sample[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = d2.argmin(axis=1)
        new_centers = centers.copy()
        for ci in range(k):
            mask = labels == ci
            if mask.any():
                new_centers[ci] = sample[mask].mean(axis=0)
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers

    # rotular todos os pixels
    pixf = pixels.astype(np.float32)
    d2_all = ((pixf[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    labels_all = d2_all.argmin(axis=1)

    return centers, labels_all


def _vectorize_and_group_rgba(
    img_rgba: Image.Image,
    num_colors: int,
    alpha_threshold: int = 16,
):
    """
    Simula etapa vetorial: suaviza bordas e agrupa cores em regiões sólidas.
    Retorna palette RGB usada, mapa de labels e máscara opaca.
    """
    arr_rgba = np.array(img_rgba, dtype=np.uint8)
    rgb_arr = arr_rgba[:, :, :3].copy()
    alpha = arr_rgba[:, :, 3]
    opaque_mask = alpha >= alpha_threshold

    if not opaque_mask.any():
        raise ValueError("A imagem parece totalmente transparente.")

    # Evita que área transparente influencie criação de paleta.
    fill_rgb = np.median(rgb_arr[opaque_mask], axis=0).astype(np.uint8)
    rgb_arr[~opaque_mask] = fill_rgb

    base = Image.fromarray(rgb_arr, mode="RGB")

    # Suavização para reduzir serrilhado e ruído antes da paleta.
    smooth = base.filter(ImageFilter.MedianFilter(size=5)).filter(ImageFilter.SMOOTH_MORE)

    # Quantização sem dithering gera "blocos" de cor mais vetoriais.
    q = smooth.quantize(
        colors=max(1, int(num_colors)),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    )

    q_idx = np.array(q, dtype=np.int32)
    pal = np.array(q.getpalette(), dtype=np.uint8).reshape(-1, 3)

    # Considerar apenas cores presentes nas áreas opacas e remapear índices.
    used = np.unique(q_idx[opaque_mask])
    remap = {int(old): new for new, old in enumerate(used.tolist())}

    label_img = np.full(q_idx.shape, -1, dtype=np.int32)
    for old, new in remap.items():
        label_img[(q_idx == old) & opaque_mask] = new

    centers_u8 = pal[used]
    return centers_u8, label_img, opaque_mask


def _make_segments_for_mask(mask: np.ndarray, mm_per_px: float, step_mm: float):
    """Gera preenchimento tipo tatami curto (segmentos diagonais curtos)."""
    H, W = mask.shape
    step_px = max(1, int(round(step_mm / mm_per_px)))
    segments_mm: list[tuple[tuple[float, float], tuple[float, float]]] = []

    # Suavização morfológica simples para reduzir ruído de 1 px.
    m = mask.astype(np.uint8)
    nb = (
        m
        + np.roll(m, 1, axis=0)
        + np.roll(m, -1, axis=0)
        + np.roll(m, 1, axis=1)
        + np.roll(m, -1, axis=1)
    )
    mask = nb >= 3

    short_stitch_px = max(2, int(round(2.2 / mm_per_px)))
    slant_px = max(1, step_px // 2)

    # Duas passadas com ângulos opostos para textura mais natural.
    passes = [
        (step_px, slant_px, 0, 3),
        (max(step_px * 2, 1), -slant_px, max(1, step_px // 2), 2),
    ]

    for pass_step, pass_slant, y_offset, phase_div in passes:
        for y in range(y_offset, H, pass_step):
            row = mask[y]
            xs = np.where(row)[0]
            if xs.size == 0:
                continue

            seg_starts = [int(xs[0])]
            seg_ends: list[int] = []
            for i in range(1, xs.size):
                if xs[i] != xs[i - 1] + 1:
                    seg_ends.append(int(xs[i - 1]))
                    seg_starts.append(int(xs[i]))
            seg_ends.append(int(xs[-1]))

            reverse = ((y // max(1, pass_step)) % 2 == 1)
            phase = ((y // max(1, pass_step)) % phase_div) * max(1, short_stitch_px // phase_div)

            for x0, x1 in zip(seg_starts, seg_ends):
                if (x1 - x0 + 1) < 2:
                    continue

                if reverse:
                    x = x1 - phase
                    while x > x0:
                        xa = int(np.clip(x, x0, x1))
                        xb = int(np.clip(x - short_stitch_px, x0, x1))
                        yb = int(np.clip(
                            y + (pass_slant if ((x // max(1, short_stitch_px)) % 2 == 0) else -pass_slant),
                            0,
                            H - 1,
                        ))
                        if not mask[yb, xb]:
                            yb = y
                        segments_mm.append(((xa * mm_per_px, y * mm_per_px), (xb * mm_per_px, yb * mm_per_px)))
                        x -= short_stitch_px
                else:
                    x = x0 + phase
                    while x < x1:
                        xa = int(np.clip(x, x0, x1))
                        xb = int(np.clip(x + short_stitch_px, x0, x1))
                        yb = int(np.clip(
                            y + (pass_slant if ((x // max(1, short_stitch_px)) % 2 == 0) else -pass_slant),
                            0,
                            H - 1,
                        ))
                        if not mask[yb, xb]:
                            yb = y
                        segments_mm.append(((xa * mm_per_px, y * mm_per_px), (xb * mm_per_px, yb * mm_per_px)))
                        x += short_stitch_px

    return segments_mm


def convert_image_to_embroidery(
    input_image_path: Path,
    out_dir: Path,
    size_cm: int,
    out_format: str,
    num_colors: int,
    detail: str,
):
    out_format = out_format.upper().replace(".", "")
    if out_format == "E3D":
        raise ValueError("E3D (Embird nativo) não é suportado nesta versão.")
    if out_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Formato não suportado: {out_format}. Use {sorted(SUPPORTED_FORMATS)}")

    detail = detail.lower()
    if detail not in DETAIL_STEP_MM:
        detail = "medium"
    step_mm = DETAIL_STEP_MM[detail]  # tipo: ignore[index]

    # carregar imagem (preservando alpha para não bordar o fundo transparente)
    img = Image.open(input_image_path).convert("RGBA")

    # reduzir um pouco se for enorme (performance)
    max_side = 900
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    width_px, height_px = img.size

    # mm_per_px para escalar para size_cm na maior dimensão
    target_mm = float(size_cm) * 10.0
    max_dim_px = float(max(width_px, height_px))
    mm_per_px = target_mm / max_dim_px

    # Vetorizar/agrupar imagem antes de gerar pontos de bordado.
    centers_u8, label_img, opaque_mask = _vectorize_and_group_rgba(
        img,
        num_colors=num_colors,
    )

    # ordenar cores por frequência (para reduzir troca de cores muito “ruins”)
    labels_used = label_img[opaque_mask]
    counts = np.bincount(labels_used, minlength=int(centers_u8.shape[0]))
    order = np.argsort(-counts)

    pattern = EmbPattern()

    # adicionar uma cor “inicial” para o primeiro bloco
    # (pyembroidery usa threadlist; aqui colocamos RGB aproximado como metadado)
    # Vamos inserir as cores na ordem em que vamos bordar.
    for ci in order:
        r, g, b = map(int, centers_u8[ci])
        pattern.add_thread({"color": (r << 16) | (g << 8) | b, "description": f"c{ci}"})

    # gerar stitches por cor
    first_color = True
    total_stitches = 0
    max_stitch_mm = 2.8
    connect_travel_mm = 4.0
    cursor_x = 0.0
    cursor_y = 0.0

    for oi, ci in enumerate(order):
        if counts[ci] == 0:
            continue

        # máscara da cor
        mask = label_img == int(ci)

        segments = _make_segments_for_mask(mask, mm_per_px=mm_per_px, step_mm=step_mm)
        if not segments:
            continue

        # troca de cor (exceto primeira)
        if not first_color:
            pattern.add_command(COLOR_CHANGE)
        first_color = False

        # pyembroidery espera coordenadas relativas ao cursor global do padrão.
        # Usamos JUMP entre segmentos para não costurar atravessando áreas vazias.
        for (x0, y0), (x1, y1) in segments:
            travel = math.hypot(x0 - cursor_x, y0 - cursor_y)
            if travel <= connect_travel_mm:
                pattern.add_stitch_relative(STITCH, x0 - cursor_x, y0 - cursor_y)
                total_stitches += 1
            else:
                pattern.add_stitch_relative(JUMP, x0 - cursor_x, y0 - cursor_y)
            cursor_x, cursor_y = x0, y0

            # Dividir segmentos longos em vários pontos melhora o preenchimento
            # e evita pontos muito extensos em formatos com limites de distância.
            span = max(abs(x1 - x0), abs(y1 - y0))
            steps = max(1, int(np.ceil(span / max_stitch_mm)))
            for si in range(1, steps + 1):
                tx = x0 + (x1 - x0) * (si / steps)
                ty = y0 + (y1 - y0) * (si / steps)
                pattern.add_stitch_relative(STITCH, tx - cursor_x, ty - cursor_y)
                cursor_x, cursor_y = tx, ty
                total_stitches += 1

        # total_stitches contabiliza apenas comandos STITCH.

    pattern.add_command(END)

    # salvar arquivo
    out_ext = out_format.lower()
    out_path = out_dir / f"output.{out_ext}"
    pattern.write(str(out_path))

    # gerar preview PNG
    preview_path = out_dir / "preview.png"
    render_preview(pattern, preview_path)

    meta = ConvertMeta(
        width_px=width_px,
        height_px=height_px,
        size_cm=size_cm,
        mm_per_px=mm_per_px,
        num_colors=num_colors,
        detail=detail,
        out_format=out_format,
    ).__dict__
    meta["total_stitches_approx"] = total_stitches
    meta["step_mm"] = step_mm

    return preview_path, out_path, meta