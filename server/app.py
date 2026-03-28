from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from converter import convert_image_to_embroidery, analyze_image_for_autopunch

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Image → Embroidery Converter")

# Para GitHub Pages: permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # depois você pode travar para seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir o front localmente (opcional, mas facilita para leigos)
FRONT_DIR = BASE_DIR.parent
FRONT_INDEX = FRONT_DIR / "index.html"
FRONT_CSS = FRONT_DIR / "css"
FRONT_JS = FRONT_DIR / "js"

if FRONT_CSS.exists():
    app.mount("/css", StaticFiles(directory=str(FRONT_CSS)), name="css")
if FRONT_JS.exists():
    app.mount("/js", StaticFiles(directory=str(FRONT_JS)), name="js")

@app.get("/docs", include_in_schema=False)
def docs_redirect():
    # Compatibilidade com URLs antigas.
    return RedirectResponse(url="/", status_code=307)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Evita log de 404 quando o navegador solicita o favicon automaticamente.
    candidates = [
        FRONT_DIR / "favicon.ico",
        BASE_DIR.parent / "favicon.ico",
    ]
    for icon_path in candidates:
        if icon_path.exists():
            return FileResponse(str(icon_path), media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def root():
    # Em local, já abre a UI
    if FRONT_INDEX.exists():
        index_path = FRONT_INDEX
        return index_path.read_text(encoding="utf-8")
    return "<h1>Backend OK</h1><p>A UI está em /</p>"

@app.post("/convert")
async def convert(
    image: UploadFile = File(...),
    size_cm: int = Form(...),
    format: str = Form(...),
    colors: int = Form(...),
    detail: str = Form(...),
    quality_preset: str = Form("medio"),
    design_config: str | None = Form(None),
):
    job_id = str(uuid.uuid4())
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # salvar upload
    input_path = job_dir / f"input_{image.filename}"
    with input_path.open("wb") as f:
        f.write(await image.read())

    parsed_design_config = None
    if design_config:
        try:
            parsed_design_config = json.loads(design_config)
        except json.JSONDecodeError:
            parsed_design_config = None

    # converter
    preview_path, out_path, meta = convert_image_to_embroidery(
        input_image_path=input_path,
        out_dir=job_dir,
        size_cm=size_cm,
        out_format=format,
        num_colors=colors,
        detail=detail,
        design_config=parsed_design_config,
        quality_preset=quality_preset,
    )

    return {
        "job_id": job_id,
        "preview_url": f"/preview/{job_id}",
        "download_url": f"/download/{job_id}",
        "meta": meta,
    }


@app.post("/autopunch")
async def autopunch(
    image: UploadFile = File(...),
    colors: int = Form(12),
    detail: str = Form("medium"),
    quality_preset: str = Form("medio"),
):
    job_id = str(uuid.uuid4())
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_path = job_dir / f"input_{image.filename}"
    with input_path.open("wb") as f:
        f.write(await image.read())

    analysis = analyze_image_for_autopunch(
        input_image_path=input_path,
        num_colors=colors,
        detail=detail,
        quality_preset=quality_preset,
    )

    return {
        "job_id": job_id,
        "analysis": analysis,
    }

@app.get("/preview/{job_id}")
def preview(job_id: str):
    p = OUTPUT_DIR / job_id / "preview.png"
    if not p.exists():
        return {"error": "preview not found"}
    return FileResponse(str(p), media_type="image/png")

@app.get("/download/{job_id}")
def download(job_id: str):
    job_dir = OUTPUT_DIR / job_id
    # arquivo gerado tem extensão variável; guardamos como output.<ext>
    for file in job_dir.glob("output.*"):
        return FileResponse(
            str(file),
            media_type="application/octet-stream",
            filename=file.name,
        )
    return {"error": "output not found"}