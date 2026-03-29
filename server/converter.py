from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any, Literal

import numpy as np
from PIL import Image, ImageColor, ImageFilter

try:
    import cv2
except ImportError:
    cv2 = None

from pyembroidery import (
    EmbPattern,
    EmbThread,
    STITCH,
    JUMP,
    TRIM,
    COLOR_CHANGE,
    END,
)

from preview import render_preview

try:
    from svgelements import Color as SvgColor
    from svgelements import SVG as ParsedSVG
    from svgelements import Shape as SvgShape
except Exception:  # pragma: no cover - dependency is optional at runtime
    ParsedSVG = None
    SvgShape = None
    SvgColor = None

try:
    import cairosvg
except Exception:  # pragma: no cover - dependency is optional at runtime
    cairosvg = None


DetailLevel = Literal["low", "medium", "high"]

DETAIL_STEP_MM: dict[DetailLevel, float] = {
    "low": 0.8,
    "medium": 0.45,
    "high": 0.3,
}

SUPPORTED_FORMATS = {"PES", "DST", "JEF", "EXP", "HUS", "VP3"}  # E3D não

SUPPORTED_SOURCE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".svg",
    ".ai",
    ".cdr",
}

VECTOR_SOURCE_EXTENSIONS = {".svg", ".ai", ".cdr"}
CDR_LIKE_SOURCE_EXTENSIONS = {".cdr"}
INKSCAPE_CANDIDATES = (
    "inkscape.com",
    "inkscape",
    "C:/Program Files/Inkscape/bin/inkscape.com",
    "C:/Program Files/Inkscape/bin/inkscape.exe",
)

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

FABRIC_PROFILE_RULES = {
    # Stretch: open density a bit, stronger support and more compensation.
    "malha": {
        "density_shift": -1,
        "underlay_shift": 1,
        "shrink_add_mm": 0.12,
        "pull_add_mm": 0.10,
    },
    # Stable woven: balanced defaults.
    "brim": {
        "density_shift": 0,
        "underlay_shift": 0,
        "shrink_add_mm": 0.05,
        "pull_add_mm": 0.05,
    },
    # High pile: needs stronger base and tighter cover.
    "toalha": {
        "density_shift": 1,
        "underlay_shift": 1,
        "shrink_add_mm": 0.10,
        "pull_add_mm": 0.10,
    },
    # Heavy fabric: moderate support, medium compensation.
    "jeans": {
        "density_shift": 0,
        "underlay_shift": 0,
        "shrink_add_mm": 0.08,
        "pull_add_mm": 0.08,
    },
}

_DENSITY_ORDER = ("low", "medium", "high")
_UNDERLAY_ORDER = ("none", "low", "medium", "high")

@dataclass
class ConvertMeta:
    width_px: int
    height_px: int
    size_cm: int
    mm_per_px: float
    num_colors: int
    detail: str
    out_format: str


def _find_inkscape_command() -> str | None:
    for candidate in INKSCAPE_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
        if Path(candidate).exists():
            return candidate
    return None


def _convert_vector_to_png_with_inkscape(input_path: Path, output_png: Path) -> str | None:
    inkscape_cmd = _find_inkscape_command()
    if not inkscape_cmd:
        return "Inkscape não encontrado no sistema."

    cmd = [
        inkscape_cmd,
        str(input_path),
        "--export-type=png",
        f"--export-filename={output_png}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or (not output_png.exists()):
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        detail = stderr or stdout or f"exit_code={proc.returncode}"
        return f"Falha ao converter vetor com Inkscape ({detail})."
    return None


def _convert_vector_to_svg_with_inkscape(input_path: Path, output_svg: Path) -> str | None:
    inkscape_cmd = _find_inkscape_command()
    if not inkscape_cmd:
        return "Inkscape não encontrado no sistema."

    cmd = [
        inkscape_cmd,
        str(input_path),
        f"--export-plain-svg={output_svg}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or (not output_svg.exists()):
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        detail = stderr or stdout or f"exit_code={proc.returncode}"
        return f"Falha ao converter vetor para SVG com Inkscape ({detail})."
    return None


def _convert_svg_to_png_with_cairosvg(input_svg: Path, output_png: Path) -> str | None:
    if cairosvg is None:
        return "cairosvg não está instalado no ambiente."
    try:
        cairosvg.svg2png(url=str(input_svg), write_to=str(output_png))
    except Exception as exc:
        return f"Falha ao converter SVG com cairosvg ({exc})."
    if not output_png.exists():
        return "Falha ao converter SVG com cairosvg (arquivo PNG não gerado)."
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _svg_paint_to_hex(paint: Any) -> str | None:
    if paint is None:
        return None

    if SvgColor is not None and isinstance(paint, SvgColor):
        alpha = _safe_float(getattr(paint, "alpha", 255.0), 255.0)
        if alpha <= 0:
            return None
        r = int(np.clip(_safe_float(getattr(paint, "red", 0.0), 0.0), 0, 255))
        g = int(np.clip(_safe_float(getattr(paint, "green", 0.0), 0.0), 0, 255))
        b = int(np.clip(_safe_float(getattr(paint, "blue", 0.0), 0.0), 0, 255))
        return f"#{r:02x}{g:02x}{b:02x}"

    if isinstance(paint, (tuple, list)) and len(paint) >= 3:
        try:
            r = int(np.clip(float(paint[0]), 0, 255))
            g = int(np.clip(float(paint[1]), 0, 255))
            b = int(np.clip(float(paint[2]), 0, 255))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return None

    text = str(paint).strip()
    if not text:
        return None
    if text.lower() in {"none", "transparent", "currentcolor", "url(#none)"}:
        return None

    try:
        rgb = ImageColor.getrgb(text)
    except Exception:
        return None

    if isinstance(rgb, tuple) and len(rgb) >= 3:
        r, g, b = map(int, rgb[:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _extract_vector_objects_from_svg(svg_path: Path):
    if ParsedSVG is None or SvgShape is None:
        return None

    try:
        svg = ParsedSVG.parse(str(svg_path), reify=True, ppi=96)
    except Exception:
        return None

    width_px = _safe_float(getattr(svg, "width", 0.0), 0.0)
    height_px = _safe_float(getattr(svg, "height", 0.0), 0.0)

    if width_px <= 0 or height_px <= 0:
        viewbox = getattr(svg, "viewbox", None)
        if isinstance(viewbox, (tuple, list)) and len(viewbox) == 4:
            width_px = _safe_float(viewbox[2], width_px)
            height_px = _safe_float(viewbox[3], height_px)

    if width_px <= 0:
        width_px = 1000.0
    if height_px <= 0:
        height_px = 1000.0

    objects: list[dict[str, Any]] = []
    for idx, element in enumerate(svg.elements()):
        if not isinstance(element, SvgShape):
            continue

        values = getattr(element, "values", None)
        if isinstance(values, dict):
            display = str(values.get("display", "")).strip().lower()
            visibility = str(values.get("visibility", "")).strip().lower()
            if display == "none" or visibility == "hidden":
                continue

        try:
            bbox = element.bbox()
        except Exception:
            continue
        if not bbox or len(bbox) != 4:
            continue

        minx = _safe_float(bbox[0], 0.0)
        miny = _safe_float(bbox[1], 0.0)
        maxx = _safe_float(bbox[2], 0.0)
        maxy = _safe_float(bbox[3], 0.0)
        if maxx < minx:
            minx, maxx = maxx, minx
        if maxy < miny:
            miny, maxy = maxy, miny

        w = max(0.0, maxx - minx)
        h = max(0.0, maxy - miny)
        if w < 0.15 and h < 0.15:
            continue

        fill_hex = _svg_paint_to_hex(getattr(element, "fill", None))
        stroke_hex = _svg_paint_to_hex(getattr(element, "stroke", None))
        stroke_width_px = max(0.0, _safe_float(getattr(element, "stroke_width", 0.0), 0.0))

        has_fill = fill_hex is not None
        has_stroke = stroke_hex is not None and stroke_width_px > 0.0
        if not (has_fill or has_stroke):
            continue

        color_hex = fill_hex or stroke_hex or "#000000"
        bbox_area = max(1.0, w * h)
        if has_fill:
            area_px = int(round(bbox_area))
        else:
            area_px = int(round(max(1.0, max(w, h) * max(1.0, stroke_width_px))))

        kind = type(element).__name__.lower()
        roundness = 0.15
        corner_ratio = 0.25
        if kind in {"circle", "ellipse"}:
            roundness = 0.9
            corner_ratio = 0.05
        elif kind in {"path", "polygon", "polyline"}:
            roundness = 0.35
            corner_ratio = 0.2

        orientation_hint = 0.0 if w >= h else 90.0
        width_hint_px = max(0.3, min(w, h))
        if (not has_fill) and has_stroke:
            width_hint_px = max(0.2, stroke_width_px)

        objects.append(
            {
                "id": f"v_{idx}",
                "bbox": [int(round(minx)), int(round(miny)), int(round(maxx)), int(round(maxy))],
                "area_px": int(max(1, area_px)),
                "color": color_hex,
                "has_fill": bool(has_fill),
                "has_stroke": bool(has_stroke),
                "stroke_width_px": float(stroke_width_px),
                "source_kind": kind,
                "orientation_hint_deg": float(orientation_hint),
                "width_hint_px": float(width_hint_px),
                "roundness_hint": float(roundness),
                "corner_ratio_hint": float(corner_ratio),
            }
        )

    if not objects:
        return None

    return {
        "canvas_width_px": int(max(1, round(width_px))),
        "canvas_height_px": int(max(1, round(height_px))),
        "objects": objects,
    }


def _load_source_rgba(input_image_path: Path, *, allow_vector_blank_fallback: bool = False) -> tuple[Image.Image, dict]:
    ext = input_image_path.suffix.strip().lower()

    if ext not in VECTOR_SOURCE_EXTENSIONS:
        try:
            with Image.open(input_image_path) as pil_img:
                return pil_img.convert("RGBA"), {
                    "input_extension": ext or "(sem_ext)",
                    "vector_imported": False,
                }
        except Exception as direct_err:
            direct_error = direct_err
    else:
        direct_error = None

    if ext in VECTOR_SOURCE_EXTENSIONS:
        vector_png = input_image_path.with_name(f"{input_image_path.stem}__vector_import.png")
        vector_svg: Path | None = None
        vector_source_for_png = input_image_path

        if ext in CDR_LIKE_SOURCE_EXTENSIONS:
            vector_svg = input_image_path.with_name(f"{input_image_path.stem}__vector_import.svg")
            conversion_error = _convert_vector_to_svg_with_inkscape(input_image_path, vector_svg)
            if conversion_error:
                raise ValueError(
                    "Não foi possível importar arquivo vetorial. "
                    "Para .CDR/.AI/.SVG, instale o Inkscape e tente novamente. "
                    f"Detalhe: {conversion_error}"
                )
            vector_source_for_png = vector_svg

        vector_analysis = None
        if vector_source_for_png.suffix.lower() == ".svg":
            vector_analysis = _extract_vector_objects_from_svg(vector_source_for_png)

        conversion_error = None
        if vector_source_for_png.suffix.lower() == ".svg":
            conversion_error = _convert_svg_to_png_with_cairosvg(vector_source_for_png, vector_png)
            if conversion_error:
                conversion_error = _convert_vector_to_png_with_inkscape(vector_source_for_png, vector_png)
        else:
            conversion_error = _convert_vector_to_png_with_inkscape(vector_source_for_png, vector_png)

        if conversion_error and allow_vector_blank_fallback and vector_analysis is not None:
            canvas_w = int(max(1, vector_analysis.get("canvas_width_px", 1000)))
            canvas_h = int(max(1, vector_analysis.get("canvas_height_px", 1000)))
            source_info = {
                "input_extension": ext,
                "vector_imported": True,
                "vector_engine": "svg-properties-only",
                "vector_pipeline": "svg_properties_only",
                "vector_properties_used": True,
                "vector_objects_count": int(len(vector_analysis.get("objects", []))),
                "vector_canvas_px": {
                    "width": canvas_w,
                    "height": canvas_h,
                },
                "_vector_objects": vector_analysis.get("objects", []),
                "vector_raster_fallback": "blank_canvas",
            }
            return Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0)), source_info

        if conversion_error:
            raise ValueError(
                "Não foi possível importar arquivo vetorial. "
                "Para .CDR/.AI/.SVG, instale o Inkscape (ou cairosvg para SVG) e tente novamente. "
                f"Detalhe: {conversion_error}"
            )
        try:
            with Image.open(vector_png) as pil_img:
                pipeline = "vector_to_png"
                if ext in CDR_LIKE_SOURCE_EXTENSIONS:
                    pipeline = "cdr_to_svg_to_png"
                source_info = {
                    "input_extension": ext,
                    "vector_imported": True,
                    "vector_engine": "inkscape",
                    "vector_pipeline": pipeline,
                }
                if vector_analysis is not None:
                    source_info["vector_properties_used"] = True
                    source_info["vector_objects_count"] = int(len(vector_analysis.get("objects", [])))
                    source_info["vector_canvas_px"] = {
                        "width": int(vector_analysis.get("canvas_width_px", pil_img.size[0])),
                        "height": int(vector_analysis.get("canvas_height_px", pil_img.size[1])),
                    }
                    # Chave interna: usada no autopunch e removida antes de retornar ao cliente.
                    source_info["_vector_objects"] = vector_analysis.get("objects", [])
                else:
                    source_info["vector_properties_used"] = False
                return pil_img.convert("RGBA"), source_info
        finally:
            try:
                vector_png.unlink(missing_ok=True)
            except OSError:
                pass
            if vector_svg is not None:
                try:
                    vector_svg.unlink(missing_ok=True)
                except OSError:
                    pass

    if ext and ext not in SUPPORTED_SOURCE_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_EXTENSIONS))
        raise ValueError(f"Formato de entrada não suportado: {ext}. Use: {allowed}")

    raise ValueError(
        "Não foi possível abrir o arquivo de entrada como imagem. "
        "Use PNG/JPG ou vetor SVG/AI/CDR. "
        f"Erro original: {direct_error}"
    )


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


def _normalize_fabric_profile(value: str | None) -> str:
    if not value:
        return "brim"
    key = str(value).strip().lower()
    aliases = {
        "malha": "malha",
        "mesh": "malha",
        "stretch": "malha",
        "brim": "brim",
        "sarja": "brim",
        "toalha": "toalha",
        "towel": "toalha",
        "jeans": "jeans",
        "denim": "jeans",
    }
    norm = aliases.get(key, key)
    if norm in FABRIC_PROFILE_RULES:
        return norm
    return "brim"


def _shift_density(base: str, shift: int) -> str:
    key = str(base or "medium").strip().lower()
    if key not in _DENSITY_ORDER:
        key = "medium"
    idx = _DENSITY_ORDER.index(key)
    idx = max(0, min(len(_DENSITY_ORDER) - 1, idx + int(shift)))
    return _DENSITY_ORDER[idx]


def _shift_underlay(base: str, shift: int) -> str:
    key = _normalize_underlay(base, "medium")
    idx = _UNDERLAY_ORDER.index(key) if key in _UNDERLAY_ORDER else _UNDERLAY_ORDER.index("medium")
    idx = max(0, min(len(_UNDERLAY_ORDER) - 1, idx + int(shift)))
    return _UNDERLAY_ORDER[idx]


def _estimate_principal_angle_deg(xs: np.ndarray, ys: np.ndarray) -> float:
    if xs.size < 3 or ys.size < 3:
        return 45.0
    pts = np.column_stack((xs.astype(np.float64), ys.astype(np.float64)))
    pts = pts - pts.mean(axis=0, keepdims=True)
    cov = np.cov(pts, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    major = eigvecs[:, int(np.argmax(eigvals))]
    angle = math.degrees(math.atan2(float(major[1]), float(major[0]))) % 180.0
    return angle


def _estimate_corner_ratio(boundary_mask: np.ndarray) -> float:
    if not boundary_mask.any():
        return 0.0
    polylines = _trace_boundary_polylines(boundary_mask, min_len_px=10)
    corners = 0
    samples = 0
    for poly in polylines:
        if len(poly) < 5:
            continue
        for i in range(1, len(poly) - 1):
            y0, x0 = poly[i - 1]
            y1, x1 = poly[i]
            y2, x2 = poly[i + 1]
            v1x, v1y = x1 - x0, y1 - y0
            v2x, v2y = x2 - x1, y2 - y1
            n1 = math.hypot(v1x, v1y)
            n2 = math.hypot(v2x, v2y)
            if n1 < 1e-6 or n2 < 1e-6:
                continue
            dot = (v1x * v2x + v1y * v2y) / (n1 * n2)
            dot = max(-1.0, min(1.0, dot))
            angle = math.degrees(math.acos(dot))
            samples += 1
            if angle < 70.0:
                corners += 1
    if samples == 0:
        return 0.0
    return float(corners / samples)


def _estimate_object_geometry(mask: np.ndarray, mm_per_px: float) -> dict:
    ys, xs = np.where(mask)
    if ys.size == 0:
        return {
            "width_mm": 0.0,
            "stroke_mm": 0.0,
            "roundness": 0.0,
            "elongation": 1.0,
            "corner_ratio": 0.0,
            "orientation_deg": 45.0,
            "bbox_fill_ratio": 0.0,
        }

    minx = int(xs.min())
    maxx = int(xs.max())
    miny = int(ys.min())
    maxy = int(ys.max())
    bbox_w = max(1, maxx - minx + 1)
    bbox_h = max(1, maxy - miny + 1)
    bbox_area = max(1, bbox_w * bbox_h)

    area_px = int(ys.size)
    boundary = _boundary_mask(mask)
    perimeter_px = max(1, int(np.count_nonzero(boundary)))

    min_dim_mm = float(min(bbox_w, bbox_h) * mm_per_px)
    stroke_px = float((2.0 * area_px) / perimeter_px)
    stroke_mm = float(stroke_px * mm_per_px)

    roundness = float((4.0 * math.pi * area_px) / max(1.0, perimeter_px * perimeter_px))
    roundness = max(0.0, min(1.0, roundness))

    orientation = _estimate_principal_angle_deg(xs, ys)

    pts = np.column_stack((xs.astype(np.float64), ys.astype(np.float64)))
    pts = pts - pts.mean(axis=0, keepdims=True)
    cov = np.cov(pts, rowvar=False)
    eigvals, _ = np.linalg.eigh(cov)
    eigvals = np.maximum(eigvals, 1e-9)
    elongation = float(math.sqrt(float(np.max(eigvals) / np.min(eigvals))))

    corner_ratio = _estimate_corner_ratio(boundary)
    bbox_fill_ratio = float(area_px / bbox_area)

    if bbox_fill_ratio > 0.45:
        width_mm = min_dim_mm
    else:
        width_mm = max(stroke_mm, min_dim_mm * 0.55)

    return {
        "width_mm": float(max(0.2, width_mm)),
        "stroke_mm": float(max(0.15, stroke_mm)),
        "roundness": round(roundness, 4),
        "elongation": round(elongation, 4),
        "corner_ratio": round(float(corner_ratio), 4),
        "orientation_deg": round(float(orientation), 2),
        "bbox_fill_ratio": round(float(bbox_fill_ratio), 4),
    }


def _classify_art_type(
    *,
    used_colors: int,
    dominant_ratio: float,
    boundary_ratio: float,
    micro_colors: int,
    thin_object_ratio: float,
) -> str:
    if thin_object_ratio >= 0.35:
        return "texto_fino"
    if used_colors <= 6 and dominant_ratio >= 0.34 and boundary_ratio <= 0.42 and micro_colors <= 3:
        return "logo_vetorial_simples"
    if micro_colors >= max(4, used_colors // 3) and boundary_ratio >= 0.5:
        return "degrade_ou_ruido"
    if boundary_ratio >= 0.45 and used_colors <= 12:
        return "desenho_organico"
    return "misto"


def _decide_object_embroidery_cfg(
    *,
    geometry: dict,
    art_type: str,
    global_cfg: dict,
    fabric_profile: str,
    object_index: int,
) -> dict:
    width_mm = float(geometry.get("width_mm", 4.0))
    roundness = float(geometry.get("roundness", 0.0))
    elongation = float(geometry.get("elongation", 1.0))
    corner_ratio = float(geometry.get("corner_ratio", 0.0))
    orientation_deg = float(geometry.get("orientation_deg", 45.0))

    density = str(global_cfg.get("density", "medium"))
    underlay = str(global_cfg.get("underlay", "medium"))
    fill_type = str(global_cfg.get("fill_type", "tatami"))
    fill_enabled = True
    outline_type = str(global_cfg.get("outline_type", "satin"))
    outline_width_mm = float(global_cfg.get("outline_width_mm", 1.5))
    outline_overlap_mm = float(global_cfg.get("outline_overlap_mm", 0.4))
    outline_keepout_mm = float(global_cfg.get("outline_keepout_mm", 0.0))
    shrink_comp_mm = float(global_cfg.get("shrink_comp_mm", 0.4))
    outline_pull_comp_mm = float(global_cfg.get("outline_pull_comp_mm", 0.3))

    if width_mm < 2.0:
        # Regra clássica para traços finos: evitar fill e usar coluna/linha corrida.
        fill_enabled = False
        fill_type = "zigzag"
        density = "low"
        underlay = "none"
        outline_type = "bean" if width_mm < 1.2 else "running"
        outline_width_mm = max(0.6, min(1.4, width_mm * 0.7))
        outline_overlap_mm = min(outline_overlap_mm, 0.2)
    elif width_mm <= 8.0:
        fill_type = "satin"
        density = "high"
        underlay = "high" if width_mm > 4.5 else "medium"
        outline_type = "satin" if width_mm > 3.0 else "running"
        outline_width_mm = max(0.8, min(1.8, width_mm * 0.28))
    else:
        fill_type = "tatami"
        density = "high" if art_type in {"logo_vetorial_simples", "texto_fino"} else "medium"
        underlay = "high" if art_type in {"logo_vetorial_simples", "degrade_ou_ruido"} else "medium"
        if roundness >= 0.72 and corner_ratio <= 0.16:
            fill_type = "radial"
        elif elongation >= 2.6 and corner_ratio <= 0.14:
            fill_type = "spiral"
        outline_type = "satin"
        outline_width_mm = max(1.2, min(2.8, width_mm * 0.12))

    fabric = FABRIC_PROFILE_RULES.get(fabric_profile, FABRIC_PROFILE_RULES["brim"])
    density = _shift_density(density, int(fabric.get("density_shift", 0)))
    underlay = _shift_underlay(underlay, int(fabric.get("underlay_shift", 0)))

    shrink_comp_mm = shrink_comp_mm + float(fabric.get("shrink_add_mm", 0.0)) + min(0.22, corner_ratio * 0.45)
    if elongation > 3.2:
        shrink_comp_mm += 0.05
    if width_mm < 2.0:
        shrink_comp_mm = min(shrink_comp_mm, 0.25)

    outline_pull_comp_mm = outline_pull_comp_mm + float(fabric.get("pull_add_mm", 0.0)) + min(0.18, corner_ratio * 0.35)
    if width_mm < 2.0:
        outline_pull_comp_mm *= 0.65

    stitch_angle_deg = orientation_deg
    if fill_type == "tatami" and object_index % 2 == 1:
        # Alterna ângulo entre áreas adjacentes para reduzir efeito de bloco.
        stitch_angle_deg = (stitch_angle_deg + 90.0) % 180.0

    return {
        "fill_enabled": bool(fill_enabled),
        "fill_type": _normalize_fill_type(fill_type),
        "density": str(density),
        "underlay": _normalize_underlay(underlay, "medium"),
        "shrink_comp_mm": round(float(max(0.05, min(1.2, shrink_comp_mm))), 3),
        "outline_keepout_mm": round(float(max(0.0, min(1.5, outline_keepout_mm))), 3),
        "outline_type": _normalize_outline_type(outline_type),
        "outline_width_mm": round(float(max(0.5, min(4.0, outline_width_mm))), 3),
        "outline_pull_comp_mm": round(float(max(0.05, min(1.5, outline_pull_comp_mm))), 3),
        "outline_overlap_mm": round(float(max(0.0, min(1.5, outline_overlap_mm))), 3),
        "stitch_angle_deg": round(float(stitch_angle_deg), 2),
        "geometry": {
            "width_mm": round(width_mm, 3),
            "stroke_mm": round(float(geometry.get("stroke_mm", width_mm)), 3),
            "roundness": round(roundness, 4),
            "elongation": round(elongation, 4),
            "corner_ratio": round(corner_ratio, 4),
        },
    }


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

    # Melhoria 1: Aplicar bilateral filter (preserva bordas) + median blur para suavização
    if cv2 is not None:
        try:
            # Bilateral filter: suaviza preservando bordas reais
            rgb_arr = cv2.bilateralFilter(rgb_arr, 9, 75, 75)
            # Median blur: elimina ruído de cor pontual
            rgb_arr = cv2.medianBlur(rgb_arr, 3)
        except Exception:
            # Fallback se cv2 falhar
            pass

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


def _clean_color_component_mask(mask: np.ndarray, min_area_px: int = 28):
    """Reduce quantization noise before extracting connected embroidery objects."""
    if not mask.any():
        return mask

    # Close tiny holes and reconnect near-border pixels.
    smooth = _erode_once(_dilate_once(mask))
    # Remove one-pixel spikes introduced by color quantization.
    smooth = _dilate_once(_erode_once(smooth))

    # Melhoria 4: Aplicar dilate + erode morfológico (open/close) para arredondar bordas
    if cv2 is not None:
        try:
            mask_uint8 = smooth.astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            # Dilate para expandir bordas
            dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
            # Erode para suavizar (closing)
            smooth_cv = cv2.erode(dilated, kernel, iterations=1)
            smooth = smooth_cv.astype(bool)
        except Exception:
            pass

    if min_area_px <= 1:
        return smooth

    comps, comp_map = _find_components(smooth, min_area_px=1)
    if not comps:
        return smooth

    clean = np.zeros_like(smooth, dtype=bool)
    for comp in comps:
        if int(comp.get("area_px", 0)) < int(min_area_px):
            continue
        clean |= comp_map == int(comp["id"])

    return clean if clean.any() else smooth


def _build_component_candidates_from_vector_objects(
    vector_objects: list[dict[str, Any]],
    *,
    canvas_width_px: int,
    canvas_height_px: int,
    mm_per_px: float,
):
    color_to_label: dict[str, int] = {}
    label_areas: list[int] = []
    component_candidates: list[dict[str, Any]] = []

    w = max(1, int(canvas_width_px))
    h = max(1, int(canvas_height_px))
    opaque_mask = np.zeros((h, w), dtype=bool)

    for idx, obj in enumerate(vector_objects):
        bbox = obj.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue

        x0 = int(np.clip(int(round(_safe_float(bbox[0], 0.0))), 0, w - 1))
        y0 = int(np.clip(int(round(_safe_float(bbox[1], 0.0))), 0, h - 1))
        x1 = int(np.clip(int(round(_safe_float(bbox[2], 0.0))), 0, w - 1))
        y1 = int(np.clip(int(round(_safe_float(bbox[3], 0.0))), 0, h - 1))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0

        bw = max(1, x1 - x0 + 1)
        bh = max(1, y1 - y0 + 1)

        color_hex = str(obj.get("color", "#000000"))
        if color_hex not in color_to_label:
            color_to_label[color_hex] = len(color_to_label)
            label_areas.append(0)
        label_idx = color_to_label[color_hex]

        area_px = int(max(1, _safe_float(obj.get("area_px", bw * bh), bw * bh)))
        label_areas[label_idx] += area_px

        opaque_mask[y0 : y1 + 1, x0 : x1 + 1] = True

        has_fill = bool(obj.get("has_fill", True))
        has_stroke = bool(obj.get("has_stroke", False))
        stroke_width_px = max(0.0, _safe_float(obj.get("stroke_width_px", 0.0), 0.0))

        width_hint_px = max(0.2, _safe_float(obj.get("width_hint_px", min(bw, bh)), min(bw, bh)))
        if (not has_fill) and has_stroke:
            width_hint_px = max(0.2, stroke_width_px)

        stroke_hint_px = stroke_width_px if stroke_width_px > 0 else max(0.2, width_hint_px * 0.65)
        elongation = float(max(bw, bh) / max(1.0, min(bw, bh)))
        geometry = {
            "width_mm": round(float(max(0.2, width_hint_px * mm_per_px)), 3),
            "stroke_mm": round(float(max(0.15, stroke_hint_px * mm_per_px)), 3),
            "roundness": round(float(_safe_float(obj.get("roundness_hint", 0.2), 0.2)), 4),
            "elongation": round(float(elongation), 4),
            "corner_ratio": round(float(_safe_float(obj.get("corner_ratio_hint", 0.2), 0.2)), 4),
            "orientation_deg": round(float(_safe_float(obj.get("orientation_hint_deg", 0.0), 0.0)), 2),
            "bbox_fill_ratio": round(float(min(1.0, area_px / max(1.0, bw * bh))), 4),
        }

        vector_hint_outline = "satin"
        if (not has_fill) and has_stroke:
            vector_hint_outline = "running"
            if stroke_width_px >= 2.2:
                vector_hint_outline = "bean"

        component_candidates.append(
            {
                "id": str(obj.get("id") or f"v_{idx}"),
                "label_index": int(label_idx),
                "bbox": [x0, y0, x1, y1],
                "area_px": int(area_px),
                "color": color_hex,
                "geometry": geometry,
                "vector_hint_fill_enabled": bool(has_fill),
                "vector_hint_outline_type": vector_hint_outline,
            }
        )

    if not component_candidates:
        return None

    centers_u8 = np.zeros((max(1, len(color_to_label)), 3), dtype=np.uint8)
    for color_hex, label_idx in color_to_label.items():
        rgb = _parse_hex_color(color_hex) or (0, 0, 0)
        centers_u8[label_idx] = np.array(rgb, dtype=np.uint8)

    counts = np.array(label_areas, dtype=np.int64)
    order = np.argsort(-counts)
    return component_candidates, centers_u8, counts, order, opaque_mask


def _recommend_autopunch_settings(
    *,
    width_px: int,
    height_px: int,
    opaque_mask: np.ndarray,
    color_counts: np.ndarray,
    requested_colors: int,
    requested_detail: str,
    thin_object_ratio: float,
    fabric_profile: str,
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

    art_type = _classify_art_type(
        used_colors=used_colors,
        dominant_ratio=dominant_ratio,
        boundary_ratio=boundary_ratio,
        micro_colors=micro_colors,
        thin_object_ratio=thin_object_ratio,
    )

    if art_type in {"logo_vetorial_simples", "texto_fino"}:
        rec_detail = "high"
        rec_preset = "premium_clean"
    elif art_type == "degrade_ou_ruido":
        rec_detail = "high"
        rec_preset = "premium"
    elif detail_score >= 1.1:
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
    if art_type == "logo_vetorial_simples":
        rec_colors = min(rec_colors, 12)
    elif art_type == "degrade_ou_ruido":
        rec_colors = max(rec_colors, min(24, requested_colors + 2))

    preset = QUALITY_PRESETS[rec_preset]
    fabric = FABRIC_PROFILE_RULES.get(_normalize_fabric_profile(fabric_profile), FABRIC_PROFILE_RULES["brim"])

    density = str(preset["density"])
    underlay = str(preset["underlay"])
    if art_type in {"logo_vetorial_simples", "texto_fino"}:
        density = _shift_density(density, 1)
        underlay = _shift_underlay(underlay, 1)

    density = _shift_density(density, int(fabric.get("density_shift", 0)))
    underlay = _shift_underlay(underlay, int(fabric.get("underlay_shift", 0)))

    global_cfg = {
        "fill_type": "tatami",
        "density": density,
        "shrink_comp_mm": float(preset["shrink_comp_mm"]) + float(fabric.get("shrink_add_mm", 0.0)),
        "underlay": underlay,
        "outline_type": preset.get("outline_type", "satin"),
        "outline_width_mm": float(preset.get("outline_width_mm", 1.5)),
        "outline_pull_comp_mm": float(preset.get("outline_pull_comp_mm", 0.3)) + float(fabric.get("pull_add_mm", 0.0)),
        "outline_overlap_mm": float(preset.get("outline_overlap_mm", 0.4)),
        "outline_keepout_mm": float(preset.get("outline_keepout_mm", 0.0)),
        "jump_between_segments_only": True,
        "connect_travel_mm": 0.8,
        "max_jump_mm": 8.0,
        "trim_long_jump_mm": 14.0,
        "fabric_profile": _normalize_fabric_profile(fabric_profile),
        "auto_quality_engine": "v2",
    }

    return {
        "quality_preset": rec_preset,
        "detail": rec_detail,
        "colors": rec_colors,
        "art_type": art_type,
        "fabric_profile": _normalize_fabric_profile(fabric_profile),
        "global": global_cfg,
        "metrics": {
            "coverage": round(coverage, 4),
            "boundary_ratio": round(boundary_ratio, 4),
            "used_colors": used_colors,
            "dominant_ratio": round(dominant_ratio, 4),
            "detail_score": round(detail_score, 4),
            "thin_object_ratio": round(float(thin_object_ratio), 4),
        },
    }


def analyze_image_for_autopunch(
    input_image_path: Path,
    num_colors: int,
    detail: str = "medium",
    quality_preset: str = "medio",
    size_cm: int = 20,
    fabric_profile: str = "brim",
    smart_first_pass: bool = True,
):
    """Retorna objetos agrupados com configuração inicial editável."""
    requested_preset = _normalize_quality_preset(quality_preset)
    requested_detail = str(detail or "medium").strip().lower()
    if requested_detail not in DETAIL_STEP_MM:
        requested_detail = "medium"
    fabric_profile = _normalize_fabric_profile(fabric_profile)

    img, source_info = _load_source_rgba(input_image_path, allow_vector_blank_fallback=True)
    vector_objects = source_info.pop("_vector_objects", None)

    max_side = 1400 if bool(source_info.get("vector_imported")) else 900
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    target_mm = max(40.0, float(size_cm) * 10.0)
    source_canvas = source_info.get("vector_canvas_px") if isinstance(source_info, dict) else None
    reference_max_px = float(max(1, max(img.size)))
    if isinstance(source_canvas, dict):
        sw = int(max(1, _safe_float(source_canvas.get("width", 0), 0)))
        sh = int(max(1, _safe_float(source_canvas.get("height", 0), 0)))
        if sw > 0 and sh > 0:
            reference_max_px = float(max(sw, sh))
    mm_per_px = target_mm / reference_max_px

    using_vector_autopunch = False
    built = None
    if isinstance(vector_objects, list) and vector_objects:
        built = _build_component_candidates_from_vector_objects(
            vector_objects,
            canvas_width_px=img.size[0],
            canvas_height_px=img.size[1],
            mm_per_px=mm_per_px,
        )

    if built is not None:
        using_vector_autopunch = True
        component_candidates, centers_u8, counts, order, opaque_mask = built
    else:
        centers_u8, label_img, opaque_mask = _vectorize_and_group_rgba(img, num_colors=num_colors)
        labels_used = label_img[opaque_mask]
        counts = np.bincount(labels_used, minlength=int(centers_u8.shape[0]))
        order = np.argsort(-counts)
        component_candidates = []

    if smart_first_pass:
        thin_objects = 0
        if using_vector_autopunch:
            for item in component_candidates:
                if float(item.get("geometry", {}).get("width_mm", 99.0)) < 2.2:
                    thin_objects += 1
        else:
            for ci in order.tolist():
                if ci < 0 or counts[ci] == 0:
                    continue
                color_mask = _clean_color_component_mask(label_img == int(ci), min_area_px=24)
                comps, comp_map = _find_components(color_mask)
                r, g, b = map(int, centers_u8[ci])
                for comp in comps:
                    oid = f"c{ci}_o{comp['id']}"
                    x0, y0, x1, y1 = map(int, comp["bbox"])
                    comp_slice = comp_map[y0 : y1 + 1, x0 : x1 + 1]
                    comp_mask = comp_slice == int(comp["id"])
                    geometry = _estimate_object_geometry(comp_mask, mm_per_px=mm_per_px)
                    if float(geometry.get("width_mm", 99.0)) < 2.2:
                        thin_objects += 1
                    component_candidates.append(
                        {
                            "id": oid,
                            "label_index": int(ci),
                            "bbox": comp["bbox"],
                            "area_px": int(comp["area_px"]),
                            "color": f"#{r:02x}{g:02x}{b:02x}",
                            "geometry": geometry,
                        }
                    )

        thin_object_ratio = float(thin_objects / max(1, len(component_candidates)))

        recommended = _recommend_autopunch_settings(
            width_px=img.size[0],
            height_px=img.size[1],
            opaque_mask=opaque_mask,
            color_counts=counts,
            requested_colors=int(num_colors),
            requested_detail=requested_detail,
            thin_object_ratio=thin_object_ratio,
            fabric_profile=fabric_profile,
        )

        if requested_preset in {"premium", "premium_clean"}:
            fabric = FABRIC_PROFILE_RULES.get(fabric_profile, FABRIC_PROFILE_RULES["brim"])
            override = QUALITY_PRESETS[requested_preset]
            recommended["quality_preset"] = requested_preset
            recommended["global"] = {
                **recommended.get("global", {}),
                **override,
                "fill_type": "tatami",
                "density": _shift_density(str(override.get("density", "medium")), int(fabric.get("density_shift", 0))),
                "underlay": _shift_underlay(str(override.get("underlay", "medium")), int(fabric.get("underlay_shift", 0))),
            }
    else:
        if not using_vector_autopunch:
            for ci in order.tolist():
                if ci < 0 or counts[ci] == 0:
                    continue
                color_mask = _clean_color_component_mask(label_img == int(ci), min_area_px=24)
                comps, _ = _find_components(color_mask)
                r, g, b = map(int, centers_u8[ci])
                for comp in comps:
                    oid = f"c{ci}_o{comp['id']}"
                    component_candidates.append(
                        {
                            "id": oid,
                            "label_index": int(ci),
                            "bbox": comp["bbox"],
                            "area_px": int(comp["area_px"]),
                            "color": f"#{r:02x}{g:02x}{b:02x}",
                        }
                    )

        fabric = FABRIC_PROFILE_RULES.get(fabric_profile, FABRIC_PROFILE_RULES["brim"])
        base = QUALITY_PRESETS[requested_preset]
        global_cfg_manual = {
            "fill_type": "tatami",
            "density": _shift_density(str(base.get("density", "medium")), int(fabric.get("density_shift", 0))),
            "shrink_comp_mm": float(base.get("shrink_comp_mm", 0.4)) + float(fabric.get("shrink_add_mm", 0.0)),
            "underlay": _shift_underlay(str(base.get("underlay", "medium")), int(fabric.get("underlay_shift", 0))),
            "outline_type": str(base.get("outline_type", "satin")),
            "outline_width_mm": float(base.get("outline_width_mm", 1.5)),
            "outline_pull_comp_mm": float(base.get("outline_pull_comp_mm", 0.3)) + float(fabric.get("pull_add_mm", 0.0)),
            "outline_overlap_mm": float(base.get("outline_overlap_mm", 0.4)),
            "outline_keepout_mm": float(base.get("outline_keepout_mm", 0.0)),
            "jump_between_segments_only": True,
            "connect_travel_mm": 0.8,
            "max_jump_mm": 8.0,
            "trim_long_jump_mm": 14.0,
            "fabric_profile": fabric_profile,
            "auto_quality_engine": "v2",
        }
        recommended = {
            "quality_preset": requested_preset,
            "detail": requested_detail,
            "colors": int(num_colors),
            "art_type": "manual_follow",
            "fabric_profile": fabric_profile,
            "global": global_cfg_manual,
            "metrics": {
                "smart_first_pass": False,
            },
        }

    if isinstance(recommended, dict):
        metrics = recommended.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}
        metrics["smart_first_pass"] = bool(smart_first_pass)
        metrics["vector_properties_used"] = bool(using_vector_autopunch)
        if using_vector_autopunch:
            metrics["vector_objects_count"] = int(len(component_candidates))
        recommended["metrics"] = metrics

    preset_name = _normalize_quality_preset(recommended.get("quality_preset", requested_preset))
    preset = QUALITY_PRESETS[preset_name]
    global_cfg = recommended.get("global", {}) if isinstance(recommended, dict) else {}
    rec_detail = str(recommended.get("detail", requested_detail))
    art_type = str(recommended.get("art_type", "misto"))

    out_objects = []
    if smart_first_pass:
        for idx, item in enumerate(component_candidates):
            cfg = _decide_object_embroidery_cfg(
                geometry=item["geometry"],
                art_type=art_type,
                global_cfg=global_cfg,
                fabric_profile=fabric_profile,
                object_index=idx,
            )

            if ("vector_hint_fill_enabled" in item) and (not bool(item.get("vector_hint_fill_enabled", True))):
                cfg["fill_enabled"] = False
                cfg["underlay"] = "none"
                cfg["density"] = "low"
                cfg["outline_type"] = str(item.get("vector_hint_outline_type", "running"))

            out_objects.append(
                {
                    "id": item["id"],
                    "label_index": int(item["label_index"]),
                    "bbox": item["bbox"],
                    "area_px": int(item["area_px"]),
                    "enabled": True,
                    "color": item["color"],
                    "fill_enabled": bool(cfg.get("fill_enabled", True)),
                    "fill_type": str(cfg.get("fill_type", global_cfg.get("fill_type", "tatami"))),
                    "density": str(cfg.get("density", global_cfg.get("density", preset["density"]))),
                    "shrink_comp_mm": float(cfg.get("shrink_comp_mm", global_cfg.get("shrink_comp_mm", preset["shrink_comp_mm"]))),
                    "underlay": str(cfg.get("underlay", global_cfg.get("underlay", preset["underlay"]))),
                    "outline_keepout_mm": float(cfg.get("outline_keepout_mm", global_cfg.get("outline_keepout_mm", preset.get("outline_keepout_mm", 0.0)))),
                    "outline_type": str(cfg.get("outline_type", global_cfg.get("outline_type", preset.get("outline_type", "satin")))),
                    "outline_width_mm": float(cfg.get("outline_width_mm", global_cfg.get("outline_width_mm", preset.get("outline_width_mm", 1.5)))),
                    "outline_pull_comp_mm": float(cfg.get("outline_pull_comp_mm", global_cfg.get("outline_pull_comp_mm", preset.get("outline_pull_comp_mm", 0.3)))),
                    "outline_overlap_mm": float(cfg.get("outline_overlap_mm", global_cfg.get("outline_overlap_mm", preset.get("outline_overlap_mm", 0.4)))),
                    "stitch_angle_deg": float(cfg.get("stitch_angle_deg", item["geometry"].get("orientation_deg", 45.0))),
                    "geometry": cfg.get("geometry", item["geometry"]),
                }
            )
    else:
        for item in component_candidates:
            bbox = item["bbox"]
            bw_px = max(1, int(bbox[2]) - int(bbox[0]) + 1)
            bh_px = max(1, int(bbox[3]) - int(bbox[1]) + 1)
            width_mm = float(min(bw_px, bh_px) * mm_per_px)
            base_geometry = item.get("geometry")
            if not isinstance(base_geometry, dict):
                base_geometry = {
                    "width_mm": round(width_mm, 3),
                    "stroke_mm": round(width_mm, 3),
                    "roundness": 0.0,
                    "elongation": round(float(max(bw_px, bh_px) / max(1, min(bw_px, bh_px))), 4),
                    "corner_ratio": 0.0,
                }

            fill_enabled_manual = bool(item.get("vector_hint_fill_enabled", True))
            outline_type_manual = str(item.get("vector_hint_outline_type", global_cfg.get("outline_type", preset.get("outline_type", "satin"))))
            out_objects.append(
                {
                    "id": item["id"],
                    "label_index": int(item["label_index"]),
                    "bbox": item["bbox"],
                    "area_px": int(item["area_px"]),
                    "enabled": True,
                    "color": item["color"],
                    "fill_enabled": fill_enabled_manual,
                    "fill_type": str(global_cfg.get("fill_type", "tatami")),
                    "density": str(global_cfg.get("density", preset["density"])),
                    "shrink_comp_mm": float(global_cfg.get("shrink_comp_mm", preset["shrink_comp_mm"])),
                    "underlay": "none" if not fill_enabled_manual else str(global_cfg.get("underlay", preset["underlay"])),
                    "outline_keepout_mm": float(global_cfg.get("outline_keepout_mm", preset.get("outline_keepout_mm", 0.0))),
                    "outline_type": outline_type_manual,
                    "outline_width_mm": float(global_cfg.get("outline_width_mm", preset.get("outline_width_mm", 1.5))),
                    "outline_pull_comp_mm": float(global_cfg.get("outline_pull_comp_mm", preset.get("outline_pull_comp_mm", 0.3))),
                    "outline_overlap_mm": float(global_cfg.get("outline_overlap_mm", preset.get("outline_overlap_mm", 0.4))),
                    "stitch_angle_deg": 45.0,
                    "geometry": base_geometry,
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
            "fabric_profile": fabric_profile,
            "art_type": art_type,
            "auto_quality_engine": "v2-vector" if using_vector_autopunch else "v2",
            "smart_first_pass": bool(smart_first_pass),
        },
        "recommended": recommended,
        "image_size": {"width": img.size[0], "height": img.size[1]},
        "mm_per_px_estimate": round(mm_per_px, 6),
        "input_source": source_info,
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


def _touches_image_border(bbox: list[int] | tuple[int, int, int, int], width: int, height: int, margin: int = 1) -> bool:
    minx, miny, maxx, maxy = [int(v) for v in bbox]
    return (minx <= margin) or (miny <= margin) or (maxx >= (width - 1 - margin)) or (maxy >= (height - 1 - margin))


def _is_extreme_neutral_rgb(rgb: tuple[int, int, int]) -> bool:
    r, g, b = [int(v) for v in rgb]
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    saturation = cmax - cmin
    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    return saturation <= 28 and (luminance <= 26.0 or luminance >= 244.0)


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


def _trace_boundary_polylines_cv2(boundary_mask: np.ndarray, min_len_px: int = 8):
    """
    Melhoria 3: Use cv2.findContours com CHAIN_APPROX_TC89_KCOS para contornos mais suavizados.
    Aplica approxPolyDP para suavizar o traçado imitando movimento real da máquina.
    """
    if cv2 is None:
        # Fallback para abordagem original
        return _trace_boundary_polylines(boundary_mask, min_len_px)
    
    try:
        # Converter máscara para uint8
        mask_uint8 = (boundary_mask.astype(np.uint8) * 255)
        
        # Usar CHAIN_APPROX_TC89_KCOS para maior precisão de contornos
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)
        
        polylines = []
        for contour in contours:
            # Aplicar approxPolyDP para suavizar
            epsilon = 2.5
            contour_approx = cv2.approxPolyDP(contour, epsilon, closed=True)
            
            # Converter para lista de tuplas (y, x) formato esperado
            if len(contour_approx) >= min_len_px:
                points = [(int(pt[0][1]), int(pt[0][0])) for pt in contour_approx]
                polylines.append(points)
        
        return polylines
    except Exception:
        # Fallback para abordagem original se cv2 falhar
        return _trace_boundary_polylines(boundary_mask, min_len_px)


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
    # Melhoria 3: Use cv2.findContours with CHAIN_APPROX_TC89_KCOS
    polylines = _trace_boundary_polylines_cv2(boundary_mask, min_len_px=max(8, step_px * 2))
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


def _resample_polyline_px(points: list[tuple[float, float]], step_px: float):
    if len(points) < 2:
        return points

    step_px = max(0.6, float(step_px))
    out: list[tuple[float, float]] = [points[0]]
    remain = step_px
    curx, cury = points[0]

    for nxtx, nxty in points[1:]:
        while True:
            dx = nxtx - curx
            dy = nxty - cury
            seg_len = math.hypot(dx, dy)
            if seg_len < 1e-9:
                break
            if seg_len >= remain:
                t = remain / seg_len
                px = curx + dx * t
                py = cury + dy * t
                out.append((px, py))
                curx, cury = px, py
                remain = step_px
                continue
            remain -= seg_len
            break
        curx, cury = nxtx, nxty

    last = points[-1]
    if math.hypot(last[0] - out[-1][0], last[1] - out[-1][1]) > (step_px * 0.35):
        out.append(last)
    return out


def _scanline_fill_segments(
    mask: np.ndarray,
    *,
    mm_per_px: float,
    stitch_len_mm: float,
    row_gap_mm: float,
    angle_deg: float,
):
    if not mask.any():
        return []

    ys, xs = np.where(mask)
    if ys.size < 2:
        return []

    angle = math.radians(float(angle_deg) % 180.0)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    xsf = xs.astype(np.float64)
    ysf = ys.astype(np.float64)
    rx = xsf * cos_a + ysf * sin_a
    ry = -xsf * sin_a + ysf * cos_a

    row_gap_px = max(1.0, row_gap_mm / max(mm_per_px, 1e-6))
    stitch_px = max(0.8, stitch_len_mm / max(mm_per_px, 1e-6))
    gap_break_px = max(1.8, row_gap_px * 1.55)

    min_ry = float(ry.min())
    max_ry = float(ry.max())

    segments_mm: list[tuple[tuple[float, float], tuple[float, float]]] = []
    row_idx = 0
    curr = min_ry
    # Melhoria 2: band_half deve ser row_gap_px / 2 (não 0.42) para sem gaps entre bandas
    band_half = max(0.55, row_gap_px * 0.5)

    while curr <= max_ry:
        in_band = np.abs(ry - curr) <= band_half
        if in_band.any():
            bx = xsf[in_band]
            by = ysf[in_band]
            brx = rx[in_band]
            order = np.argsort(brx)
            bx = bx[order]
            by = by[order]

            runs: list[tuple[np.ndarray, np.ndarray]] = []
            start = 0
            for i in range(1, bx.size):
                gap_xy = math.hypot(float(bx[i] - bx[i - 1]), float(by[i] - by[i - 1]))
                gap_rot = float(brx[order][i] - brx[order][i - 1])
                # Quebra corrida se houver salto grande no eixo da varredura
                # ou no espaço original da imagem.
                if gap_rot > gap_break_px or gap_xy > gap_break_px:
                    runs.append((bx[start:i], by[start:i]))
                    start = i
            runs.append((bx[start:], by[start:]))

            if row_idx % 2 == 1:
                runs = list(reversed(runs))

            for run_x, run_y in runs:
                if run_x.size < 2:
                    continue

                if row_idx % 2 == 1:
                    run_x = run_x[::-1]
                    run_y = run_y[::-1]

                raw_points = [(float(px), float(py)) for px, py in zip(run_x.tolist(), run_y.tolist())]
                sampled = _resample_polyline_px(raw_points, step_px=stitch_px)
                if len(sampled) < 2:
                    continue

                for i in range(len(sampled) - 1):
                    ax, ay = sampled[i]
                    bx2, by2 = sampled[i + 1]
                    if math.hypot(bx2 - ax, by2 - ay) > (stitch_px * 1.9):
                        continue
                    segments_mm.append(((ax * mm_per_px, ay * mm_per_px), (bx2 * mm_per_px, by2 * mm_per_px)))

        curr += row_gap_px
        row_idx += 1

    return segments_mm


def _make_segments_for_mask(
    mask: np.ndarray,
    mm_per_px: float,
    step_mm: float,
    fill_type: str = "tatami",
    stitch_angle_deg: float = 45.0,
):
    """Gera preenchimento tipo tatami curto (segmentos diagonais curtos)."""
    H, W = mask.shape
    fill_type = _normalize_fill_type(fill_type)
    step_px = max(1, int(round(step_mm / mm_per_px)))
    segments_mm: list[tuple[tuple[float, float], tuple[float, float]]] = []

    # Suavização morfológica simples para reduzir ruído de 1 px.
    # Importante: não usar np.roll aqui, pois ele faz wrap nas bordas e cria
    # conexões falsas entre lados opostos da imagem (artefatos em cantos).
    m = mask.astype(np.uint8)
    p = np.pad(m, ((1, 1), (1, 1)), mode="constant", constant_values=0)
    nb = (
        p[1:-1, 1:-1]
        + p[:-2, 1:-1]
        + p[2:, 1:-1]
        + p[1:-1, :-2]
        + p[1:-1, 2:]
    )
    mask = nb >= 3

    short_stitch_px = max(2, int(round(2.2 / mm_per_px)))
    slant_px = max(1, step_px // 2)

    if fill_type in {"tatami", "satin", "prog_fill", "zigzag"}:
        # Pitch padrão de bordado profissional: 0.35–0.55 mm entre linhas para cobertura densa.
        # Linhas muito espaçadas (>1 mm) geram faixas visíveis tanto na prévia quanto no tecido.
        row_gap_mm = max(0.35, min(0.55, step_mm * 1.4))
        # Ponto tatami clássico: comprimento 2–4 mm, levemente maior que o espaçamento entre linhas.
        stitch_len_mm = max(2.0, min(3.8, step_mm * 9.0))

        if fill_type == "satin":
            # Satin: linhas mais próximas para cobertura total (simula ponto cheio).
            row_gap_mm = max(0.28, min(0.45, step_mm * 1.1))
            stitch_len_mm = max(1.5, min(3.0, step_mm * 7.0))
        elif fill_type == "prog_fill":
            row_gap_mm = max(0.32, min(0.50, step_mm * 1.3))
            stitch_len_mm = max(1.8, min(3.5, step_mm * 8.5))
        elif fill_type == "zigzag":
            row_gap_mm = max(0.38, min(0.58, step_mm * 1.5))
            stitch_len_mm = max(1.8, min(3.5, step_mm * 8.5))

        main = _scanline_fill_segments(
            mask,
            mm_per_px=mm_per_px,
            stitch_len_mm=stitch_len_mm,
            row_gap_mm=row_gap_mm,
            angle_deg=stitch_angle_deg,
        )

        if fill_type in {"prog_fill", "zigzag"}:
            cross = _scanline_fill_segments(
                mask,
                mm_per_px=mm_per_px,
                stitch_len_mm=min(2.8, stitch_len_mm * 1.05),
                row_gap_mm=max(0.2, row_gap_mm * 1.45),
                angle_deg=(stitch_angle_deg + 90.0) % 180.0,
            )
            return main + cross

        return main

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

    # carregar imagem (raster ou vetor convertido), preservando alpha para não bordar fundo transparente
    img, source_info = _load_source_rgba(input_image_path)
    source_info.pop("_vector_objects", None)

    # reduzir um pouco se for enorme (performance)
    max_side = 1400 if bool(source_info.get("vector_imported")) else 900
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
        # Melhoria 7: usar min_area_px=8 para não eliminar regiões legítimas pequenas (olhos, nariz, coração)
        color_mask = _clean_color_component_mask(label_img == int(ci), min_area_px=8)
        comps, comp_map = _find_components(color_mask)
        r, g, b = map(int, centers_u8[ci])
        color_rgb = (r, g, b)
        is_neutral_extreme = _is_extreme_neutral_rgb(color_rgb)
        for comp in comps:
            oid = f"c{ci}_o{comp['id']}"
            area_px = int(comp.get("area_px", 0))
            bbox = comp["bbox"]
            touches_border = _touches_image_border(bbox, width_px, height_px, margin=1)
            area_ratio = area_px / float(max(1, width_px * height_px))
            likely_background = touches_border and is_neutral_extreme and (area_ratio >= 0.02)
            
            # Melhoria 7: Lógica de tamanho
            # Regiões < 8px: eliminadas (não adicionado)
            # Regiões 8-30px: apenas outline (sem fill)
            # Regiões > 30px: fill + outline (padrão)
            fill_enabled = area_px > 30
            
            default_objects.append(
                {
                    "id": oid,
                    "label_index": int(ci),
                    "component_index": int(comp["id"]),
                    "bbox": bbox,
                    "area_px": area_px,
                    "enabled": not likely_background,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "fill_enabled": (fill_enabled and (not likely_background)),  # Determinado pelo tamanho
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
            o["fill_enabled"] = _as_bool(user_o.get("fill_enabled", o.get("fill_enabled", True)), True)
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
    max_stitch_mm = 2.4
    # Evita linhas indesejadas atravessando "vazios" (ex.: letras C/A/O).
    # Por padrão, o deslocamento entre segmentos vira JUMP em vez de STITCH.
    jump_between_segments_only = _as_bool(cfg_global.get("jump_between_segments_only", True), True)
    connect_travel_mm = float(cfg_global.get("connect_travel_mm", 0.8))
    max_jump_mm = max(1.0, float(cfg_global.get("max_jump_mm", 8.0)))
    trim_long_jump_mm = max(0.0, float(cfg_global.get("trim_long_jump_mm", 14.0)))
    cursor_x = 0.0
    cursor_y = 0.0
    has_stitched_any = False

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
        stitch_angle_deg = float(obj.get("stitch_angle_deg", 45.0))

        shrink_comp_mm = float(obj.get("shrink_comp_mm", global_shrink))
        mask = _apply_shrink_comp(mask, mm_per_px=mm_per_px, shrink_comp_mm=shrink_comp_mm)

        underlay = _normalize_underlay(obj.get("underlay", global_underlay), global_underlay)
        underlay_factor = UNDERLAY_FACTORS.get(underlay, UNDERLAY_FACTORS["medium"])
        fill_enabled = _as_bool(obj.get("fill_enabled", True), True)

        fill_type = _normalize_fill_type(str(obj.get("fill_type", "tatami")))
        border_width_mm = float(obj.get("border_width_mm", global_border_width_mm))
        border_px = max(1, int(round(border_width_mm / max(mm_per_px, 1e-6))))

        inner_mask = _erode_n(mask, border_px)
        border_mask = mask & (~inner_mask)
        outline_mask = _boundary_mask(mask)

        underlay_segments = []
        if fill_enabled and underlay_factor > 0:
            underlay_segments = _make_segments_for_mask(
                inner_mask if inner_mask.any() else mask,
                mm_per_px=mm_per_px,
                step_mm=step_obj_mm * underlay_factor,
                fill_type="zigzag" if fill_type != "zigzag" else "tatami",
                stitch_angle_deg=(stitch_angle_deg + 90.0) % 180.0,
            )

        if not fill_enabled:
            segments = []
        else:
            # Auto comercial: satin na borda + tatami no miolo quando fill padrão.
            if fill_type == "tatami":
                core_segments = _make_segments_for_mask(
                    inner_mask if inner_mask.any() else mask,
                    mm_per_px=mm_per_px,
                    step_mm=step_obj_mm,
                    fill_type="tatami",
                    stitch_angle_deg=stitch_angle_deg,
                )
                border_segments = _make_segments_for_mask(
                    border_mask if border_mask.any() else outline_mask,
                    mm_per_px=mm_per_px,
                    step_mm=max(step_obj_mm * 0.9, 0.2),
                    fill_type="satin",
                    stitch_angle_deg=(stitch_angle_deg + 90.0) % 180.0,
                )
                segments = underlay_segments + core_segments + border_segments
            else:
                segments = _make_segments_for_mask(
                    mask,
                    mm_per_px=mm_per_px,
                    step_mm=step_obj_mm,
                    fill_type=fill_type,
                    stitch_angle_deg=stitch_angle_deg,
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

            # Melhoria 5: outline gerado UMA VEZ - adicionado após fill (TRIM → outline, mesmo thread)
            outline_segments = _vector_outline_segments(
                outline_src,
                mm_per_px=mm_per_px,
                step_mm=max(step_obj_mm * global_outline_mult, 0.18),
                outline_type=_normalize_outline_type(obj.get("outline_type", global_outline_type)),
                width_mm=float(obj.get("outline_width_mm", global_outline_width_mm)),
                pull_comp_mm=float(obj.get("outline_pull_comp_mm", global_outline_pull_comp_mm)),
            )
        else:
            outline_segments = []
        
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
            if travel > 1e-9:
                should_connect_with_stitch = (not jump_between_segments_only) and (travel <= connect_travel_mm)
                if should_connect_with_stitch:
                    pattern.add_stitch_relative(STITCH, x0 - cursor_x, y0 - cursor_y)
                    total_stitches += 1
                    has_stitched_any = True
                else:
                    # Saltos longos são quebrados para manter o deslocamento estável em máquinas/formats.
                    jump_steps = max(1, int(np.ceil(travel / max_jump_mm)))
                    for ji in range(1, jump_steps + 1):
                        jx = cursor_x + (x0 - cursor_x) * (ji / jump_steps)
                        jy = cursor_y + (y0 - cursor_y) * (ji / jump_steps)
                        pattern.add_stitch_relative(JUMP, jx - cursor_x, jy - cursor_y)
                        cursor_x, cursor_y = jx, jy
                    # TRIM em saltos longos reduz linhas de arraste visíveis no tecido.
                    if has_stitched_any and trim_long_jump_mm > 0 and travel >= trim_long_jump_mm:
                        pattern.add_stitch_relative(TRIM, 0, 0)
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
                has_stitched_any = True

        # Melhoria 5: Depois dos fill stitches, TRIM e outline NO MESMO thread (sem COLOR_CHANGE extra).
        # COLOR_CHANGE extra quebraria a threadlist já construída, embaralhando cores.
        if outline_segments:
            # TRIM para separar visualmente fill de outline (a máquina corta o fio, sem rastro).
            if has_stitched_any:
                pattern.add_stitch_relative(TRIM, 0, 0)

            for (x0, y0), (x1, y1) in outline_segments:
                travel = math.hypot(x0 - cursor_x, y0 - cursor_y)
                if travel > 1e-9:
                    should_connect_with_stitch = (not jump_between_segments_only) and (travel <= connect_travel_mm)
                    if should_connect_with_stitch:
                        pattern.add_stitch_relative(STITCH, x0 - cursor_x, y0 - cursor_y)
                        total_stitches += 1
                        has_stitched_any = True
                    else:
                        jump_steps = max(1, int(np.ceil(travel / max_jump_mm)))
                        for ji in range(1, jump_steps + 1):
                            jx = cursor_x + (x0 - cursor_x) * (ji / jump_steps)
                            jy = cursor_y + (y0 - cursor_y) * (ji / jump_steps)
                            pattern.add_stitch_relative(JUMP, jx - cursor_x, jy - cursor_y)
                            cursor_x, cursor_y = jx, jy
                        if has_stitched_any and trim_long_jump_mm > 0 and travel >= trim_long_jump_mm:
                            pattern.add_stitch_relative(TRIM, 0, 0)
                cursor_x, cursor_y = x0, y0

                span = max(abs(x1 - x0), abs(y1 - y0))
                steps = max(1, int(np.ceil(span / max_stitch_mm)))
                for si in range(1, steps + 1):
                    tx = x0 + (x1 - x0) * (si / steps)
                    ty = y0 + (y1 - y0) * (si / steps)
                    pattern.add_stitch_relative(STITCH, tx - cursor_x, ty - cursor_y)
                    cursor_x, cursor_y = tx, ty
                    total_stitches += 1
                    has_stitched_any = True

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
    meta["jump_between_segments_only"] = jump_between_segments_only
    meta["trim_long_jump_mm"] = trim_long_jump_mm
    meta["input_source"] = source_info

    return preview_path, out_path, meta