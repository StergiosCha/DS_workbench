"use strict";

const research = { result: null, selected: null, loaded: null, pendingSource: null, catalog: [], catalogRun: 0, searchRun: 0, dictionaryRun: 0, searchBusy: false };
const corpusNames = { grdd_cretan: "Cretan", grdd_cypriot: "Cypriot", grdd_pontic: "Pontic", grdd_tsakonian: "Tsakonian", grdd_griko: "Griko", grdd_northern: "Northern Greek", grdd_eptanisian: "Eptanisian", grdd_maniot: "Maniot", grdd_katharevousa: "Katharevousa" };
const corpusName = (value) => corpusNames[value] || value;
const researchLanguage = () => $("research-language").value;
const researchEndpoint = (name) => (researchLanguage() === "en" ? "english/" : "") + name;
const researchSourceName = () => researchLanguage() === "en" ? "the local corpus" : "Svarna";

async function researchGet(path, params = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 35000);
  try {
    const response = await fetch(`/api/research/${path}?${new URLSearchParams(params)}`, { signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The source could not return results.");
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The source took too long. Choose a smaller corpus or narrow the query.");
    throw error;
  } finally { clearTimeout(timer); }
}

function researchLink(text, url) {
  const link = element("a", "text-button", text);
  link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
  return link;
}

function researchDownload(data, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const link = element("a"); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function filterOptions(id, values, title) {
  const options = [new Option(title, ""), ...[...new Set(values)].filter(Boolean).sort().map(v => new Option(id === "corpus-filter" ? corpusName(v) : v, v))];
  $(id).replaceChildren(...options);
}

async function loadCorpusCatalog() {
  const run = ++research.catalogRun;
  const db = $("corpus-db").value;
  $("corpus-reload").hidden = true;
  $("corpus-catalog-status").textContent = "Loading corpus filters…";
  for (const id of ["corpus-filter", "corpus-register", "corpus-mode"]) $(id).disabled = true;
  research.catalog = [];
  const documentTitle = researchLanguage() === "en" ? "All documents / books" : "All corpora / varieties";
  const registerTitle = researchLanguage() === "en" ? "All genres" : "All registers";
  filterOptions("corpus-filter", [], documentTitle);
  filterOptions("corpus-register", [], registerTitle);
  filterOptions("corpus-mode", [], "All modes");
  try {
    const result = await researchGet(researchEndpoint("corpora"), { db });
    if (run !== research.catalogRun) return;
    research.catalog = result.stats;
    for (const row of result.stats) if (row.label) corpusNames[row.corpus] = row.label;
    filterOptions("corpus-filter", result.stats.map(r => r.corpus), documentTitle);
    filterOptions("corpus-register", result.stats.map(r => r.register), registerTitle);
    filterOptions("corpus-mode", result.stats.map(r => r.mode), "All modes");
    $("corpus-catalog-status").textContent = researchLanguage() === "en" ? `${result.stats.length} documents · ${result.stats.reduce((n, row) => n + row.sentence_count, 0).toLocaleString()} sentence units in the local index.` : `${new Set(result.stats.map(r => r.corpus)).size} corpora available. Filters come from Svarna.`;
  } catch (error) {
    if (run !== research.catalogRun) return;
    $("corpus-catalog-status").textContent = error.message;
    $("corpus-reload").hidden = false;
  } finally {
    if (run === research.catalogRun) for (const id of ["corpus-filter", "corpus-register", "corpus-mode"]) $(id).disabled = !research.catalog.length;
  }
}

function invalidateCorpusSearch() {
  ++research.searchRun; research.searchBusy = false; research.result = null;
  $("corpus-search").disabled = false; $("corpus-export").disabled = true;
  $("corpus-results").replaceChildren(); $("corpus-page").textContent = "";
  $("corpus-previous").disabled = true; $("corpus-next").disabled = true;
  $("corpus-status").textContent = "Search to find examples with these settings.";
}

function corpusParameters() {
  return { db: $("corpus-db").value, q: $("corpus-query").value.trim(), kind: $("corpus-kind").value,
    corpus: $("corpus-filter").value, register: $("corpus-register").value, mode: $("corpus-mode").value };
}

async function searchCorpus(offset = 0) {
  const params = corpusParameters();
  if (!params.q) { $("corpus-query").focus(); return; }
  if (params.kind === "regex" && !params.corpus && !(researchLanguage() === "en" && params.register)) { $("corpus-status").textContent = researchLanguage() === "en" ? "Choose a document, book or genre for a regex search." : "Choose one corpus or variety for a regex search."; $("corpus-filter").focus(); return; }
  const run = ++research.searchRun;
  research.searchBusy = true; research.result = null;
  $("corpus-search").disabled = true; $("corpus-export").disabled = true;
  $("corpus-previous").disabled = true; $("corpus-next").disabled = true;
  $("corpus-status").textContent = `Searching ${researchSourceName()}…`; $("corpus-page").textContent = "";
  $("corpus-results").replaceChildren();
  try {
    const result = await researchGet(researchEndpoint("search"), { ...params, offset: String(offset), limit: "20" });
    if (run !== research.searchRun) return;
    research.result = result;
    $("corpus-status").textContent = result.total ? `${result.total.toLocaleString()} matching ${result.language === "en" ? "sentence units" : "sentences"}${result.total_is_exact ? "" : " reported (scan may be capped)"}.` : "No matching sentences for this query and these filters.";
    $("corpus-results").replaceChildren(...result.results.map(row => renderCorpusRow(row, result)));
    $("corpus-results").append(element("p", "source-note", result.note));
    $("corpus-page").textContent = result.results.length ? `${offset + 1}–${offset + result.results.length}` : "";
    $("corpus-previous").disabled = offset === 0; $("corpus-next").disabled = !result.has_more;
    $("corpus-export").disabled = false;
  } catch (error) {
    if (run === research.searchRun) $("corpus-status").textContent = error.message;
  } finally {
    if (run === research.searchRun) { research.searchBusy = false; $("corpus-search").disabled = false; }
  }
}

function renderCorpusRow(row, result) {
  const card = element("article", "corpus-result");
  const meta = [row.label || corpusName(row.corpus), row.register, row.mode, row.year].filter(Boolean).join(" · ");
  card.append(element("p", "source-note", meta));
  const sentence = element("p", "corpus-text"); sentence.lang = result.language || "el";
  // Use the full source text, not a reconstructed/truncated KWIC sentence.
  const match = row.keyword || row.match || "";
  const index = match ? Number.isInteger(row.match_start) ? row.match_start : row.full_text.indexOf(match) : -1;
  if (index >= 0) sentence.append(document.createTextNode(row.full_text.slice(0, index)), element("mark", "", match), document.createTextNode(row.full_text.slice(index + match.length)));
  else sentence.textContent = row.full_text;
  const controls = element("div", "corpus-result-actions");
  const select = element("button", "text-button", "Select example →"); select.type = "button";
  select.addEventListener("click", () => selectCorpusExample(row, result));
  const word = element("button", "text-button", "Look up selected word"); word.type = "button";
  // Capture selection before a pointer click moves focus away from the sentence.
  let selectedWord = "";
  word.addEventListener("pointerdown", () => { const selection = window.getSelection(); selectedWord = selection && sentence.contains(selection.anchorNode) && sentence.contains(selection.focusNode) ? selection.toString().trim() : ""; });
  word.addEventListener("click", () => {
    const selection = window.getSelection();
    const text = selectedWord || (selection && sentence.contains(selection.anchorNode) && sentence.contains(selection.focusNode) ? selection.toString().trim() : "");
    selectedWord = "";
    if (!text || text.length > 160) { $("dictionary-status").textContent = "Select a word in this example first, or type its lemma above."; $("dictionary-query").focus(); return; }
    $("dictionary-query").value = text; $("dictionary-scope").value = "headword"; lookupDictionary();
  });
  controls.append(select, word); card.append(sentence, controls);
  return card;
}

function selectCorpusExample(row, result) {
  research.selected = { source: result.source || "Svarna", language: result.language || "el", source_url: row.source_url || result.source_url, search_url: result.source_url, fetched_at: result.fetched_at,
    db: result.db, query: result.query, search_kind: result.kind, filters: result.filters, observation: row };
  $("research-selection").hidden = false;
  $("selected-corpus-meta").textContent = `${corpusName(row.corpus)} · ${row.register} · ${row.mode}`;
  $("selected-corpus-original").textContent = row.full_text;
  $("selected-corpus-original").lang = research.selected.language;
  $("selected-corpus-details").textContent = JSON.stringify(research.selected, null, 2);
  $("selected-corpus-text").value = row.full_text;
  const systems = [new Option("Constructive · Σ / Π", "mltt"), new Option("Classical · λ / ε / τ", "classical")];
  if (research.selected.language === "en") systems.push(new Option("DS-TTR · records", "ttr"));
  $("selected-corpus-system").replaceChildren(...systems);
  $("selected-corpus-system").value = research.selected.language === "en" ? $("system").value : $("system").value === "classical" ? "classical" : "mltt";
  configureComparisonGrammar();
  // GRDD Griko includes material not identified as the Salentino grammar's fragment.
  if (research.selected.language !== "en") $("selected-corpus-grammar").value = { grdd_cypriot: "cypriot", grdd_pontic: "pontic" }[row.corpus] || "";
  updateResearchSelection(); $("research-selection").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function configureComparisonGrammar() {
  if (!research.selected) return;
  const previous = $("selected-corpus-grammar").value;
  let choices;
  if (research.selected.language === "en") {
    choices = $("selected-corpus-system").value === "ttr" ? (state.config?.systems.find(s => s.id === "ttr")?.grammars || []).filter(id => id.includes("english")).map(id => new Option(id, id)) : [new Option("English", "english")];
  } else choices = [new Option("Choose a Greek grammar…", ""), new Option("Standard Modern Greek", "smg"), new Option("Cypriot Greek", "cypriot"), new Option("Pontic Greek", "pontic"), new Option("Grico (Salentino Greek)", "grico")];
  $("selected-corpus-grammar").replaceChildren(...choices);
  if (choices.some(c => c.value === previous)) $("selected-corpus-grammar").value = previous;
  else if (choices.some(c => c.value === "2015-english-ttr")) $("selected-corpus-grammar").value = "2015-english-ttr";
}

function comparisonGrammarId() {
  const system = $("selected-corpus-system").value, grammar = $("selected-corpus-grammar").value;
  return system === "ttr" ? grammar : `2026-${grammar}-${system}`;
}

function updateResearchSelection() {
  if (!research.selected) return;
  const text = $("selected-corpus-text").value.trim();
  const grammar = $("selected-corpus-grammar").value;
  const changed = text !== research.selected.observation.full_text.trim();
  const words = text ? text.split(/\s+/u).length : 0;
  const messages = [`${text.length}/500 characters · ${words}/40 whitespace-separated tokens.`, changed ? "Edited excerpt; the original is preserved." : "Original source text."];
  if (!grammar) messages.push("Choose a comparison grammar; the corpus label alone does not select one.");
  if (text.length > 500 || words > 40) messages.push("Select a shorter excerpt to fit the parser’s limits.");
  if (state.busy) messages.push("Wait for the current derivation to finish.");
  const available = state.config?.grammars.includes(comparisonGrammarId());
  $("selected-corpus-analyse").disabled = !text || !available || text.length > 500 || words > 40 || state.busy;
  $("selected-corpus-note").textContent = messages.join(" ");
}

function researchSourceFor(sentence) {
  return state.inputMode === "sentence" && research.loaded?.analysed_text === sentence ? { ...structuredClone(research.loaded), comparison_grammar: $("grammar").value } : null;
}

function renderResearchProvenance(source) {
  $("research-provenance").hidden = !source;
  if (!source) return;
  $("research-provenance").replaceChildren(document.createTextNode(`${source.source} · ${source.observation.label || corpusName(source.observation.corpus)} · ${source.edited ? "edited excerpt" : source.language === "en" ? "source text" : "original text"} · compared using ${source.comparison_grammar}. `), researchLink(source.language === "en" ? "Source passage ↗" : "Source search ↗", source.source_url));
}

$("selected-corpus-analyse").addEventListener("click", () => {
  if (state.busy || !research.selected) return;
  const sentence = $("selected-corpus-text").value.trim();
  const grammar = comparisonGrammarId();
  if (!state.config.grammars.includes(grammar) || !sentence || sentence.length > 500 || sentence.split(/\s+/u).length > 40) return;
  setInputMode("sentence"); $("system").value = $("selected-corpus-system").value; selectSystem();
  $("grammar").value = grammar; updateGrammar(); $("sentence").value = sentence;
  research.loaded = { ...structuredClone(research.selected), analysed_text: sentence,
    edited: sentence !== research.selected.observation.full_text.trim(), comparison_grammar: grammar };
  // A corpus lookup does not automatically enable model calls.
  if (research.selected.language === "en") $("lexical-mode").value = state.config.lexical?.dictionary?.installed ? "dictionary" : "bundled";
  $("decision-mode").value = "off";
  renderLexicalSettings();
  parseSentence(); $("parse-form").scrollIntoView({ behavior: "smooth", block: "start" });
});

async function lookupDictionary() {
  const q = $("dictionary-query").value.trim();
  if (!q) { $("dictionary-query").focus(); return; }
  const run = ++research.dictionaryRun;
  $("dictionary-search").disabled = true; $("dictionary-status").textContent = "Looking up the published entry…";
  $("dictionary-results").replaceChildren();
  const params = { q, scope: $("dictionary-scope").value };
  const english = researchLanguage() === "en";
  const url = new URL(english ? "https://wordnet.princeton.edu/" : "https://www.greek-language.gr/greekLang/modern_greek/tools/lexica/triantafyllides/search.html");
  url.search = new URLSearchParams({ lq: q, dq: "", ...(params.scope === "entry" ? { loptall: "true" } : {}) });
  $("dictionary-source").href = english ? "https://wordnet.princeton.edu/" : url;
  try {
    const result = await researchGet(researchEndpoint("dictionary"), params);
    if (run !== research.dictionaryRun) return;
    $("dictionary-status").textContent = result.total ? `${result.entries.length} of ${result.total} ${english ? "senses" : "entries"} shown.${result.has_more ? english ? " Narrow the query to see other senses." : " Open the dictionary for the remaining results." : ""}` : english ? "No noun or verb sense found. Try a lemma or definition search." : "No entry found. Try the lemma or whole-entry search. Dialect words may be absent.";
    for (const entry of result.entries) {
      const details = element("details", "dictionary-entry"); details.open = result.entries.length === 1;
      details.append(element("summary", "", entry.pos ? `${entry.headword} · ${entry.pos} · ${entry.synset}` : entry.headword));
      const text = element("p", "dictionary-text", entry.text); text.lang = english ? "en" : "el";
      if (entry.synonyms?.length) details.append(element("p", "source-note", `Synset words: ${entry.synonyms.join(", ")}`));
      if (entry.inflection) details.append(element("p", "source-note", `Match: ${entry.inflection.replaceAll("_", " ")}`));
      if (entry.frames?.length) { const frames = element("ul", "wordnet-frames"); for (const frame of entry.frames) frames.append(element("li", "", `${frame.id}: ${frame.text}`)); details.append(frames); }
      const find = element("button", "text-button", english ? "Search this lemma in the corpus" : "Search this headword in Svarna"); find.type = "button";
      find.addEventListener("click", () => { $("corpus-query").value = entry.headword; $("corpus-kind").value = "words"; updateSearchHelp(); searchCorpus(); });
      details.append(text, researchLink(english ? "About WordNet ↗" : "Published entry ↗", entry.url), find); $("dictionary-results").append(details);
    }
    $("dictionary-results").append(element("p", "source-note", result.attribution), element("p", "source-note", result.note));
  } catch (error) {
    if (run === research.dictionaryRun) $("dictionary-status").textContent = error.message;
  } finally { if (run === research.dictionaryRun) $("dictionary-search").disabled = false; }
}

function updateSearchHelp() {
  const english = researchLanguage() === "en";
  $("corpus-search-help").textContent = $("corpus-kind").value === "regex" ? english ? "Regex searches within one document, book or genre, with a 15-second time limit." : "Regex searches source text within one corpus or variety. Scans may be slow or capped; they do not identify grammatical constructions." : english ? "Literal words/phrases use the local word index. Case is ignored; inflected forms are searched separately." : "Words and phrases use Svarna’s word index. Inflected forms are searched separately.";
}

function selectResearchLanguage() {
  const english = researchLanguage() === "en";
  invalidateCorpusSearch(); ++research.dictionaryRun; research.selected = null;
  $("research-selection").hidden = true; $("dictionary-results").replaceChildren(); $("dictionary-search").disabled = false;
  $("dictionary-status").textContent = "Look up a lemma, or select a word in a corpus example.";
  $("corpus-db").replaceChildren(...(english ? [new Option("Brown · general English", "brown"), new Option("Gutenberg · literature", "gutenberg")] : [new Option("Greek varieties", "dialectal"), new Option("General Greek", "corpus"), new Option("Literature", "literature")]));
  $("corpus-query").value = english ? "bank" : "ατό"; $("corpus-kind").value = "words";
  $("dictionary-query").value = english ? "bank" : "δίνω";
  $("dictionary-scope").replaceChildren(new Option(english ? "Words / lemmas" : "Headwords", "headword"), new Option(english ? "Definitions" : "Whole entries", "entry"));
  $("dictionary-title").textContent = english ? "WordNet dictionary" : "Triantafyllidis dictionary";
  $("dictionary-description").textContent = english ? "Local noun and verb senses, synset words, examples and verb frames." : "Standard Modern Greek senses, forms, and examples. Dialect words may have no entry.";
  $("dictionary-source").href = english ? "https://wordnet.princeton.edu/" : "https://www.greek-language.gr/greekLang/modern_greek/tools/lexica/triantafyllides/";
  $("corpus-filter-label").textContent = english ? "Document / book" : "Corpus / variety";
  $("corpus-register-label").textContent = english ? "Genre" : "Register";
  $("corpus-search").textContent = english ? "Search corpus" : "Search Svarna";
  $("corpus-home").textContent = english ? "About the corpora ↗" : "Open Svarna ↗";
  $("corpus-home").href = english ? "https://www.nltk.org/nltk_data/" : "https://greek-corpus-workbench.wonderfulhill-e1c9f1a0.westeurope.azurecontainerapps.io/";
  $("research-language-note").textContent = english ? "Local corpora and WordNet. No model key needed." : "Live Greek and dialectal sources.";
  updateSearchHelp(); loadCorpusCatalog();
}

$("research-language").addEventListener("change", selectResearchLanguage);
$("selected-corpus-system").addEventListener("change", () => { configureComparisonGrammar(); updateResearchSelection(); });

$("corpus-form").addEventListener("submit", e => { e.preventDefault(); searchCorpus(); });
$("dictionary-form").addEventListener("submit", e => { e.preventDefault(); lookupDictionary(); });
$("corpus-db").addEventListener("change", () => { invalidateCorpusSearch(); loadCorpusCatalog(); });
for (const id of ["corpus-query", "corpus-filter", "corpus-register", "corpus-mode", "corpus-kind"]) $(id).addEventListener(id === "corpus-query" ? "input" : "change", () => { invalidateCorpusSearch(); updateSearchHelp(); });
for (const id of ["dictionary-query", "dictionary-scope"]) $(id).addEventListener(id === "dictionary-query" ? "input" : "change", () => { ++research.dictionaryRun; $("dictionary-search").disabled = false; $("dictionary-results").replaceChildren(); $("dictionary-status").textContent = "Look up to search with these settings."; });
$("corpus-reload").addEventListener("click", loadCorpusCatalog);
$("corpus-previous").addEventListener("click", () => searchCorpus(Math.max(0, research.result.offset - research.result.limit)));
$("corpus-next").addEventListener("click", () => searchCorpus(research.result.offset + research.result.limit));
$("corpus-export").addEventListener("click", () => { if (research.result) researchDownload(research.result, research.result.language === "en" ? "english-corpus-results.json" : "svarna-results.json"); });
for (const id of ["selected-corpus-text", "selected-corpus-grammar", "selected-corpus-system"]) $(id).addEventListener("input", updateResearchSelection);
$("selected-corpus-reset").addEventListener("click", () => { if (research.selected) { $("selected-corpus-text").value = research.selected.observation.full_text; updateResearchSelection(); } });
// Defer external reads until the researcher reaches the panel.
const researchObserver = new IntersectionObserver(entries => {
  if (entries.some(entry => entry.isIntersecting)) { researchObserver.disconnect(); loadCorpusCatalog(); }
}, { rootMargin: "150px" });
researchObserver.observe($("research"));
