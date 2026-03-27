// Configure aqui a API padrão.
// Para GitHub Pages: configure para a URL do backend hospedado.
// Para local: http://127.0.0.1:8000
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const el = (id) => document.getElementById(id);

const form = el("converterForm");
const statusEl = el("status");
const resultCard = el("resultCard");
const previewImg = el("previewImg");
const downloadBtn = el("downloadBtn");
const metaEl = el("meta");
const btnReset = el("btnReset");
const apiBaseInput = el("apiBase");
const qualityAlert = el("qualityAlert");

apiBaseInput.value = DEFAULT_API_BASE_URL;

function setStatus(msg, kind="info"){
  statusEl.textContent = msg || "";
  statusEl.style.color =
    kind === "error" ? "#ffd7d7" :
    kind === "ok" ? "#a6ffd0" :
    "var(--muted)";
}

function checkQuality(file){
  // Heurística: checar resolução lendo imagem no browser
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
});

el("image").addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  qualityAlert.hidden = true;
  if (!file) return;

  const q = await checkQuality(file);
  if (q && q.minSide < 1200) {
    qualityAlert.hidden = false;
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

    // Preview e download
    previewImg.src = `${apiBase}${data.preview_url}?t=${Date.now()}`;
    downloadBtn.href = `${apiBase}${data.download_url}`;

    metaEl.textContent = JSON.stringify(data.meta, null, 2);

    resultCard.hidden = false;
    btnReset.disabled = false;
    setStatus("Conversão concluída.", "ok");
  } catch (err) {
    setStatus(`Falha na conversão:\n${err.message}`, "error");
  }
});