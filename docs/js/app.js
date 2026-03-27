// Configure aqui a API padrão.
// Para GitHub Pages: configure para a URL do backend hospedado.
// Para local: http://127.0.0.1:8000
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

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
const editorCard = el("editorCard");
const objectsEditor = el("objectsEditor");
const apiBaseInput = el("apiBase");
const qualityAlert = el("qualityAlert");

apiBaseInput.value = DEFAULT_API_BASE_URL;

let autoPunchModel = null;

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

function renderObjectsEditor() {
  if (!autoPunchModel?.analysis?.objects?.length) {
    editorCard.hidden = true;
    objectsEditor.innerHTML = "";
    return;
  }

  const html = autoPunchModel.analysis.objects.map((obj, i) => `
    <details class="objItem" data-id="${esc(obj.id)}" ${i < 4 ? "open" : ""}>
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
        </div>
      </div>
    </details>
  `).join("");

  objectsEditor.innerHTML = html;
  editorCard.hidden = false;
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
    },
    objects: autoPunchModel.analysis.objects,
  };
}

btnReset.addEventListener("click", () => {
  form.reset();
  apiBaseInput.value = DEFAULT_API_BASE_URL;
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

  const imageFile = el("image").files?.[0];
  if (!imageFile) return;

  const apiBase = (apiBaseInput.value || "").trim().replace(/\/+$/, "");
  if (!apiBase) {
    setStatus("Informe a URL do backend (API).", "error");
    return;
  }

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

  setStatus("Convertendo... isso pode levar alguns segundos.", "info");
  resultCard.hidden = true;
  btnReset.disabled = true;

  try {
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
    setStatus("Conversao concluida.", "ok");
  } catch (err) {
    setStatus(`Falha na conversao:\n${err.message}`, "error");
  }
});