"use strict";

const $ = (id) => document.getElementById(id);
const state = { config: null, result: null, paragraph: null, paragraphIndex: 0, readingIndex: 0, mode: "actions", inputMode: "sentence", index: 0, selected: null, timer: null, busy: false, view: null, drag: null, expandedFormulas: [] };
const selectedReading = () => state.result?.readings?.[state.readingIndex];
const playback = () => selectedReading()?.trace || state.result;
const frames = () => playback()?.[state.mode] || [];
const selectedCoq = () => selectedReading()?.coq ?? state.result?.coq;
const current = () => frames()[state.index];
const svgNS = "http://www.w3.org/2000/svg";

function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function svgElement(tag, attributes = {}, text) {
  const el = document.createElementNS(svgNS, tag);
  for (const [name, value] of Object.entries(attributes)) el.setAttribute(name, value);
  if (text !== undefined) el.textContent = text;
  return el;
}

function math(text) {
  return String(text).replaceAll("==", " ≔ ").replace(/(?<=[a-zA-Z)])>(?=[a-zA-Z(])/g, " → ").replaceAll("\\/", "↓").replaceAll("/\\", "↑");
}

function excerpt(text, max = 29) {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

function formatRecord(text) {
  if (!text) return "No semantic projection is available at this step.";
  let depth = 0;
  return text.replace(/[\[\]|]/g, (char) => {
    if (char === "[") { depth++; return char; }
    if (char === "]") { depth--; return char; }
    return depth === 1 ? "\n  " : " | ";
  }).replace(/^\[/, "[ ").replace(/\]$/, " ]");
}

function message(text, error = false) {
  $("message").hidden = !text;
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}

function stop() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
  $("play").textContent = "▶";
  $("play").setAttribute("aria-label", "Play derivation");
}

function updateControls() {
  const unavailable = !state.result;
  $("first").disabled = unavailable || state.index === 0;
  $("previous").disabled = unavailable || state.index === 0;
  $("next").disabled = unavailable || state.index >= frames().length - 1;
  $("play").disabled = unavailable || (!state.busy && frames().length < 2);
  $("timeline").disabled = unavailable || frames().length < 2;
  $("export").disabled = (!state.paragraph && unavailable) || state.busy;
  $("coq").hidden = state.result?.backend !== "mltt";
  $("coq").disabled = state.busy || !selectedCoq();
  $("reading").disabled = state.busy;
  $("show-final").disabled = unavailable || state.busy || state.index >= frames().length - 1;
  $("copy").disabled = unavailable || !current()?.semantics;
  for (const button of document.querySelectorAll("[data-mode]")) button.disabled = unavailable || !playback()?.[button.dataset.mode]?.length;
  for (const id of ["zoom-in", "zoom-out", "fit"]) $(id).disabled = unavailable;
}

function setBusy(busy) {
  state.busy = busy;
  $("loading-state").hidden = !busy;
  $("parse-button").disabled = busy;
  $("parse-label").textContent = busy ? "Parsing…" : state.inputMode === "dialogue" ? "Build dialogue" : state.inputMode === "paragraph" ? "Parse paragraph" : "Build derivation";
  $("grammar").disabled = busy;
  $("system").disabled = busy;
  $("scope").disabled = busy || $("system").value !== "mltt" || Boolean(greekGrammar());
  $("n-best").disabled = busy || state.inputMode !== "sentence";
  $("sentence").disabled = busy || state.inputMode !== "sentence";
  $("paragraph").disabled = busy || state.inputMode !== "paragraph";
  $("lexical-mode").disabled = busy || !lexicalSupported();
  $("decision-mode").disabled = busy;
  $("use-dictionaries").disabled = busy || !state.config;
  for (const button of document.querySelectorAll("[data-guide-example]")) button.disabled = busy || !state.config;
  for (const control of document.querySelectorAll("#lexical-examples button")) control.disabled = busy;
  for (const control of document.querySelectorAll("#dialogue-editor input, #dialogue-editor select, #dialogue-editor button, [data-input-mode]")) control.disabled = busy;
  $("add-turn").disabled = busy || $("dialogue-rows").children.length >= 12;
  document.querySelector(".workbench").setAttribute("aria-busy", String(busy));
  for (const button of document.querySelectorAll("#examples button, #action-list button")) button.disabled = busy;
  for (const button of document.querySelectorAll("[data-greek-example]")) button.disabled = busy;
  if (current()) renderTokens(current());
  updateControls();
  if (typeof updateResearchSelection === "function") updateResearchSelection();
  window.openrouterControls?.setBusy();
  if (state.config) renderJevControls();
  renderAssistanceControls();
}

function receiveEvent(event) {
  if (event.event === "paragraph_start") {
    state.paragraph = { sentences: event.sentences.map((s, index) => ({...s, index, status: "pending"})) };
    renderParagraph();
    $("result-status").textContent = "Reading paragraph…";
  } else if (event.event === "paragraph_trace") {
    state.paragraphIndex = event.sentence_index;
    receiveEvent(event.trace);
    state.paragraph.sentences[event.sentence_index].status = "parsing";
    renderParagraph();
  } else if (event.event === "paragraph_sentence") {
    state.paragraph.sentences[event.sentence.index] = event.sentence;
    renderParagraph();
  } else if (event.event === "result" && event.result.kind === "paragraph") {
    state.paragraph = event.result;
    renderParagraph(); showParagraphSentence(0);
  } else if (event.event === "lexical") {
    $("result-status").textContent = event.message;
  } else if (event.event === "start") {
    stop();
    state.result = { ...event, words: [event.initial], actions: [event.initial], operations: event.trace_level === "actions" ? [] : [event.initial], repairs: [], context_trees: [], backend: event.initial.backend };
    state.readingIndex = 0; $("readings-panel").hidden = true;
    state.mode = event.trace_level === "words" ? "words" : "actions"; state.index = 0; state.selected = "0"; state.view = null;
    $("empty-state").hidden = true; $("loading-state").hidden = true;
    $("result-status").textContent = event.dialogue ? "Reading dialogue…" : "Reading sentence…";
    selectTab("trace"); renderTrace(); render(); play();
    renderLexicalReport(event.lexical);
  } else if (event.event === "frame") {
    state.result[event.channel].push(event.frame);
    if (state.paragraph && event.channel === "actions" && ["word", "completion", "backtrack", "repair", "trace_gap"].includes(event.frame.kind)) {
      state.result.words.push({...event.frame, label: event.frame.kind === "word" ? state.result.tokens[event.frame.word_index] : event.frame.label});
    }
    renderTrace(); updateControls();
    $("timeline").max = frames().length - 1;
  } else if (event.event === "result") {
    const result = event.result;
    if (result.error) throw new Error(result.error);
    state.result = result;
    if (result.trace_level === "words") {
      state.mode = "words"; state.index = Math.max(0, result.words.length - 1);
      state.readingIndex = 0; state.selected = "0"; state.view = null;
      $("empty-state").hidden = true; $("loading-state").hidden = true;
      selectTab("trace");
    }
    if (typeof research !== "undefined" && research.pendingSource) state.result.research_source = research.pendingSource;
    $("result-status").textContent = result.complete ? "Complete derivation" : result.ok ? "Partial derivation" : "Stopped at a word";
    $("result-status").className = "badge" + (result.complete ? "" : " warn");
    $("elapsed").textContent = `${result.elapsed_ms} ms · ${result.tokens.length} tokens`;
    if (result.failure) message(result.failure.message, true);
    else if (result.pending_repair) message("Repair initiated. Add a replacement after the repair marker.");
    else if (!result.complete) message("A tree still has outstanding requirements. Inspect the open nodes or extend the input.");
    renderDiagnostics(result);
    renderReadings();
    renderTrace(); render();
  }
}

async function parseSentence(options = {}) {
  if (state.busy) return;
  if (options.reveal !== false) window.workbenchLayout?.showPanel("parse");
  const sentence = $("sentence").value.trim();
  if (state.inputMode === "sentence" && !sentence) { message("Enter a sentence to begin."); $("sentence").focus(); return; }
  if (state.inputMode === "paragraph" && !$("paragraph").value.trim()) { message("Enter a paragraph to begin."); $("paragraph").focus(); return; }
  if (typeof researchSourceFor === "function") {
    research.pendingSource = researchSourceFor(sentence);
    if (research.pendingSource) research.pendingSource.comparison_grammar = $("grammar").value;
    renderResearchProvenance(research.pendingSource);
  }
  const payload = { grammar: $("grammar").value, scope: $("scope").value };
  payload.n_best = state.inputMode !== "sentence" ? 1 : Number($("n-best").value);
  payload.reading_traces = payload.n_best > 1;
  payload.lexical_mode = lexicalSupported() ? $("lexical-mode").value : "off";
  payload.allow_model_fallback = $("llm-enabled").checked;
  if (liveGreekSourcesActive()) {
    payload.live_greek_sources = true;
    payload.greek_source_corpus = $("greek-source-corpus").value;
  }
  payload.decision_mode = $("decision-mode").value;
  if (jevComparisonActive()) { payload.compare_jev = true; payload.n_best = 1; payload.reading_traces = false; payload.decision_mode = "off"; }
  if (state.inputMode === "dialogue") payload.dialogue = readDialogue();
  else if (state.inputMode === "paragraph") payload.paragraph = $("paragraph").value;
  else payload.sentence = sentence;
  state.paragraph = null; state.expandedFormulas = []; $("paragraph-results").hidden = true;
  stop(); message(""); $("diagnostics").hidden = true; $("lexical-report").hidden = true; $("method-result").hidden = true; $("jev-impact").hidden = true; $("playback-status").hidden = true; setBusy(true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  let finished = false;
  try {
    const headers = { "Content-Type": "application/json" };
    window.openrouterControls?.applyToRequest(payload, headers);
    const response = await fetch("/api/parse/stream", {
      method: "POST", headers,
      body: JSON.stringify(payload), signal: controller.signal,
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || "The parser could not return a result.");
    }
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split("\n"); buffer = lines.pop();
      for (const line of lines) if (line.trim()) {
        const event = JSON.parse(line); receiveEvent(event);
        if (event.event === "result") finished = true;
      }
      if (done) break;
    }
    if (!finished) throw new Error("The parser stream ended before returning a result.");
  } catch (error) {
    stop();
    $("result-status").textContent = "Request did not complete";
    $("result-status").className = "badge warn";
    message(error.name === "AbortError" ? "The parser took too long to respond. Try a shorter sentence." : error.message, true);
  } finally {
    clearTimeout(timeout); setBusy(false);
  }
}

const nodeTextMeasure = document.createElement("canvas").getContext("2d");

function nodeTypeLabel(node) {
  return node.type ? `Ty(${math(node.type)})` : node.required_type ? `?Ty(${math(node.required_type)})` : node.requirements.find((label) => label.startsWith("?Ty(")) || "Type not set";
}

function wrapNodeLabel(text, maxWidth = 240) {
  // Preserve every character, including spaces at line breaks and long symbols.
  const lines = [];
  let line = "";
  for (const word of text.match(/\S+\s*|\s+/gu) || []) {
    if (line && nodeTextMeasure.measureText(line + word).width > maxWidth) { lines.push(line); line = ""; }
    for (const char of word) {
      if (line && nodeTextMeasure.measureText(line + char).width > maxWidth) { lines.push(line); line = ""; }
      line += char;
    }
  }
  if (line || !lines.length) lines.push(line);
  return lines;
}

function layoutTree(frame) {
  const styles = getComputedStyle(document.documentElement);
  const typeFont = `17px ${styles.getPropertyValue("--serif")}`;
  const formulaFont = `12px ${styles.getPropertyValue("--mono")}`;
  const map = new Map(frame.nodes.map((node) => {
    nodeTextMeasure.font = typeFont;
    const typeLabel = nodeTypeLabel(node), typeLines = wrapNodeLabel(typeLabel);
    let width = Math.max(166, ...typeLines.map(line => nodeTextMeasure.measureText(line).width + 32), (node.id.length + 4) * 6 + (node.clause ? 82 : 40));
    const formulaText = node.formula || (node.requirements.length ? "Awaiting a formula" : "No formula");
    const expandable = Boolean(node.formula && node.formula.length > 25);
    const expanded = expandable && state.expandedFormulas.includes(node.id);
    nodeTextMeasure.font = formulaFont;
    const formulaLines = expanded ? wrapNodeLabel(formulaText, 320) : [excerpt(formulaText, 25)];
    if (expanded) width = Math.max(width, ...formulaLines.map(line => nodeTextMeasure.measureText(line).width + 32));
    const height = 68 + (typeLines.length - 1) * 21 + (expanded ? 4 + (formulaLines.length - 1) * 18 : 0) + (expandable ? 30 : 0);
    return [node.id, { ...node, typeLabel, typeLines, formulaLines, expandable, expanded, width: Math.ceil(width), height, children: [] }];
  }));
  for (const edge of frame.edges) {
    const child = map.get(edge.target);
    child.path = edge.path;
    map.get(edge.source)?.children.push(child);
  }
  const roots = [...map.values()].filter((node) => !frame.edges.some((edge) => edge.target === node.id));
  const rank = (node) => node.path?.startsWith("0") ? 0 : node.path?.startsWith("1") ? 2 : /[LC]/.test(node.path || "") ? 3 : 1;
  const siblingGap = 310, contourGap = 58;
  // One shared height per depth keeps branches aligned even with wrapped types.
  const levelHeights = [];
  const measureLevels = (node, depth) => {
    node.depth = depth;
    levelHeights[depth] = Math.max(levelHeights[depth] || 0, node.height);
    node.children.forEach(child => measureLevels(child, depth + 1));
  };
  roots.forEach(root => measureLevels(root, 0));
  const levelY = [0];
  for (let depth = 1; depth < levelHeights.length; depth++) levelY[depth] = levelY[depth - 1] + levelHeights[depth - 1] / 2 + 52 + levelHeights[depth] / 2;
  const shift = (branch, dx, dy) => {
    for (const node of branch.nodes) { node.x += dx; node.y += dy; }
    branch.left = branch.left.map((x) => x + dx);
    branch.right = branch.right.map((x) => x + dx);
  };
  const visit = (node) => {
    node.x = node.y = 0;
    node.children.sort((a, b) => rank(a) - rank(b) || a.id.localeCompare(b.id));
    const branches = node.children.map(visit);
    const left = [], right = [];
    let previousRoot = 0;
    branches.forEach((branch, index) => {
      let offset = index ? previousRoot + siblingGap : 0;
      // Separate the actual contours at every shared depth, so an asymmetric
      // subtree has room without stretching every leaf into a separate column.
      branch.left.forEach((x, depth) => {
        if (right[depth] !== undefined) offset = Math.max(offset, right[depth] + contourGap - x);
      });
      shift(branch, offset, 0);
      branch.left.forEach((x, depth) => { left[depth] = Math.min(left[depth] ?? Infinity, x); });
      branch.right.forEach((x, depth) => { right[depth] = Math.max(right[depth] ?? -Infinity, x); });
      previousRoot = offset;
    });
    const center = branches.length > 1 ? previousRoot / 2 : 0;
    // A lone 0/1 daughter retains its left/right direction during make/go/put
    // playback, instead of turning the growing tree into a vertical stack.
    const singleOffset = branches.length === 1 ? (rank(node.children[0]) < 2 ? -155 : 155) : 0;
    branches.forEach((branch) => shift(branch, singleOffset - center, 0));
    return {
      nodes: [node, ...branches.flatMap((branch) => branch.nodes)],
      left: [-node.width / 2, ...left.map((x) => x + singleOffset - center)],
      right: [node.width / 2, ...right.map((x) => x + singleOffset - center)],
    };
  };
  let forestRight = -Infinity;
  roots.forEach((root) => {
    const branch = visit(root);
    const offset = Number.isFinite(forestRight) ? forestRight + contourGap - Math.min(...branch.left) : 0;
    shift(branch, offset, 0);
    forestRight = Math.max(...branch.right);
  });
  for (const node of map.values()) node.y = levelY[node.depth];
  return map;
}

function applyView() {
  if (!state.view) return;
  const { x, y, w, h } = state.view;
  $("tree").setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
}

function fitTree(map) {
  if (!map?.size) return;
  const nodes = [...map.values()];
  const minX = Math.min(...nodes.map((n) => n.x - n.width / 2)) - 30;
  const maxX = Math.max(...nodes.map((n) => n.x + n.width / 2)) + 55;
  const minY = Math.min(...nodes.map((n) => n.y - n.height / 2)) - 32;
  const maxY = Math.max(...nodes.map((n) => n.y + n.height / 2)) + 36;
  const box = $("tree-stage").getBoundingClientRect();
  if (box.width <= 0 || box.height <= 0) return;
  const aspect = box.width / box.height;
  let w = Math.max(maxX - minX, box.width / 1.1), h = Math.max(maxY - minY, box.height / 1.1);
  if (w / h < aspect) w = h * aspect; else h = w / aspect;
  state.view = { x: (minX + maxX - w) / 2, y: (minY + maxY - h) / 2, w, h };
  applyView();
}

function renderTree(frame) {
  const map = layoutTree(frame);
  const previous = frames()[state.index - 1];
  const previousNodes = new Map((previous?.nodes || []).map((node) => [node.id, node]));
  const motion = $("tree-pointer-motion"); motion.replaceChildren();
  const from = map.get(frame.pointer_before), to = map.get(frame.pointer);
  if (from && to && from.id !== to.id && state.mode === "operations") {
    const fromX = from.x + from.width / 2 + 7, toX = to.x + to.width / 2 + 7;
    motion.append(svgElement("path", { d: `M ${fromX} ${from.y} Q ${Math.max(fromX, toX) + 50} ${(from.y + to.y) / 2} ${toX} ${to.y}`, class: "pointer-travel", "marker-end": "url(#pointer-arrow)" }));
  }
  const edges = $("tree-edges"), nodes = $("tree-nodes");
  edges.replaceChildren(); nodes.replaceChildren();
  for (const edge of frame.edges) {
    const source = map.get(edge.source), target = map.get(edge.target);
    const start = source.y + source.height / 2, end = target.y - target.height / 2;
    edges.append(svgElement("path", { d: `M ${source.x} ${start} L ${target.x} ${end}`, class: `tree-edge ${edge.kind}` }));
    edges.append(svgElement("text", { x: (source.x + target.x) / 2 + (target.x < source.x ? -10 : 10), y: (start + end) / 2 - 6, "text-anchor": "middle", class: "edge-label" }, edge.path));
  }
  for (const node of map.values()) {
    const old = previousNodes.get(node.id);
    const changed = Boolean(previous) && (!old || JSON.stringify(old.labels) !== JSON.stringify(node.labels));
    const pointed = frame.pointer === node.id;
    const selected = state.selected === node.id;
    const group = svgElement("g", { transform: `translate(${node.x} ${node.y})`,
      class: `tree-node${node.clause ? " clause-node" : ""}${!old ? " entering" : ""}${changed ? " changed" : ""}${pointed ? " pointed" : ""}${selected ? " selected" : ""}`,
      "data-node": node.id, role: "group", "aria-label": `Tree node ${node.id}`,
    });
    const content = svgElement("g", { class: "node-content", tabindex: "0", role: "button", "aria-pressed": String(selected),
      "aria-label": `Node ${node.id}, ${node.type ? "type " + node.type : "requires " + (node.required_type || "decoration")}${pointed ? ", current pointer" : ""}` });
    const left = -node.width / 2, top = -node.height / 2;
    content.append(svgElement("title", {}, `${node.typeLabel}\n${node.formula || "No formula yet"}`));
    content.append(svgElement("rect", { x: left, y: top, width: node.width, height: node.height, rx: 6, class: "node-box" }));
    content.append(svgElement("text", { x: left + 14, y: top + 15, class: "node-address" }, `Tn(${node.id})`));
    if (node.clause) content.append(svgElement("text", { x: node.width / 2 - 30, y: top + 15, "text-anchor": "end", class: "clause-mark" }, "CLAUSE"));
    const type = svgElement("text", { class: "node-type" });
    node.typeLines.forEach((line, index) => type.append(svgElement("tspan", { x: left + 14, y: top + 37 + index * 21 }, line)));
    content.append(type);
    const formulaId = `node-formula-${encodeURIComponent(node.id)}`;
    const formula = svgElement("text", { id: formulaId, class: `node-formula${node.expanded ? " expanded" : ""}` });
    node.formulaLines.forEach((line, index) => formula.append(svgElement("tspan", { x: left + 14, y: top + 57 + (node.typeLines.length - 1) * 21 + index * 18 }, line)));
    content.append(formula);
    content.append(svgElement("circle", { cx: node.width / 2 - 18, cy: top + 15, r: 3, class: "pointer-mark" }));
    if (pointed) content.append(svgElement("text", { x: 0, y: top - 12, "text-anchor": "middle", class: "pointer-label" }, "POINTER"));
    const choose = () => {
      stop(); state.selected = node.id; $("inspector-drawer").open = true;
      selectTab("node"); renderTree(frame); renderInspector(frame);
    };
    content.addEventListener("click", choose);
    content.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); choose(); }
    });
    group.append(content);
    if (node.expandable) {
      const button = svgElement("g", { class: "formula-toggle", "data-formula-toggle": node.id,
        tabindex: "0", role: "button", "aria-expanded": String(node.expanded), "aria-controls": formulaId,
        "aria-label": `${node.expanded ? "Collapse" : "Expand"} formula at node ${node.id}` });
      button.append(svgElement("rect", { x: left + 10, y: node.height / 2 - 31, width: node.width - 20, height: 25, rx: 4 }));
      button.append(svgElement("text", { x: left + 16, y: node.height / 2 - 14 }, node.expanded ? "− Collapse formula" : "+ Expand formula"));
      const toggle = (event) => {
        event.preventDefault(); event.stopPropagation(); stop();
        state.expandedFormulas = node.expanded ? state.expandedFormulas.filter(id => id !== node.id) : [...state.expandedFormulas, node.id];
        state.selected = node.id; state.view = null;
        renderTree(frame); renderInspector(frame);
        $("tree-nodes").querySelector(`[data-formula-toggle="${CSS.escape(node.id)}"]`)?.focus({ preventScroll: true });
      };
      button.addEventListener("click", toggle);
      button.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") toggle(event); });
      group.append(button);
    }
    nodes.append(group);
  }
  if (!state.view) fitTree(map);
}

function field(panel, title, value, extra = "") {
  const block = element("div", "inspector-field");
  block.append(element("p", "field-heading", title), element("p", `inspector-value ${extra}`, value));
  panel.append(block);
}

function renderInspector(frame) {
  const node = frame.nodes.find((n) => n.id === state.selected);
  const panel = $("node-panel"); panel.replaceChildren();
  if (!node) { panel.append(element("p", "inspector-empty", "Select a node to inspect its decorations.")); return; }
  const heading = element("div", "node-heading");
  const title = element("h3", "", node.id === "0" ? "Root node" : node.clause ? "Complement clause" : "Node " + node.id);
  title.append(element("span", "", `Tn(${node.id})`));
  heading.append(title, element("span", "node-kind", node.id === frame.pointer ? "Current pointer" : node.fixed ? "Fixed address" : "Unfixed address"));
  panel.append(heading);
  field(panel, node.type ? "SEMANTIC TYPE" : "REQUIRED TYPE", math(node.type || node.required_type || "Not yet specified"), "type-value");
  field(panel, "FORMULA", node.formula || "No formula yet.");
  if (node.clause) field(panel, "CLAUSE BOUNDARY", node.clause_closed ? "Closed before combination with the embedding verb. Indefinite witnesses stay inside this content." : "This clause must finish before it can combine with the embedding verb.");
  if (node.type === "Content") field(panel, "CONSTRUCTIVE CONTENT", "A closed proof type, including Σ/Π content. Coq exports this semantic domain as Type.");
  const req = element("div", "inspector-field");
  req.append(element("p", "field-heading", `REQUIREMENTS · ${node.requirements.length}`));
  if (!node.requirements.length) req.append(element("span", "muted-copy", "All requirements satisfied here."));
  else node.requirements.forEach((label) => req.append(element("span", "decoration requirement", math(label))));
  panel.append(req);
  const decorations = element("div", "inspector-field");
  decorations.append(element("p", "field-heading", "ALL DECORATIONS"));
  node.labels.forEach((label) => decorations.append(element("span", "decoration", label)));
  if (!node.labels.length) decorations.append(element("p", "muted-copy", "This node has no decorations yet."));
  panel.append(decorations, element("p", "selection-hint", "Select another node in the tree to inspect it. Playback follows the pointer."));
}

function renderTokens(frame) {
  const container = $("word-tokens"); container.replaceChildren();
  const axiom = element("button", "axiom-token" + (frame.word_index < 0 ? " current" : " visited"), "∅ Axiom");
  axiom.addEventListener("click", () => setIndex(0)); container.append(axiom);
  state.result.tokens.forEach((token, index) => {
    const failed = state.result.failure?.index === index;
    const button = element("button", `${index < frame.word_index ? "visited" : ""}${index === frame.word_index ? " current" : ""}${failed ? " failed" : ""}`, token);
    button.setAttribute("aria-label", `View state after token ${index + 1}: ${token}`);
    const target = frames().findLastIndex((step) => step.word_index === index);
    button.disabled = target < 0 || failed;
    if (failed) button.title = state.result.failure.message;
    button.addEventListener("click", () => setIndex(target));
    container.append(button);
  });
}

function renderTrace() {
  const list = $("action-list"); list.replaceChildren();
  const channel = state.mode === "operations" ? "operations" : "actions";
  (playback()[channel] || []).forEach((frame, index) => {
    const item = element("li");
    const button = element("button"); button.dataset.actionIndex = index; button.dataset.channel = channel;
    button.append(element("span", "action-word", frame.word_index < 0 ? "START" : `${frame.speaker ? frame.speaker + " · " : ""}WORD ${frame.word_index + 1} · ${state.result.tokens[frame.word_index]}`));
    if (frame.rule_kind) button.append(element("span", `rule-kind ${frame.rule_kind}`, ruleKindLabel(frame)));
    if (frame.rule && frame.rule !== frame.label) button.append(element("span", "action-rule", frame.rule));
    button.append(document.createTextNode(math(frame.label)));
    button.addEventListener("click", () => { stop(); state.mode = channel; setIndex(index); });
    item.append(button); list.append(item);
  });
}

function renderReadings() {
  const readings = state.result?.readings || [];
  $("readings-panel").hidden = readings.length < 2;
  const names = { fixed: "Fixed structure", "star-adjunction": "Unfixed node + MERGE", link: "LINK" };
  $("reading").replaceChildren(...readings.map((reading, index) => {
    const strategy = reading.strategies.map((name) => names[name] || name).join(" + ");
    const option = element("option", "", `${index + 1} · ${strategy} · ${excerpt(reading.normalized || reading.semantics || "", 65)}`);
    option.value = index; return option;
  }));
  $("reading").value = state.readingIndex;
  const search = state.result?.reading_search || {};
  const notes = {
    reading_limit: search.requested === 1 ? "Showing the first complete analysis. Request more above to explore alternatives." : "Stopped at the requested number of analyses; more may exist.",
    exhausted: "Search exhausted the available alternatives.",
    candidate_limit: "Stopped at the candidate limit; more complete analyses may exist.",
    search_limit: "Alternative search reached a parser limit. The first complete analysis is retained.",
  };
  $("readings-summary").textContent = `${readings.length} complete ${readings.length === 1 ? "analysis" : "analyses"}. ${notes[search.stop_reason] || ""}${search.top_n_cuts?.length ? " Some lexical readings were excluded by the entry limit." : ""} Strategy labels describe tree operations, not discourse or grammaticality judgments.`;
}

function ruleKindLabel(frame) {
  return { lexical: "Lexical rule", computational: "Computational rule", grouped: "Grouped transition", action: "Parser action" }[frame.rule_kind] || "Parser transition";
}

function renderOperation(frame) {
  $("operation-rule").hidden = frame.kind === "action" && frame.rule === frame.label;
  $("operation-kind").textContent = ruleKindLabel(frame);
  $("operation-kind").className = `rule-kind ${frame.rule_kind || "transition"}`;
  if (state.mode !== "words" && frame.kind === "trace_gap") {
    $("operation-detail").hidden = false; $("operation-program").hidden = true;
    $("operation-rule").textContent = "Trace limit";
    $("operation-code").textContent = "Jump to the final recorded tree";
    $("pointer-transition").textContent = "";
    $("operation-change").textContent = "Intermediate rule snapshots exceeded the display budget. DS continued parsing; this jump does not represent one rule.";
    return;
  }
  if (state.mode !== "words" && frame.kind === "backtrack") {
    $("operation-detail").hidden = false; $("operation-program").hidden = true;
    $("operation-rule").textContent = "Revise an earlier interpretation";
    $("operation-code").textContent = "Return to the earlier tree";
    $("pointer-transition").textContent = `Pointer ${frame.pointer_before} → ${frame.pointer}`;
    $("operation-change").textContent = frame.lexical_changes?.length ? frame.lexical_changes.map((change) => `${change.reason}: ${change.before.word}, ${change.before.template} / ${change.before.symbol} → ${change.after.template} / ${change.after.symbol}`).join("; ") : "The observed continuation requires another derivation. The following steps replay its actions.";
    return;
  }
  if (state.mode !== "words" && frame.kind === "repair") {
    $("operation-detail").hidden = false; $("operation-program").hidden = true;
    $("operation-rule").textContent = "Local repair · context transition";
    $("operation-code").textContent = "Restore the earlier tree";
    $("pointer-transition").textContent = `Pointer ${frame.repair.from_pointer} → ${frame.repair.to_pointer}`;
    $("operation-change").textContent = `Reopen the position before “${frame.repair.replaced.map((i) => state.result.tokens[i]).join(" ")}”. The next frames execute the replacement’s lexical actions.`;
    return;
  }
  const atomic = state.mode === "operations" && frame.kind === "operation";
  const active = atomic || (state.mode === "actions" && frame.kind === "action");
  $("operation-detail").hidden = !active;
  $("operation-program").hidden = !atomic;
  if (!active) return;
  $("operation-rule").textContent = frame.rule;
  $("operation-code").textContent = math(frame.label);
  const moved = frame.pointer_before !== frame.pointer;
  $("pointer-transition").textContent = moved ? `Pointer ${frame.pointer_before} → ${frame.pointer}` : `Pointer stays at ${frame.pointer}`;
  const delta = frame.delta || {created: [], removed: [], decorations: []};
  const changes = [];
  if (delta.created.length) changes.push("Created " + delta.created.map((id) => `Tn(${id})`).join(", "));
  if (delta.removed.length) changes.push("Removed " + delta.removed.map((id) => `Tn(${id})`).join(", "));
  for (const decoration of delta.decorations) {
    if (decoration.added.length) changes.push(`At ${decoration.node}: + ${decoration.added.map(math).join(", ")}`);
    if (decoration.removed.length) changes.push(`At ${decoration.node}: − ${decoration.removed.map(math).join(", ")}`);
  }
  $("operation-change").textContent = changes.join(" · ") || (moved ? "Traversal; node decorations are unchanged." : "Tree unchanged by this step.");
  if (!atomic) return;
  const program = $("operation-program"); program.replaceChildren();
  program.append(element("p", "program-heading", frame.rule));
  for (const condition of frame.conditions) {
    program.append(element("p", "program-keyword", "IF"));
    for (const check of condition.checks) program.append(element("div", "program-check", `${check.passed ? "✓" : "✕"} ${math(check.label)}`));
    program.append(element("p", "program-keyword", condition.branch));
  }
  playback().operations.forEach((operation, index) => {
    if (operation.kind !== "operation" || operation.rule_index !== frame.rule_index) return;
    const line = element("button", "program-line" + (index === state.index ? " executing" : ""), math(operation.label));
    line.setAttribute("aria-current", String(index === state.index));
    line.addEventListener("click", () => setIndex(index)); program.append(line);
  });
}

function render() {
  const frame = current(); if (!frame) return;
  const word = frame.word_index < 0 ? "Initial tree" : `While processing word ${frame.word_index + 1}: “${state.result.tokens[frame.word_index]}”`;
  const attempt = state.result.attempt || state.result.assistance?.derivation_attempts?.length;
  $("rule-progress").textContent = `${state.paragraph ? `Sentence ${state.paragraphIndex + 1} · ` : ""}${attempt ? `DS attempt ${attempt} · ` : ""}${word}`;
  $("playback-explanation").textContent = state.result.trace_truncated
    ? state.result.trace_note
    : "Rules shows lexical and computational steps in order as the tree grows. These steps replay the path selected at each word; a backtrack explicitly returns to an earlier tree.";
  if (!frame.nodes.some((node) => node.id === state.selected)) state.selected = frame.pointer;
  $("frame-label").textContent = state.mode === "words" ? (state.index ? `After ${frame.label === "Completion" ? "completion" : "“" + frame.label + "”"}` : `The axiom · ?Ty(${frame.nodes[0]?.required_type || "t"})`) : math(frame.label) + (frame.kind === "grouped" ? " · grouped replay" : "");
  $("frame-label").title = $("frame-label").textContent;
  $("step-count").textContent = `${state.index} / ${frames().length - 1}`;
  $("timeline").max = frames().length - 1; $("timeline").value = state.index;
  $("semantics").textContent = frame.backend === "ttr" ? formatRecord(frame.semantics) : (frame.semantics || "Root formula under construction · inspect the growing node formulas above.");
  $("semantic-system").textContent = { mltt: "Constructive · Σ / Π", classical: "Classical · λ / ε / τ", ttr: "TTR" }[frame.backend];
  $("normalized").hidden = !frame.normalized || frame.normalized === frame.semantics;
  $("normalized").textContent = "Simplified: " + (frame.normalized || "");
  $("speech-act").hidden = !frame.speech_act;
  $("speech-act").textContent = frame.speech_act?.kind === "polar_question"
    ? "Question content · this proposition is being asked about."
    : frame.speech_act?.kind === "polarity_answer"
      ? `${frame.speech_act.polarity === "no" ? "Negative" : "Positive"} answer to the previous question: ${frame.speech_act.question_content}.`
      : "";
  $("reflexive-binding").hidden = !frame.reflexive_bindings?.length;
  $("reflexive-binding").textContent = (frame.reflexive_bindings || []).map((binding) => `${binding.word} → local subject ${binding.antecedent_label || binding.antecedent} · spoken by ${binding.speaker}`).join("; ");
  const finished = typeof state.result?.complete === "boolean";
  const finalComplete = Boolean(selectedReading() || state.result?.complete);
  const atEnd = state.index === frames().length - 1;
  $("playback-status").hidden = !finished;
  const inputLabel = state.paragraph ? "This sentence" : "The whole input";
  $("playback-status-text").textContent = `${inputLabel} ${finalComplete ? "has a complete derivation." : "is incomplete."} ${atEnd ? "Showing the final recorded tree." : `Viewing an earlier tree: step ${state.index} of ${frames().length - 1}.`}`;
  $("semantic-status").textContent = frame.complete ? "COMPLETE TREE AT THIS STEP" : finished && finalComplete ? "EARLIER TREE · FINAL DERIVATION COMPLETE" : "INCOMPLETE TREE AT THIS STEP";
  if (finished && finalComplete && atEnd && frame.complete) $("semantic-status").textContent = "COMPLETE TREE";
  $("semantic-note").textContent = frame.semantic_error || (frame.complete ? "All requirements are satisfied. This formula was composed by the selected semantic backend." : `${frame.requirement_count} outstanding requirement${frame.requirement_count === 1 ? "" : "s"}. Node formulas and types develop as the pointer moves through the tree.`);
  if (finished && !atEnd) $("semantic-note").textContent += finalComplete ? " These are requirements at this earlier playback step; the final derivation completed. Use Show final result to inspect it." : " This is an earlier playback step; the whole input did not complete.";
  if (finished && !finalComplete && atEnd && frame.complete) $("semantic-note").textContent += " This tree covers the accepted prefix; the whole input did not complete.";
  if (frame.complete && frame.context_assumptions?.length) $("semantic-note").textContent += ` Context assumptions: ${frame.context_assumptions.join(" ")}`;
  for (const button of document.querySelectorAll("[data-mode]")) {
    const active = button.dataset.mode === state.mode;
    button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active));
  }
  for (const button of document.querySelectorAll("[data-action-index]")) {
    const active = button.dataset.channel === state.mode && Number(button.dataset.actionIndex) === state.index;
    button.classList.toggle("current", active);
    button.setAttribute("aria-current", String(active));
    if (active && !$("trace-panel").hidden) {
      const panel = $("trace-panel"), bounds = panel.getBoundingClientRect(), item = button.getBoundingClientRect();
      if (item.top < bounds.top || item.bottom > bounds.bottom) panel.scrollTop += item.top - bounds.top - 12;
    }
  }
  renderOperation(frame); renderTree(frame); renderInspector(frame); renderTokens(frame); renderDialoguePlayback(frame); updateControls();
}

function setIndex(index, playing = false) {
  if (!frames().length) return;
  if (!playing) stop();
  state.index = Math.max(0, Math.min(frames().length - 1, index));
  state.selected = current().pointer;
  if ($("follow-tree").checked) state.view = null;
  render();
}

function play() {
  if (!state.result) return;
  if (state.timer) { stop(); return; }
  if (state.index === frames().length - 1 && !state.busy) setIndex(0);
  $("play").textContent = "Ⅱ"; $("play").setAttribute("aria-label", "Pause derivation");
  state.timer = setInterval(() => {
    if (state.index >= frames().length - 1) { if (!state.busy) stop(); return; }
    setIndex(state.index + 1, true);
  }, Number($("speed").value));
}

function selectTab(tab) {
  for (const name of ["node", "trace"]) {
    const active = name === tab;
    $(name + "-tab").setAttribute("aria-selected", String(active));
    $(name + "-panel").hidden = !active;
  }
}

$("parse-form").addEventListener("submit", (event) => { event.preventDefault(); parseSentence(); });
$("first").addEventListener("click", () => setIndex(0));
$("previous").addEventListener("click", () => setIndex(state.index - 1));
$("next").addEventListener("click", () => setIndex(state.index + 1));
$("play").addEventListener("click", play);
$("timeline").addEventListener("input", (event) => setIndex(Number(event.target.value)));
$("node-tab").addEventListener("click", () => selectTab("node"));
$("trace-tab").addEventListener("click", () => selectTab("trace"));
for (const button of document.querySelectorAll("[data-mode]")) button.addEventListener("click", () => {
  if (!state.result) return;
  const wordIndex = current().word_index;
  state.mode = button.dataset.mode;
  renderTrace();
  setIndex(Math.max(0, frames().findLastIndex((frame) => frame.word_index === wordIndex)));
});

$("fit").addEventListener("click", () => { if (current()) fitTree(layoutTree(current())); });
function zoom(factor) {
  if (!state.view) return;
  const view = state.view;
  if (view.w * factor < 160 || view.w * factor > 7000) return;
  $("follow-tree").checked = false;
  view.x += view.w * (1 - factor) / 2; view.y += view.h * (1 - factor) / 2;
  view.w *= factor; view.h *= factor; applyView();
}
$("zoom-in").addEventListener("click", () => zoom(.8));
$("zoom-out").addEventListener("click", () => zoom(1.25));
$("tree").addEventListener("pointerdown", (event) => {
  if (!state.view || event.target.closest(".tree-node")) return;
  $("follow-tree").checked = false;
  state.drag = { x: event.clientX, y: event.clientY, view: { ...state.view } };
  $("tree").setPointerCapture(event.pointerId);
});
$("tree").addEventListener("pointermove", (event) => {
  if (!state.drag) return;
  const box = $("tree").getBoundingClientRect(), drag = state.drag;
  state.view.x = drag.view.x - (event.clientX - drag.x) * drag.view.w / box.width;
  state.view.y = drag.view.y - (event.clientY - drag.y) * drag.view.h / box.height;
  applyView();
});
for (const event of ["pointerup", "pointercancel"]) $("tree").addEventListener(event, () => { state.drag = null; });
new ResizeObserver(() => { if (current() && $("follow-tree").checked) fitTree(layoutTree(current())); }).observe($("tree-stage"));
$("follow-tree").addEventListener("change", () => { if ($("follow-tree").checked && current()) fitTree(layoutTree(current())); });

$("copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText(current().semantics); $("copy").textContent = "Copied ✓"; }
  catch { message("Clipboard access is unavailable. Select and copy the formula below."); }
  setTimeout(() => { $("copy").textContent = "Copy formula"; }, 1800);
});
$("export").addEventListener("click", () => {
  if (!state.result && !state.paragraph) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(state.paragraph || state.result, null, 2)], { type: "application/json" }));
  const link = element("a"); link.href = url; link.download = state.paragraph ? "ds-paragraph.json" : "ds-derivation.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$("help-open").addEventListener("click", () => { stop(); $("help-dialog").showModal(); });
$("help-close").addEventListener("click", () => $("help-dialog").close());
$("method-help").addEventListener("click", () => { stop(); $("help-dialog").showModal(); $("help-dialog").scrollTop = 0; });
$("pp-help").addEventListener("click", () => {
  stop(); $("guide-pps").open = true; $("help-dialog").showModal();
  $("guide-pps").querySelector("summary").focus(); $("guide-pps").scrollIntoView({ block: "start" });
});
$("use-dictionaries").addEventListener("click", useDictionariesOnly);
for (const button of document.querySelectorAll("[data-guide-example]")) button.addEventListener("click", () => {
  if (state.busy || !state.config) return;
  setInputMode("sentence");
  if ($("system").value === "ttr") { $("system").value = "mltt"; selectSystem(); }
  $("grammar").value = `2026-${button.dataset.guideLanguage || "english"}-${$("system").value}`; updateGrammar();
  useDictionariesOnly(); $("n-best").value = button.dataset.guideReadings || "1";
  $("sentence").value = button.dataset.guideExample;
  $("help-dialog").close(); parseSentence();
  document.querySelector(".composer").scrollIntoView({ behavior: "smooth", block: "start" });
});
document.addEventListener("keydown", (event) => {
  if (!state.result || $("help-dialog").open || event.target.closest("input, select, textarea")) return;
  if (event.key === " " && event.target.closest("button, [role=button]")) return;
  const callbacks = { ArrowLeft: () => setIndex(state.index - 1), ArrowRight: () => setIndex(state.index + 1), Home: () => setIndex(0), End: () => setIndex(frames().length - 1), " ": play };
  if (callbacks[event.key]) { event.preventDefault(); callbacks[event.key](); }
});
document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });

function greekGrammar() {
  return state.config?.greek?.grammars[$("grammar").value];
}

function readDialogue() {
  return [...$("dialogue-rows").children].map((row) => ({ speaker: row.querySelector(".turn-speaker").value.trim(), text: row.querySelector(".turn-text").value.trim(), boundary: row.querySelector(".turn-boundary").value }));
}

function setDialogue(turns) {
  $("dialogue-rows").replaceChildren(...turns.map((turn, index) => {
    const row = element("div", "dialogue-row");
    const speaker = element("input", "turn-speaker"); speaker.value = turn.speaker; speaker.maxLength = 32; speaker.setAttribute("aria-label", `Speaker for turn ${index + 1}`);
    const text = element("input", "turn-text"); text.value = turn.text; text.maxLength = 500; text.placeholder = "Words contributed in this turn"; text.setAttribute("aria-label", `Words for turn ${index + 1}`); text.spellcheck = false;
    text.addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); parseSentence(); } });
    const boundary = element("select", "turn-boundary"); boundary.setAttribute("aria-label", `Tree boundary for turn ${index + 1}`);
    for (const [id, label] of [["continue", "Continue tree"], ["new_tree", "New tree"]]) { const option = element("option", "", label); option.value = id; boundary.append(option); }
    boundary.value = turn.boundary || "continue";
    const remove = element("button", "remove-turn", "×"); remove.type = "button"; remove.setAttribute("aria-label", `Remove turn ${index + 1}`);
    remove.addEventListener("click", () => { const current = readDialogue(); current.splice(index, 1); setDialogue(current.length ? current : [{speaker:"A",text:""}]); });
    row.append(speaker, text, boundary, remove); return row;
  }));
  $("add-turn").disabled = state.busy || turns.length >= 12;
}

function dialogueExamples() {
  const family = greekGrammar()?.dialect || "english";
  return (state.config?.dialogue?.examples || []).filter((example) => example.family === family && (!example.backends || example.backends.includes($("system").value)));
}

function renderDialogueExamples() {
  $("dialogue-examples").replaceChildren(...dialogueExamples().map((example) => {
    const button = element("button", "", example.label); button.type = "button"; button.dataset.dialogueExample = example.id;
    button.addEventListener("click", () => { setDialogue(example.turns); parseSentence(); }); return button;
  }));
  $("dialogue-coverage-text").textContent = state.config?.dialogue?.coverage || "";
}

function setInputMode(mode) {
  if (state.busy) return;
  stop(); state.inputMode = mode;
  $("dialogue-editor").hidden = mode !== "dialogue";
  $("paragraph-editor").hidden = mode !== "paragraph";
  $("sentence").closest(".sentence-field").hidden = mode !== "sentence";
  $("sentence").disabled = mode !== "sentence";
  $("paragraph").disabled = mode !== "paragraph";
  $("n-best").disabled = mode !== "sentence";
  document.querySelector(".examples").hidden = mode !== "sentence";
  for (const button of document.querySelectorAll("[data-input-mode]")) { const active = button.dataset.inputMode === mode; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); }
  if (mode === "dialogue" && !$("dialogue-rows").children.length) setDialogue(dialogueExamples()[0]?.turns || [{speaker:"A",text:""}, {speaker:"B",text:""}]);
  $("parse-label").textContent = mode === "dialogue" ? "Build dialogue" : mode === "paragraph" ? "Parse paragraph" : "Build derivation";
  renderDialogueExamples();
  renderLexicalSettings();
}

function renderParagraph() {
  const paragraph = state.paragraph;
  $("paragraph-results").hidden = !paragraph;
  if (!paragraph) return;
  const total = paragraph.sentences.length, complete = paragraph.sentences.filter(s => s.complete).length;
  $("paragraph-summary").textContent = `${complete} / ${total} sentences have complete DS derivations${paragraph.coverage ? paragraph.complete ? "" : " · paragraph incomplete" : " · parsing…"}`;
  $("paragraph-context").textContent = paragraph.context_note || "Parsing each sentence in order. Completed sentences supply context to later ones.";
  $("paragraph-sentences").replaceChildren(...paragraph.sentences.map((row, index) => {
    const item = element("li", row.complete ? "paragraph-complete" : "paragraph-incomplete");
    const button = element("button", "paragraph-sentence", row.text);
    button.type = "button"; button.dataset.sentenceIndex = index;
    button.disabled = !paragraph.coverage;
    button.setAttribute("aria-pressed", String(index === state.paragraphIndex));
    button.addEventListener("click", () => showParagraphSentence(index));
    item.append(button, element("span", "paragraph-status", row.complete ? "Complete DS derivation" : row.status === "pending" ? "Waiting…" : row.status === "parsing" ? "Reading rules…" : row.failure?.message || "Incomplete"));
    if (row.context_gaps?.length) item.append(element("span", "paragraph-status", `Context excludes failed sentence${row.context_gaps.length > 1 ? "s" : ""} ${row.context_gaps.map(i => i + 1).join(", ")}.`));
    return item;
  }));
}

function showParagraphSentence(index) {
  stop(); state.paragraphIndex = index; state.expandedFormulas = [];
  const row = state.paragraph.sentences[index];
  state.result = row.result || null;
  state.readingIndex = 0; state.mode = row.result?.actions?.length ? "actions" : "words"; state.index = 0;
  state.selected = "0"; state.view = null;
  $("loading-state").hidden = true; $("empty-state").hidden = Boolean(row.result);
  $("readings-panel").hidden = true;
  $("result-status").textContent = `Sentence ${index + 1} · ${row.complete ? "complete derivation" : row.status.replaceAll("_", " ")}`;
  $("result-status").className = "badge" + (row.complete ? "" : " warn");
  $("elapsed").textContent = `${state.paragraph.elapsed_ms} ms · ${state.paragraph.sentences.length} sentences`;
  message(row.failure?.message || (row.context_gaps.length ? "This sentence was parsed with gaps in the preceding context." : ""), !row.complete);
  if (row.result) { renderDiagnostics(row.result); selectTab("trace"); renderTrace(); render(); }
  else {
    $("playback-status").hidden = true;
    $("tree").replaceChildren(); $("diagnostics").hidden = true; $("lexical-report").hidden = true; $("method-result").hidden = true;
    $("action-list").replaceChildren();
    $("semantics").textContent = "No completed analysis is available for this sentence.";
    $("semantic-status").textContent = "UNVERIFIED";
    $("semantic-note").textContent = row.failure?.message || "";
    $("normalized").hidden = true;
    $("speech-act").hidden = true;
    $("reflexive-binding").hidden = true;
    $("operation-detail").hidden = true;
  }
  renderParagraph(); updateControls();
  if (row.result) play();
}

for (const button of document.querySelectorAll("[data-input-mode]")) button.addEventListener("click", () => setInputMode(button.dataset.inputMode));
$("add-turn").addEventListener("click", () => {
  const turns = readDialogue(); if (turns.length >= 12) return;
  turns.push({ speaker: turns.at(-1)?.speaker === "A" ? "B" : "A", text: "", boundary: "continue" }); setDialogue(turns);
  $("dialogue-rows").lastElementChild.querySelector(".turn-text").focus();
});

function dialogueJump(index, kind = "word") {
  state.mode = kind === "repair" ? "operations" : "words"; renderTrace();
  const target = frames().findIndex((frame) => frame.word_index === index && frame.kind === kind);
  if (target >= 0) setIndex(target);
}

function renderDialoguePlayback(frame) {
  const result = state.result, turns = result?.dialogue;
  $("dialogue-playback").hidden = !turns; $("dialogue-history").hidden = !turns;
  if (!turns) return;
  const metadata = result.token_metadata;
  const speakerClass = (speaker) => `speaker-${turns[0].speaker === speaker ? "a" : "b"}`;
  $("dialogue-now").textContent = frame.speaker ? `Tree ${frame.clause_index + 1} · Turn ${frame.turn_index + 1} · ${frame.speaker} → ${frame.addressee}` : "Shared context · initial tree";
  const superseded = new Set((result.repairs || []).filter((repair) => repair.replacement <= frame.word_index).flatMap((repair) => repair.replaced));
  $("dialogue-transcript").replaceChildren(...turns.map((turn, turnIndex) => {
    const row = element("div", "transcript-turn" + (frame.turn_index === turnIndex ? " active-turn" : ""));
    row.append(element("span", `speaker-tag ${speakerClass(turn.speaker)}`, turn.speaker));
    if (turn.boundary === "new_tree") row.append(element("span", "boundary-tag", "New tree"));
    result.tokens.forEach((word, index) => {
      if (metadata[index].turn_index !== turnIndex) return;
      const status = index > frame.word_index ? "future" : superseded.has(index) ? "superseded" : "contributed";
      const button = element("button", `transcript-word ${status}${index === frame.word_index ? " current-word" : ""}`, word);
      button.type = "button"; button.dataset.dialogueWord = index; button.title = `${turn.speaker}: ${word}${superseded.has(index) ? " · replaced" : ""}`;
      button.disabled = !result.words.some((f) => f.word_index === index && f.kind === "word");
      button.addEventListener("click", () => dialogueJump(index)); row.append(button);
    });
    return row;
  }));
  $("repair-history").replaceChildren(...(result.repairs || []).map((repair) => {
    const item = element("div", "repair-record");
    const old = repair.replaced.map((index) => result.tokens[index]).join(" ");
    item.append(element("p", "", `${old} → ${result.tokens[repair.replacement]} · ${repair.speaker}`));
    for (const [label, index, kind] of [["Before", Math.max(...repair.replaced), "word"], ["Rollback", repair.replacement, "repair"], ["Replacement", repair.replacement, "word"]]) {
      const button = element("button", "text-button", label); button.type = "button"; button.dataset.repairStep = label.toLowerCase(); button.addEventListener("click", () => dialogueJump(index, kind)); item.append(button);
    }
    return item;
  }));
  if (!result.repairs?.length) $("repair-history").append(element("p", "context-empty", "No recorded repair. A local correction preserves the original contribution here."));
  $("context-history").replaceChildren(...(result.context_trees || []).filter((tree) => tree.clause_index < frame.clause_index).map((tree) => {
    const item = element("div", "context-record");
    item.append(element("p", "", `${tree.label} · ${tree.speech_act?.kind === "polar_question" ? "question content · " : ""}${tree.complete ? "complete" : "incomplete"}`), element("code", "", tree.semantics || "Open requirements"));
    const button = element("button", "text-button", "Inspect tree"); button.type = "button";
    button.addEventListener("click", () => { state.mode = "words"; renderTrace(); setIndex(frames().findLastIndex((f) => f.clause_index === tree.clause_index)); }); item.append(button); return item;
  }));
  if (!$("context-history").children.length) $("context-history").append(element("p", "context-empty", "This point in the dialogue has no earlier tree. Speaker changes continue the current one."));
}

function updateGrammar() {
  const greek = greekGrammar();
  $("scope").disabled = $("system").value !== "mltt" || Boolean(greek);
  $("coverage").textContent = greek ? `${greek.short}: ${greek.explanation}`
    : $("system").value === "ttr" ? "Installed DS-TTR grammars."
    : "English fragment: names, determiners, verbs, PP arguments and modifiers, finite complements, temporal/causal/conditional/concessive clauses, restrictive relatives and main-clause nonrestrictive relatives with named heads.";
  $("greek-context").hidden = !greek;
  $("greek-context").textContent = greek ? "The examples use a small reviewed vocabulary. Open the Greek lab below for each variety’s supported constructions, source judgments and context assumptions." : "";
  renderExamples();
  renderDialogueExamples();
  renderLexicalSettings();
  const baseline = state.config?.paragraph?.baseline;
  const probe = state.config?.paragraph?.assisted_probe;
  if (probe) {
    const backend = $("system").value === "classical" ? "classical" : "mltt";
    const en = probe[`english-${backend}`], el = probe[`smg-${backend}`];
    $("paragraph-assisted-probe").textContent = `Open text development check: ${en.complete_sentences}/${en.sentences} English and ${el.complete_sentences}/${el.sentences} Greek sentences completed with model assistance. Six hand-written passages, including harder failures; this is not a general accuracy estimate.`;
  }
  if (baseline) {
    const en = baseline["en-mltt"], el = baseline["el-mltt"];
    $("paragraph-baseline").textContent = `Unseen-text baseline: ${en.complete_passages}/${en.passages} English paragraphs and ${el.complete_passages}/${el.passages} Greek passages completed in both semantic systems. ${state.config.paragraph.baseline_note}`;
  }
}

function lexicalSupported() {
  return state.config?.lexical?.grammars.includes($("grammar").value);
}

function useDictionariesOnly() {
  if (state.busy || !state.config) return;
  const config = state.config.lexical;
  const greek = config.greek_corpus?.grammars.includes($("grammar").value);
  $("lexical-mode").value = !lexicalSupported() ? "off" : greek ? (config.greek_corpus.installed ? "corpus" : "off") : config.dictionary?.installed ? "dictionary" : "bundled";
  $("decision-mode").value = "off";
  $("llm-enabled").checked = false;
  renderLexicalSettings();
}

function dictionaryMode() {
  const config = state.config?.lexical;
  if (!lexicalSupported()) return "off";
  if (config.greek_corpus?.grammars.includes($("grammar").value)) return config.greek_corpus.installed ? "corpus" : "off";
  return config.dictionary?.installed ? "dictionary" : "bundled";
}

function analysisMode() {
  return state.inputMode === "dialogue" ? "model" : "assisted";
}

function assistanceAvailability() {
  const config = state.config?.lexical;
  const greek = config?.greek_corpus?.grammars.includes($("grammar").value);
  const gates = state.config?.decision?.grammars?.[$("grammar").value] || {};
  return {
    llm: Boolean(lexicalSupported() && config?.provider.configured && !(greek && state.inputMode === "dialogue")),
    senses: Boolean(lexicalSupported() && !greek && config?.selection?.configured),
    search: Boolean(state.config?.decision?.configured && (gates.entry || gates.fanout)),
  };
}

function changeAssistance(kind) {
  if (state.busy || !state.config) return;
  const available = assistanceAvailability();
  if (kind === "llm") {
    if ($("lexical-mode").value !== "jev") $("lexical-mode").value = $("llm-enabled").checked ? analysisMode() : dictionaryMode();
  } else if ($("jev-enabled").checked) {
    if (available.senses) $("lexical-mode").value = "jev";
    else if (available.search) $("decision-mode").value = "jev";
  } else {
    $("decision-mode").value = "off";
    if ($("lexical-mode").value === "jev") $("lexical-mode").value = $("llm-enabled").checked ? analysisMode() : dictionaryMode();
  }
  renderLexicalSettings();
}

function renderAssistanceControls() {
  if (!state.config) return;
  const available = assistanceAvailability(), config = state.config.lexical;
  const mode = lexicalSupported() ? $("lexical-mode").value : "off";
  const llm = ["assisted", "model"].includes(mode) || (mode === "jev" && $("llm-enabled").checked && available.llm);
  const jev = mode === "jev" || $("decision-mode").value === "jev";
  $("llm-enabled").checked = llm;
  $("jev-enabled").checked = jev;
  $("llm-enabled").disabled = state.busy || !available.llm;
  $("jev-enabled").disabled = state.busy || !(available.senses || available.search);
  $("model-settings-button").disabled = state.busy;
  $("llm-state").textContent = llm ? "ON · when needed" : "OFF";
  $("jev-state").textContent = jev ? "ON" : "OFF";
  $("llm-help").textContent = mode === "jev"
    ? "With Jev: proposes missing words only. Open text construction assistance resumes when Jev is off."
    : state.inputMode === "dialogue" ? "Proposes missing vocabulary for dialogue. DS builds the shared tree."
    : "Proposes vocabulary and supported constructions when needed. It may make no request if DS can proceed.";
  $("jev-help").textContent = available.senses || !available.search
    ? "Ranks alternative word meanings as context arrives. DS checks the choices."
    : "Orders parser choices for this calibrated grammar. DS checks the choices.";
  $("llm-model").textContent = !lexicalSupported() ? "Unavailable for this grammar, including TTR."
    : !config.provider.configured ? "Connect and choose a model to enable."
    : !available.llm ? "Unavailable for Greek dialogue; choose Sentence or Paragraph."
    : `Selected: ${config.provider.model}`;
  $("jev-model").textContent = !(available.senses || available.search)
    ? lexicalSupported() && !config.greek_corpus?.grammars.includes($("grammar").value) ? "Connect OpenRouter with Jev available to enable." : "Word-meaning assistance is available for native English only."
    : `Pinned model: ${available.senses ? config.selection.model : state.config.decision.model}`;
  for (const id of ["llm", "jev"]) $(id + "-enabled").closest(".assistance-card").classList.toggle("enabled", $(id + "-enabled").checked);
  $("assistance-hint").textContent = !lexicalSupported() ? "AI unavailable for this grammar" : !config.provider.configured ? "Optional · connect to enable" : "DS checks every derivation";
}

function liveGreekSourcesActive() {
  return Boolean(state.config?.lexical?.greek_sources?.grammars.includes($("grammar").value)
    && state.inputMode !== "dialogue" && $("lexical-mode").value === "assisted" && $("live-greek-sources").checked);
}

function jevComparisonActive() {
  return Boolean(state.config?.lexical?.selection?.comparison?.grammars.includes($("grammar").value)
    && state.inputMode === "sentence" && $("lexical-mode").value === "jev" && $("compare-jev").checked);
}

function prepareJevExample(sentence) {
  const backend = $("system").value;
  if (!["classical", "mltt"].includes(backend)) { message("Choose Classical or Constructive to run this native English Jev example."); return; }
  setInputMode("sentence");
  $("grammar").value = `2026-english-${backend}`;
  updateGrammar();
  $("sentence").value = sentence;
  $("compare-jev").checked = true;
  $("jev-demo").open = true;
  runJevComparison();
}

function runJevComparison() {
  if (!state.config?.lexical?.selection?.configured) {
    $("lexical-settings").open = true;
    $("openrouter-key").focus();
    message("The example is ready. Connect OpenRouter, then press Compare this sentence.");
    return;
  }
  $("lexical-mode").value = "jev";
  $("compare-jev").checked = true;
  $("decision-mode").value = "off";
  $("n-best").value = "1";
  renderLexicalSettings(); parseSentence();
}

function renderJevControls() {
  const selection = state.config?.lexical?.selection;
  const supported = selection?.comparison?.grammars.includes($("grammar").value) && state.inputMode === "sentence";
  $("compare-jev").disabled = state.busy;
  $("jev-run").disabled = state.busy || !supported || !selection?.configured;
  $("jev-demo-button").disabled = state.busy;
  $("jev-demo-status").textContent = !selection?.configured ? "Connect OpenRouter to run Jev. The examples use native English Classical or Constructive DS." : !supported ? "Choose an English Classical or Constructive sentence, or one of the examples above." : "Ready · same candidates, two DS runs · up to eight fresh Jev requests.";
  $("jev-examples").replaceChildren(...(selection?.comparison?.examples || []).map(example => {
    const button = element("button", "example-chip", example.label); button.type = "button";
    button.disabled = state.busy; button.title = example.sentence;
    button.addEventListener("click", () => prepareJevExample(example.sentence));
    return button;
  }));
  if (jevComparisonActive()) { $("n-best").value = "1"; $("decision-mode").value = "off"; }
  $("n-best").disabled = state.busy || state.inputMode !== "sentence" || jevComparisonActive();
}

function renderMethodMode() {
  const mode = lexicalSupported() ? $("lexical-mode").value : "off";
  const descriptions = {
    off: "Next parse: the original grammar lexicon. No lexical model requests.",
    bundled: "Next parse: the grammar plus bundled vocabulary. No lexical model requests.",
    dictionary: "Next parse: the grammar, bundled vocabulary and WordNet candidates. No lexical model requests.",
    corpus: "Next parse: the Standard Greek grammar and corpus lexical candidates. No lexical model requests.",
    assisted: "Next parse: DS and dictionaries first; your selected model may help with vocabulary and constructions.",
    model: "Next parse: the grammar and bundled vocabulary, with model proposals for missing content words. DS builds and checks the derivation.",
    jev: "Next parse: DS + Jev word meanings. " + ($("llm-enabled").checked ? "The analysis LLM may supply missing words only." : "The analysis LLM is off, including the missing-word fallback."),
  };
  const ordering = $("decision-mode").value === "jev" ? " Jev may also order parser choices." : "";
  $("method-mode").textContent = descriptions[mode] + ordering;
  if (liveGreekSourcesActive()) $("method-mode").textContent += " Needed lexical proposals will receive Svarna examples and Triantafyllidis excerpts, within the retrieval limit.";
  if (jevComparisonActive()) $("method-mode").textContent += " A second DS run without Jev will show whether the same candidates lead to a different meaning.";
  $("use-dictionaries").disabled = state.busy;
  $("use-dictionaries").textContent = "Turn off all AI";
}

function renderLexicalSettings() {
  const config = state.config?.lexical;
  if (!config) return;
  const greekCorpus = config.greek_corpus?.grammars.includes($("grammar").value);
  if (!lexicalSupported()) $("lexical-mode").value = "off";
  if (["model", "assisted"].includes($("lexical-mode").value) && !config.provider.configured) $("lexical-mode").value = dictionaryMode();
  if ($("lexical-mode").value === "jev" && !config.selection?.configured) $("lexical-mode").value = dictionaryMode();
  $("lexical-mode").disabled = state.busy || !lexicalSupported();
  $("lexical-mode").querySelector('[value="assisted"]').disabled = !config.provider.configured || state.inputMode === "dialogue";
  if (state.inputMode === "dialogue" && $("lexical-mode").value === "assisted") $("lexical-mode").value = greekCorpus ? dictionaryMode() : "model";
  $("lexical-mode").querySelector('[value="model"]').disabled = greekCorpus || !config.provider.configured;
  $("lexical-mode").querySelector('[value="dictionary"]').disabled = greekCorpus || !config.dictionary?.installed;
  $("lexical-mode").querySelector('[value="corpus"]').disabled = !greekCorpus || !config.greek_corpus.installed;
  $("lexical-mode").querySelector('[value="bundled"]').disabled = greekCorpus;
  $("lexical-mode").querySelector('[value="jev"]').disabled = greekCorpus || !config.selection?.configured;
  if (greekCorpus && !["off", "corpus", "assisted"].includes($("lexical-mode").value)) $("lexical-mode").value = config.greek_corpus.installed ? "corpus" : "off";
  if (!greekCorpus && $("lexical-mode").value === "corpus") $("lexical-mode").value = config.dictionary?.installed ? "dictionary" : "bundled";
  $("greek-source-controls").hidden = !config.greek_sources?.grammars.includes($("grammar").value);
  const sourceAvailable = greekCorpus && state.inputMode !== "dialogue" && $("lexical-mode").value === "assisted" && config.provider.configured;
  $("live-greek-sources").disabled = state.busy || !sourceAvailable;
  $("greek-source-corpus").disabled = state.busy || !sourceAvailable || !$("live-greek-sources").checked;
  $("greek-source-help").textContent = sourceAvailable ? "Up to four forms per sentence or whole paragraph; eight seconds shared by source lookups and retries. No lookup is needed if DS completes without lexical model assistance." : "Choose Open text assistance and connect a model to enable this option. Available for sentences and paragraphs.";
  const selecting = $("lexical-mode").value === "jev";
  $("lexical-selection-description").hidden = !selecting || !lexicalSupported();
  $("lexical-selection-description").textContent = "Jev revisits word meanings as context arrives; DS checks revisions and keeps alternatives. " + ($("llm-enabled").checked ? "The analysis LLM may propose missing words using left context." : "The analysis LLM is off: no model fallback or cached model proposals will be added.");
  $("lexical-mode-badge").textContent = !lexicalSupported() || $("lexical-mode").value === "off" ? "Original lexicon" : selecting ? "Dictionary + Jev" : $("lexical-mode").value === "model" ? config.provider.model : $("lexical-mode").value === "dictionary" ? "WordNet candidates" : "Bundled extension";
  $("lexical-provider").textContent = selecting ? `${config.selection.provider} · ${config.selection.model}` : config.provider.message;
  if (greekCorpus) { $("lexical-provider").textContent = `${config.greek_corpus.source} · ${config.greek_corpus.license}`; $("lexical-mode-badge").textContent = $("lexical-mode").value === "corpus" ? "Greek corpus hypotheses" : "Original lexicon"; }
  $("lexical-coverage").textContent = lexicalSupported() ? config.coverage : "This grammar uses its original lexicon. The expansion templates currently cover native English classical and constructive DS.";
  if (greekCorpus) $("lexical-coverage").textContent = config.greek_corpus.coverage;
  if (lexicalSupported() && $("lexical-mode").value === "assisted") { $("lexical-mode-badge").textContent = "Open text · verified DS"; $("lexical-provider").textContent = config.provider.message; $("lexical-coverage").textContent = "Greek or English. Dictionary/corpus candidates plus contextual model hypotheses and bounded DS retries. All sentences count toward coverage; unsupported constructions stay incomplete."; }
  if (!lexicalSupported() || ["off", "bundled", "dictionary"].includes($("lexical-mode").value)) $("lexical-provider").textContent = "No lexical model requests";
  $("lexical-examples").replaceChildren(...(lexicalSupported() && !greekCorpus ? config.examples : []).map((text) => {
    const button = element("button", "example-chip", text); button.type = "button";
    button.addEventListener("click", () => { setInputMode("sentence"); if ($("lexical-mode").value === "off") $("lexical-mode").value = "bundled"; $("sentence").value = text; parseSentence(); });
    return button;
  }));
  const decision = state.config?.decision;
  const gates = decision?.grammars?.[$("grammar").value] || {};
  const enabled = decision?.configured && (gates.entry || gates.fanout);
  $("decision-mode").querySelector('[value="jev"]').disabled = !enabled;
  if (!enabled && $("decision-mode").value === "jev") $("decision-mode").value = "off";
  const evaluated = Object.values(gates.evaluation || {});
  const noBenefit = evaluated.length && evaluated.every((row) => row.replay_backtracks >= row.baseline_backtracks);
  $("decision-status").textContent = !decision?.configured ? "Jev key not configured" : enabled ? `${decision.model} · calibrated ${gates.entry ? "lexical" : ""}${gates.entry && gates.fanout ? " and " : ""}${gates.fanout ? "tree" : ""} preferences` : evaluated.length ? noBenefit ? "Evaluated: no search benefit in the current sample · normal DS order retained" : "Evaluated: more evidence needed before enabling preferences" : `Jev key configured via ${decision.provider} · calibration required for this grammar`;
  $("decision-description").hidden = $("decision-mode").value !== "jev";
  if ($("decision-mode").value === "off") $("decision-status").textContent = "Normal search order. " + (selecting ? "Jev word-meaning preferences are still on. " : "") + (evaluated.length ? $("decision-status").textContent : !enabled ? "Jev search ordering is unavailable until this grammar is calibrated." : "Calibrated Jev search ordering is available as an additional option.");
  renderJevControls();
  renderAssistanceControls();
  renderMethodMode();
}

function renderLiveSources(report) {
  const sources = report?.live_sources;
  $("live-source-report").hidden = !sources;
  if (!sources) return;
  $("live-source-summary").textContent = sources.words.length
    ? `${sources.items.length} observations retrieved for ${sources.words.length} forms from Triantafyllidis and Svarna (${sources.corpus}). These are candidate analyses, not necessarily the final DS path. Citations identify retrieved text; their relevance and the inferred meaning are not independently verified.`
    : "Live sources were enabled; no lookup is recorded for this sentence. Retrieval happens when a lexical model proposal is needed, for at most four forms across the request.";
  if (sources.skipped?.length) $("live-source-summary").textContent += ` Retrieval word limit reached; no live lookup for: ${sources.skipped.join(", ")}.`;
  $("live-source-words").replaceChildren(...sources.words.map(word => {
    const details = element("details", "lexical-entry source-word");
    details.append(element("summary", "", `${word.surface} · observations and inferred analyses`));
    details.append(element("p", "", "Dictionary queries: " + word.lemma_queries.map(q => `${q.query} (${q.basis})`).join("; ") + (word.lemma_alternatives_truncated ? ". Additional lemma alternatives exceeded the lookup limit." : ".")));
    for (const lookup of word.lookups) {
      const status = {found: "examples/entries retrieved", no_results: "no matching results", unavailable: "source unavailable", time_limit: "retrieval time limit"}[lookup.status] || lookup.status;
      details.append(element("p", "source-note", `${lookup.source}: ${lookup.query} · ${status}${lookup.message ? ". " + lookup.message : ""}`));
    }
    const candidates = report.entries.filter(e => e.surface === word.surface && e.source === "model");
    details.append(element("h4", "", "Model inferences"));
    if (!candidates.length) details.append(element("p", "", "No model candidate was compiled for this form. Observations alone do not create a lexical entry."));
    for (const candidate of candidates) {
      details.append(element("p", "", `${candidate.lemma} → ${candidate.template} (${candidate.domains.join(", ")}). ${candidate.evidence}`));
      const cited = sources.items.filter(item => candidate.evidence_ids?.includes(item.id));
      details.append(element("p", "source-note", cited.length ? "Cites: " + cited.map(item => `${item.source} · ${item.headword || item.query}`).join("; ") : "No retrieved observation cited in support of this candidate."));
    }
    details.append(element("h4", "", "Retrieved observations"));
    for (const item of sources.items.filter(item => item.surfaces.includes(word.surface))) {
      const block = element("div", "source-observation");
      const link = element("a", "text-button", `${item.source} · ${item.headword || item.query} ↗`);
      // Source links come from fixed server adapters, never model output.
      if (/^https:\/\/(?:www\.greek-language\.gr|greek-corpus-workbench\.wonderfulhill-e1c9f1a0\.westeurope\.azurecontainerapps\.io)\//.test(item.url)) link.href = item.url;
      link.target = "_blank"; link.rel = "noopener noreferrer";
      block.append(link, element("blockquote", "", item.excerpt));
      block.append(element("p", "source-note", [item.attribution, item.corpus, item.register, item.mode, item.variety, `Retrieved ${item.fetched_at}`, item.truncated ? "Excerpt shortened; open source for full context." : "", item.data_use].filter(Boolean).join(" · ")));
      details.append(block);
    }
    return details;
  }));
}

function watchLexicalRevision(change) {
  stop(); state.readingIndex = 0; state.mode = "operations"; renderReadings(); renderTrace();
  const index = frames().findIndex((frame) => frame.kind === "backtrack" && frame.word_index === change.after_index && frame.lexical_changes?.some((item) => item.target_index === change.target_index && item.after.symbol === change.after.symbol && item.reason === change.reason));
  if (index >= 0) setIndex(index);
  document.querySelector(".workbench").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderLexicalReport(report) {
  renderLiveSources(report);
  $("lexical-report").hidden = !report || report.mode === "off" || (!report.entries.length && !report.notices.length && !report.remaining.length && !report.live_sources);
  if (!report) return;
  $("lexical-summary").textContent = `${report.entries.length} lexical ${report.entries.length === 1 ? "candidate" : "candidates"}`;
  $("lexical-status").textContent = { assisted: "LLM hypotheses · DS checks", ready: "Bundled extension", corpus: "Greek corpus hypotheses", dictionary: "WordNet candidates", jev: "Dictionary + Jev", proposed: "Model proposals", cached: "Cached model proposals", unavailable: "Source unavailable", rejected: "Proposal rejected", limited: "Expansion limit", unsupported: "Original lexicon" }[report.status] || "Original lexicon";
  if (report.mode === "assisted") $("lexical-status").textContent = report.attempts?.length ? `${report.attempts.length} model call${report.attempts.length === 1 ? "" : "s"} · DS checks` : "DS checks · no model call";
  $("lexical-notices").textContent = [...report.notices, ...(report.remaining.length ? [`Still missing: ${report.remaining.join(", ")}.`] : [])].join(" ");
  if (report.attempts?.length) $("lexical-notices").textContent += " " + report.attempts.map((a, i) => `Model attempt ${i + 1}: ${a.status}${a.trigger ? ` after ${a.trigger.kind.replaceAll("_", " ")}` : a.kind === "construction" ? " for connective interpretation" : a.kind === "vocabulary_and_construction" ? " for vocabulary and constructions" : " for missing vocabulary"}.`).join(" ");
  $("lexical-selection").hidden = !report.selection;
  if (report.selection) {
    const selection = report.selection;
    $("lexical-selection-summary").textContent = `${selection.decisions.length} lexical decisions · ${selection.live_calls} live calls · ${selection.provider}`;
    $("lexical-selection-decisions").replaceChildren(...selection.decisions.map((decision) => {
      const details = element("details", "lexical-entry");
      const preference = decision.preferred || {};
      details.append(element("summary", "", `${decision.word} · ${decision.phase === "reconsider" ? "reconsidered · " : ""}${decision.status === "preferred" ? "lexical preference" : decision.status === "uncertain" ? "context leaves alternatives open" : "normal candidate order retained"}${decision.cached ? " · cached" : ""}`));
      details.append(element("p", "", `Prefix: ${(decision.prefix || []).join(" ") || "(start of input)"}`));
      if (decision.phase === "lookup") details.append(element("p", "", `Current word: ${decision.word}. Later words were not supplied.`));
      if (preference.sense) details.append(element("p", "", `Sense: ${preference.sense.evidence}`));
      if (preference.frame) details.append(element("p", "", `Frame: ${preference.frame.template} · ${preference.frame.description}`));
      for (const [name, answer] of Object.entries(decision.answers || {})) {
        details.append(element("p", "", `${name === "sense" ? "Sense" : "Frame"} preference: ${answer.choice === "uncertain" ? "uncertain" : (100 * answer.probabilities[answer.choice]).toFixed(1) + "%"}`));
        const probabilities = element("div", "jev-probabilities");
        const criteria = decision.questions?.[name]?.criteria || {};
        for (const [choice, probability] of Object.entries(answer.probabilities || {}).sort((a, b) => b[1] - a[1])) {
          const option = criteria[choice];
          const label = typeof option === "string" ? option : option?.evidence || option?.description || choice;
          const row = element("div", "jev-probability");
          row.append(element("span", "", label), element("strong", "", `${(probability * 100).toFixed(1)}%`));
          const bar = element("progress", ""); bar.max = 1; bar.value = probability; bar.setAttribute("aria-label", label);
          row.append(bar); probabilities.append(row);
        }
        details.append(probabilities, element("p", "source-note", `Distribution confidence: ${answer.confidence?.toFixed(2) ?? "not supplied"}. These are model preferences among the supplied alternatives, not measured probabilities of a correct interpretation.`));
      }
      if (decision.error) details.append(element("p", "", decision.error));
      if (decision.gate === "request_budget") details.append(element("p", "", "Jev request budget reached; normal candidate order retained."));
      if (decision.latency_ms != null) details.append(element("p", "source-note", `${decision.cached ? "Cached answer" : "Decision request"} · ${decision.latency_ms} ms${decision.cost_usd != null ? ` · reported cost $${Number(decision.cost_usd).toFixed(6)}` : ""}`));
      return details;
    }));
    $("lexical-selection-used").textContent = selection.used.length ? `Primary DS path: ${selection.used.map((entry) => `${entry.word} → ${entry.symbol} (${entry.template})`).join("; ")}` : "No expanded entry is on the final active path.";
    $("lexical-path-updates").replaceChildren(...(selection.path_updates || []).map((change) => {
      const row = element("div", "lexical-entry");
      row.append(element("p", "", `${change.reason} after “${change.observed_prefix.join(" ")}”: ${change.before.word} · ${change.before.template} / ${change.before.symbol} → ${change.after.template} / ${change.after.symbol}`));
      const button = element("button", "text-button", "Watch this revision"); button.type = "button";
      button.addEventListener("click", () => watchLexicalRevision(change));
      row.append(button); return row;
    }));
    $("lexical-reconsiderations").hidden = !selection.revisions?.length;
    const outcomes = { revised: "Preference accepted after DS replay", retained: "Current sense retained", uncertain: "No reliable sense preference", no_viable_preference: "Preferred sense did not yield a compatible DS continuation; current tree retained", search_limit: "Reconsideration reached a search limit; current tree retained", candidate_limit: "Reconsideration reached its candidate limit; current tree retained" };
    $("lexical-revision-decisions").replaceChildren(...(selection.revisions || []).map((revision) => element("p", "", `${revision.word}, after “${revision.observed_prefix.join(" ")}”: ${outcomes[revision.status] || revision.status}.`)));
  }
  const entryViews = report.entries.map((entry) => {
    const details = element("details", "lexical-entry");
    details.append(element("summary", "", `${entry.surface} → ${entry.template} · ${entry.symbol}(${entry.domains.join(", ")}) · ${entry.source === "model" ? "model proposal" : entry.source === "dictionary" ? "WordNet candidate" : entry.source === "corpus" ? "GDT corpus hypothesis" : "bundled"}`));
    details.append(element("p", "", `Lemma: ${entry.lemma} · ${entry.morphology}. ${entry.evidence}`));
    if (entry.model) details.append(element("p", "", `${entry.provider} / ${entry.model} · ${entry.cached ? "cache reused" : "new proposal"} · ${entry.created_at}`));
    details.append(element("p", "", entry.validation), element("pre", "", entry.program.join("\n")));
    return details;
  });
  window.workbenchLayout?.groupEntries(report, entryViews) ?? $("lexical-entries").replaceChildren(...entryViews);
}

function lexicalGloss(entry) {
  return (entry.evidence || entry.lemma || entry.symbol).replace(/^Princeton WordNet 3\.0 \w+: /, "").split("; ")[0];
}

function renderJevComparison(result) {
  const comparison = result?.jev_comparison;
  $("jev-impact").hidden = !comparison;
  if (!comparison) return;
  const descriptions = {
    changed: "Jev changed a selected lexical analysis. Both DS derivations completed; compare their meanings below.",
    same: "Both runs selected the same lexical analyses. Jev supplied preferences, but the final choice did not change.",
    no_model_answer: "No usable Jev answer was available. Both runs used normal DS choices; no Jev benefit is claimed.",
    inconclusive: "At least one derivation did not complete. This comparison does not establish a successful change of interpretation."
  };
  $("jev-impact-summary").textContent = `${descriptions[comparison.status]} ${comparison.live_calls} live Jev request${comparison.live_calls === 1 ? "" : "s"}; ${comparison.valid_decisions} usable decisions.`;
  for (const [id, run] of [["jev-baseline", comparison.without_jev], ["jev-preferred", comparison.with_jev]]) {
    const panel = $(id); panel.replaceChildren(element("strong", "", run.complete ? "Complete DS derivation" : "Incomplete derivation"));
    if (run.failure?.message) panel.append(element("p", "", run.failure.message));
    for (const entry of run.used) {
      panel.append(element("p", "", `${entry.word} → “${lexicalGloss(entry)}” (${entry.template})`));
      if (entry.evidence) { const source = element("details", "source-note"); source.append(element("summary", "", "Source wording"), element("p", "", entry.evidence)); panel.append(source); }
    }
    panel.append(element("pre", "jev-meaning", run.meaning || "Meaning incomplete"));
    panel.append(element("p", "source-note", `${run.stats.backtracks_called ?? "—"} backtracks · ${run.elapsed_ms ?? "—"} ms.${id === "jev-preferred" ? " Includes model requests." : ""}`));
  }
  $("jev-impact-changes").replaceChildren(...comparison.changes.map(change => element("p", "", `Changed “${change.word}”: “${lexicalGloss(change.without_jev)}” → “${lexicalGloss(change.with_jev)}”.`)));
  const selection = result.lexical.selection;
  $("jev-journey").replaceChildren(...selection.decisions.map(decision => {
    const row = element("li", "");
    const observed = [...(decision.prefix || []), ...(decision.phase === "lookup" ? [decision.word] : [])].join(" ");
    const revision = selection.revisions?.find(r => r.target_index === decision.target_index && r.observed_prefix.join(" ") === observed);
    const answer = decision.answers?.sense;
    const preference = decision.preferred?.sense;
    const gloss = preference && lexicalGloss(preference);
    const outcome = revision?.status === "revised" ? "DS replay accepted the change." : revision?.status === "no_viable_preference" ? "DS replay found no compatible continuation yet; the current tree was retained." : revision?.status === "retained" ? "DS already used that sense." : revision ? "DS kept the current tree; inspect the revision details." : "DS kept the available alternatives.";
    row.append(element("p", "", `“${observed}” · ${preference ? `Jev preferred “${gloss}” (${(100 * answer.probabilities[answer.choice]).toFixed(1)}%).` : answer ? "Jev gave no reliable preference." : "No usable Jev answer."} ${outcome}`));
    const change = selection.path_updates?.find(r => r.target_index === decision.target_index && r.observed_prefix.join(" ") === observed && r.reason === "Jev preference validated by DS");
    if (revision?.status === "revised") {
      const target = change || selection.path_updates?.find(r => r.target_index === decision.target_index && r.observed_prefix.join(" ") === observed);
      if (target) { const button = element("button", "text-button", "Watch this revision"); button.type = "button"; button.addEventListener("click", () => watchLexicalRevision(target)); row.append(button); }
    }
    return row;
  }));
  if (!selection.decisions.length) $("jev-journey").append(element("li", "", "No ambiguous expanded entry required a Jev choice."));
  $("jev-impact-note").textContent = `${comparison.same_inventory ? "Identical lexical programs were verified in both runs." : "Lexical inventories differ; comparison is not controlled."} The tree below shows the Jev run. The baseline has a four-second search allowance. This single comparison is not an accuracy or speed benchmark.${comparison.shared_model_candidates ? ` ${comparison.shared_model_candidates} lexical-model candidates were shared by both runs.` : " No generative lexical-model candidates were needed."}`;
}

function renderMethodResult(result) {
  renderJevComparison(result);
  renderConstructionReport(result);
  const report = result.lexical, mode = report?.mode || "off";
  const selection = report?.selection, decision = result.decision;
  const modelEntries = (report?.entries || []).filter(entry => entry.source === "model");
  const modelRequests = mode === "assisted" ? report.attempts?.length || 0 : report?.model_requests || 0;
  const modelAllowed = ["assisted", "model"].includes(mode) || (mode === "jev" && report.allow_model_fallback !== false);
  const jevRequests = (selection?.live_calls || 0) + (decision?.mode === "jev" ? decision.live_calls || 0 : 0);
  const cachedJev = [...(selection?.decisions || []), ...(decision?.decisions || [])].some(item => item.cached);
  const modelUsage = modelRequests ? `${modelRequests} request${modelRequests === 1 ? "" : "s"}` : modelEntries.length ? "earlier proposals" : modelAllowed ? "no request made" : "off";
  const jevUsage = jevRequests ? `${jevRequests} request${jevRequests === 1 ? "" : "s"}` : cachedJev ? "cached preferences" : mode === "jev" || decision?.mode === "jev" ? "no request made" : "off";
  $("method-usage").replaceChildren(element("span", "usage-label", "This result"), element("span", "badge", "DS parser · ran"), element("span", "badge muted", `Analysis LLM · ${modelUsage}`), element("span", "badge muted", `Jev · ${jevUsage}`));
  const notes = [];
  let title = "No LLM used";
  if (mode === "assisted") {
    const count = report.attempts?.length || 0;
    title = count ? `LLM assistance · ${count} model request${count === 1 ? "" : "s"}` : "No model request made";
    const constructionCalls = report.attempts?.filter(a => a.kind === "construction").length || 0;
    const combinedCalls = report.attempts?.filter(a => a.kind === "vocabulary_and_construction").length || 0;
    notes.push(count ? `${count - constructionCalls - combinedCalls} vocabulary request(s), ${constructionCalls} construction request(s), ${combinedCalls} combined request(s). The selected model proposed analyses; DS built and checked the derivation.` : result.complete ? "DS completed with the grammar and available lexical candidates. The selected analysis model was not called to review the meaning." : "No model request was made, and DS did not complete the derivation. Inspect the failure and assistance notices below.");
    if (state.paragraph && count) notes.push("Assistance counts are shared across this paragraph and reported up to this sentence.");
    if (report.attempts?.some(attempt => attempt.status === "unavailable")) notes.push("A model request was unavailable; further requests stopped.");
    if (report.live_sources?.words.length) notes.push(`Live lexical retrieval supplied ${report.live_sources.items.length} observations. Inspect Why this analysis? for source failures, quotations and model inferences.`);
  } else if (mode === "model" && (modelRequests || modelEntries.length || ["rejected", "unavailable"].includes(report.status))) {
    const reused = !modelRequests && (report.status === "cached" || (report.status === "ready" && modelEntries.every(entry => entry.cached || entry.reused)));
    title = reused ? "Earlier LLM proposals used" : "Lexical model assistance";
    notes.push(reused ? "DS used cached or earlier paragraph lexical proposals; no new vocabulary request was needed for this sentence." : "A lexical model request supplied proposals or returned a reported error. DS determines completion.");
  } else if (mode === "jev") {
    title = "Jev vocabulary mode";
    notes.push(selection ? `${selection.live_calls} live Jev requests; ${selection.decisions.length} recorded lexical decisions (which may include cached preferences).` : "No Jev lexical decision was recorded.");
    if (modelEntries.length) notes.push("Lexical-model fallback candidates were also supplied; their provenance appears below.");
    if (report.model_requests) notes.push(`${report.model_requests} analysis LLM request(s) for missing words; unsuccessful proposals remain reported below.`);
    if (report.allow_model_fallback === false) notes.push("The analysis LLM was off, including its missing-word fallback.");
  } else {
    notes.push({off: "DS ran with the original grammar lexicon.", bundled: "DS ran with the grammar and bundled vocabulary.", dictionary: "DS ran with the grammar, bundled vocabulary and WordNet candidates.", corpus: "DS ran with the Standard Greek grammar and corpus lexical candidates."}[mode] || "DS ran with the available lexical entries.");
  }
  if (decision?.mode === "jev") {
    title = title === "No LLM used" || title === "No model request made" ? "Jev search ordering requested" : title + " · Jev search";
    notes.push(`${decision.live_calls || 0} live requests for Jev search ordering. ` + (decision.active ? "Jev preferences ordered choices; inspect Search decisions for details." : "Normal DS order was retained."));
  }
  notes.push(result.complete ? "Complete means the grammar’s requirements were satisfied under the displayed lexical and context assumptions." : "The derivation is incomplete; assistance does not turn a failed DS analysis into a verified one.");
  $("method-result").hidden = false;
  $("method-result-title").textContent = title;
  $("method-result-detail").textContent = notes.join(" ");
}

function renderConstructionReport(result) {
  const used = result.clause_constructions || [], proposals = result.lexical?.constructions || [];
  const attempts = (result.lexical?.attempts || []).filter(a => ["construction", "vocabulary_and_construction"].includes(a.kind));
  $("construction-report").hidden = !used.length && !proposals.length && !attempts.length;
  $("construction-summary").textContent = attempts.length
    ? `${attempts.length} construction model request(s). ${result.complete ? "The final DS derivation completed." : "The DS derivation remains incomplete."} Proposals and actual choices are shown separately.`
    : "The grammar supplied these clause constructions without a construction model request.";
  $("construction-proposals").replaceChildren(...proposals.map(p => {
    const details = element("details", "lexical-entry");
    details.append(element("summary", "", `Model proposed: ${p.surface} → ${p.relation.replaceAll("_", " ")}`));
    details.append(element("p", "", p.evidence), element("p", "", `${p.provider || "Model"} / ${p.model || ""}. ${p.added_programs} new programs; ${p.alternatives_retained} alternative programs retained.`), element("p", "", p.validation), element("pre", "", p.programs.map(lines => lines.join("\n")).join("\n\n")));
    return details;
  }));
  for (const a of attempts.filter(a => a.status !== "compiled")) $("construction-proposals").append(element("p", "", `Construction request: ${a.status.replaceAll("_", " ")}${a.message ? " · " + a.message : " · no reading preference installed"}.`));
  $("construction-used").replaceChildren(...used.map(c => element("p", "", `${result.complete ? "DS used" : "Accepted prefix used"}: “${c.surface}” → ${c.relation.replaceAll("_", " ")} · ${c.template}. ${c.description}`)));
}

function renderDiagnostics(result) {
  if (result.failure) {
    const inspect = element("button", "text-button", "Inspect failure ↗");
    inspect.type = "button"; inspect.id = "inspect-failure";
    inspect.addEventListener("click", () => {
      $("result-evidence").open = true;
      $("result-evidence").scrollIntoView({behavior: "smooth", block: "start"});
      $("result-evidence").querySelector("summary").focus();
    });
    $("inspect-failure")?.remove();
    if (!$("message").hidden) $("message").append(inspect);
  }
  renderMethodResult(result);
  renderLexicalReport(result.lexical);
  const decision = result.decision;
  $("decision-report").hidden = !decision || decision.mode === "off";
  if (decision) {
    $("decision-summary").textContent = `${decision.decisions.length} choices · ${decision.active ? "Jev ordering" : decision.mode === "stub" ? "local recording" : "normal DS order"}`;
    $("decision-entries").replaceChildren(element("p", "", decision.limits), ...decision.decisions.map((item) => {
      const answer = Object.values(item.answers || {})[0];
      const label = item.stub ? `Normal order retained${item.gate ? " · " + item.gate.replaceAll("_", " ") : ""}` : Object.entries(answer?.probabilities || {}).map(([candidate, probability]) => `${candidate}: ${(100 * probability).toFixed(1)}%`).join(" · ");
      return element("p", "", `Word ${item.word_index + 1} · ${item.idea === 1 ? "lexical entries" : "tree continuations"} · ${label}`);
    }));
  }
  const report = result.diagnostics;
  $("diagnostics").hidden = !report;
  if (!report) return;
  const titles = { search_limit: "Search limit reached", lexicon_gap: "Missing lexical entry", construction_gap: "Construction outside fragment", constraint_violation: "Grammar constraint violated", pcc_violation: "Person–Case Constraint (PCC)", semantic_type_mismatch: "Semantic type mismatch", unresolved_parse_failure: "No derivation · cause unassessed", missing_context: "Missing repair context", repair_unavailable: "Local repair unavailable", context_boundary: "Tree boundary needed" };
  $("diagnosis-title").textContent = result.failure ? titles[result.failure.kind] || "Parse stopped" : result.complete ? "Complete derivation" : "Incomplete derivation";
  $("diagnosis-detail").textContent = result.failure ? `Stopped at token ${result.failure.index + 1}: “${result.failure.token}”. The accepted prefix remains available in the tree.` : result.pending_repair ? "The repair marker is waiting for replacement words." : result.complete ? "All tree requirements are satisfied in this grammar." : "The input was accepted, but a current or earlier tree has open requirements.";
  if (result.failure?.kind === "search_limit") $("diagnosis-detail").textContent = result.failure.message;
  if (report.grammar_constraint) $("diagnosis-detail").textContent = report.grammar_constraint.explanation + " Basis: " + report.grammar_constraint.source;
  const missing = report.lexical_coverage.filter((word) => !word.known);
  $("lexicon-summary").textContent = missing.length ? `Missing: ${[...new Set(missing.map((word) => word.token))].join(", ")}` : report.lexical_coverage.some((word) => word.source === "parser_control") ? "Every token recognized · includes parser controls" : "Every token has an entry";
  $("vocabulary-report").replaceChildren(...report.lexical_coverage.map((word) => element("span", word.known ? "vocab-known" : "vocab-missing", `${word.token} ${word.source === "parser_control" ? "· parser control" : word.source === "model" ? "· proposed" : word.source === "bundled" ? "· extension" : word.known ? "✓" : "— missing"}`)));
  $("vocabulary-report").append(element("p", "", "Lexical lookup covers the whole input, including tokens the parser did not reach."));
  const judgment = report.judgment;
  $("judgment-title").textContent = { not_assessed: "Grammaticality not assessed", licensed_pattern: "Sourced placement pattern", excluded_in_described_variety: "Unlicensed in the described variety" }[judgment.status];
  $("judgment-detail").textContent = judgment.status === "not_assessed" ? judgment.explanation : `${judgment.scope} Source: ${judgment.source.author}, historical clitic chapter; comparison ${judgment.case}.`;
}

function showGreekCase(item, reverse) {
  if (state.busy) return;
  setInputMode("sentence");
  if ($("system").value === "ttr") { $("system").value = "classical"; selectSystem(); }
  $("grammar").value = `2026-${item.dialect}-${$("system").value}`;
  updateGrammar(); $("sentence").value = reverse ? item.reverse : item.sentence;
  parseSentence(); document.querySelector(".composer").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDialectCards(environment = "finite") {
  const lab = state.config.greek;
  $("dialect-cards").replaceChildren();
  for (const dialect of [...new Set(Object.values(lab.grammars).map((info) => info.dialect))]) {
    const info = lab.grammars[`2026-${dialect}-classical`];
    const item = lab.cases.find((entry) => entry.dialect === dialect && entry.environment === environment);
    const card = element("article", "dialect-card");
    card.append(element("h3", "", info.label));
    card.append(element("code", "clitic-gate", info.gate));
    if (item) {
      card.append(element("p", "greek-sentence", item.sentence), element("p", "gloss", item.gloss), element("p", "dialect-explanation", item.explanation));
      const actions = element("div", "case-actions");
      for (const reverse of [false, true]) {
        const button = element("button", reverse ? "case-reverse" : "case-build", reverse ? `Test reverse: ${item.reverse}` : "Build this derivation ↗");
        button.type = "button"; button.dataset.greekExample = `${item.id}${reverse ? "-reverse" : ""}`;
        button.disabled = state.busy; button.addEventListener("click", () => showGreekCase(item, reverse)); actions.append(button);
      }
      card.append(actions);
    } else {
      card.append(element("p", "gloss", "No reviewed example for this environment"), element("p", "dialect-explanation", info.coverage));
    }
    $("dialect-cards").append(card);
  }
  for (const button of $("clitic-environments").children) button.setAttribute("aria-pressed", String(button.dataset.environment === environment));
}

function renderHistory(id) {
  const entry = state.config.greek.history.find((stage) => stage.id === id);
  const detail = $("history-detail"); detail.replaceChildren(element("h4", "", entry.title));
  const columns = element("div", "history-columns");
  for (const [heading, text] of [["Evidence", entry.evidence], ["Proposed DS explanation", entry.analysis]]) {
    const section = element("div"); section.append(element("strong", "evidence-label", heading), element("p", "", text)); columns.append(section);
  }
  detail.append(columns, element("code", "history-trigger", entry.trigger));
  if (entry.counts) {
    const disclosure = element("details", "corpus-counts"); disclosure.append(element("summary", "", "Inspect the Oxyrhynchus counts · observations, not rules"));
    const table = element("table"); const caption = element("caption", "", "Selected environments: pre-/postverbal tokens. Pappas (2006:323), as reproduced in the chapter.");
    const head = element("thead"), tr = element("tr"); for (const label of ["Environment", "Preverbal", "Postverbal"]) tr.append(element("th", "", label)); head.append(tr);
    const body = element("tbody"); for (const row of entry.counts) { const tr = element("tr"); row.forEach((value) => tr.append(element("td", "", value))); body.append(tr); }
    table.append(caption, head, body); disclosure.append(table); detail.append(disclosure);
  }
  for (const button of $("history-tabs").children) button.setAttribute("aria-pressed", String(button.dataset.history === id));
}

function renderGreekLab() {
  const lab = state.config.greek;
  $("greek-lab").hidden = !lab || $("workspace-tab-greek-lab").getAttribute("aria-selected") !== "true";
  if (!lab) return;
  $("clitic-environments").replaceChildren(...[["finite", "Bare finite clause"], ["negation", "Negation"], ["imperative", "Imperative"], ["na", "Na clause"]].map(([id, label]) => {
    const button = element("button", "", label); button.type = "button"; button.dataset.environment = id;
    button.addEventListener("click", () => renderDialectCards(id)); return button;
  }));
  $("history-tabs").replaceChildren(...lab.history.map((entry) => {
    const button = element("button", "", entry.label); button.type = "button"; button.dataset.history = entry.id;
    button.addEventListener("click", () => renderHistory(entry.id)); return button;
  }));
  $("greek-coverage").textContent = lab.grammars["2026-smg-classical"].coverage;
  $("other-dialects").textContent = lab.other_dialects;
  $("greek-source").textContent = `Source: ${lab.source.author}, “${lab.source.title}” (${lab.source.location}). Examples illustrate the stated weak-clitic placement patterns; adapted spellings are not historical quotations. Further detail: Chatzikyriakidis (2012), Lingua 122(6), 642–672, on Cypriot; thesis (2010), chapters 3 and 6, on Standard/Grico placement and clusters. Historical analysis is presented as a proposal, with the chapter’s corpus and regional qualifications.`;
  renderDialectCards(); renderHistory("koine");
}

function renderExamples() {
  const grammar = $("grammar").value;
  if (state.exampleGrammar !== grammar) { state.exampleGrammar = grammar; state.showAllExamples = false; }
  const examples = greekGrammar()?.examples || (/-(mltt|classical)$/.test(grammar) ? state.config.native_examples
    : grammar === "2015-english-ttr" ? state.config.examples
    : grammar === "2026-english-ttr-test" ? [{ sentence: "a man knows you", label: "The small test grammar" }]
    : grammar === "2026-english-ttr" ? [{ sentence: "a man arrives", label: "An intransitive sentence" }] : []);
  $("examples").replaceChildren(...(state.showAllExamples ? examples : examples.slice(0, 3)).map((example) => {
    const button = element("button", "", example.sentence); button.type = "button"; button.title = example.label;
    button.addEventListener("click", () => { $("sentence").value = example.sentence; parseSentence(); }); return button;
  }));
  if (!examples.length) $("examples").append(element("span", "", "No preset examples for this grammar."));
  $("all-examples").hidden = examples.length <= 3;
  $("all-examples").textContent = state.showAllExamples ? "Fewer examples" : `All ${examples.length} examples`;
  $("all-examples").setAttribute("aria-expanded", String(Boolean(state.showAllExamples)));
}
$("all-examples").addEventListener("click", () => { state.showAllExamples = !state.showAllExamples; renderExamples(); });
$("grammar").addEventListener("change", () => {
  stop(); updateGrammar();
  if (state.inputMode === "dialogue") setDialogue(dialogueExamples()[0]?.turns || [{speaker:"A",text:""}]);
  $("sentence").value = greekGrammar()?.examples[0]?.sentence || ($("system").value === "ttr" ? "a man knows you." : "a man walks.");
  parseSentence();
});

function selectSystem() {
  stop();
  const previous = greekGrammar();
  const system = state.config.systems.find((item) => item.id === $("system").value);
  $("grammar").replaceChildren(...system.grammars.map((id) => {
    const option = element("option", "", state.config.greek?.grammars[id]?.label || (/^2026-english-(mltt|classical)$/.test(id) ? "English" : id.replace("2026-english-", "English · ").replace("2015-english-ttr", "English · TTR (2015)")));
    option.value = id; return option;
  }));
  const paired = previous && `2026-${previous.dialect}-${system.id}`;
  if (system.grammars.includes(paired)) $("grammar").value = paired;
  else $("sentence").value = system.id === "ttr" ? "a man knows you." : "a man walks.";
  updateGrammar();
  if (state.inputMode === "dialogue" && previous && !system.grammars.includes(paired)) setDialogue(dialogueExamples()[0].turns);
}
$("system").addEventListener("change", () => { selectSystem(); parseSentence(); });
$("scope").addEventListener("change", parseSentence);
$("n-best").addEventListener("change", parseSentence);
$("reading").addEventListener("change", () => {
  stop(); state.readingIndex = Number($("reading").value); state.expandedFormulas = [];
  state.index = 0; state.selected = "0"; state.view = null;
  renderTrace(); render(); play();
});
$("lexical-mode").addEventListener("change", renderLexicalSettings);
$("llm-enabled").addEventListener("change", () => changeAssistance("llm"));
$("jev-enabled").addEventListener("change", () => changeAssistance("jev"));
$("model-settings-button").addEventListener("click", () => { stop(); $("lexical-settings").open = true; $("models-dialog").showModal(); });
$("models-close").addEventListener("click", () => $("models-dialog").close());
$("compare-jev").addEventListener("change", renderLexicalSettings);
$("jev-run").addEventListener("click", runJevComparison);
$("show-final").addEventListener("click", () => setIndex(frames().length - 1));
$("jev-demo-button").addEventListener("click", () => { $("jev-demo").open = true; $("jev-demo").scrollIntoView({behavior: "smooth", block: "center"}); });
$("live-greek-sources").addEventListener("change", renderLexicalSettings);
$("greek-source-corpus").addEventListener("change", renderMethodMode);
$("decision-mode").addEventListener("change", renderLexicalSettings);
$("speed").addEventListener("change", () => { if (state.timer) { stop(); play(); } });
$("coq").addEventListener("click", () => {
  if (!selectedCoq()) return;
  const url = URL.createObjectURL(new Blob([selectedCoq()], { type: "text/plain" }));
  const link = element("a"); link.href = url; link.download = "ds_meaning.v"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

async function boot() {
  updateControls();
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error("The Python API did not respond.");
    const config = await response.json();
    state.config = config;
    window.openrouterControls?.init(config);
    if (config.lexical?.dictionary?.installed) $("lexical-mode").value = "dictionary";
    $("system").replaceChildren(...config.systems.map((system) => {
      const option = element("option", "", system.label.replace(" DS", "")); option.value = system.id; return option;
    }));
    selectSystem();
    renderGreekLab();
    renderExamples();
    $("connection").replaceChildren(element("span", "status-dot"), document.createTextNode("Python engine connected"));
    $("connection").classList.add("connected");
    $("parse-button").disabled = false; $("grammar").disabled = false; $("system").disabled = false;
    await parseSentence({reveal: false});
  } catch {
    $("connection").replaceChildren(element("span", "status-dot"), document.createTextNode("Engine unavailable"));
    message("The Python engine is unavailable. Start it with: python -m dylan.workbench_server", true);
  }
}
boot();
