"use strict";

window.openrouterControls = (() => {
  // Keep credentials separate from parser state, exports and browser storage.
  let key = "", models = [], selected = "", jev = null, baseline = null;
  let run = 0, connecting = false, controller = null;
  const usesModel = payload => ["model", "jev", "assisted"].includes(payload.lexical_mode) || payload.decision_mode === "jev";

  function renderBusy() {
    $("openrouter-connect").disabled = connecting || state.busy || !state.config;
    $("openrouter-key").disabled = state.busy;
    $("openrouter-model").disabled = state.busy || !models.length;
    $("openrouter-filter").disabled = state.busy || !models.length;
  }

  function reset(clearInput = true) {
    ++run; controller?.abort(); controller = null; connecting = false;
    key = ""; models = []; selected = ""; jev = null;
    if (clearInput) $("openrouter-key").value = "";
    $("openrouter-filter").value = "";
    $("openrouter-model").replaceChildren();
    $("openrouter-model-controls").hidden = true;
    $("openrouter-disconnect").hidden = true;
    $("openrouter-connect").hidden = false;
    $("openrouter-badge").textContent = "Not connected";
    if (baseline && state.config) {
      state.config.lexical.provider = structuredClone(baseline.provider);
      state.config.lexical.selection = structuredClone(baseline.selection);
      state.config.decision = structuredClone(baseline.decision);
      if (["model", "jev", "assisted"].includes($("lexical-mode").value)) $("lexical-mode").value = state.config.lexical.dictionary?.installed ? "dictionary" : "bundled";
      if ($("decision-mode").value === "jev") $("decision-mode").value = "off";
      renderLexicalSettings();
    }
    renderBusy();
  }

  function updateModel() {
    if (!key || !state.config) return;
    const model = models.find(item => item.id === selected);
    state.config.lexical.provider = { configured: Boolean(model), provider: "OpenRouter", model: selected, message: model ? `OpenRouter · ${selected}` : "No compatible vocabulary model is available for this key." };
    state.config.lexical.selection = { ...baseline.selection, configured: Boolean(jev?.available), provider: "openrouter", model: jev?.model || baseline.selection.model };
    state.config.decision = { ...structuredClone(baseline.decision), configured: Boolean(jev?.available), provider: "openrouter", model: jev?.model || baseline.decision.model };
    const price = value => value == null ? "variable" : `$${Number(value).toLocaleString("en-US", { maximumFractionDigits: 6 })}`;
    $("openrouter-price").textContent = model ? `${model.id} · per million tokens: ${price(model.input_per_million)} input / ${price(model.output_per_million)} output. Listed base rates from OpenRouter.` : "No model advertising structured outputs is available for this key.";
    $("openrouter-jev").textContent = jev?.available ? `${jev.name} is available for lexical preferences. Its model is pinned separately from the vocabulary model; search ordering still requires calibration.` : "The pinned Jev model is not available in this key’s model list. You can still use vocabulary proposals.";
    renderLexicalSettings(); renderBusy();
  }

  function filterModels() {
    const query = $("openrouter-filter").value.toLowerCase().trim();
    const filtered = models.filter(model => `${model.name} ${model.id}`.toLowerCase().includes(query));
    const current = models.find(model => model.id === selected);
    if (current && !filtered.includes(current)) filtered.unshift(current);
    $("openrouter-model").replaceChildren(...filtered.map(model => new Option(model.name, model.id)));
    if (!filtered.length) $("openrouter-model").append(new Option("No compatible models", ""));
    $("openrouter-model").value = selected;
  }

  async function connect(event) {
    event.preventDefault();
    const candidate = $("openrouter-key").value.trim();
    if (!candidate) { $("openrouter-status").textContent = "Enter your OpenRouter API key."; $("openrouter-key").focus(); return; }
    reset(false);
    const current = ++run;
    connecting = true; controller = new AbortController();
    const abort = controller;
    const timer = setTimeout(() => abort.abort(), 30000);
    $("openrouter-status").textContent = "Checking your key and loading compatible models…";
    renderBusy();
    try {
      const response = await fetch("/api/openrouter/connect", { method: "POST", headers: { Authorization: `Bearer ${candidate}` }, signal: abort.signal });
      const result = await response.json();
      if (current !== run) return;
      if (!response.ok) throw new Error(result.error || "Could not connect to OpenRouter.");
      if (!result.connected || !Array.isArray(result.models)) throw new Error("The connection returned an invalid model list.");
      key = candidate; models = result.models; selected = result.default_model || models[0]?.id || ""; jev = result.jev;
      $("openrouter-key").value = "";
      $("openrouter-key").placeholder = "Connected · paste another key to replace";
      $("openrouter-badge").textContent = "Connected";
      $("openrouter-disconnect").hidden = false; $("openrouter-connect").hidden = true;
      $("openrouter-model-controls").hidden = false;
      $("openrouter-status").textContent = `Connected · ${models.length} compatible models. Choose a model, then tick Use analysis LLM or Use Jev above. Connecting does not turn either on.`;
      filterModels(); updateModel();
    } catch (error) {
      if (current !== run) return;
      $("openrouter-status").textContent = error.name === "AbortError" ? "OpenRouter took too long. Try connecting again." : error.message;
    } finally {
      clearTimeout(timer);
      if (current === run) { connecting = false; controller = null; renderBusy(); }
    }
  }

  $("openrouter-form").addEventListener("submit", connect);
  $("openrouter-key").addEventListener("input", () => {
    if (key || connecting) reset(false);
    $("openrouter-status").textContent = "Press Connect to check this key. No model call is made.";
  });
  $("openrouter-disconnect").addEventListener("click", () => {
    reset(); $("openrouter-key").placeholder = "Paste your key";
    $("openrouter-status").textContent = state.busy ? "Disconnected. The current request may finish; no further request will use the key." : "Disconnected. Your key has been cleared from this tab.";
  });
  $("openrouter-filter").addEventListener("input", filterModels);
  $("openrouter-model").addEventListener("change", () => { selected = $("openrouter-model").value; updateModel(); });
  window.addEventListener("pagehide", () => reset());

  return {
    init(config) {
      $("openrouter-panel").hidden = !config.openrouter?.enabled;
      if (!baseline) baseline = structuredClone({ provider: config.lexical.provider, selection: config.lexical.selection, decision: config.decision });
      renderBusy();
    },
    setBusy: renderBusy,
    applyToRequest(payload, headers) {
      if (!key || !usesModel(payload)) return;
      headers.Authorization = `Bearer ${key}`;
      if ((["model", "assisted"].includes(payload.lexical_mode) || (payload.lexical_mode === "jev" && payload.allow_model_fallback)) && selected) payload.openrouter_model = selected;
    },
  };
})();
if (state.config) window.openrouterControls.init(state.config);
