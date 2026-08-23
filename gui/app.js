/**
 * Torchlight TurboQuant Studio GUI Application
 */

const PRESETS = {
  "1": "Write a clean, complete Python implementation of an LRU Cache with O(1) time complexity for get(key) and put(key, value) using collections.OrderedDict or a doubly linked list. Include type hints and docstrings.",
  "2": "Write an asynchronous token-bucket rate limiter in Python using asyncio, type annotations, and thread-safe locking.",
  "3": "Write a complete Python BST class with insert, search, delete, and generator-based in_order_traversal with type annotations.",
  "custom": ""
};

let appState = {
  engine: "llamacpp",
  kvMode: "turbo3",
  models: { gguf: [], mlx: [] },
  selectedModel: null,
  history: []
};

// DOM Elements
const engineCards = document.querySelectorAll(".engine-card");
const kvPills = document.querySelectorAll(".kv-pill");
const modelSelect = document.getElementById("model-select");
const btnRefreshModels = document.getElementById("btn-refresh-models");
const metaSize = document.getElementById("meta-size");
const metaType = document.getElementById("meta-type");
const metaLocation = document.getElementById("meta-location");
const maxTokensSlider = document.getElementById("max-tokens");
const maxTokensVal = document.getElementById("max-tokens-val");
const threadsSlider = document.getElementById("threads");
const threadsVal = document.getElementById("threads-val");
const promptInput = document.getElementById("prompt-input");
const presetButtons = document.querySelectorAll(".preset-btn");
const btnRunTest = document.getElementById("btn-run-test");
const btnCopyCode = document.getElementById("btn-copy-code");
const codeOutput = document.getElementById("code-output");
const astBadge = document.getElementById("ast-badge");
const valPrefill = document.getElementById("val-prefill");
const valDecode = document.getElementById("val-decode");
const valTtft = document.getElementById("val-ttft");
const valRam = document.getElementById("val-ram");
const resultsTbody = document.getElementById("results-tbody");
const btnClearHistory = document.getElementById("btn-clear-history");
const btnExportJson = document.getElementById("btn-export-json");
const serverStatus = document.getElementById("server-status");

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadModels();
  promptInput.value = PRESETS["1"];
});

function setupEventListeners() {
  // Engine Selector
  engineCards.forEach(card => {
    card.addEventListener("click", () => {
      engineCards.forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      appState.engine = card.dataset.engine;
      updateModelDropdown();
    });
  });

  // KV Cache Selector
  kvPills.forEach(pill => {
    pill.addEventListener("click", () => {
      kvPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      const radio = pill.querySelector("input");
      if (radio) radio.checked = true;
      appState.kvMode = pill.dataset.kv;
    });
  });

  // Sliders
  maxTokensSlider.addEventListener("input", (e) => {
    maxTokensVal.textContent = e.target.value;
  });

  threadsSlider.addEventListener("input", (e) => {
    threadsVal.textContent = e.target.value;
  });

  // Presets
  presetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      presetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const key = btn.dataset.preset;
      if (PRESETS[key] !== undefined) {
        if (key !== "custom") {
          promptInput.value = PRESETS[key];
        } else {
          promptInput.focus();
        }
      }
    });
  });

  // Model Select Change
  modelSelect.addEventListener("change", (e) => {
    const selectedPath = e.target.value;
    updateModelMetadata(selectedPath);
  });

  // Refresh Models Button
  btnRefreshModels.addEventListener("click", loadModels);

  // Run Test Button
  btnRunTest.addEventListener("click", executeRun);

  // Copy Code Button
  btnCopyCode.addEventListener("click", () => {
    const code = codeOutput.textContent;
    navigator.clipboard.writeText(code).then(() => {
      btnCopyCode.textContent = "✓ Copied!";
      setTimeout(() => { btnCopyCode.textContent = "📋 Copy"; }, 2000);
    });
  });

  // Clear History
  btnClearHistory.addEventListener("click", () => {
    appState.history = [];
    resultsTbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="8">No benchmark runs recorded yet. Click "Run Benchmark & Test" above.</td>
      </tr>
    `;
  });

  // Export JSON
  btnExportJson.addEventListener("click", () => {
    if (!appState.history.length) {
      alert("No benchmark history to export.");
      return;
    }
    const blob = new Blob([JSON.stringify(appState.history, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `torchlight_benchmark_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

// Fetch models from Python API
async function loadModels() {
  btnRefreshModels.textContent = "Scanning...";
  try {
    const res = await fetch("/api/models");
    if (!res.ok) throw new Error("Failed to scan models");
    const data = await res.json();
    appState.models = data;
    updateModelDropdown();
    btnRefreshModels.textContent = "🔄 Refresh";
  } catch (err) {
    console.error(err);
    btnRefreshModels.textContent = "⚠️ Error";
    modelSelect.innerHTML = `<option value="">Error scanning models</option>`;
  }
}

function updateModelDropdown() {
  modelSelect.innerHTML = "";
  const list = appState.engine === "llamacpp" ? appState.models.gguf : appState.models.mlx;

  if (!list || list.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = `No ${appState.engine.toUpperCase()} models found in ./models`;
    modelSelect.appendChild(opt);
    updateModelMetadata(null);
    return;
  }

  list.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m.path;
    opt.textContent = `${m.name} (${(m.size_mb).toFixed(1)} MB)`;
    modelSelect.appendChild(opt);
  });

  updateModelMetadata(list[0].path);
}

function updateModelMetadata(path) {
  if (!path) {
    metaSize.textContent = "- MB";
    metaType.textContent = "None";
    metaLocation.textContent = "-";
    appState.selectedModel = null;
    return;
  }

  const list = appState.engine === "llamacpp" ? appState.models.gguf : appState.models.mlx;
  const found = list.find(m => m.path === path);
  if (found) {
    appState.selectedModel = found;
    metaSize.textContent = `${found.size_mb.toFixed(1)} MB`;
    metaType.textContent = found.format.toUpperCase();
    metaLocation.textContent = found.rel_path;
  }
}

// Execute Benchmark Run
async function executeRun() {
  if (!appState.selectedModel) {
    alert("Please select a valid model first.");
    return;
  }

  btnRunTest.disabled = true;
  btnRunTest.innerHTML = `<span class="status-dot"></span> Benchmarking in progress...`;
  codeOutput.textContent = "// Executing benchmark run on Apple Silicon Metal...";
  astBadge.className = "ast-badge";
  astBadge.textContent = "AST: RUNNING";

  const payload = {
    engine: appState.engine,
    kv_mode: appState.kvMode,
    model_path: appState.selectedModel.path,
    prompt: promptInput.value,
    max_tokens: parseInt(maxTokensSlider.value, 10),
    threads: parseInt(threadsSlider.value, 10)
  };

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Benchmark execution failed");
    const result = await res.json();

    // Update Gauges
    valPrefill.textContent = result.prompt_tps > 0 ? result.prompt_tps.toFixed(1) : "--";
    valDecode.textContent = result.gen_tps > 0 ? result.gen_tps.toFixed(1) : "--";
    valTtft.textContent = result.ttft_ms > 0 ? result.ttft_ms.toFixed(1) : "--";
    valRam.textContent = result.peak_memory_mb > 0 ? result.peak_memory_mb.toFixed(1) : "--";

    // Update Code & AST
    codeOutput.textContent = result.output_text || "// [Benchmark Completed - No Text Output]";
    if (result.syntax_valid) {
      astBadge.className = "ast-badge valid";
      astBadge.textContent = "AST: VALID ✓";
    } else {
      astBadge.className = "ast-badge invalid";
      astBadge.textContent = "AST: SYNTAX ERROR ✗";
    }

    // Append to Table
    appendResultRow(result);

  } catch (err) {
    console.error(err);
    codeOutput.textContent = `// Error executing benchmark: ${err.message}`;
    astBadge.className = "ast-badge invalid";
    astBadge.textContent = "AST: ERROR";
  } finally {
    btnRunTest.disabled = false;
    btnRunTest.innerHTML = `<span class="btn-icon">▶</span> Run Benchmark & Test`;
  }
}

function appendResultRow(record) {
  const emptyRow = resultsTbody.querySelector(".empty-row");
  if (emptyRow) emptyRow.remove();

  appState.history.unshift(record);

  const tr = document.createElement("tr");
  const syntaxBadge = record.syntax_valid
    ? `<span style="color: #10b981;">✓ PASS</span>`
    : `<span style="color: #ef4444;">✗ FAIL</span>`;

  tr.innerHTML = `
    <td><strong>${record.engine}</strong></td>
    <td style="color: #a855f7;">${record.kv_mode}</td>
    <td style="color: #f8fafc;" title="${record.model_name}">${record.model_name.length > 20 ? record.model_name.substring(0, 18) + '...' : record.model_name}</td>
    <td style="color: #10b981;">${record.prompt_tps.toFixed(1)}</td>
    <td style="color: #00f0ff;">${record.gen_tps.toFixed(1)}</td>
    <td style="color: #a855f7;">${record.ttft_ms.toFixed(1)}</td>
    <td style="color: #f59e0b;">${record.peak_memory_mb.toFixed(1)} MB</td>
    <td>${syntaxBadge}</td>
  `;

  resultsTbody.insertBefore(tr, resultsTbody.firstChild);
}
