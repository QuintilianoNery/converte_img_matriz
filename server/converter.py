from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageFilter

from pyembroidery import (
    EmbPattern,
    EmbThread,
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

FILL_TYPE_ALIASES = {
    "tatami": "tatami",
    "ponto de preenchimento": "tatami",
    "ponto preenchimento": "tatami",
    "fill": "tatami",
    "ponto cheio": "satin",
    "satin": "satin",
    "ponto de preenchimento prog": "prog_fill",
    "prog_fill": "prog_fill",
    "ponto de enfeite": "ornamental",
    "ponto ornamental": "ornamental",
    "ornamental": "ornamental",
    "ponto cruz": "cross",
    "cross": "cross",
    "ponto em circulo concentrico": "concentric",
    "concentrico": "concentric",
    "concentric": "concentric",
    "ponto radial": "radial",
    "radial": "radial",
    "ponto espiral": "spiral",
    "espiral": "spiral",
    "spiral": "spiral",
    "ponto pontilhado": "stipple",
    "pontilhado": "stipple",
    "stipple": "stipple",
    "ponto de preenchimento em rede": "network",
    "rede": "network",
    "network": "network",
    "ponto de preenchimento em zigzag": "zigzag",
    "zigzag": "zigzag",
}

OUTLINE_TYPE_ALIASES = {
    "satin": "satin",
    "coluna": "satin",
    "zig-zag": "satin",
    "zigzag": "satin",
    "running": "running",
    "running stitch": "running",
    "ponto corrido": "running",
    "triple": "triple",
    "triple stitch": "triple",
    "ponto triplo": "triple",
    "bean": "bean",
    "bean stitch": "bean",
    "e": "e_stitch",
    "e-stitch": "e_stitch",
    "e stitch": "e_stitch",
    "cover": "cover",
    "cover stitch": "cover",
}

DENSITY_FACTORS = {
    "low": 1.35,
    "medium": 1.0,
    "high": 0.75,
}

UNDERLAY_FACTORS = {
    "none": 0.0,
    "low": 2.1,
    "medium": 1.65,
    "high": 1.25,
}

QUALITY_PRESETS = {
    "leve": {
        "density": "low",
        "underlay": "low",
        "shrink_comp_mm": 0.25,
        "outline": True,
        "outline_step_mult": 1.2,
        "border_width_mm": 0.7,
        "outline_type": "running",
        "outline_width_mm": 1.0,
        "outline_pull_comp_mm": 0.2,
        "outline_overlap_mm": 0.3,
    },
    "medio": {
        "density": "medium",
        "underlay": "medium",
        "shrink_comp_mm": 0.4,
        "outline": True,
        "outline_step_mult": 1.0,
        "border_width_mm": 0.9,
        "outline_type": "satin",
        "outline_width_mm": 1.5,
        "outline_pull_comp_mm": 0.3,
        "outline_overlap_mm": 0.4,
    },
    "premium": {
        "density": "high",
        "underlay": "high",
        "shrink_comp_mm": 0.5,
        "outline": True,
        "outline_step_mult": 0.75,
        "border_width_mm": 1.15,
        "outline_keepout_mm": 0.0,
        "outline_type": "satin",
        "outline_width_mm": 1.8,
        "outline_pull_comp_mm": 0.35,
        "outline_overlap_mm": 0.45,
    },
    "premium_clean": {
        "density": "high",
        "underlay": "medium",
        "shrink_comp_mm": 0.35,
        "outline": True,
        "outline_step_mult": 1.35,
        "border_width_mm": 0.75,
        "outline_keepout_mm": 0.45,
        "outline_type": "satin",
        "outline_width_mm": 1.4,
        "outline_pull_comp_mm": 0.3,
        "outline_overlap_mm": 0.35,
    },
}

@dataclass
class ConvertMeta:
    width_px: int
    height_px: int
    size_cm: int
    mm_per_px: float
    num_colors: int
    detail: str
    out_format: str


def _normalize_fill_type(value: str | None) -> str:
    if not value:
        return "tatami"
    key = str(value).strip().lower()
    return FILL_TYPE_ALIASES.get(key, "tatami")


def _normalize_quality_preset(value: str | None) -> str:
    if not value:
        return "medio"
    v = str(value).strip().lower()
    if v in QUALITY_PRESETS:
        return v
    if v in {"premium clean", "premium-clean", "clean premium"}:
        return "premium_clean"
    if v == "médio":
        return "medio"
    return "medio"


def _normalize_outline_type(value: str | None) -> str:
    if not value:
        return "satin"
    key = str(value).strip().lower()
    return OUTLINE_TYPE_ALIASES.get(key, "satin")


def _normalize_underlay(value: str | None, default: str = "medium") -> str:
    if value is None:
        return default
    key = str(value).strip().lower()
    if key in {"none", "off", "disabled", "desligado", "desligada"}:
        return "none"
    if key in UNDERLAY_FACTORS:
        return key
    return default


def _parse_hex_color(value: str | None):
    if not value:
        return None
    s = value.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


def _as_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "sim", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "nao", "não", "no", "n", "off"}:
            return False
    return default


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


def _find_components(mask: np.ndarray, min_area_px: int = 36):
    """Connected components 4-neighborhood returning metadata per object."""
    H, W = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    object_map = np.full((H, W), -1, dtype=np.int32)
    objects = []
    next_id = 0

    for y in range(H):
        for x in range(W):
            if not mask[y, x] or visited[y, x]:
                continue

            q = deque([(y, x)])
            visited[y, x] = True
            pixels = []
            minx = maxx = x
            miny = maxy = y

            while q:
                cy, cx = q.popleft()
                pixels.append((cy, cx))
                if cx < minx:
                    minx = cx
                if cx > maxx:
                    maxx = cx
                if cy < miny:
                    miny = cy
                if cy > maxy:
                    maxy = cy

                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if ny < 0 or ny >= H or nx < 0 or nx >= W:
                        continue
                    if visited[ny, nx] or not mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    q.append((ny, nx))

            area = len(pixels)
            if area < min_area_px:
                continue

            for py, px in pixels:
                object_map[py, px] = next_id

            objects.append(
                {
                    "id": next_id,
                    "area_px": area,
                    "bbox": [int(minx), int(miny), int(maxx), int(maxy)],
                }
            )
            next_id += 1

    return objects, object_map


def _recommend_autopunch_settings(
    *,
    width_px: int,
    height_px: int,
    opaque_mask: np.ndarray,
    color_counts: np.ndarray,
    requested_colors: int,
    requested_detail: str,
) -> dict:
    total_px = max(1, width_px * height_px)
    opaque_px = int(np.count_nonzero(opaque_mask))
    coverage = opaque_px / float(total_px)

    used_counts = color_counts[color_counts > 0]
    used_colors = int(used_counts.size)
    dominant_ratio = float(used_counts.max() / max(1, opaque_px)) if used_counts.size else 1.0
    micro_colors = int(np.count_nonzero(used_counts < max(40, int(opaque_px * 0.01))))

    boundary_ratio = 0.0
    if opaque_px > 0:
        boundary_ratio = float(np.count_nonzero(_boundary_mask(opaque_mask)) / opaque_px)

    detail_score = boundary_ratio * 1.4 + (1.0 - dominant_ratio) * 0.8 + min(1.0, micro_colors / 8.0) * 0.45

    if detail_score >= 1.1:
        rec_detail = "high"
        rec_preset = "premium_clean"
    elif detail_score >= 0.72:
        rec_detail = "medium"
        rec_preset = "premium"
    else:
        rec_detail = "medium" if requested_detail == "high" else "low"
        rec_preset = "medio" if coverage > 0.22 else "leve"

    rec_colors = int(max(4, min(24, round(used_colors + max(0, micro_colors // 2)))))
    rec_colors = int(max(4, min(24, round((rec_colors * 0.6) + (requested_colors * 0.4)))))

    preset = QUALITY_PRESETS[rec_preset]
    global_cfg = {
        "fill_type": "tatami",
        "density": preset["density"],
        "shrink_comp_mm": float(preset["shrink_comp_mm"]),
        "underlay": preset["underlay"],
        "outline_type": preset.get("outline_type", "satin"),
        "outline_width_mm": float(preset.get("outline_width_mm", 1.5)),
        "outline_pull_comp_mm": float(preset.get("outline_pull_comp_mm", 0.3)),
        "outline_overlap_mm": float(preset.get("outline_overlap_mm", 0.4)),
        "outline_keepout_mm": float(preset.get("outline_keepout_mm", 0.0)),
    }

    return {
        "quality_preset": rec_preset,
        "detail": rec_detail,
        "colors": rec_colors,
        "global": global_cfg,
        "metrics": {
            "coverage": round(coverage, 4),
            "boundary_ratio": round(boundary_ratio, 4),
            "used_colors": used_colors,
            "dominant_ratio": round(dominant_ratio, 4),
            "detail_score": round(detail_score, 4),
        },
    }


def analyze_image_for_autopunch(
    input_image_path: Path,
    num_colors: int,
    detail: str = "medium",
    quality_preset: str = "medio",
):
    """Retorna objetos agrupados com configuração inicial editável."""
    requested_preset = _normalize_quality_preset(quality_preset)
    requested_detail = str(detail or "medium").strip().lower()
    if requested_detail not in DETAIL_STEP_MM:
        requested_detail = "medium"

    img = Image.open(input_image_path).convert("RGBA")
    max_side = 900
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    centers_u8, label_img, opaque_mask = _vectorize_and_group_rgba(img, num_colors=num_colors)

    labels_used = label_img[opaque_mask]
    counts = np.bincount(labels_used, minlength=int(centers_u8.shape[0]))
    order = np.argsort(-counts)

    recommended = _recommend_autopunch_settings(
        width_px=img.size[0],
        height_px=img.size[1],
        opaque_mask=opaque_mask,
        color_counts=counts,
        requested_colors=int(num_colors),
        requested_detail=requested_detail,
    )
    if requested_preset in {"premium", "premium_clean"}:
        recommended["quality_preset"] = requested_preset
        recommended["global"] = {
            **recommended.get("global", {}),
            **QUALITY_PRESETS[requested_preset],
            "fill_type": "tatami",
        }

    preset_name = _normalize_quality_preset(recommended.get("quality_preset", requested_preset))
    preset = QUALITY_PRESETS[preset_name]
    global_cfg = recommended.get("global", {}) if isinstance(recommended, dict) else {}
    rec_detail = str(recommended.get("detail", requested_detail))

    out_objects = []
    for ci in order.tolist():
        if ci < 0 or counts[ci] == 0:
            continue
        color_mask = label_img == int(ci)
        comps, _ = _find_components(color_mask)
        r, g, b = map(int, centers_u8[ci])
        for comp in comps:
            oid = f"c{ci}_o{comp['id']}"
            out_objects.append(
                {
                    "id": oid,
                    "label_index": int(ci),
                    "bbox": comp["bbox"],
                    "area_px": comp["area_px"],
                    "enabled": True,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "fill_type": str(global_cfg.get("fill_type", "tatami")),
                    "density": str(global_cfg.get("density", preset["density"])),
                    "shrink_comp_mm": float(global_cfg.get("shrink_comp_mm", preset["shrink_comp_mm"])),
                    "underlay": str(global_cfg.get("underlay", preset["underlay"])),
                    "outline_keepout_mm": float(global_cfg.get("outline_keepout_mm", preset.get("outline_keepout_mm", 0.0))),
                    "outline_type": str(global_cfg.get("outline_type", preset.get("outline_type", "satin"))),
                    "outline_width_mm": float(global_cfg.get("outline_width_mm", preset.get("outline_width_mm", 1.5))),
                    "outline_pull_comp_mm": float(global_cfg.get("outline_pull_comp_mm", preset.get("outline_pull_comp_mm", 0.3))),
                    "outline_overlap_mm": float(global_cfg.get("outline_overlap_mm", preset.get("outline_overlap_mm", 0.4))),
                }
            )

    return {
        "objects": out_objects,
        "defaults": {
            "fill_type": str(global_cfg.get("fill_type", "tatami")),
            "density": str(global_cfg.get("density", preset["density"])),
            "shrink_comp_mm": float(global_cfg.get("shrink_comp_mm", preset["shrink_comp_mm"])),
            "underlay": str(global_cfg.get("underlay", preset["underlay"])),
            "outline_keepout_mm": float(global_cfg.get("outline_keepout_mm", preset.get("outline_keepout_mm", 0.0))),
            "outline_type": str(global_cfg.get("outline_type", preset.get("outline_type", "satin"))),
            "outline_width_mm": float(global_cfg.get("outline_width_mm", preset.get("outline_width_mm", 1.5))),
            "outline_pull_comp_mm": float(global_cfg.get("outline_pull_comp_mm", preset.get("outline_pull_comp_mm", 0.3))),
            "outline_overlap_mm": float(global_cfg.get("outline_overlap_mm", preset.get("outline_overlap_mm", 0.4))),
            "quality_preset": preset_name,
            "detail": rec_detail,
        },
        "recommended": recommended,
        "image_size": {"width": img.size[0], "height": img.size[1]},
    }


def _dilate_once(mask: np.ndarray):
    p = np.pad(mask, 1, mode="constant", constant_values=False)
    return (
        p[1:-1, 1:-1]
        | p[:-2, 1:-1]
        | p[2:, 1:-1]
        | p[1:-1, :-2]
        | p[1:-1, 2:]
        | p[:-2, :-2]
        | p[:-2, 2:]
        | p[2:, :-2]
        | p[2:, 2:]
    )


def _erode_once(mask: np.ndarray):
    p = np.pad(mask, 1, mode="constant", constant_values=False)
    return (
        p[1:-1, 1:-1]
        & p[:-2, 1:-1]
        & p[2:, 1:-1]
        & p[1:-1, :-2]
        & p[1:-1, 2:]
        & p[:-2, :-2]
        & p[:-2, 2:]
        & p[2:, :-2]
        & p[2:, 2:]
    )


def _erode_n(mask: np.ndarray, iterations: int):
    out = mask.copy()
    for _ in range(max(0, iterations)):
        out = _erode_once(out)
        if not out.any():
            break
    return out


def _dilate_n(mask: np.ndarray, iterations: int):
    out = mask.copy()
    for _ in range(max(0, iterations)):
        out = _dilate_once(out)
    return out


def _boundary_mask(mask: np.ndarray):
    er = _erode_once(mask)
    return mask & (~er)


def _point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return math.hypot(px - ax, py - ay)
    c2 = vx * vx + vy * vy
    if c2 <= 1e-9:
        return math.hypot(px - ax, py - ay)
    t = min(1.0, max(0.0, c1 / c2))
    qx = ax + t * vx
    qy = ay + t * vy
    return math.hypot(px - qx, py - qy)


def _douglas_peucker(path: list[tuple[int, int]], epsilon: float):
    if len(path) < 3:
        return path

    ax, ay = path[0][1], path[0][0]
    bx, by = path[-1][1], path[-1][0]
    max_dist = -1.0
    index = -1
    for i in range(1, len(path) - 1):
        px, py = path[i][1], path[i][0]
        d = _point_segment_distance(px, py, ax, ay, bx, by)
        if d > max_dist:
            max_dist = d
            index = i

    if max_dist <= epsilon or index < 0:
        return [path[0], path[-1]]

    left = _douglas_peucker(path[: index + 1], epsilon)
    right = _douglas_peucker(path[index:], epsilon)
    return left[:-1] + right


def _adaptive_density_multiplier(area_px: int) -> float:
    """Increase step for large objects to reduce points while preserving small details."""
    if area_px <= 600:
        return 0.86
    if area_px <= 1800:
        return 1.0
    if area_px <= 5000:
        return 1.12
    if area_px <= 12000:
        return 1.24
    return 1.36


def _neighbors8(pt: tuple[int, int]):
    y, x = pt
    return (
        (y - 1, x - 1),
        (y - 1, x),
        (y - 1, x + 1),
        (y, x - 1),
        (y, x + 1),
        (y + 1, x - 1),
        (y + 1, x),
        (y + 1, x + 1),
    )


def _trace_boundary_polylines(boundary_mask: np.ndarray, min_len_px: int = 8):
    """Trace connected boundary pixels into ordered polyline paths."""
    comps, comp_map = _find_components(boundary_mask, min_area_px=max(8, min_len_px))
    polylines: list[list[tuple[int, int]]] = []

    for comp in comps:
        cid = int(comp["id"])
        ys, xs = np.where(comp_map == cid)
        if ys.size < min_len_px:
            continue

        points = {(int(y), int(x)) for y, x in zip(ys.tolist(), xs.tolist())}
        if not points:
            continue

        degree = {}
        for p in points:
            degree[p] = sum(1 for n in _neighbors8(p) if n in points)

        remaining = set(points)
        while remaining:
            endpoints = [p for p in remaining if degree.get(p, 0) <= 1]
            start = endpoints[0] if endpoints else min(remaining)

            path = [start]
            remaining.remove(start)
            prev = None
            cur = start

            while True:
                candidates = [n for n in _neighbors8(cur) if n in points and n != prev]
                if not candidates:
                    break

                # Prefer unvisited neighbor and smoother continuation.
                unvisited = [n for n in candidates if n in remaining]
                if not unvisited:
                    break

                if prev is None:
                    nxt = min(unvisited)
                else:
                    vy = cur[0] - prev[0]
                    vx = cur[1] - prev[1]

                    def _score(pt):
                        dy = pt[0] - cur[0]
                        dx = pt[1] - cur[1]
                        return (vx * dx + vy * dy, -abs(dx), -abs(dy))

                    nxt = max(unvisited, key=_score)

                path.append(nxt)
                remaining.remove(nxt)
                prev, cur = cur, nxt

            if len(path) >= min_len_px:
                polylines.append(path)

    return polylines


def _vector_outline_polylines(boundary_mask: np.ndarray, mm_per_px: float, step_mm: float):
    """Return smoothed vector-like contour polylines in mm coordinates."""
    if not boundary_mask.any():
        return []

    step_px = max(1, int(round(step_mm / max(mm_per_px, 1e-6))))
    max_edge_px = max(3.0, step_px * 2.8)
    polylines = _trace_boundary_polylines(boundary_mask, min_len_px=max(8, step_px * 2))
    polylines_mm: list[list[tuple[float, float]]] = []

    for path in polylines:
        epsilon_px = max(0.6, step_px * 0.35)
        path = _douglas_peucker(path, epsilon=epsilon_px)
        sampled = path[::step_px]
        if sampled[-1] != path[-1]:
            sampled.append(path[-1])
        if len(sampled) < 2:
            continue

        clean: list[tuple[float, float]] = []
        for i in range(len(sampled) - 1):
            y0, x0 = sampled[i]
            y1, x1 = sampled[i + 1]
            if math.hypot(x1 - x0, y1 - y0) > max_edge_px:
                continue
            if not clean:
                clean.append((x0 * mm_per_px, y0 * mm_per_px))
            clean.append((x1 * mm_per_px, y1 * mm_per_px))

        if len(clean) >= 2:
            polylines_mm.append(clean)

    return polylines_mm


def _outline_segments_from_polyline(
    polyline_mm: list[tuple[float, float]],
    outline_type: str,
    width_mm: float,
    step_mm: float,
    pull_comp_mm: float,
):
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    if len(polyline_mm) < 2:
        return segments

    outline_type = _normalize_outline_type(outline_type)
    width_eff = max(0.2, width_mm + pull_comp_mm)

    def add_running(points: list[tuple[float, float]], repeats: int = 1):
        if len(points) < 2:
            return
        for _ in range(max(1, repeats)):
            for i in range(len(points) - 1):
                segments.append((points[i], points[i + 1]))

    if outline_type == "running":
        add_running(polyline_mm, repeats=1)
        return segments

    if outline_type == "triple":
        add_running(polyline_mm, repeats=3)
        return segments

    if outline_type == "bean":
        add_running(polyline_mm, repeats=2)
        return segments

    sample_step = max(0.35, step_mm)
    half_w = max(0.1, width_eff * 0.5)

    for i in range(len(polyline_mm) - 1):
        x0, y0 = polyline_mm[i]
        x1, y1 = polyline_mm[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue

        ux = dx / L
        uy = dy / L
        nx = -uy
        ny = ux
        n_samples = max(1, int(math.ceil(L / sample_step)))

        if outline_type in {"satin", "cover"}:
            for s in range(n_samples + 1):
                t = s / n_samples
                px = x0 + dx * t
                py = y0 + dy * t
                a = (px + nx * half_w, py + ny * half_w)
                b = (px - nx * half_w, py - ny * half_w)
                segments.append((a, b))
            continue

        if outline_type == "e_stitch":
            for s in range(n_samples + 1):
                t = s / n_samples
                px = x0 + dx * t
                py = y0 + dy * t
                c = (px, py)
                a = (px + nx * half_w, py + ny * half_w)
                b = (px - nx * half_w, py - ny * half_w)
                segments.append((c, a))
                segments.append((a, c))
                segments.append((c, b))
            continue

        # fallback seguro
        segments.append(((x0, y0), (x1, y1)))

    return segments


def _vector_outline_segments(
    boundary_mask: np.ndarray,
    mm_per_px: float,
    step_mm: float,
    outline_type: str,
    width_mm: float,
    pull_comp_mm: float,
):
    polylines = _vector_outline_polylines(boundary_mask, mm_per_px=mm_per_px, step_mm=step_mm)
    out: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for poly in polylines:
        out.extend(
            _outline_segments_from_polyline(
                poly,
                outline_type=outline_type,
                width_mm=width_mm,
                step_mm=step_mm,
                pull_comp_mm=pull_comp_mm,
            )
        )
    return out


def _apply_shrink_comp(mask: np.ndarray, mm_per_px: float, shrink_comp_mm: float):
    if shrink_comp_mm <= 0:
        return mask
    iterations = int(max(0, round(shrink_comp_mm / max(mm_per_px, 1e-6))))
    out = mask.copy()
    for _ in range(iterations):
        out = _dilate_once(out)
    return out


def _make_segments_for_mask(mask: np.ndarray, mm_per_px: float, step_mm: float, fill_type: str = "tatami"):
    """Gera preenchimento tipo tatami curto (segmentos diagonais curtos)."""
    H, W = mask.shape
    fill_type = _normalize_fill_type(fill_type)
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

    if fill_type in {"ornamental", "stipple"}:
        short_stitch_px = max(1, short_stitch_px // 2)
    elif fill_type == "satin":
        short_stitch_px = max(3, int(round(3.2 / mm_per_px)))
        step_px = max(1, int(round(step_px * 0.8)))
    elif fill_type == "prog_fill":
        step_px = max(1, int(round(step_px * 0.85)))
    elif fill_type == "zigzag":
        slant_px = max(2, step_px)

    # Duas passadas com ângulos opostos para textura mais natural.
    if fill_type in {"cross", "network"}:
        passes = [
            (step_px, slant_px, 0, 3),
            (max(step_px, 1), -slant_px, max(1, step_px // 2), 2),
            (max(step_px * 2, 1), 0, max(1, step_px // 3), 2),
        ]
    elif fill_type in {"radial", "concentric", "spiral", "ornamental", "stipple"}:
        passes = [
            (step_px, slant_px, 0, 3),
        ]
    else:
        passes = [
            (step_px, slant_px, 0, 3),
            (max(step_px * 2, 1), -slant_px, max(1, step_px // 2), 2),
        ]

    ys, xs = np.where(mask)
    cx = float(xs.mean()) if xs.size else 0.0
    cy = float(ys.mean()) if ys.size else 0.0

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
                        yb = int(np.clip(y + (pass_slant if ((x // max(1, short_stitch_px)) % 2 == 0) else -pass_slant), 0, H - 1))
                        if fill_type in {"radial", "concentric", "spiral", "ornamental", "stipple"}:
                            ang = math.atan2(y - cy, xa - cx)
                            if fill_type == "radial":
                                ang = ang
                            elif fill_type == "concentric":
                                ang = ang + math.pi / 2.0
                            elif fill_type == "spiral":
                                r = math.hypot(xa - cx, y - cy)
                                ang = ang + (r * 0.02)
                            elif fill_type == "ornamental":
                                ang = ang + (((xa + y) % 11) - 5) * 0.08
                            else:  # stipple
                                h = (xa * 73856093) ^ (y * 19349663)
                                ang = (h % 360) * math.pi / 180.0
                            xb = int(np.clip(xa + math.cos(ang) * short_stitch_px, x0, x1))
                            yb = int(np.clip(y + math.sin(ang) * short_stitch_px, 0, H - 1))
                        if not mask[yb, xb]:
                            yb = y
                        segments_mm.append(((xa * mm_per_px, y * mm_per_px), (xb * mm_per_px, yb * mm_per_px)))
                        x -= short_stitch_px
                else:
                    x = x0 + phase
                    while x < x1:
                        xa = int(np.clip(x, x0, x1))
                        xb = int(np.clip(x + short_stitch_px, x0, x1))
                        yb = int(np.clip(y + (pass_slant if ((x // max(1, short_stitch_px)) % 2 == 0) else -pass_slant), 0, H - 1))
                        if fill_type in {"radial", "concentric", "spiral", "ornamental", "stipple"}:
                            ang = math.atan2(y - cy, xa - cx)
                            if fill_type == "radial":
                                ang = ang
                            elif fill_type == "concentric":
                                ang = ang + math.pi / 2.0
                            elif fill_type == "spiral":
                                r = math.hypot(xa - cx, y - cy)
                                ang = ang + (r * 0.02)
                            elif fill_type == "ornamental":
                                ang = ang + (((xa + y) % 11) - 5) * 0.08
                            else:  # stipple
                                h = (xa * 73856093) ^ (y * 19349663)
                                ang = (h % 360) * math.pi / 180.0
                            xb = int(np.clip(xa + math.cos(ang) * short_stitch_px, x0, x1))
                            yb = int(np.clip(y + math.sin(ang) * short_stitch_px, 0, H - 1))
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
    design_config: dict | None = None,
    quality_preset: str = "medio",
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

    quality_preset = _normalize_quality_preset(quality_preset)

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

    # Quebrar cada cor em objetos/ilhas para permitir edição objeto a objeto.
    default_objects = []
    for ci in order.tolist():
        if ci < 0 or counts[ci] == 0:
            continue
        comps, comp_map = _find_components(label_img == int(ci))
        r, g, b = map(int, centers_u8[ci])
        for comp in comps:
            oid = f"c{ci}_o{comp['id']}"
            default_objects.append(
                {
                    "id": oid,
                    "label_index": int(ci),
                    "component_index": int(comp["id"]),
                    "bbox": comp["bbox"],
                    "area_px": comp["area_px"],
                    "enabled": True,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "fill_type": "tatami",
                    "density": "medium",
                    "shrink_comp_mm": 0.4,
                    "underlay": "medium",
                    "_component_map": comp_map,
                }
            )

    cfg_global = (design_config or {}).get("global", {}) if isinstance(design_config, dict) else {}
    preset_name = _normalize_quality_preset(cfg_global.get("quality_preset", quality_preset))
    preset = QUALITY_PRESETS[preset_name]
    cfg_objects = (design_config or {}).get("objects", []) if isinstance(design_config, dict) else []
    cfg_by_id = {str(o.get("id")): o for o in cfg_objects if isinstance(o, dict) and "id" in o}

    global_density = str(cfg_global.get("density", preset["density"])).lower()
    global_underlay = _normalize_underlay(cfg_global.get("underlay", preset["underlay"]), preset["underlay"])
    global_shrink = float(cfg_global.get("shrink_comp_mm", preset["shrink_comp_mm"]))
    global_outline = bool(cfg_global.get("outline", preset["outline"]))
    global_outline_mult = float(cfg_global.get("outline_step_mult", preset["outline_step_mult"]))
    global_border_width_mm = float(cfg_global.get("border_width_mm", preset["border_width_mm"]))
    global_outline_keepout_mm = float(cfg_global.get("outline_keepout_mm", preset.get("outline_keepout_mm", 0.0)))
    global_outline_type = _normalize_outline_type(cfg_global.get("outline_type", preset.get("outline_type", "satin")))
    global_outline_width_mm = float(cfg_global.get("outline_width_mm", preset.get("outline_width_mm", 1.5)))
    global_outline_pull_comp_mm = float(cfg_global.get("outline_pull_comp_mm", preset.get("outline_pull_comp_mm", 0.3)))
    global_outline_overlap_mm = float(cfg_global.get("outline_overlap_mm", preset.get("outline_overlap_mm", 0.4)))

    objects = []
    for obj in default_objects:
        o = obj.copy()
        user_o = cfg_by_id.get(o["id"], {})
        if isinstance(user_o, dict):
            o["enabled"] = _as_bool(user_o.get("enabled", o["enabled"]), bool(o["enabled"]))
            o["fill_type"] = _normalize_fill_type(user_o.get("fill_type", o["fill_type"]))
            o["density"] = str(user_o.get("density", o["density"])).lower()
            o["underlay"] = _normalize_underlay(user_o.get("underlay", o["underlay"]), o["underlay"])
            o["shrink_comp_mm"] = float(user_o.get("shrink_comp_mm", o["shrink_comp_mm"]))
            o["color"] = str(user_o.get("color", o["color"]))
            o["outline"] = _as_bool(user_o.get("outline", global_outline), global_outline)
            o["border_width_mm"] = float(user_o.get("border_width_mm", global_border_width_mm))
            o["outline_type"] = _normalize_outline_type(user_o.get("outline_type", global_outline_type))
            o["outline_width_mm"] = float(user_o.get("outline_width_mm", global_outline_width_mm))
            o["outline_pull_comp_mm"] = float(user_o.get("outline_pull_comp_mm", global_outline_pull_comp_mm))
            o["outline_overlap_mm"] = float(user_o.get("outline_overlap_mm", global_outline_overlap_mm))
        objects.append(o)

    pattern = EmbPattern()

    # Criar threadlist na ordem de objetos habilitados (objeto a objeto).
    enabled_objects = [o for o in objects if o.get("enabled", True)]
    for o in enabled_objects:
        rgb = _parse_hex_color(o.get("color"))
        if rgb is None:
            ci = int(o["label_index"])
            rgb = tuple(map(int, centers_u8[ci]))
        r, g, b = rgb
        thread = EmbThread()
        thread.set_color(int(r), int(g), int(b))
        thread.description = str(o["id"])
        pattern.add_thread(thread)

    # gerar stitches por cor
    first_color = True
    total_stitches = 0
    max_stitch_mm = 2.8
    connect_travel_mm = 4.0
    cursor_x = 0.0
    cursor_y = 0.0

    for oi, obj in enumerate(enabled_objects):
        ci = int(obj["label_index"])
        if counts[ci] == 0:
            continue

        comp_map = obj.get("_component_map")
        if not isinstance(comp_map, np.ndarray):
            continue
        comp_idx = int(obj.get("component_index", -1))
        mask = comp_map == comp_idx
        if not mask.any():
            continue

        density = str(obj.get("density", global_density)).lower()
        density_factor = DENSITY_FACTORS.get(density, DENSITY_FACTORS["medium"])
        area_px = int(obj.get("area_px", 0))
        adaptive_factor = _adaptive_density_multiplier(area_px)
        step_obj_mm = step_mm * density_factor * adaptive_factor

        shrink_comp_mm = float(obj.get("shrink_comp_mm", global_shrink))
        mask = _apply_shrink_comp(mask, mm_per_px=mm_per_px, shrink_comp_mm=shrink_comp_mm)

        underlay = _normalize_underlay(obj.get("underlay", global_underlay), global_underlay)
        underlay_factor = UNDERLAY_FACTORS.get(underlay, UNDERLAY_FACTORS["medium"])

        fill_type = _normalize_fill_type(str(obj.get("fill_type", "tatami")))
        border_width_mm = float(obj.get("border_width_mm", global_border_width_mm))
        border_px = max(1, int(round(border_width_mm / max(mm_per_px, 1e-6))))

        inner_mask = _erode_n(mask, border_px)
        border_mask = mask & (~inner_mask)
        outline_mask = _boundary_mask(mask)

        underlay_segments = []
        if underlay_factor > 0:
            underlay_segments = _make_segments_for_mask(
                inner_mask if inner_mask.any() else mask,
                mm_per_px=mm_per_px,
                step_mm=step_obj_mm * underlay_factor,
                fill_type="zigzag" if fill_type != "zigzag" else "tatami",
            )

        # Auto comercial: satin na borda + tatami no miolo quando fill padrão.
        if fill_type == "tatami":
            core_segments = _make_segments_for_mask(
                inner_mask if inner_mask.any() else mask,
                mm_per_px=mm_per_px,
                step_mm=step_obj_mm,
                fill_type="tatami",
            )
            border_segments = _make_segments_for_mask(
                border_mask if border_mask.any() else outline_mask,
                mm_per_px=mm_per_px,
                step_mm=max(step_obj_mm * 0.9, 0.2),
                fill_type="satin",
            )
            segments = underlay_segments + core_segments + border_segments
        else:
            segments = _make_segments_for_mask(
                mask,
                mm_per_px=mm_per_px,
                step_mm=step_obj_mm,
                fill_type=fill_type,
            )
            segments = underlay_segments + segments

        if bool(obj.get("outline", global_outline)):
            outline_src = outline_mask
            keepout_mm = float(obj.get("outline_keepout_mm", global_outline_keepout_mm))
            if keepout_mm > 0:
                keepout_px = max(1, int(round(keepout_mm / max(mm_per_px, 1e-6))))
                keepout_zone = _dilate_n(border_mask, keepout_px)
                reduced = outline_mask & (~keepout_zone)
                if reduced.any():
                    outline_src = reduced

            outline_overlap_mm = float(obj.get("outline_overlap_mm", global_outline_overlap_mm))
            if outline_overlap_mm > 0:
                overlap_px = max(1, int(round(outline_overlap_mm / max(mm_per_px, 1e-6))))
                outline_src = _dilate_n(outline_src, overlap_px)

            outline_segments = _vector_outline_segments(
                outline_src,
                mm_per_px=mm_per_px,
                step_mm=max(step_obj_mm * global_outline_mult, 0.18),
                outline_type=_normalize_outline_type(obj.get("outline_type", global_outline_type)),
                width_mm=float(obj.get("outline_width_mm", global_outline_width_mm)),
                pull_comp_mm=float(obj.get("outline_pull_comp_mm", global_outline_pull_comp_mm)),
            )
            segments = segments + outline_segments
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
    if out_format == "PES":
        # PES v6 mantém melhor as informações da threadlist (RGB) em softwares como Embird.
        pattern.write(str(out_path), version=6)
    else:
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
    meta["quality_preset"] = preset_name
    meta["adaptive_density"] = True

    return preview_path, out_path, meta