"use strict";

// Presentation only: switching areas never starts a parse or a model request.
window.workbenchLayout = (() => {
  const panels = {parse: "parse-workspace", research: "research", "greek-lab": "greek-lab", library: "library"};
  const tabs = [...document.querySelectorAll("[data-workspace]")];
  let area = "parse";

  function showPanel(name, {focus = false, history = true} = {}) {
    if (!panels[name]) return;
    if (name !== "parse") stop();
    area = name;
    for (const tab of tabs) {
      const selected = tab.dataset.workspace === name;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      $(panels[tab.dataset.workspace]).hidden = !selected;
      if (selected && focus) tab.focus();
    }
    if (history && location.hash !== `#${name}`) window.history.replaceState(null, "", `#${name}`);
    if (name === "parse" && current()) render();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showPanel(tab.dataset.workspace));
    tab.addEventListener("keydown", event => {
      const next = event.key === "ArrowRight" ? (index + 1) % tabs.length
        : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length
        : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
      if (next < 0) return;
      event.preventDefault(); showPanel(tabs[next].dataset.workspace, {focus: true});
    });
  });
  window.addEventListener("hashchange", () => showPanel(location.hash.slice(1), {history: false}));
  // Existing source/example links can still address the old section anchors.
  document.addEventListener("click", event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    const id = link.getAttribute("href").slice(1);
    if (panels[id]) { event.preventDefault(); showPanel(id, {focus: true}); }
    else if ($(id)?.closest("#result-evidence")) $("result-evidence").open = true;
  });

  const mobile = window.matchMedia("(max-width: 780px)");
  const inspector = $("inspector-drawer");
  function sizeInspector() { inspector.open = !mobile.matches; }
  sizeInspector(); mobile.addEventListener("change", sizeInspector);
  $("models-dialog").addEventListener("close", () => {
    $("lexical-settings").open = false;
    $("model-settings-button").focus();
  });

  function groupEntries(report, views) {
    const grouped = new Map();
    const used = report.selection?.used || report.used || [];
    report.entries.forEach((entry, index) => {
      if (!grouped.has(entry.surface)) grouped.set(entry.surface, []);
      const selected = used.some(item => item.word === entry.surface && item.symbol === entry.symbol && item.template === entry.template);
      grouped.get(entry.surface).push({entry, view: views[index], selected});
    });
    const groups = [...grouped].map(([word, entries]) => {
      const group = element("details", "lexical-word-group");
      group.dataset.word = word;
      const count = entries.filter(e => e.selected).length;
      group.append(element("summary", "", `${word} · ${entries.length} ${entries.length === 1 ? "candidate" : "candidates"}${count ? " · selected analysis recorded" : ""}`));
      for (const {view, selected} of entries.sort((a, b) => Number(b.selected) - Number(a.selected))) {
        if (selected) view.querySelector("summary").prepend(element("span", "badge", "Selected on DS path"));
        group.append(view);
      }
      return group;
    });
    $("lexical-entries").replaceChildren(...groups);
    return true;
  }

  const library = window.dsLibraryData;
  if (library) {
    const root = "https://github.com/StergiosCha/DS_workbench/blob/main/";
    for (const category of library.categories) {
      const option = element("option", "", category.title); option.value = category.id;
      $("library-category").append(option);
    }
    for (const [id, label] of Object.entries(library.frameworks)) {
      const option = element("option", "", label); option.value = id;
      $("library-framework").append(option);
    }
    function renderLibrary() {
      const query = $("library-query").value.trim().toLocaleLowerCase();
      const category = $("library-category").value, framework = $("library-framework").value;
      const papers = library.papers.filter(paper => {
        const b = paper.bibliographic;
        const searchable = [paper.id, b.title, ...b.author.map(a => `${a.given || ""} ${a.family || ""}`),
          b.issued["date-parts"][0][0], ...paper.tags.languages, ...paper.tags.mechanisms].join(" ").replaceAll("_", " ").toLocaleLowerCase();
        return (!query || searchable.includes(query)) && (!category || paper.tags.categories.includes(category)) && (!framework || paper.tags.frameworks.includes(framework));
      });
      $("library-count").textContent = `${papers.length} of ${library.papers.length} works · library updated ${library.date}`;
      $("library-results").replaceChildren(...papers.map(paper => {
        const b = paper.bibliographic, card = element("article", "library-card");
        card.dataset.paper = paper.id;
        card.append(element("p", "library-meta", `${paper.id} · ${b.issued["date-parts"][0][0]} · ${library.review_statuses[paper.review.status]}`));
        const title = element("h3", "", b.title); card.append(title);
        card.append(element("p", "", b.author.map(a => `${a.given || ""} ${a.family || ""}`.trim()).join(", ")));
        const tags = element("p", "library-meta", paper.tags.frameworks.map(id => library.frameworks[id]).join(" · "));
        if (paper.ttr_integration) tags.append(document.createTextNode(" · " + library.ttr_integrations[paper.ttr_integration]));
        card.append(tags, element("p", "library-scope", paper.review.scope));
        const details = element("details"); details.append(element("summary", "", "Classification & review scope"), element("p", "", paper.classification_basis), element("p", "", `Community review: ${paper.review.community_review}.`));
        card.append(details);
        const links = element("p", "library-links");
        const source = b.URL || (b.DOI ? `https://doi.org/${b.DOI}` : null);
        if (source?.startsWith("https://")) {
          const a = element("a", "", "Publication ↗"); a.href = source; a.target = "_blank"; a.rel = "noopener noreferrer"; links.append(a);
        }
        const record = element("a", "", "Source record ↗"); record.href = root + "docs/research/library/papers.json"; record.target = "_blank"; record.rel = "noopener noreferrer"; links.append(record);
        card.append(links); return card;
      }));
      if (!papers.length) $("library-results").append(element("p", "", "No matching works. Try a shorter search or clear a filter."));
    }
    $("library-query").addEventListener("input", renderLibrary);
    $("library-category").addEventListener("change", renderLibrary);
    $("library-framework").addEventListener("change", renderLibrary);
    renderLibrary();
  }
  showPanel(location.hash.slice(1) || "parse", {history: false});
  return {showPanel, groupEntries, get area() { return area; }};
})();
