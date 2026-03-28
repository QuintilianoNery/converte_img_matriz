// Configure aqui a API padrão.
// Para GitHub Pages: configure para a URL do backend hospedado.
// Para local: http://127.0.0.1:8000
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "converter.apiBaseUrl";

const FILL_OPTIONS = [
  ["tatami", "Ponto de preenchimento (tatami)"],
  ["satin", "Ponto cheio"],
  ["prog_fill", "Ponto de preenchimento prog"],
  ["ornamental", "Ponto ornamental / enfeite"],
  ["cross", "Ponto cruz"],
  ["concentric", "Ponto em circulo concentrico"],
  ["radial", "Ponto radial"],
  ["spiral", "Ponto espiral"],
  ["stipple", "Ponto pontilhado"],
  ["network", "Ponto de preenchimento em rede"],
  ["zigzag", "Ponto de preenchimento em zigzag"],
];

const OUTLINE_OPTIONS = [
  ["satin", "Satin (coluna / zig-zag)"],
  ["running", "Running stitch (ponto corrido)"],
  ["triple", "Triple stitch (ponto triplo)"],
  ["bean", "Bean stitch"],
  ["e_stitch", "E-stitch"],
  ["cover", "Cover stitch"],
];

const el = (id) => document.getElementById(id);

const form = el("converterForm");
const statusEl = el("status");
const resultCard = el("resultCard");
const previewImg = el("previewImg");
const downloadBtn = el("downloadBtn");
const metaEl = el("meta");
const btnReset = el("btnReset");
const btnAutoPunch = el("btnAutoPunch");
const btnExpandAll = el("btnExpandAll");
const btnCollapseAll = el("btnCollapseAll");
const btnApplyBulk = el("btnApplyBulk");
const editorCard = el("editorCard");
const objectsEditor = el("objectsEditor");
const paletteEditor = el("paletteEditor");
const objectFilter = el("objectFilter");
const objectsCount = el("objectsCount");
const colorsSelect = el("colors");
const bulkFillType = el("bulkFillType");
const bulkDensity = el("bulkDensity");
const bulkUnderlay = el("bulkUnderlay");
const bulkShrink = el("bulkShrink");
const bulkOutlineType = el("bulkOutlineType");
const bulkOutlineWidth = el("bulkOutlineWidth");
const bulkOutlinePull = el("bulkOutlinePull");
const bulkOutlineOverlap = el("bulkOutlineOverlap");
const apiBaseInput = el("apiBase");
const btnApiSettings = el("btnApiSettings");
const apiSettingsBackdrop = el("apiSettingsBackdrop");
const btnCloseApiSettings = el("btnCloseApiSettings");
const btnCancelApiSettings = el("btnCancelApiSettings");
const btnSaveApiSettings = el("btnSaveApiSettings");
const qualityAlert = el("qualityAlert");

function normalizeApiBase(url) {
  return String(url || "").trim().replace(/\/+$/, "");
}

function loadSavedApiBase() {
  let saved = "";
  try {
    saved = localStorage.getItem(API_BASE_STORAGE_KEY) || "";
  } catch (_) {
    saved = "";
  }
  apiBaseInput.value = normalizeApiBase(saved) || DEFAULT_API_BASE_URL;
}

function saveApiBase() {
  const normalized = normalizeApiBase(apiBaseInput.value);
  if (!normalized) {
    setStatus("Informe a URL do backend (API).", "error");
    apiBaseInput.focus();
    return false;
  }
  apiBaseInput.value = normalized;
  try {
    localStorage.setItem(API_BASE_STORAGE_KEY, normalized);
  } catch (_) {
    // Ignora falha de storage e mantém apenas na sessão atual.
  }
  closeApiSettings();
  setStatus(`API configurada para ${normalized}`, "ok");
  return true;
}

function openApiSettings() {
  if (!apiSettingsBackdrop) return;
  apiSettingsBackdrop.hidden = false;
  apiBaseInput.focus();
  apiBaseInput.select();
}

function closeApiSettings() {
  if (!apiSettingsBackdrop) return;
  apiSettingsBackdrop.hidden = true;
}

loadSavedApiBase();

let autoPunchModel = null;
let autoPreviewTimer = null;
let autoPreviewRunning = false;
let autoPreviewPending = false;

function initColorSelector() {
  if (!colorsSelect) return;
  const current = Number(colorsSelect.value || 16);
  colorsSelect.innerHTML = "";
  for (let n = 1; n <= 24; n += 1) {
    const opt = document.createElement("option");
    opt.value = String(n);
    opt.textContent = String(n);
    if (n === current || (current < 1 && n === 16)) {
      opt.selected = true;
    }
    colorsSelect.appendChild(opt);
  }
}

initColorSelector();

if (bulkFillType) {
  bulkFillType.innerHTML = FILL_OPTIONS.map(([value, label]) => (`
    <option value="${value}" ${value === "tatami" ? "selected" : ""}>${esc(label)}</option>
  `)).join("");
}

if (bulkOutlineType) {
  bulkOutlineType.innerHTML = OUTLINE_OPTIONS.map(([value, label]) => (`
    <option value="${value}" ${value === "satin" ? "selected" : ""}>${esc(label)}</option>
  `)).join("");
}

function setStatus(msg, kind = "info") {
  statusEl.textContent = msg || "";
  statusEl.style.color =
    kind === "error" ? "#ffd7d7" :
    kind === "ok" ? "#a6ffd0" :
    "var(--muted)";
}

function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function checkQuality(file) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const minSide = Math.min(img.width, img.height);
      resolve({ width: img.width, height: img.height, minSide });
    };
    img.onerror = () => resolve(null);
    img.src = URL.createObjectURL(file);
  });
}

function fillOptionsHtml(selected) {
  return FILL_OPTIONS.map(([value, label]) => (
    `<option value="${value}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`
  )).join("");
}

function outlineOptionsHtml(selected) {
  return OUTLINE_OPTIONS.map(([value, label]) => (
    `<option value="${value}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`
  )).join("");
}

function renderObjectsEditor() {
  if (!autoPunchModel?.analysis?.objects?.length) {
    editorCard.hidden = true;
    objectsEditor.innerHTML = "";
    if (paletteEditor) paletteEditor.innerHTML = "";
    return;
  }

  const html = autoPunchModel.analysis.objects.map((obj, i) => `
    <details class="objItem" data-id="${esc(obj.id)}" data-label-index="${Number(obj.label_index)}" ${i < 4 ? "open" : ""}>
      <summary class="objHead">
        <span class="objHeadLeft">
          <span class="swatch" style="background:${esc(obj.color)}"></span>
          <strong>${esc(obj.id)}</strong>
        </span>
        <span class="objMeta">area ${obj.area_px}px</span>
      </summary>
      <div class="objBody">
        <div class="objGrid">
          <label class="field">
            <span>Habilitado</span>
            <select data-prop="enabled">
              <option value="true" ${obj.enabled ? "selected" : ""}>Sim</option>
              <option value="false" ${!obj.enabled ? "selected" : ""}>Nao</option>
            </select>
          </label>
          <label class="field">
            <span>Cor</span>
            <input type="color" data-prop="color" value="${esc(obj.color)}" />
          </label>
          <label class="field">
            <span>Preenchimento</span>
            <select data-prop="fill_type">${fillOptionsHtml(obj.fill_type || "tatami")}</select>
          </label>
          <label class="field">
            <span>Densidade</span>
            <select data-prop="density">
              <option value="low" ${obj.density === "low" ? "selected" : ""}>Baixa</option>
              <option value="medium" ${obj.density !== "low" && obj.density !== "high" ? "selected" : ""}>Media</option>
              <option value="high" ${obj.density === "high" ? "selected" : ""}>Alta</option>
            </select>
          </label>
          <label class="field">
            <span>Compensacao encolhimento (mm)</span>
            <input type="number" data-prop="shrink_comp_mm" min="0" max="2" step="0.1" value="${Number(obj.shrink_comp_mm ?? 0.4)}" />
          </label>
          <label class="field">
            <span>Sob-costura</span>
            <select data-prop="underlay">
              <option value="low" ${obj.underlay === "low" ? "selected" : ""}>Baixa</option>
              <option value="medium" ${obj.underlay !== "low" && obj.underlay !== "high" ? "selected" : ""}>Media</option>
              <option value="high" ${obj.underlay === "high" ? "selected" : ""}>Alta</option>
            </select>
          </label>
          <label class="field">
            <span>Tipo de contorno</span>
            <select data-prop="outline_type">${outlineOptionsHtml(obj.outline_type || "satin")}</select>
          </label>
          <label class="field">
            <span>Largura contorno (mm)</span>
            <input type="number" data-prop="outline_width_mm" min="0.5" max="4" step="0.1" value="${Number(obj.outline_width_mm ?? 1.5)}" />
          </label>
          <label class="field">
            <span>Pull comp contorno (mm)</span>
            <input type="number" data-prop="outline_pull_comp_mm" min="0" max="0.8" step="0.1" value="${Number(obj.outline_pull_comp_mm ?? 0.3)}" />
          </label>
          <label class="field">
            <span>Overlap contorno (mm)</span>
            <input type="number" data-prop="outline_overlap_mm" min="0" max="1" step="0.1" value="${Number(obj.outline_overlap_mm ?? 0.4)}" />
          </label>
        </div>
      </div>
    </details>
  `).join("");

  objectsEditor.innerHTML = html;
  editorCard.hidden = false;
  renderPaletteEditor();
  applyObjectFilter();
}

function renderPaletteEditor() {
  if (!paletteEditor) return;
  const objects = autoPunchModel?.analysis?.objects || [];
  if (!objects.length) {
    paletteEditor.innerHTML = "";
    return;
  }

  const grouped = new Map();
  objects.forEach((obj) => {
    const idx = Number(obj.label_index);
    if (!grouped.has(idx)) {
      grouped.set(idx, {
        labelIndex: idx,
        color: obj.color,
        count: 0,
      });
    }
    grouped.get(idx).count += 1;
  });

  const rows = [...grouped.values()]
    .sort((a, b) => a.labelIndex - b.labelIndex)
    .map((row) => `
      <label class="paletteItem">
        <span class="paletteMeta">Cor ${row.labelIndex + 1} (${row.count} objeto(s))</span>
        <input type="color" value="${esc(row.color)}" data-palette-label="${row.labelIndex}" />
      </label>
    `)
    .join("");

  paletteEditor.innerHTML = rows;
}

function applyPaletteColorToLabel(labelIndex, colorHex) {
  const objects = autoPunchModel?.analysis?.objects || [];
  objects.forEach((obj) => {
    if (Number(obj.label_index) === Number(labelIndex)) {
      obj.color = colorHex;
    }
  });

  const cards = objectsEditor.querySelectorAll(`details.objItem[data-label-index="${Number(labelIndex)}"]`);
  cards.forEach((card) => {
    const sw = card.querySelector(".swatch");
    if (sw) sw.style.background = colorHex;
    const input = card.querySelector("input[data-prop='color']");
    if (input) input.value = colorHex;
  });
}

function applyObjectFilter() {
  const q = (objectFilter?.value || "").trim().toLowerCase();
  const cards = [...objectsEditor.querySelectorAll("details.objItem")];
  let visible = 0;
  cards.forEach((card) => {
    const id = (card.getAttribute("data-id") || "").toLowerCase();
    const show = !q || id.includes(q);
    card.classList.toggle("hiddenByFilter", !show);
    if (show) visible += 1;
  });
  if (objectsCount) {
    objectsCount.textContent = `${visible} visíveis / ${cards.length} objetos`;
  }
}

function applyBulkToAllObjects() {
  if (!autoPunchModel?.analysis?.objects?.length) return;
  readEditorIntoModel();
  autoPunchModel.analysis.objects.forEach((obj) => {
    obj.fill_type = bulkFillType?.value || obj.fill_type;
    obj.density = bulkDensity?.value || obj.density;
    obj.underlay = bulkUnderlay?.value || obj.underlay;
    obj.shrink_comp_mm = Number(bulkShrink?.value || obj.shrink_comp_mm || 0.4);
    obj.outline_type = bulkOutlineType?.value || obj.outline_type || "satin";
    obj.outline_width_mm = Number(bulkOutlineWidth?.value || obj.outline_width_mm || 1.5);
    obj.outline_pull_comp_mm = Number(bulkOutlinePull?.value || obj.outline_pull_comp_mm || 0.3);
    obj.outline_overlap_mm = Number(bulkOutlineOverlap?.value || obj.outline_overlap_mm || 0.4);
  });
  renderObjectsEditor();
}

function readEditorIntoModel() {
  if (!autoPunchModel?.analysis?.objects?.length) return;

  const map = new Map(autoPunchModel.analysis.objects.map((o) => [o.id, o]));
  objectsEditor.querySelectorAll("details.objItem").forEach((card) => {
    const id = card.getAttribute("data-id");
    const obj = map.get(id);
    if (!obj) return;

    card.querySelectorAll("[data-prop]").forEach((input) => {
      const prop = input.getAttribute("data-prop");
      const value = input.value;
      if (prop === "enabled") {
        obj.enabled = value === "true";
      } else if (prop === "shrink_comp_mm") {
        obj.shrink_comp_mm = Number(value || 0);
      } else {
        obj[prop] = value;
      }
    });
  });
}

function getDesignConfig() {
  readEditorIntoModel();
  if (!autoPunchModel?.analysis?.objects?.length) return null;
  const qualityPreset = el("qualityPreset")?.value || "medio";
  const defaults = autoPunchModel?.analysis?.defaults || {};
  return {
    global: {
      quality_preset: qualityPreset,
      density: defaults.density || "medium",
      shrink_comp_mm: Number(defaults.shrink_comp_mm ?? 0.4),
      underlay: defaults.underlay || "medium",
      outline: true,
      outline_keepout_mm: Number(defaults.outline_keepout_mm ?? 0),
      outline_type: defaults.outline_type || "satin",
      outline_width_mm: Number(defaults.outline_width_mm ?? 1.5),
      outline_pull_comp_mm: Number(defaults.outline_pull_comp_mm ?? 0.3),
      outline_overlap_mm: Number(defaults.outline_overlap_mm ?? 0.4),
    },
    objects: autoPunchModel.analysis.objects,
  };
}

function buildConvertFormData() {
  const imageFile = el("image").files?.[0];
  if (!imageFile) return null;

  const fd = new FormData();
  fd.append("image", imageFile);
  fd.append("size_cm", el("sizeCm").value);
  fd.append("format", el("format").value);
  fd.append("colors", el("colors").value);
  fd.append("detail", el("detail").value);
  fd.append("quality_preset", el("qualityPreset").value);

  const designConfig = getDesignConfig();
  if (designConfig) {
    fd.append("design_config", JSON.stringify(designConfig));
  }
  return fd;
}

async function runConvert({ silent = false } = {}) {
  const imageFile = el("image").files?.[0];
  if (!imageFile) return;

  const apiBase = (apiBaseInput.value || "").trim().replace(/\/+$/, "");
  if (!apiBase) {
    if (!silent) setStatus("Informe a URL do backend (API).", "error");
    return;
  }

  const fd = buildConvertFormData();
  if (!fd) return;

  if (!silent) {
    setStatus("Convertendo... isso pode levar alguns segundos.", "info");
    resultCard.hidden = true;
  }
  btnReset.disabled = true;

  const res = await fetch(`${apiBase}/convert`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Erro HTTP ${res.status}`);
  }

  const data = await res.json();
  previewImg.src = `${apiBase}${data.preview_url}?t=${Date.now()}`;
  downloadBtn.href = `${apiBase}${data.download_url}`;
  metaEl.textContent = JSON.stringify(data.meta, null, 2);
  resultCard.hidden = false;
  btnReset.disabled = false;

  if (!silent) {
    setStatus("Conversao concluida.", "ok");
  }
}

function scheduleAutoPreviewUpdate() {
  if (autoPreviewTimer) {
    clearTimeout(autoPreviewTimer);
  }

  autoPreviewTimer = setTimeout(async () => {
    if (autoPreviewRunning) {
      autoPreviewPending = true;
      return;
    }

    autoPreviewRunning = true;
    try {
      await runConvert({ silent: true });
      setStatus("Alteracao salva automaticamente e preview atualizado.", "ok");
    } catch (err) {
      setStatus(`Falha ao atualizar preview automaticamente:\n${err.message}`, "error");
    } finally {
      autoPreviewRunning = false;
      if (autoPreviewPending) {
        autoPreviewPending = false;
        scheduleAutoPreviewUpdate();
      }
    }
  }, 850);
}

btnReset.addEventListener("click", () => {
  form.reset();
  resultCard.hidden = true;
  previewImg.removeAttribute("src");
  downloadBtn.href = "#";
  metaEl.textContent = "";
  setStatus("");
  btnReset.disabled = true;
  qualityAlert.hidden = true;
  autoPunchModel = null;
  editorCard.hidden = true;
  objectsEditor.innerHTML = "";
});

btnExpandAll?.addEventListener("click", () => {
  objectsEditor.querySelectorAll("details.objItem").forEach((d) => { d.open = true; });
});

btnCollapseAll?.addEventListener("click", () => {
  objectsEditor.querySelectorAll("details.objItem").forEach((d) => { d.open = false; });
});

btnApplyBulk?.addEventListener("click", () => {
  applyBulkToAllObjects();
  setStatus("Ajustes globais aplicados aos objetos.", "ok");
});

objectFilter?.addEventListener("input", () => {
  applyObjectFilter();
});

paletteEditor?.addEventListener("input", (ev) => {
  const target = ev.target;
  if (!(target instanceof HTMLInputElement)) return;
  const label = target.getAttribute("data-palette-label");
  if (label === null) return;
  applyPaletteColorToLabel(Number(label), target.value);
  scheduleAutoPreviewUpdate();
});

objectsEditor?.addEventListener("input", (ev) => {
  const target = ev.target;
  if (!(target instanceof HTMLElement)) return;
  const prop = target.getAttribute("data-prop");
  if (!prop) return;

  readEditorIntoModel();

  if (prop === "color") {
    const card = target.closest("details.objItem");
    if (card) {
      const sw = card.querySelector(".swatch");
      if (sw && target instanceof HTMLInputElement) {
        sw.style.background = target.value;
      }
    }
    renderPaletteEditor();
    scheduleAutoPreviewUpdate();
  }
});

objectsEditor?.addEventListener("change", (ev) => {
  const target = ev.target;
  if (!(target instanceof HTMLElement)) return;
  const prop = target.getAttribute("data-prop");
  if (!prop) return;

  readEditorIntoModel();
  if (prop === "color") {
    renderPaletteEditor();
    scheduleAutoPreviewUpdate();
  }
});

paletteEditor?.addEventListener("change", (ev) => {
  const target = ev.target;
  if (!(target instanceof HTMLInputElement)) return;
  const label = target.getAttribute("data-palette-label");
  if (label === null) return;
  applyPaletteColorToLabel(Number(label), target.value);
  scheduleAutoPreviewUpdate();
});

el("image").addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  qualityAlert.hidden = true;
  if (!file) return;

  const q = await checkQuality(file);
  if (q && q.minSide < 1200) qualityAlert.hidden = false;
});

btnAutoPunch?.addEventListener("click", async () => {
  const imageFile = el("image").files?.[0];
  if (!imageFile) {
    setStatus("Selecione uma imagem antes da perfuracao automatica.", "error");
    return;
  }

  const apiBase = (apiBaseInput.value || "").trim().replace(/\/+$/, "");
  if (!apiBase) {
    setStatus("Informe a URL do backend (API).", "error");
    return;
  }

  const fd = new FormData();
  fd.append("image", imageFile);
  fd.append("colors", el("colors").value);
  fd.append("detail", el("detail").value);
  fd.append("quality_preset", el("qualityPreset").value);

  setStatus("Executando perfuracao automatica...", "info");
  btnReset.disabled = true;

  try {
    const res = await fetch(`${apiBase}/autopunch`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Erro HTTP ${res.status}`);
    }

    autoPunchModel = await res.json();
    renderObjectsEditor();
    btnReset.disabled = false;
    setStatus("Perfuracao concluida. Ajuste os objetos e clique em converter.", "ok");
  } catch (err) {
    setStatus(`Falha na perfuracao automatica:\n${err.message}`, "error");
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await runConvert({ silent: false });
  } catch (err) {
    setStatus(`Falha na conversao:\n${err.message}`, "error");
  }
});

btnApiSettings?.addEventListener("click", () => {
  openApiSettings();
});

btnCloseApiSettings?.addEventListener("click", () => {
  closeApiSettings();
});

btnCancelApiSettings?.addEventListener("click", () => {
  closeApiSettings();
});

btnSaveApiSettings?.addEventListener("click", () => {
  saveApiBase();
});

apiBaseInput?.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") {
    ev.preventDefault();
    saveApiBase();
  }
});

apiSettingsBackdrop?.addEventListener("click", (ev) => {
  if (ev.target === apiSettingsBackdrop) {
    closeApiSettings();
  }
});

document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && apiSettingsBackdrop && !apiSettingsBackdrop.hidden) {
    closeApiSettings();
  }
});