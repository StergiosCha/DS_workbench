"use strict";
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
let catalog, study, lastResult;
async function api(path, payload) {
  const response = await fetch(`/api/experiments/${path}`, payload ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)} : {});
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}
function select(label, name, values, selected) {
  const wrapper = el("label", label); const control = el("select"); control.name = name;
  Object.entries(values).forEach(([value, text]) => {const o = el("option", text); o.value = value; control.append(o);});
  control.value = selected; wrapper.append(control); return wrapper;
}
function addConfiguration(grammar = "ccg-application-v1") {
  const card = el("article", undefined, "panel"); card.append(el("h3", `Configuration ${$("configurations").children.length + 1}`, "wide"));
  card.append(select("GRAMMAR + PROCESSING + SEMANTICS", "grammar", Object.fromEntries(Object.entries(catalog.grammars).map(([k,v]) => [k, `${v.family} · ${k.replace(/^(ds|ccg)-/, "")}`])), grammar));
  card.append(select("MEMORY", "memory", catalog.memories, "exponential-v1"));
  card.append(select("REPRESENTATION", "representation", catalog.representations, "native"));
  card.append(select("MEASUREMENT", "measurement", catalog.measurements, "lognormal-v1"));
  const decay = el("label", "RECENCY FACTOR · EXPONENTIAL MEMORY"); const input = el("input"); Object.assign(input, {name:"decay", type:"number", min:"0.01", max:"1", step:"0.01", value:"0.8"}); decay.append(input); card.append(decay);
  const remove = el("button", "Remove"); remove.type = "button"; remove.onclick = () => {if ($("configurations").children.length > 1) card.remove(); $("add-config").disabled = false;}; card.append(remove);
  const description = el("p", "", "wide configuration-description"); card.append(description);
  const refresh = () => {const spec = catalog.grammars[card.querySelector('[name="grammar"]').value]; description.textContent = `${spec.processing}. Semantics: ${spec.semantics}. ${spec.reference}. Limit: ${spec.max_words} words.`; input.disabled = card.querySelector('[name="memory"]').value !== "exponential-v1";};
  card.addEventListener("change", refresh); refresh(); $("configurations").append(card); $("add-config").disabled = $("configurations").children.length >= 4;
}
function configurations() {
  return [...$("configurations").children].map(card => Object.fromEntries([...card.querySelectorAll("select,input")].map(n => [n.name, n.name === "decay" ? Number(n.value) : n.value])));
}
function disclosure(title, value) {const d = el("details"); d.append(el("summary", title), el("pre", JSON.stringify(value, null, 2))); return d;}
function table(headers, rows) {const wrap = el("div", undefined, "table-wrap"), t = el("table"), head = el("thead"), tr = el("tr"), body = el("tbody"); headers.forEach(h => tr.append(el("th",h))); head.append(tr); rows.forEach(row => {const r = el("tr"); row.forEach(value => r.append(el("td", String(value)))); body.append(r);}); t.append(head,body); wrap.append(t); return wrap;}
function stateView(analysis, state) {
  const v = el("div", undefined, "state-view");
  if (state.categories) {v.append(el("p", "CCG categories over the observed prefix")); state.categories.forEach(c => v.append(el("span", c, "category"))); if (!state.categories.length) v.append(el("p", "No full-span category yet; chart cells are retained."));}
  else if (state.nodes) {v.append(el("p", `DS tree · pointer ${state.pointer ?? "—"}`)); state.nodes.forEach(n => v.append(el("div", `${n.address}: ${n.labels.join(" · ")}`)));}
  else v.append(el("pre", JSON.stringify(state, null, 2)));
  v.append(el("p", `Native completion: ${state.complete ? "complete" : "open"}`)); return v;
}
function renderRuns(result) {
  const grid = el("div", undefined, "run-grid");
  result.runs.forEach(run => {
    const card = el("article", undefined, "panel block"), c = run.configuration;
    card.append(el("h2", c.grammar), el("p", `${c.memory} · ${c.representation} · ${c.measurement}`, "configuration-id"));
    run.events.forEach((event,i) => {
      const a = event.analysis, o = a.observation, section = el("section", undefined, "event");
      section.append(el("h4", `${i === 0 ? "Prime" : i === run.events.length - 1 ? "Target" : "Filler"}: ${o.text}`));
      section.append(el("p", `Context: ${o.left_context || "∅"} · ${a.status} · ${event.cue_count} cues`));
      section.append(el("p", `Activation before update: ${event.activation === null ? "unavailable" : event.activation.toFixed(4)}. ${event.prediction.status === "illustrative" ? `Illustrative mean RT: ${event.prediction.mean_rt_ms.toFixed(1)} ms.` : "Prediction unavailable."}`));
      if (a.meanings.length) section.append(el("p", `Meaning: ${a.meanings.join("; ")}`));
      if (a.states.length) {
        const buttons = el("div", undefined, "step-buttons"), viewer = el("div");
        a.states.forEach((frame,j) => {const b = el("button", frame.word, frame.context ? "context-word" : ""); b.type = "button"; b.setAttribute("aria-pressed", "false"); b.onclick = () => {buttons.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", String(x === b))); viewer.replaceChildren(el("p", `After “${frame.word}”`), stateView(a, frame.after));}; buttons.append(b); if (j === a.states.length - 1) b.click();});
        section.append(buttons, viewer);
      }
      section.append(disclosure("Cues, native trace and provenance", event)); card.append(section);
    }); grid.append(card);
  }); $("results").replaceChildren(grid);
}
async function run(mode) {
  $("run-status").textContent = "Running the selected configurations…"; $("run-pair").disabled = $("run-study").disabled = true;
  try {
    let payload = {mode, configurations: configurations()};
    if (mode === "study") Object.assign(payload, {family: $("family").value, condition: $("condition").value, lag: Number($("study-lag").value)});
    else Object.assign(payload, {prime: $("prime").value, target: $("target").value, prime_context: $("prime-context").value, target_context: $("target-context").value, task: $("task").value, fillers: study.fillers.slice(0,Number($("pair-lag").value))});
    lastResult = await api("run", payload); renderRuns(lastResult); $("download").disabled = false; $("run-status").textContent = "Comparison ready · illustrative coefficients";
    if (mode === "study") $("run-status").scrollIntoView({behavior:"smooth", block:"start"});
  } catch(error) {$("run-status").textContent = error.message;}
  finally {$("run-pair").disabled = $("run-study").disabled = false;}
}
function preview() {const f = study.families.find(x => x.id === $("family").value), p = f.conditions[$("condition").value]; $("item-preview").textContent = `Prime: [${p.left_context}] ${p.text}. Target: [${f.target.left_context}] ${f.target.text}. ${$("study-lag").value} intervening observations.`;}
function renderReport(report) {
  if (report.status === "not_built") {$("report").textContent = "The synthetic pilot has not been built in this checkout."; return;}
  const panel = el("article", undefined, "panel block"), comparison = report.comparison, summary = report.recovery_summary;
  panel.append(el("h3", "Synthetic results"), el("p", `${comparison.n} simulated targets per dataset · ${comparison.participants} simulated participants · ${report.coverage.common_families.length} common families · ${summary.runs} recovery datasets.`));
  panel.append(el("p", `Exact generating configuration among the best converged models: ${summary.exact_generator_best}/${summary.runs}. Small score differences and recovery failures limit identification. These are synthetic results, not human evidence.`, "note"));
  panel.append(el("h3", "Coverage"), table(["Grammar", "Supported families"], [...Object.entries(report.coverage.grammars), ...Object.entries(report.legacy_ccg_coverage.grammars)].map(([k,v]) => [k, `${v.supported_families.length}/${study.families.length}`])));
  panel.append(el("p", "The older CCG lexicon is a separate coverage audit. Its missing vocabulary is not evidence about CCG as a theory."));
  panel.append(el("h3", "Held-out predictions · first synthetic dataset"), el("p", `${comparison.split}. ${comparison.metric}. Non-converged rows remain diagnostic only.`));
  panel.append(table(["Grammar / memory / measurement", "Mean log density", "Gain over baseline [95% interval]", "RMSE (ms)", "Converged"], Object.entries(comparison.models).sort((a,b) => b[1].mean_log_density-a[1].mean_log_density).map(([k,v]) => [k, v.mean_log_density.toFixed(4), `${v.gain_over_baseline.mean.toFixed(4)} [${v.gain_over_baseline.interval_95.map(x => x.toFixed(4)).join(", ")}]`, v.rmse_ms.toFixed(1), v.converged ? "yes" : "NO · diagnostic only"])));
  panel.append(el("p", comparison.uncertainty, "timing-note"));
  panel.append(el("h3", "Model recovery"), table(["Generator", "Seed", "Best converged configuration(s)", "Generator − best"], report.recovery.map(r => [r.generator, r.seed, r.best.join("; "), r.generator_gain_from_best?.toFixed(6) ?? "unavailable"])));
  panel.append(disclosure("Identical design matrices in this dataset", comparison.identical_design_groups));
  const limits = el("ul"); report.limitations.forEach(x => limits.append(el("li", x))); panel.append(limits, disclosure("Frozen protocol, configuration hashes and fit diagnostics", report)); $("report").replaceChildren(panel);
}
$("pair-form").onsubmit = event => {event.preventDefault(); run("pair");}; $("run-study").onclick = () => run("study"); $("add-config").onclick = () => addConfiguration();
$("download").onclick = () => {const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)],{type:"application/json"})); const a = el("a"); a.href=url; a.download="configuration-comparison.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);};
(async () => {try {
  [catalog, study] = await Promise.all([api("catalog"),api("study")]); addConfiguration("ds-english-v1"); addConfiguration("ccg-incremental-v1");
  study.families.forEach(f => {const o = el("option", `${f.id} · ${f.target.left_context} ${f.target.text}`); o.value = f.id; $("family").append(o);}); ["family","condition","study-lag"].forEach(id => $(id).onchange = preview); preview();
  const [report, refs] = await Promise.all([api("report"),api("references")]); renderReport(report); $("references").textContent = JSON.stringify(refs,null,2); $("connection").textContent = "Independent engine workers ready";
} catch(error) {$("connection").textContent = `Cannot load the lab: ${error.message}. Start the local ds-workbench server.`; $("run-pair").disabled = $("run-study").disabled = true;}})();
