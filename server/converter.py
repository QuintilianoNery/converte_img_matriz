from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from pyembroidery import (
    EmbPattern,
    STITCH,
    COLOR_CHANGE,
    END,
)

from preview import render_preview


DetailLevel = Literal["low", "medium", "high"]

DETAIL_STEP_MM: dict[DetailLevel, float] = {
    "low": 3.0,
    "medium": 2.0,
    "high": 1.4,
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


def _make_stitches_for_mask(mask: np.ndarray, mm_per_px: float, step_mm: float):
    """
    mask: (H,W) bool
    Gera pontos por varredura (linhas horizontais) dentro da área.
    Retorna lista de (x_mm, y_mm) relativos (0,0) no canto superior esquerdo.
    """
    H, W = mask.shape
    step_px = max(1, int(round(step_mm / mm_per_px)))
    stitches: list[tuple[float, float]] = []

    for y in range(0, H, step_px):
        row = mask[y]
        if not row.any():
            continue

        # achar segmentos contínuos
        xs = np.where(row)[0]
        if xs.size == 0:
            continue

        # segmentar por gaps
        seg_starts = [xs[0]]
        seg_ends = []
        for i in range(1, xs.size):
            if xs[i] != xs[i - 1] + 1:
                seg_ends.append(xs[i - 1])
                seg_starts.append(xs[i])
        seg_ends.append(xs[-1])

        # alternar sentido para minimizar saltos
        reverse = ((y // step_px) % 2 == 1)
        segments = list(zip(seg_starts, seg_ends))
        if reverse:
            segments = list(reversed(segments))

        for x0, x1 in segments:
            if reverse:
                x0, x1 = x1, x0
            stitches.append((x0 * mm_per_px, y * mm_per_px))
            stitches.append((x1 * mm_per_px, y * mm_per_px))

    return stitches


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

    # carregar imagem
    img = Image.open(input_image_path).convert("RGB")

    # reduzir um pouco se for enorme (performance)
    max_side = 900
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    width_px, height_px = img.size

    # mm_per_px para escalar para size_cm na maior dimensão
    target_mm = float(size_cm) * 10.0
    max_dim_px = float(max(width_px, height_px))
    mm_per_px = target_mm / max_dim_px

    # converter para array
    arr = np.array(img, dtype=np.uint8)
    flat = arr.reshape(-1, 3)

    # kmeans quantização
    centers, labels = _kmeans_colors(flat, k=num_colors, iters=14)
    centers_u8 = np.clip(np.rint(centers), 0, 255).astype(np.uint8)

    # reconstruir imagem quantizada
    q_flat = centers_u8[labels]
    q_img = q_flat.reshape(height_px, width_px, 3)

    # ordenar cores por frequência (para reduzir troca de cores muito “ruins”)
    counts = np.bincount(labels, minlength=num_colors)
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

    for oi, ci in enumerate(order):
        if counts[ci] == 0:
            continue

        # máscara da cor
        color = centers_u8[ci]
        mask = np.all(q_img == color[None, None, :], axis=2)

        stitches = _make_stitches_for_mask(mask, mm_per_px=mm_per_px, step_mm=step_mm)
        if len(stitches) < 2:
            continue

        # troca de cor (exceto primeira)
        if not first_color:
            pattern.add_command(COLOR_CHANGE)
        first_color = False

        # adicionar pontos (STITCH)
        # pyembroidery espera coordenadas relativas (em unidades internas). Usaremos mm.
        # converter para "deltas" (movimentos) a partir do ponto anterior
        last_x, last_y = 0.0, 0.0
        for x, y in stitches:
            dx = x - last_x
            dy = y - last_y
            pattern.add_stitch_relative(STITCH, dx, dy)
            last_x, last_y = x, y

        total_stitches += len(stitches)

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