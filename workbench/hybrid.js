"use strict";
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
let config, evidence, currentTrace;

async function api(path, payload) {
  const response = await fetch(path, payload ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)} : {});
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function jsonDetails(parent, title, value, open = false) {
  const d = el("details"); d.open = open; d.append(el("summary", title), el("pre", JSON.stringify(value, null, 2))); parent.append(d); return d;
}
function table(parent, headings, rows) {
  parent.replaceChildren(); const t = el("table"), head = el("thead"), hr = el("tr"), body = el("tbody");
  headings.forEach(h => {const n = el("th", h); n.scope = "col"; hr.append(n);}); head.append(hr);
  rows.forEach(row => { const r = el("tr"); row.forEach(value => r.append(el("td", String(value)))); body.append(r); });
  t.append(head, body); parent.append(t);
}
function panel(title, parent) { const p = el("article", undefined, "panel block"); p.append(el("h2", title)); parent.append(p); return p; }
function displayState(state, title) {
  const box = el("div", undefined, "tree-state"); box.append(el("h3", title));
  if (!state) return box;
  box.append(el("p", `Pointer: ${state.pointer} · ${state.complete ? "complete" : `${state.pending.length} pending requirements`}`, "badge"));
  state.nodes.forEach(node => {
    const row = el("div", undefined, "node"); row.append(el("span", node.address, "address"));
    const labels = el("div", undefined, "labels"); node.labels.forEach(label => labels.append(el("div", label, label.startsWith("?") ? "pending" : "")));
    row.append(labels); box.append(row);
  }); return box;
}
function showStep(index) {
  const frame = currentTrace.frames[index]; if (!frame) return;
  $("step-title").textContent = `After “${frame.word}” · ${frame.accepted ? "accepted" : "no successful continuation"}${frame.context ? " · left context" : ""}`;
  document.querySelectorAll(".step-buttons button").forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
  $("step-states").replaceChildren(displayState(frame.before, "Before this word"), displayState(frame.after, "After this word"));
  $("step-actions").replaceChildren();
  const programs = frame.selected_actions.flatMap(group => group.programs);
  $("step-actions").append(el("p", `${programs.length} selected actions · ${frame.lexical_candidates.length} lexical candidates · atomic replay ${frame.replay_expanded ? "verified" : "incomplete"}`));
  programs.forEach(program => jsonDetails($("step-actions"), `${program.name} · ${program.template || program.class}`, program));
  jsonDetails($("step-actions"), "All candidates and search counters", {candidates: frame.lexical_candidates, search: frame.search});
  if (frame.lfg && $("lfg-panel")) renderLFG(frame.lfg, $("lfg-panel"), `after “${frame.word}”`);
}
function renderLFG(data, p, label) {
  p.replaceChildren(el("h2", `Grammatical functions · ${label}`));
  if (data.status === "projected") {
    p.append(el("p", data.checks.complete ? "Valence requirements are satisfied." : "Requirements remain open at this prefix."));
    const holder = el("div", undefined, "table-wrap"); p.append(holder);
    table(holder, ["Function", "DS address", "Shared f-node", "Semantic value"], data.structure.mappings.map(m => [m.function, m.ds_address, m.f_node, m.semantic_value]));
    jsonDetails(p, "Completeness, coherence and pending functions", data.checks, true);
  } else p.append(el("p", data.reason, "note"));
  jsonDetails(p, "F-structure and mapping contract", data);
}
function renderAnalysis(result) {
  const root = $("analysis-result"); root.replaceChildren();
  for (const [name, data] of Object.entries(result.modules)) {
    if (name === "ds") {
      currentTrace = data; const p = panel("Interpretation grows word by word", root);
      p.append(el("span", data.status.replaceAll("_", " "), "badge"), el("p", data.ambiguity));
      if (data.failure) p.append(el("p", `Stopped at ${data.failure.word || "completion"}. This records coverage in this grammar.`, "note"));
      const buttons = el("div", undefined, "step-buttons");
      data.frames.forEach((frame, i) => {const b = el("button", frame.word, frame.context ? "context-word" : ""); b.type = "button"; b.setAttribute("aria-pressed", "false"); b.addEventListener("click", () => showStep(i)); buttons.append(b);});
      const title = el("h3"); title.id = "step-title"; const states = el("div", undefined, "tree-grid"); states.id = "step-states"; const actions = el("div"); actions.id = "step-actions";
      p.append(buttons, title, states, actions);
      jsonDetails(p, "Final state after optional completion", data.state);
      jsonDetails(p, "Complete trace and resource fingerprint", data);
      showStep(data.frames.length - 1);
    } else if (name === "lfg") {
      const p = panel("Grammatical functions", root); p.id = "lfg-panel";
      renderLFG(data, p, "final submitted prefix");
    } else if (name === "features") {
      const p = panel("Agreement and shared reference", root); p.append(el("p", data.status === "compatible" ? "Nominal descriptions unify on one referential index." : data.message, data.status === "conflict" ? "note bad" : "good"));
      jsonDetails(p, "Typed graph constraints", data, true);
    } else {
      const p = panel(name === "ccg" ? "Categorial derivations" : "Feature-driven Merge and Move", root);
      p.append(el("span", data.status.replaceAll("_", " "), "badge"));
      if (name === "ccg") p.append(el("p", "An unfinished category can be derived without being a complete sentence. Category and combinator choices are part of the analysis."));
      (data.analyses || []).forEach((analysis, i) => {p.append(el("h3", `Analysis ${i + 1}${analysis.category ? ` · ${analysis.category}` : ""}`), el("pre", analysis.meaning)); jsonDetails(p, "Derivation", analysis, true);});
      if (!(data.analyses || []).length) p.append(el("p", data.unknown ? `Outside this lexicon: ${data.unknown.join(", ")}` : "No complete derivation in this declared fragment.", "note"));
      jsonDetails(p, "Configuration", data.config || data);
    }
  }
  if (result.assumptions) {const p = panel("Contextual assumptions", root); result.assumptions.forEach(text => p.append(el("p", text)));}
}

$("analysis-form").addEventListener("submit", async event => {
  event.preventDefault(); $("build").disabled = true; $("analysis-status").textContent = "Building…";
  try {const r = await api("/api/hybrid/analyse", {text: $("text").value, left_context: $("left-context").value, grammar: $("grammar").value, framework: $("framework").value, complete: $("complete").checked}); renderAnalysis(r); $("analysis-status").textContent = "Analysis ready";}
  catch (e) {$("analysis-status").textContent = e.message;}
  finally {$("build").disabled = false;}
});
function chooseExample() {
  const ex = config.examples[Number($("example").value)];
  $("text").value = ex.text; $("grammar").value = ex.grammar; $("framework").value = ex.framework; $("complete").checked = ex.complete; $("left-context").value = ex.left_context || "";
}
$("example").addEventListener("change", chooseExample);

function renderComparison() {
  const cohort = $("cohort").value, data = evidence.comparisons[cohort][$("regime").value];
  const note = $("comparison-note");
  if (data.status !== "evaluated") { note.textContent = `Comparison unavailable: ${data.status.replaceAll("_", " ")}. Only ${data.groups || 0} independent groups are supported.`; $("comparison-table").replaceChildren(); return; }
  note.textContent = `${data.n.toLocaleString()} retained trials · ${data.groups} held-out groups. Gain is mean log predictive density relative to M0; higher is better. Intervals use a group bootstrap with fixed fitted models.`;
  if (cohort === "ds_matched") note.textContent += " This subset has two families and one observation per participant. Rank-deficient designs and confounded variance components prevent theoretical interpretation of these scores.";
  table($("comparison-table"), ["Model", "Log predictive density", "Gain over M0", "95% interval", "Diagnostics"], Object.entries(data.models).map(([name, m]) => [name, m.mean_log_predictive_density.toFixed(6), m.gain_over_M0.mean.toFixed(6), m.gain_over_M0.group_bootstrap_95.map(x => x.toFixed(6)).join(" to "), `${m.converged_all_folds ? "converged" : "fit warning"}${m.rank_deficient ? "; rank deficient" : ""}`]));
}
$("cohort").addEventListener("change", renderComparison); $("regime").addEventListener("change", renderComparison);
function renderEvidence() {
  const intro = $("evidence-intro"); intro.replaceChildren(el("h2", evidence.article.title));
  intro.append(el("p", "Nielsen & Christiansen · Four preregistered phrasal-decision experiments. Sequence priming is evidence about representation and processing; it does not by itself eliminate hierarchy."));
  const stats = el("div", undefined, "stats");
  [[evidence.participants.toLocaleString(), "participants"], [evidence.retained_trials.toLocaleString(), "retained prime–target pairs"], ["4 / 4", "preprocessing reproductions"]].forEach(([value, label]) => {const stat = el("div", undefined, "stat"); stat.append(el("strong", value), el("span", label)); stats.append(stat);}); intro.append(stats);
  table($("posterior-table"), ["Study", "Contrast", "Median difference (ms)", "95% posterior interval"], evidence.posterior.studies.flatMap(study => Object.entries(study.contrasts).map(([name, v]) => [study.study, name.replaceAll("_", " "), v.estimate_ms.toFixed(2), `${v.lower_ms.toFixed(2)} to ${v.upper_ms.toFixed(2)}`])));
  table($("coverage-table"), ["Vocabulary", "Strings recognized", "Unknown lexicon", "No analysis", "Complete matched families", "Retained trials"], Object.entries(evidence.coverage).map(([name, c]) => [name, `${c.statuses.recognized_fragment || 0} / ${c.strings}`, c.statuses.unsupported_lexicon || 0, c.statuses.no_analysis_in_context_bank || 0, `${c.fully_supported_matched_families.length} / ${c.families}`, c.included_trials_in_matched_families]));
  $("coverage-note").textContent = "A family counts only if every prime alternative and target is supported. The dictionary expansion leaves only two matched families. This cannot establish the predictive adequacy of DS.";
  table($("matched-table"), ["Family / condition", "Prime", "Target", "Human mean RT (ms)", "N"], (evidence.matched_examples || []).map(row => [row.family + " / " + row.condition, row.prime, row.target, row.human_mean_rt_ms.toFixed(1), row.retained_trials]));
  $("matched-features").replaceChildren();
  jsonDetails($("matched-features"), "POS patterns and mean representational features", evidence.matched_examples || []);
  $("limitations").replaceChildren(...evidence.limitations.map(text => el("li", text)));
  $("sources").replaceChildren(el("h3", "Sources and provenance"));
  evidence.sources.forEach(source => {const p = el("p"), a = el("a", source.name); a.href = source.url; a.target = "_blank"; a.rel = "noopener noreferrer"; p.append(a, document.createTextNode(` · ${source.license || source.scope}`)); $("sources").append(p);});
  jsonDetails($("sources"), "Protocol and artifact hashes", {protocol: evidence.protocol, artifacts: evidence.artifact_sha256, assistance_checks: evidence.assistance_checks});
  renderComparison();
}
async function assist(action) {
  $("rank").disabled = true; $("draft").disabled = true; $("assist-status").textContent = "Evaluating…";
  try {const result = await api("/api/hybrid/analyse", {action, prefix: $("assist-prefix").value, word: $("assist-word").value, live: action === "draft" || $("live-jev").checked});
    $("assistance-result").replaceChildren(); const p = panel(action === "rank" ? "Candidate judgments" : "Compiled proposal for review", $("assistance-result"));
    p.append(el("span", result.status.replaceAll("_", " "), "badge"));
    if (result.record) {p.append(el("p", `${result.record.provider} · ${result.record.model} · ${result.record.stub ? "stub response" : "model response"}`)); jsonDetails(p, "Typed answers", result.record.answers, true);}
    jsonDetails(p, "Candidate inventory, state and full result", result, !result.record); $("assist-status").textContent = "Result ready";
  } catch (e) {$("assist-status").textContent = e.message;}
  finally {$("rank").disabled = false; $("draft").disabled = !config.assistance.llm.configured;}
}
$("assistance-form").addEventListener("submit", e => {e.preventDefault(); assist("rank");});
$("draft").addEventListener("click", () => {if ($("assistance-form").reportValidity()) assist("draft");});

const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(tab) {tabs.forEach(t => {const active = t === tab; t.setAttribute("aria-selected", String(active)); t.tabIndex = active ? 0 : -1; $(t.getAttribute("aria-controls")).hidden = !active;});}
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", e => {let next; if (e.key === "ArrowRight") next = (index + 1) % tabs.length; if (e.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length; if (e.key === "Home") next = 0; if (e.key === "End") next = tabs.length - 1; if (next !== undefined) {e.preventDefault(); selectTab(tabs[next]); tabs[next].focus();}});
});
async function init() {
  try {
    config = await api("/api/hybrid/config");
    config.examples.forEach((ex, i) => {const o = el("option", ex.label); o.value = i; $("example").append(o);}); $("example").value = "1"; chooseExample();
    $("live-jev").disabled = !config.assistance.jev.configured; $("draft").disabled = !config.assistance.llm.configured;
    $("provider-status").textContent = `Jev: ${config.assistance.jev.configured ? config.assistance.jev.provider : "credential unavailable"}. LLM: ${config.assistance.llm.message}.`;
    $("connection").textContent = "Research worker ready · separate experimental modules";
    evidence = await api("/api/hybrid/evidence"); if (evidence.status === "not_built") $("evidence-intro").textContent = evidence.message; else renderEvidence();
  } catch (e) {$("connection").textContent = `Research worker unavailable: ${e.message}`; $("build").disabled = true; $("rank").disabled = true; $("draft").disabled = true;}
}
init();
