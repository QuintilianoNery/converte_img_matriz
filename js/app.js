// Configure aqui a API padrão.
// Para GitHub Pages: configure para a URL do backend hospedado.
// Para local: http://127.0.0.1:8000

// ============================================================
// StitchMaster Pro – app.js
// Todas as funcionalidades originais + integração com novo layout
// ============================================================

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

// ── Element References ──────────────────────────────────────
const el = (id) => document.getElementById(id);

const form          = el("converterForm");
const statusEl      = el("status");
const statusEditorEl = el("statusEditor");
const resultCard    = el("resultCard");
const resultCardEditor = el("resultCardEditor");
const previewImg    = el("previewImg");
const downloadBtn   = el("downloadBtn");
const downloadBtnEditor = el("downloadBtnEditor");
const metaEl        = el("meta");
const metaEditorEl  = el("metaEditor");
const btnReset      = el("btnReset");
const btnReset2     = el("btnReset2");
const btnAutoPunch  = el("btnAutoPunch");
const btnConvert    = el("btnConvert");
const btnExpandAll  = el("btnExpandAll");
const btnCollapseAll = el("btnCollapseAll");
const btnApplyBulk  = el("btnApplyBulk");
const editorCard    = el("editorCard");
const objectsEditor = el("objectsEditor");
const paletteEditor = el("paletteEditor");
const objectFilter  = el("objectFilter");
const objectsCount  = el("objectsCount");
const colorsSelect  = el("colors");
const bulkFillType  = el("bulkFillType");
const bulkDensity   = el("bulkDensity");
const bulkUnderlay  = el("bulkUnderlay");
const bulkShrink    = el("bulkShrink");
const bulkOutlineType   = el("bulkOutlineType");
const bulkOutlineWidth  = el("bulkOutlineWidth");
const bulkOutlinePull   = el("bulkOutlinePull");
const bulkOutlineOverlap = el("bulkOutlineOverlap");
const apiBaseInput  = el("apiBase");
const btnApiSettings = el("btnApiSettings");
const apiSettingsBackdrop = el("apiSettingsBackdrop");
const btnCloseApiSettings = el("btnCloseApiSettings");
const btnCancelApiSettings = el("btnCancelApiSettings");
const btnSaveApiSettings = el("btnSaveApiSettings");
const qualityAlert  = el("qualityAlert");
const barPoints     = el("barPoints");
const barLine       = el("barLine");
const stageTitle    = el("stageTitle");
const stagePercent  = el("stagePercent");
const stageBarFill  = el("stageBarFill");
const stageSubtext  = el("stageSubtext");
const stageTitleInline = el("stageTitleInline");
const stagePercentInline = el("stagePercentInline");
const stageBarFillInline = el("stageBarFillInline");
const stageSubtextInline = el("stageSubtextInline");
const recentProjectsGrid = el("recentProjectsGrid");
const objectPreviewPopup = el("objectPreviewPopup");
const objectPreviewImage = el("objectPreviewImage");
const objectPreviewLabel = el("objectPreviewLabel");
const proTipsSection = el("proTipsSection");
const btnHideProTips = el("btnHideProTips");
const uploadMainSection = el("uploadMainSection");

// View elements
const dashView       = el("dashView");
const dashSidebar    = el("dashSidebar");
const editorToolbox  = el("editorToolbox");
const editorInspector = el("editorInspector");
const navPainel      = el("navPainel");
const navEditor      = el("navEditor");
const editorPreview  = el("editorPreview");
const canvasPlaceholder = el("canvasPlaceholder");
const inspObjectTree = el("inspObjectTree");
const inspBtnGenerate = el("inspBtnGenerate");
const inspFillType = el("inspFillType");
const inspFillType2 = el("inspFillType2");
const inspOutlineType = el("inspOutlineType");
const inspOutlineWidth = el("inspOutlineWidth");
const inspDensityRange = el("inspDensityRange");
const inspShrinkRange = el("inspShrinkRange");
const inspAutoUnderlayToggle = el("inspAutoUnderlayToggle");
const inspAutoUnderlayThumb = el("inspAutoUnderlayThumb");
const btnInspectorCollapse = el("btnInspectorCollapse");
const inspectorResizeHandle = el("inspectorResizeHandle");
const previewZoomRange = el("previewZoomRange");
const previewZoomPct = el("previewZoomPct");
const previewZoomBadge = el("previewZoomBadge");
const btnGenerateMachine = el("btnGenerateMachine");

// ── View Switching ──────────────────────────────────────────
let currentView = "dash"; // "dash" | "editor"

function switchToDashView(e) {
  if (e) e.preventDefault();
  currentView = "dash";

  dashView.classList.remove("hidden");
  editorCard.classList.add("hidden");

  dashSidebar.classList.remove("hidden");
  editorToolbox.classList.add("hidden");
  editorInspector.classList.add("hidden");

  // Nav active state
  navPainel.classList.add("text-primary", "border-b-2", "border-primary");
  navPainel.classList.remove("text-on-surface-variant", "border-transparent");
  navEditor.classList.remove("text-primary", "border-b-2", "border-primary");
  navEditor.classList.add("text-on-surface-variant", "border-transparent");
}

function switchToEditorView(e) {
  if (e) e.preventDefault();

  // Only switch if we have autopunch data, unless called from nav
  currentView = "editor";

  dashView.classList.add("hidden");
  editorCard.classList.remove("hidden");

  dashSidebar.classList.add("hidden");
  editorToolbox.classList.remove("hidden");
  editorToolbox.style.display = "flex";
  editorInspector.classList.remove("hidden");
  editorInspector.style.display = "flex";

  // Nav active state
  navEditor.classList.add("text-primary", "border-b-2", "border-primary");
  navEditor.classList.remove("text-on-surface-variant", "border-transparent");
  navPainel.classList.remove("text-primary", "border-b-2", "border-primary");
  navPainel.classList.add("text-on-surface-variant", "border-transparent");
}

// Inspector Tab Switching
function switchInspTab(tab, btn) {
  const panels = { props: "inspPanelProps", stitch: "inspPanelStitch", fill: "inspPanelFill", layers: "inspPanelLayers" };
  const buttons = { props: "inspTabProps", stitch: "inspTabStitch", fill: "inspTabFill", layers: "inspTabLayers" };

  Object.keys(panels).forEach(k => {
    const panel = el(panels[k]);
    const tabBtn = el(buttons[k]);
    if (k === tab) {
      panel.classList.remove("hidden");
      tabBtn.classList.add("text-primary", "border-b", "border-primary");
      tabBtn.classList.remove("text-on-surface-variant");
    } else {
      panel.classList.add("hidden");
      tabBtn.classList.remove("text-primary", "border-b", "border-primary");
      tabBtn.classList.add("text-on-surface-variant");
    }
  });
}

// ── API Settings ────────────────────────────────────────────
function normalizeApiBase(url) {
  return String(url || "").trim().replace(/\/+$/, "");
}

function loadSavedApiBase() {
  let saved = "";
  try { saved = localStorage.getItem(API_BASE_STORAGE_KEY) || ""; } catch (_) {}
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
  try { localStorage.setItem(API_BASE_STORAGE_KEY, normalized); } catch (_) {}
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

// ── State ───────────────────────────────────────────────────
let autoPunchModel = null;
let autoPreviewTimer = null;
let autoPreviewRunning = false;
let autoPreviewPending = false;
let requestInFlight = false;
let stageProgressValue = 0;
let stageProgressTimer = null;
let sourceImagePreviewUrl = "";
let sourceImageEl = new Image();
let autoUnderlayEnabled = true;
const underlayBackupByObjectId = new Map();

const RECENT_PROJECTS_KEY = "converter.recentProjects";
const UI_SETTINGS_KEY = "converter.uiSettings";
const DEFAULT_UI_SETTINGS = {
  hideProTips: false,
  inspectorCollapsed: false,
  inspectorWidth: 360,
  previewZoomPct: 100,
};

// ── Init Selects ────────────────────────────────────────────
function initColorSelector() {
  if (!colorsSelect) return;
  const current = Number(colorsSelect.value || 16);
  colorsSelect.innerHTML = "";
  for (let n = 1; n <= 24; n++) {
    const opt = document.createElement("option");
    opt.value = String(n);
    opt.textContent = String(n);
    if (n === current || (current < 1 && n === 16)) opt.selected = true;
    colorsSelect.appendChild(opt);
  }
}

initColorSelector();

if (bulkFillType) {
  bulkFillType.innerHTML = FILL_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === "tatami" ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

if (bulkOutlineType) {
  bulkOutlineType.innerHTML = OUTLINE_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === "satin" ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

if (inspFillType) {
  inspFillType.innerHTML = FILL_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === "tatami" ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

if (inspFillType2) {
  inspFillType2.innerHTML = FILL_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === "tatami" ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

if (inspOutlineType) {
  inspOutlineType.innerHTML = OUTLINE_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === "satin" ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

function applyInspectorSelections() {
  if (!autoPunchModel?.analysis?.objects?.length) {
    setStatus("Execute a perfuração automática para aplicar tipo de ponto no editor.", "info");
    return;
  }

  if (bulkFillType && inspFillType?.value) bulkFillType.value = inspFillType.value;
  if (bulkOutlineType && inspOutlineType?.value) bulkOutlineType.value = inspOutlineType.value;
  if (bulkOutlineWidth && inspOutlineWidth?.value) bulkOutlineWidth.value = inspOutlineWidth.value;

  applyBulkToAllObjects();
  scheduleAutoPreviewUpdate();
}

// ── Status ──────────────────────────────────────────────────
function setStatus(msg, kind = "info") {
  const text = msg || "";
  const colorClass = kind === "error" ? "status-error" : kind === "ok" ? "status-ok" : "status-info";

  // Update both status elements
  [statusEl, statusEditorEl].forEach(el => {
    if (!el) return;
    el.textContent = text;
    el.className = text ? `text-xs font-medium ${colorClass}` : "";
  });
}

function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeUnderlayValue(value, fallback = "medium") {
  const v = String(value || "").trim().toLowerCase();
  if (["none", "off", "disabled", "desligada", "desligado"].includes(v)) return "none";
  if (["low", "medium", "high"].includes(v)) return v;
  return fallback;
}

function isUnderlayDisabledValue(value) {
  return normalizeUnderlayValue(value, "none") === "none";
}

function setAutoUnderlayToggleUI(enabled) {
  autoUnderlayEnabled = !!enabled;
  if (inspAutoUnderlayToggle) {
    inspAutoUnderlayToggle.setAttribute("aria-checked", autoUnderlayEnabled ? "true" : "false");
    inspAutoUnderlayToggle.classList.toggle("bg-primary", autoUnderlayEnabled);
    inspAutoUnderlayToggle.classList.toggle("bg-outline-variant", !autoUnderlayEnabled);
  }
  if (inspAutoUnderlayThumb) {
    inspAutoUnderlayThumb.classList.toggle("translate-x-4", autoUnderlayEnabled);
    inspAutoUnderlayThumb.classList.toggle("translate-x-0", !autoUnderlayEnabled);
  }
  if (bulkUnderlay) {
    bulkUnderlay.disabled = !autoUnderlayEnabled;
    bulkUnderlay.classList.toggle("opacity-50", !autoUnderlayEnabled);
    if (!autoUnderlayEnabled) {
      bulkUnderlay.value = "none";
    } else if (isUnderlayDisabledValue(bulkUnderlay.value)) {
      bulkUnderlay.value = "medium";
    }
  }
  objectsEditor?.querySelectorAll("select[data-prop='underlay']").forEach((input) => {
    input.disabled = !autoUnderlayEnabled;
    input.classList.toggle("opacity-50", !autoUnderlayEnabled);
  });
}

function syncAutoUnderlayStateFromModel() {
  const objects = autoPunchModel?.analysis?.objects || [];
  if (!objects.length) {
    setAutoUnderlayToggleUI(true);
    return;
  }
  const enabled = objects.some((obj) => !isUnderlayDisabledValue(obj.underlay));
  setAutoUnderlayToggleUI(enabled);
}

function toggleAutoUnderlay(nextEnabled) {
  const objects = autoPunchModel?.analysis?.objects || [];
  if (!objects.length) {
    setStatus("Execute a perfuração automática para usar este controle.", "info");
    setAutoUnderlayToggleUI(true);
    return;
  }

  readEditorIntoModel();
  const enabled = typeof nextEnabled === "boolean" ? nextEnabled : !autoUnderlayEnabled;

  if (!enabled) {
    objects.forEach((obj) => {
      const current = normalizeUnderlayValue(obj.underlay, "medium");
      if (current !== "none") {
        underlayBackupByObjectId.set(obj.id, current);
      }
      obj.underlay = "none";
    });
    setStatus("Sob-costura automática desabilitada.", "ok");
  } else {
    const fallback = normalizeUnderlayValue(bulkUnderlay?.value, "medium");
    objects.forEach((obj) => {
      const restored = normalizeUnderlayValue(underlayBackupByObjectId.get(obj.id), fallback);
      obj.underlay = restored === "none" ? "medium" : restored;
    });
    setStatus("Sob-costura automática habilitada.", "ok");
  }

  setAutoUnderlayToggleUI(enabled);
  renderObjectsEditor();
  scheduleAutoPreviewUpdate();
}

function setNetworkActionButtonsDisabled(disabled) {
  [
    btnAutoPunch,
    btnConvert,
    btnGenerateMachine,
    inspBtnGenerate,
    el("btnToolAutoPunch"),
  ].forEach((button) => {
    if (!button) return;
    button.disabled = !!disabled;
  });
}

function setStageProgress(stage, value, subtext) {
  const safeValue = Math.max(0, Math.min(100, Number(value || 0)));
  [stageTitle, stageTitleInline].forEach((node) => { if (node) node.textContent = stage; });
  [stagePercent, stagePercentInline].forEach((node) => { if (node) node.textContent = `${safeValue.toFixed(0)}%`; });
  [stageBarFill, stageBarFillInline].forEach((node) => { if (node) node.style.width = `${safeValue}%`; });
  [stageSubtext, stageSubtextInline].forEach((node) => { if (node) node.textContent = subtext; });
}

function beginStageProgress(stage) {
  if (stageProgressTimer) {
    clearInterval(stageProgressTimer);
    stageProgressTimer = null;
  }
  stageProgressValue = 3;
  setStageProgress(stage, stageProgressValue, `${stage} em andamento...`);
  stageProgressTimer = setInterval(() => {
    stageProgressValue = Math.min(95, stageProgressValue + Math.max(1, (98 - stageProgressValue) * 0.07));
    setStageProgress(stage, stageProgressValue, `${stage} em andamento...`);
  }, 220);
}

function endStageProgress(stage, ok = true, subtext = "") {
  if (stageProgressTimer) {
    clearInterval(stageProgressTimer);
    stageProgressTimer = null;
  }
  if (ok) {
    setStageProgress(stage, 100, subtext || `${stage} concluído.`);
  } else {
    setStageProgress(stage, stageProgressValue || 0, subtext || `${stage} falhou.`);
  }
}

function updateFooterStats(totalPoints) {
  const stitches = Math.max(0, Number(totalPoints || 0));
  const lineMeters = stitches * 0.0004;
  if (barPoints) {
    barPoints.textContent = `PONTOS: ${stitches.toLocaleString("pt-BR")}`;
  }
  if (barLine) {
    barLine.textContent = `LINHA: ${lineMeters.toFixed(1)}M`;
  }
}

function loadRecentProjects() {
  try {
    const raw = localStorage.getItem(RECENT_PROJECTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function saveRecentProjects(list) {
  try {
    localStorage.setItem(RECENT_PROJECTS_KEY, JSON.stringify(list));
  } catch (_) {
    // Ignora falha de storage.
  }
}

function loadUiSettings() {
  try {
    const raw = localStorage.getItem(UI_SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_UI_SETTINGS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_UI_SETTINGS, ...(parsed || {}) };
  } catch (_) {
    return { ...DEFAULT_UI_SETTINGS };
  }
}

function saveUiSettings(next) {
  const merged = { ...loadUiSettings(), ...(next || {}) };
  try {
    localStorage.setItem(UI_SETTINGS_KEY, JSON.stringify(merged));
  } catch (_) {
    // Ignora falha de storage.
  }
  return merged;
}

function applyProTipsVisibility(hidden) {
  if (!proTipsSection) return;
  proTipsSection.classList.toggle("hidden", !!hidden);
  if (uploadMainSection) {
    uploadMainSection.classList.toggle("lg:col-span-8", !hidden);
    uploadMainSection.classList.toggle("lg:col-span-12", !!hidden);
  }
}

function applyPreviewZoom(pct) {
  const value = Math.max(50, Math.min(300, Number(pct || 100)));
  if (previewZoomRange) previewZoomRange.value = String(value);
  if (previewZoomPct) previewZoomPct.textContent = `${value}%`;
  if (previewZoomBadge) previewZoomBadge.textContent = `${value}% VISOR`;
  if (editorPreview) {
    editorPreview.style.transformOrigin = "center center";
    editorPreview.style.transform = `scale(${(value / 100).toFixed(2)})`;
  }
  saveUiSettings({ previewZoomPct: value });
}

function setInspectorCollapsed(collapsed) {
  if (!editorInspector) return;
  const next = !!collapsed;
  editorInspector.classList.toggle("inspector-collapsed", next);
  saveUiSettings({ inspectorCollapsed: next });
}

function setInspectorWidth(widthPx) {
  if (!editorInspector) return;
  const clamped = Math.max(280, Math.min(760, Number(widthPx || 360)));
  editorInspector.style.width = `${clamped}px`;
  saveUiSettings({ inspectorWidth: clamped });
}

function renderRecentProjects() {
  if (!recentProjectsGrid) return;
  const items = loadRecentProjects();
  if (!items.length) {
    recentProjectsGrid.innerHTML = `
      <div class="p-4 rounded-xl border border-outline-variant/10 bg-surface-container-low text-[11px] text-outline">
        Nenhum projeto convertido ainda.
      </div>
    `;
    return;
  }

  recentProjectsGrid.innerHTML = items.map((item) => `
    <article class="group bg-surface-container-low rounded-xl overflow-hidden border border-outline-variant/10 transition-all hover:border-primary/20 hover:shadow-xl hover:shadow-primary/5">
      <div class="h-36 relative overflow-hidden bg-surface-container-lowest flex items-center justify-center">
        ${item.previewUrl ? `<img src="${esc(item.previewUrl)}" alt="Projeto recente" class="w-full h-full object-cover"/>` : '<span class="material-symbols-outlined text-outline text-4xl">texture</span>'}
        <div class="absolute top-2 right-2 px-2 py-0.5 bg-surface-container-lowest/90 backdrop-blur rounded text-[9px] font-bold text-primary flex items-center gap-1">
          <span class="h-1.5 w-1.5 rounded-full bg-primary"></span> Concluído
        </div>
      </div>
      <div class="p-3">
        <h4 class="font-bold text-xs mb-1 text-on-surface truncate">${esc(item.title || "Projeto")}</h4>
        <div class="flex justify-between items-center text-[10px] text-outline">
          <span>${Number(item.points || 0).toLocaleString("pt-BR")} Pontos</span>
          <span>${esc(item.when || "agora")}</span>
        </div>
      </div>
    </article>
  `).join("");
}

function addRecentProject(entry) {
  const list = loadRecentProjects();
  const filtered = list.filter((x) => x.id !== entry.id);
  filtered.unshift(entry);
  saveRecentProjects(filtered.slice(0, 5));
  renderRecentProjects();
}

function hideObjectPreviewPopup() {
  if (!objectPreviewPopup) return;
  objectPreviewPopup.classList.add("hidden");
}

function updateObjectPreviewPopupPosition(ev) {
  if (!objectPreviewPopup || objectPreviewPopup.classList.contains("hidden")) return;
  const x = Math.min(window.innerWidth - 190, ev.clientX + 14);
  const y = Math.min(window.innerHeight - 170, ev.clientY + 14);
  objectPreviewPopup.style.left = `${x}px`;
  objectPreviewPopup.style.top = `${y}px`;
}

function buildObjectCropDataUrl(obj) {
  if (!obj || !sourceImageEl || !sourceImageEl.naturalWidth || !sourceImageEl.naturalHeight) return "";
  const sizeInfo = autoPunchModel?.analysis?.image_size;
  const refW = Number(sizeInfo?.width || sourceImageEl.naturalWidth);
  const refH = Number(sizeInfo?.height || sourceImageEl.naturalHeight);
  const scaleX = sourceImageEl.naturalWidth / Math.max(1, refW);
  const scaleY = sourceImageEl.naturalHeight / Math.max(1, refH);
  const [minX, minY, maxX, maxY] = obj.bbox || [0, 0, 0, 0];
  const sx = Math.max(0, Math.floor(minX * scaleX));
  const sy = Math.max(0, Math.floor(minY * scaleY));
  const sw = Math.max(1, Math.floor((maxX - minX + 1) * scaleX));
  const sh = Math.max(1, Math.floor((maxY - minY + 1) * scaleY));

  const canvas = document.createElement("canvas");
  canvas.width = 140;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  ctx.fillStyle = "#0c0e11";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const fit = Math.min(canvas.width / sw, canvas.height / sh);
  const dw = Math.max(1, Math.floor(sw * fit));
  const dh = Math.max(1, Math.floor(sh * fit));
  const dx = Math.floor((canvas.width - dw) / 2);
  const dy = Math.floor((canvas.height - dh) / 2);
  ctx.drawImage(sourceImageEl, sx, sy, sw, sh, dx, dy, dw, dh);
  return canvas.toDataURL("image/png");
}

function showObjectPreviewPopup(objectId, ev) {
  if (!objectPreviewPopup || !objectPreviewImage || !objectPreviewLabel) return;
  const objects = autoPunchModel?.analysis?.objects || [];
  const obj = objects.find((o) => String(o.id) === String(objectId));
  if (!obj) return;
  objectPreviewLabel.textContent = `${obj.id} · área ${obj.area_px}px`;
  const crop = buildObjectCropDataUrl(obj);
  if (crop) {
    objectPreviewImage.src = crop;
  } else {
    objectPreviewImage.src = "";
  }
  objectPreviewPopup.classList.remove("hidden");
  updateObjectPreviewPopupPosition(ev);
}

// ── Quality Check ───────────────────────────────────────────
function checkQuality(file) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.width, height: img.height, minSide: Math.min(img.width, img.height) });
    img.onerror = () => resolve(null);
    img.src = URL.createObjectURL(file);
  });
}

// ── Fill / Outline Options HTML ─────────────────────────────
function fillOptionsHtml(selected) {
  return FILL_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

function outlineOptionsHtml(selected) {
  return OUTLINE_OPTIONS.map(([value, label]) =>
    `<option value="${value}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`
  ).join("");
}

// ── Objects Editor ──────────────────────────────────────────
function renderObjectsEditor() {
  if (!autoPunchModel?.analysis?.objects?.length) {
    editorCard.classList.add("hidden");
    objectsEditor.innerHTML = "";
    if (paletteEditor) paletteEditor.innerHTML = "";
    return;
  }

  const objects = autoPunchModel.analysis.objects;

  const html = objects.map((obj) => `
    <details class="objItem" data-id="${esc(obj.id)}" data-label-index="${Number(obj.label_index)}">
      <summary class="objHead">
        <span class="objHeadLeft">
          <span class="swatch" style="background:${esc(obj.color)}"></span>
          <strong class="text-xs text-on-surface">${esc(obj.id)}</strong>
        </span>
        <span class="text-[10px] text-outline">area ${obj.area_px}px</span>
      </summary>
      <div class="objBody">
        <div class="objGrid">
          <div class="objField">
            <label>Habilitado</label>
            <select data-prop="enabled" class="inspector-select">
              <option value="true" ${obj.enabled ? "selected" : ""}>Sim</option>
              <option value="false" ${!obj.enabled ? "selected" : ""}>Não</option>
            </select>
          </div>
          <div class="objField">
            <label>Cor</label>
            <input type="color" data-prop="color" value="${esc(obj.color)}" class="objField"/>
          </div>
          <div class="objField">
            <label>Preenchimento</label>
            <select data-prop="fill_type" class="inspector-select">${fillOptionsHtml(obj.fill_type || "tatami")}</select>
          </div>
          <div class="objField">
            <label>Densidade</label>
            <select data-prop="density" class="inspector-select">
              <option value="low" ${obj.density === "low" ? "selected" : ""}>Baixa</option>
              <option value="medium" ${obj.density !== "low" && obj.density !== "high" ? "selected" : ""}>Média</option>
              <option value="high" ${obj.density === "high" ? "selected" : ""}>Alta</option>
            </select>
          </div>
          <div class="objField">
            <label>Compensação (mm)</label>
            <input type="number" data-prop="shrink_comp_mm" min="0" max="2" step="0.1" value="${Number(obj.shrink_comp_mm ?? 0.4)}" class="inspector-input"/>
          </div>
          <div class="objField">
            <label>Sob-costura</label>
            <select data-prop="underlay" class="inspector-select">
              <option value="none" ${normalizeUnderlayValue(obj.underlay, "medium") === "none" ? "selected" : ""}>Desligada</option>
              <option value="low" ${normalizeUnderlayValue(obj.underlay, "medium") === "low" ? "selected" : ""}>Baixa</option>
              <option value="medium" ${normalizeUnderlayValue(obj.underlay, "medium") === "medium" ? "selected" : ""}>Média</option>
              <option value="high" ${normalizeUnderlayValue(obj.underlay, "medium") === "high" ? "selected" : ""}>Alta</option>
            </select>
          </div>
          <div class="objField">
            <label>Tipo de Contorno</label>
            <select data-prop="outline_type" class="inspector-select">${outlineOptionsHtml(obj.outline_type || "satin")}</select>
          </div>
          <div class="objField">
            <label>Largura Contorno (mm)</label>
            <input type="number" data-prop="outline_width_mm" min="0.5" max="4" step="0.1" value="${Number(obj.outline_width_mm ?? 1.5)}" class="inspector-input"/>
          </div>
          <div class="objField">
            <label>Pull Comp (mm)</label>
            <input type="number" data-prop="outline_pull_comp_mm" min="0" max="0.8" step="0.1" value="${Number(obj.outline_pull_comp_mm ?? 0.3)}" class="inspector-input"/>
          </div>
          <div class="objField">
            <label>Overlap (mm)</label>
            <input type="number" data-prop="outline_overlap_mm" min="0" max="1" step="0.1" value="${Number(obj.outline_overlap_mm ?? 0.4)}" class="inspector-input"/>
          </div>
        </div>
      </div>
    </details>
  `).join("");

  objectsEditor.innerHTML = html;
  editorCard.classList.remove("hidden");
  renderPaletteEditor();
  updateInspectorObjectTree();
  applyObjectFilter();
  syncAutoUnderlayStateFromModel();

  const firstEnabled = objects.find((o) => o.enabled) || objects[0];
  if (firstEnabled) {
    if (inspFillType) inspFillType.value = firstEnabled.fill_type || "tatami";
    if (inspFillType2) inspFillType2.value = firstEnabled.fill_type || "tatami";
    if (inspOutlineType) inspOutlineType.value = firstEnabled.outline_type || "satin";
    if (inspOutlineWidth) inspOutlineWidth.value = String(Number(firstEnabled.outline_width_mm ?? 1.5));
  }

  // Update status bar
  const totalPoints = objects.reduce((acc, o) => acc + (o.area_px || 0), 0);
  updateFooterStats(totalPoints);
}

function renderPaletteEditor() {
  if (!paletteEditor) return;
  const objects = autoPunchModel?.analysis?.objects || [];
  if (!objects.length) { paletteEditor.innerHTML = ""; return; }

  const grouped = new Map();
  objects.forEach((obj) => {
    const idx = Number(obj.label_index);
    if (!grouped.has(idx)) grouped.set(idx, { labelIndex: idx, color: obj.color, count: 0 });
    grouped.get(idx).count += 1;
  });

  const rows = [...grouped.values()]
    .sort((a, b) => a.labelIndex - b.labelIndex)
    .map(row => `
      <label class="paletteItem">
        <span class="paletteMeta">Cor ${row.labelIndex + 1} (${row.count} obj.)</span>
        <input type="color" value="${esc(row.color)}" data-palette-label="${row.labelIndex}" class="paletteItem"/>
      </label>
    `).join("");

  paletteEditor.innerHTML = rows;
}

function updateInspectorObjectTree() {
  if (!inspObjectTree) return;
  const objects = autoPunchModel?.analysis?.objects || [];
  if (!objects.length) return;

  const treeHtml = objects.slice(0, 8).map((obj, i) => `
    <div class="flex items-center gap-2 p-2 rounded-lg ${i === 0 ? 'bg-primary/10 border-l-2 border-primary' : 'hover:bg-surface-container-highest'} transition-colors cursor-pointer">
      <span class="inline-block w-3 h-3 rounded flex-shrink-0" style="background:${esc(obj.color)}"></span>
      <div class="flex-1 min-w-0">
        <p class="text-[10px] font-bold text-on-surface truncate">${esc(obj.id)}</p>
        <p class="text-[9px] text-outline">Área: ${obj.area_px}px</p>
      </div>
      <button type="button" data-eye-id="${esc(obj.id)}" class="text-outline hover:text-primary transition-colors p-1 rounded">
        <span class="material-symbols-outlined text-xs">visibility</span>
      </button>
    </div>
  `).join("");

  inspObjectTree.innerHTML = treeHtml + (objects.length > 8 ? `<p class="text-[9px] text-outline mt-2 text-center">+${objects.length - 8} objetos na lista principal</p>` : "");
}

function applyPaletteColorToLabel(labelIndex, colorHex) {
  const objects = autoPunchModel?.analysis?.objects || [];
  objects.forEach(obj => {
    if (Number(obj.label_index) === Number(labelIndex)) obj.color = colorHex;
  });
  objectsEditor.querySelectorAll(`details.objItem[data-label-index="${Number(labelIndex)}"]`).forEach(card => {
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
  cards.forEach(card => {
    const id = (card.getAttribute("data-id") || "").toLowerCase();
    const show = !q || id.includes(q);
    card.classList.toggle("hiddenByFilter", !show);
    if (show) visible++;
  });
  if (objectsCount) objectsCount.textContent = `${visible} visíveis / ${cards.length} objetos`;
}

function applyBulkToAllObjects() {
  if (!autoPunchModel?.analysis?.objects?.length) return;
  readEditorIntoModel();
  autoPunchModel.analysis.objects.forEach(obj => {
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
  const map = new Map(autoPunchModel.analysis.objects.map(o => [o.id, o]));
  objectsEditor.querySelectorAll("details.objItem").forEach(card => {
    const id = card.getAttribute("data-id");
    const obj = map.get(id);
    if (!obj) return;
    card.querySelectorAll("[data-prop]").forEach(input => {
      const prop = input.getAttribute("data-prop");
      const value = input.value;
      if (prop === "enabled") obj.enabled = value === "true";
      else if (prop === "shrink_comp_mm") obj.shrink_comp_mm = Number(value || 0);
      else obj[prop] = value;
    });
  });
}

// ── Build Convert FormData ──────────────────────────────────
function getDesignConfig() {
  readEditorIntoModel();
  if (!autoPunchModel?.analysis?.objects?.length) return null;
  const qp = el("qualityPreset")?.value || "medio";
  const defaults = autoPunchModel?.analysis?.defaults || {};
  return {
    global: {
      quality_preset: qp,
      density: defaults.density || "medium",
      shrink_comp_mm: Number(defaults.shrink_comp_mm ?? 0.4),
      underlay: autoUnderlayEnabled ? (defaults.underlay || "medium") : "none",
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
  if (designConfig) fd.append("design_config", JSON.stringify(designConfig));
  return fd;
}

function applyAutoPunchRecommendations(analysis) {
  const recommended = analysis?.recommended || {};
  const globalCfg = recommended.global || analysis?.defaults || {};

  if (el("qualityPreset") && recommended.quality_preset) {
    el("qualityPreset").value = String(recommended.quality_preset);
  }
  if (el("detail") && recommended.detail) {
    el("detail").value = String(recommended.detail);
  }
  if (colorsSelect && Number.isFinite(Number(recommended.colors))) {
    const c = Math.max(1, Math.min(24, Number(recommended.colors)));
    colorsSelect.value = String(c);
  }

  if (bulkFillType && globalCfg.fill_type) bulkFillType.value = String(globalCfg.fill_type);
  if (bulkDensity && globalCfg.density) bulkDensity.value = String(globalCfg.density);
  if (bulkShrink && globalCfg.shrink_comp_mm !== undefined) bulkShrink.value = String(Number(globalCfg.shrink_comp_mm).toFixed(2));
  if (bulkOutlineType && globalCfg.outline_type) bulkOutlineType.value = String(globalCfg.outline_type);
  if (bulkOutlineWidth && globalCfg.outline_width_mm !== undefined) bulkOutlineWidth.value = String(Number(globalCfg.outline_width_mm));
  if (bulkOutlinePull && globalCfg.outline_pull_comp_mm !== undefined) bulkOutlinePull.value = String(Number(globalCfg.outline_pull_comp_mm));
  if (bulkOutlineOverlap && globalCfg.outline_overlap_mm !== undefined) bulkOutlineOverlap.value = String(Number(globalCfg.outline_overlap_mm));

  const underlay = normalizeUnderlayValue(globalCfg.underlay, "medium");
  if (bulkUnderlay) bulkUnderlay.value = underlay;
  setAutoUnderlayToggleUI(underlay !== "none");

  if (inspDensityRange && bulkDensity) {
    const map = { low: 2, medium: 5, high: 8 };
    inspDensityRange.value = String(map[bulkDensity.value] || 5);
    const label = el("inspDensityVal");
    if (label) label.textContent = (Number(inspDensityRange.value) * 0.1).toFixed(2) + "mm";
  }
  if (inspShrinkRange && bulkShrink) {
    const shr = Number(bulkShrink.value || 0.4);
    inspShrinkRange.value = String(Math.max(0, Math.min(20, Math.round(shr / 0.05))));
    const label = el("inspShrinkVal");
    if (label) label.textContent = (Number(inspShrinkRange.value) * 0.05).toFixed(2) + "mm";
  }
}

// ── Convert ─────────────────────────────────────────────────
async function runConvert({ silent = false } = {}) {
  if (requestInFlight) {
    if (!silent) setStatus("Aguarde a conclusão da ação em andamento.", "info");
    return;
  }

  const imageFile = el("image").files?.[0];
  if (!imageFile) {
    if (!silent) setStatus("Selecione uma imagem antes de converter.", "error");
    return;
  }

  const apiBase = (apiBaseInput.value || "").trim().replace(/\/+$/, "");
  if (!apiBase) {
    if (!silent) setStatus("Informe a URL do backend (API).", "error");
    return;
  }

  const fd = buildConvertFormData();
  if (!fd) return;

  requestInFlight = true;
  setNetworkActionButtonsDisabled(true);
  beginStageProgress("Converter");

  if (!silent) {
    setStatus("Convertendo... isso pode levar alguns segundos.", "info");
    resultCard.hidden = true;
    if (resultCardEditor) resultCardEditor.classList.add("hidden");
  }
  btnReset.disabled = true;

  try {
    const res = await fetch(`${apiBase}/convert`, { method: "POST", body: fd });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Erro HTTP ${res.status}`);
    }

    const data = await res.json();
    const previewUrl = `${apiBase}${data.preview_url}?t=${Date.now()}`;
    const previewBaseUrl = `${apiBase}${data.preview_url}`;
    const downloadUrl = `${apiBase}${data.download_url}`;
    const metaJson = JSON.stringify(data.meta, null, 2);

    // Update preview in both places
    previewImg.src = previewUrl;
    downloadBtn.href = downloadUrl;
    metaEl.textContent = metaJson;

    // Also update editor version
    if (downloadBtnEditor) downloadBtnEditor.href = downloadUrl;
    if (metaEditorEl) metaEditorEl.textContent = metaJson;

    // Update editor canvas preview
    if (editorPreview) {
      editorPreview.src = previewUrl;
      editorPreview.classList.remove("hidden");
      if (canvasPlaceholder) canvasPlaceholder.classList.add("hidden");
    }

    const points = Number(data?.meta?.total_stitches_approx || 0);

    addRecentProject({
      id: String(data.job_id || Date.now()),
      title: imageFile.name || "Projeto convertido",
      previewUrl: previewBaseUrl,
      downloadUrl,
      points,
      when: new Date().toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }),
    });

    resultCard.hidden = false;
    if (resultCardEditor) resultCardEditor.classList.remove("hidden");
    btnReset.disabled = false;
    endStageProgress("Converter", true, "Conversão concluída com sucesso.");

    if (!silent) setStatus("Conversão concluída.", "ok");
  } catch (err) {
    endStageProgress("Converter", false, `Falha: ${err.message || "erro desconhecido"}`);
    throw err;
  } finally {
    requestInFlight = false;
    setNetworkActionButtonsDisabled(false);
  }
}

// ── Auto-Preview ─────────────────────────────────────────────
function scheduleAutoPreviewUpdate() {
  if (autoPreviewTimer) clearTimeout(autoPreviewTimer);
  autoPreviewTimer = setTimeout(async () => {
    if (autoPreviewRunning) { autoPreviewPending = true; return; }
    autoPreviewRunning = true;
    try {
      await runConvert({ silent: true });
      setStatus("Preview atualizado automaticamente.", "ok");
    } catch (err) {
      setStatus(`Falha ao atualizar preview: ${err.message}`, "error");
    } finally {
      autoPreviewRunning = false;
      if (autoPreviewPending) { autoPreviewPending = false; scheduleAutoPreviewUpdate(); }
    }
  }, 1500);
}

// ── Upload Zone Drag & Drop ──────────────────────────────────
function setupUploadZone() {
  const zone = el("uploadZone");
  const fileInput = el("image");
  if (!zone || !fileInput) return;

  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", async e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const file = e.dataTransfer?.files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    // Transfer to file input
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    await handleFileSelected(file);
  });
}

async function handleFileSelected(file) {
  if (!file) return;
  qualityAlert.classList.add("hidden");
  const q = await checkQuality(file);
  if (q && q.minSide < 1200) qualityAlert.classList.remove("hidden");

  // New source image invalidates previous autopunch metrics/config.
  autoPunchModel = null;
  underlayBackupByObjectId.clear();
  setAutoUnderlayToggleUI(true);
  objectsEditor.innerHTML = "";
  if (paletteEditor) paletteEditor.innerHTML = "";
  editorCard.classList.add("hidden");
  hideObjectPreviewPopup();
  updateFooterStats(0);

  if (sourceImagePreviewUrl) {
    URL.revokeObjectURL(sourceImagePreviewUrl);
    sourceImagePreviewUrl = "";
  }
  sourceImagePreviewUrl = URL.createObjectURL(file);
  sourceImageEl = new Image();
  sourceImageEl.src = sourceImagePreviewUrl;

  // Show file name in upload zone
  const uploadTitle = el("uploadTitle");
  const uploadSub = el("uploadSub");
  const uploadIcon = el("uploadIcon");
  if (uploadTitle) uploadTitle.textContent = file.name;
  if (uploadSub) uploadSub.textContent = `${(file.size / 1024).toFixed(0)} KB · ${file.type}`;
  if (uploadIcon) {
    uploadIcon.innerHTML = '<span class="material-symbols-outlined text-2xl" style="font-variation-settings: \'FILL\' 1;">image</span>';
    uploadIcon.className = uploadIcon.className.replace("text-primary", "text-tertiary");
  }

  // Show image preview in canvas (editor view)
  if (editorPreview) {
    editorPreview.src = URL.createObjectURL(file);
    editorPreview.classList.remove("hidden");
    if (canvasPlaceholder) canvasPlaceholder.classList.add("hidden");
  }
}

setupUploadZone();

// ── Reset ────────────────────────────────────────────────────
function doReset() {
  form.reset();
  resultCard.hidden = true;
  if (resultCardEditor) resultCardEditor.classList.add("hidden");
  previewImg.removeAttribute("src");
  downloadBtn.href = "#";
  if (downloadBtnEditor) downloadBtnEditor.href = "#";
  metaEl.textContent = "";
  if (metaEditorEl) metaEditorEl.textContent = "";
  setStatus("");
  btnReset.disabled = true;
  qualityAlert.classList.add("hidden");
  autoPunchModel = null;
  underlayBackupByObjectId.clear();
  setAutoUnderlayToggleUI(true);
  objectsEditor.innerHTML = "";
  if (paletteEditor) paletteEditor.innerHTML = "";
  if (editorPreview) { editorPreview.src = ""; editorPreview.classList.add("hidden"); }
  if (canvasPlaceholder) canvasPlaceholder.classList.remove("hidden");
  hideObjectPreviewPopup();

  if (sourceImagePreviewUrl) {
    URL.revokeObjectURL(sourceImagePreviewUrl);
    sourceImagePreviewUrl = "";
  }

  // Reset upload zone UI
  const uploadTitle = el("uploadTitle");
  const uploadSub = el("uploadSub");
  const uploadIcon = el("uploadIcon");
  if (uploadTitle) uploadTitle.textContent = "Enviar Nova Imagem";
  if (uploadSub) uploadSub.textContent = "Arraste e solte seu arquivo PNG, SVG ou AI aqui para digitalização automática";
  if (uploadIcon) {
    uploadIcon.innerHTML = '<span class="material-symbols-outlined text-2xl">cloud_upload</span>';
    uploadIcon.className = uploadIcon.className.replace("text-tertiary", "text-primary");
  }

  updateFooterStats(0);
  setStageProgress("Aguardando", 0, "Sem processamento em execução.");

  switchToDashView();
}

// ── Event Listeners ──────────────────────────────────────────
btnReset?.addEventListener("click", doReset);
btnReset2?.addEventListener("click", () => { doReset(); });

btnExpandAll?.addEventListener("click", () => {
  objectsEditor.querySelectorAll("details.objItem").forEach(d => d.open = true);
});

btnCollapseAll?.addEventListener("click", () => {
  objectsEditor.querySelectorAll("details.objItem").forEach(d => d.open = false);
});

btnApplyBulk?.addEventListener("click", () => {
  if (!autoPunchModel?.analysis?.objects?.length) {
    setStatus("Execute a perfuração automática para aplicar ajustes globais.", "info");
    return;
  }
  beginStageProgress("Aplicar ajustes");
  applyBulkToAllObjects();
  endStageProgress("Aplicar ajustes", true, "Ajustes aplicados. Recalculando pré-visualização...");
  scheduleAutoPreviewUpdate();
  setStatus("Ajustes globais aplicados aos objetos.", "ok");
});

btnConvert?.addEventListener("click", (ev) => {
  // O botão pode estar fora do <form> no layout atual, então acionamos manualmente.
  ev.preventDefault();
  if (requestInFlight) {
    setStatus("Aguarde a conclusão da ação em andamento.", "info");
    return;
  }
  runConvert({ silent: false }).catch((err) => {
    setStatus(`Falha na conversão: ${err.message}`, "error");
  });
});

[
  bulkFillType,
  bulkDensity,
  bulkUnderlay,
  bulkShrink,
  bulkOutlineType,
  bulkOutlineWidth,
  bulkOutlinePull,
  bulkOutlineOverlap,
].forEach((input) => {
  input?.addEventListener("change", () => {
    if (!autoPunchModel?.analysis?.objects?.length) return;
    applyBulkToAllObjects();
    scheduleAutoPreviewUpdate();
  });
});

inspDensityRange?.addEventListener("input", () => {
  const v = Number(inspDensityRange.value || 4);
  const density = v <= 3 ? "low" : v <= 7 ? "medium" : "high";
  if (bulkDensity) bulkDensity.value = density;
  if (!autoPunchModel?.analysis?.objects?.length) return;
  applyBulkToAllObjects();
  scheduleAutoPreviewUpdate();
});

inspShrinkRange?.addEventListener("input", () => {
  const v = Number(inspShrinkRange.value || 3) * 0.05;
  if (bulkShrink) bulkShrink.value = v.toFixed(2);
  if (!autoPunchModel?.analysis?.objects?.length) return;
  applyBulkToAllObjects();
  scheduleAutoPreviewUpdate();
});

previewZoomRange?.addEventListener("input", () => {
  applyPreviewZoom(Number(previewZoomRange.value || 100));
});

btnHideProTips?.addEventListener("click", () => {
  applyProTipsVisibility(true);
  saveUiSettings({ hideProTips: true });
});

btnInspectorCollapse?.addEventListener("click", () => {
  const collapsed = !!editorInspector?.classList.contains("inspector-collapsed");
  setInspectorCollapsed(!collapsed);
});

if (inspectorResizeHandle && editorInspector) {
  let resizing = false;
  inspectorResizeHandle.addEventListener("mousedown", (ev) => {
    if (editorInspector.classList.contains("inspector-collapsed")) return;
    ev.preventDefault();
    resizing = true;
  });
  document.addEventListener("mousemove", (ev) => {
    if (!resizing) return;
    const nextWidth = window.innerWidth - ev.clientX;
    setInspectorWidth(nextWidth);
  });
  document.addEventListener("mouseup", () => {
    resizing = false;
  });
}

inspFillType?.addEventListener("change", () => {
  if (inspFillType2) inspFillType2.value = inspFillType.value;
  applyInspectorSelections();
});

inspFillType2?.addEventListener("change", () => {
  if (inspFillType) inspFillType.value = inspFillType2.value;
  applyInspectorSelections();
});

inspOutlineType?.addEventListener("change", () => {
  applyInspectorSelections();
});

inspOutlineWidth?.addEventListener("change", () => {
  applyInspectorSelections();
});

inspAutoUnderlayToggle?.addEventListener("click", () => {
  toggleAutoUnderlay();
});

objectFilter?.addEventListener("input", () => applyObjectFilter());

paletteEditor?.addEventListener("input", ev => {
  const target = ev.target;
  if (!(target instanceof HTMLInputElement)) return;
  const label = target.getAttribute("data-palette-label");
  if (label === null) return;
  applyPaletteColorToLabel(Number(label), target.value);
  scheduleAutoPreviewUpdate();
});

paletteEditor?.addEventListener("change", ev => {
  const target = ev.target;
  if (!(target instanceof HTMLInputElement)) return;
  const label = target.getAttribute("data-palette-label");
  if (label === null) return;
  applyPaletteColorToLabel(Number(label), target.value);
  scheduleAutoPreviewUpdate();
});

objectsEditor?.addEventListener("input", ev => {
  const target = ev.target;
  if (!(target instanceof HTMLElement)) return;
  const prop = target.getAttribute("data-prop");
  if (!prop) return;
  readEditorIntoModel();
  if (prop === "color") {
    const card = target.closest("details.objItem");
    if (card) {
      const sw = card.querySelector(".swatch");
      if (sw && target instanceof HTMLInputElement) sw.style.background = target.value;
    }
    renderPaletteEditor();
  }
  scheduleAutoPreviewUpdate();
});

objectsEditor?.addEventListener("change", ev => {
  const target = ev.target;
  if (!(target instanceof HTMLElement)) return;
  const prop = target.getAttribute("data-prop");
  if (!prop) return;
  readEditorIntoModel();
  if (prop === "color") renderPaletteEditor();
  scheduleAutoPreviewUpdate();
});

el("image")?.addEventListener("change", async e => {
  const file = e.target.files?.[0];
  if (!file) return;
  await handleFileSelected(file);
});

// Perfuração Automática
btnAutoPunch?.addEventListener("click", async () => {
  if (requestInFlight) {
    setStatus("Aguarde a conclusão da ação em andamento.", "info");
    return;
  }

  const imageFile = el("image").files?.[0];
  if (!imageFile) {
    setStatus("Selecione uma imagem antes da perfuração automática.", "error");
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

  setStatus("Executando perfuração automática...", "info");
  requestInFlight = true;
  setNetworkActionButtonsDisabled(true);
  beginStageProgress("Perfuração automática");
  btnReset.disabled = true;
  btnAutoPunch.disabled = true;
  btnAutoPunch.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">sync</span> Processando...';

  try {
    const res = await fetch(`${apiBase}/autopunch`, { method: "POST", body: fd });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Erro HTTP ${res.status}`);
    }

    autoPunchModel = await res.json();
    applyAutoPunchRecommendations(autoPunchModel?.analysis);
    renderObjectsEditor();

    const objects = autoPunchModel?.analysis?.objects || [];
    const totalPoints = objects.reduce((acc, o) => acc + Number(o.area_px || 0), 0);
    updateFooterStats(totalPoints);

    btnReset.disabled = false;
    setStatus("Perfuração concluída. Ajuste os objetos e clique em Gerar Arquivo de Máquina.", "ok");
    endStageProgress("Perfuração automática", true, "Perfuração concluída.");

    // Switch to editor view automatically
    switchToEditorView();
  } catch (err) {
    setStatus(`Falha na perfuração automática: ${err.message}`, "error");
    endStageProgress("Perfuração automática", false, `Falha: ${err.message}`);
  } finally {
    requestInFlight = false;
    setNetworkActionButtonsDisabled(false);
    btnAutoPunch.disabled = false;
    btnAutoPunch.innerHTML = '<span class="material-symbols-outlined text-[16px]">auto_fix_high</span> Perfuração Automática';
  }
});

// Toolbox "Auto-Digitalizar" button
el("btnToolAutoPunch")?.addEventListener("click", () => {
  if (requestInFlight) return;
  switchToDashView();
  setTimeout(() => btnAutoPunch?.click(), 100);
});

// Inspector "Gerar Arquivo de Máquina" button
inspBtnGenerate?.addEventListener("click", () => {
  if (requestInFlight) {
    setStatus("Aguarde a conclusão da ação em andamento.", "info");
    return;
  }
  runConvert({ silent: false }).catch((err) => {
    setStatus(`Falha na conversão: ${err.message}`, "error");
  });
});

inspObjectTree?.addEventListener("mouseover", (ev) => {
  const target = ev.target instanceof Element ? ev.target.closest("[data-eye-id]") : null;
  if (!target) return;
  showObjectPreviewPopup(target.getAttribute("data-eye-id"), ev);
});

inspObjectTree?.addEventListener("mousemove", (ev) => {
  updateObjectPreviewPopupPosition(ev);
});

inspObjectTree?.addEventListener("mouseout", (ev) => {
  const from = ev.target instanceof Element ? ev.target.closest("[data-eye-id]") : null;
  const to = ev.relatedTarget instanceof Element ? ev.relatedTarget.closest("[data-eye-id]") : null;
  if (from && !to) hideObjectPreviewPopup();
});

// Form Submit (Converter)
form.addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await runConvert({ silent: false });
    // If in dash view and result is ready, stay there
  } catch (err) {
    setStatus(`Falha na conversão: ${err.message}`, "error");
  }
});

// API Settings listeners
btnApiSettings?.addEventListener("click", openApiSettings);
btnCloseApiSettings?.addEventListener("click", closeApiSettings);
btnCancelApiSettings?.addEventListener("click", closeApiSettings);
btnSaveApiSettings?.addEventListener("click", saveApiBase);

apiBaseInput?.addEventListener("keydown", ev => {
  if (ev.key === "Enter") { ev.preventDefault(); saveApiBase(); }
});

apiSettingsBackdrop?.addEventListener("click", ev => {
  if (ev.target === apiSettingsBackdrop) closeApiSettings();
});

document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && apiSettingsBackdrop && !apiSettingsBackdrop.hidden) closeApiSettings();
});

// "Nova Digitalização" button
el("btnNovaDig")?.addEventListener("click", () => {
  // Scroll to upload zone and focus
  const zone = el("uploadZone");
  if (zone) zone.scrollIntoView({ behavior: "smooth" });
  setTimeout(() => el("image")?.click(), 300);
});

// ── Init ─────────────────────────────────────────────────────
const initialUiSettings = loadUiSettings();
applyProTipsVisibility(!!initialUiSettings.hideProTips);
setInspectorWidth(initialUiSettings.inspectorWidth);
setInspectorCollapsed(!!initialUiSettings.inspectorCollapsed);
applyPreviewZoom(initialUiSettings.previewZoomPct);
switchInspTab("props");

switchToDashView();
renderRecentProjects();
setStageProgress("Aguardando", 0, "Sem processamento em execução.");
