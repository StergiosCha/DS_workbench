"use strict";
(() => {
  const storageKey = "ds-personal-grammars-v1";
  let saved = [], draft = null, checked = null, busy = false;
  try { saved = JSON.parse(localStorage.getItem(storageKey) || "[]"); if (!Array.isArray(saved)) saved = []; } catch { saved = []; }
  saved = saved.filter(item => item?.pack?.version === 1 && typeof item.pack.name === "string").slice(0, 10);
  const dialog = element("dialog", "grammar-workshop"); dialog.id = "grammar-workshop";
  dialog.setAttribute("aria-labelledby", "workshop-title");
  dialog.innerHTML = `<button id="workshop-close" type="button" class="dialog-close" aria-label="Close grammar workshop">×</button>
    <h2 id="workshop-title">Grammar workshop</h2>
    <p>Edit a proposal, check it with DS, then save it for future sentences. Saved rules run without model calls. Shared grammar contributions still need community review.</p>
    <p><button id="pack-import" type="button" class="text-button">Import a grammar pack…</button><input id="pack-file" type="file" accept=".json,application/json" hidden></p>
    <div id="pack-editor" hidden>
      <p id="pack-origin"></p><label>Grammar name<input id="pack-name" maxlength="80"></label>
      <label>Analysis, sources and your changes<textarea id="pack-notes" rows="3" maxlength="4000"></textarea></label>
      <details open><summary>Lexical rules · edit conditions and actions</summary><p>One condition or action per line. Use executable source notation from the proposal. Removing a rule removes it from this pack.</p><div id="pack-rules"></div><button id="pack-add-rule" type="button" class="text-button">+ Add rule</button></details>
      <details><summary>Semantic declarations</summary><p>Domains are comma-separated type names. Existing signatures cannot be overwritten.</p><div id="pack-declarations"></div><button id="pack-add-declaration" type="button" class="text-button">+ Add declaration</button></details>
      <details open><summary>Regression examples</summary><p>Add sentences that should parse and counterexamples that should remain incomplete. An expected meaning checks the normalized formula exactly. Unknown words or search limits make a negative check inconclusive.</p><div id="pack-tests"></div><button id="pack-add-positive" type="button" class="text-button">+ Should parse</button> <button id="pack-add-negative" type="button" class="text-button">+ Should stay incomplete</button></details>
      <div class="workshop-actions"><button id="pack-check" type="button" class="primary">Check with DS · no AI</button><button id="pack-save" type="button" class="text-button">Save to my grammars</button><button id="pack-export" type="button" class="text-button">Download contribution pack</button><button id="pack-delete" type="button" class="text-button">Remove saved copy</button></div>
      <p>Saving stores this pack and its examples in this browser, on this device. It does not publish them. Enable <strong>Use my rules</strong> in the composer to reuse it. Export a copy to keep it or send it for review.</p>
    </div><p id="pack-status" role="status"></p><div id="pack-checks"></div>`;
  document.body.append(dialog);

  function selected() { return $("personal-pack").value===""?null:saved[Number($("personal-pack").value)]?.pack; }
  function active() { const p=selected(); return Boolean($("personal-enabled").checked && p && p.grammar===$("grammar").value && state.inputMode==="sentence"); }
  function status(text) { $("pack-status").textContent=text; }
  function dirty() { checked=null; $("pack-checks").replaceChildren(); status("Edits have not been checked."); }
  function button(text, run) { const b=element("button","text-button",text); b.type="button"; b.addEventListener("click",run); return b; }
  function field(parent, title, value, change, multiline=false) {
    const label=element("label","",title), input=element(multiline?"textarea":"input"); input.value=value;
    if (multiline) { input.rows=Math.min(8,Math.max(2,value.split("\n").length)); input.spellcheck=false; }
    input.addEventListener("input",()=>{ change(input.value); dirty(); }); label.append(input); parent.append(label); return input;
  }
  function choice(parent,title,options,value,change) {
    const label=element("label","",title), input=element("select");
    for (const [key,text] of options) { const o=element("option","",text); o.value=key; input.append(o); }
    input.value=value; input.addEventListener("change",()=>{change(input.value);dirty();});label.append(input);parent.append(label);
  }
  const lines=value=>value.split("\n").map(x=>x.trim()).filter(Boolean);
  function renderEditor() {
    $("pack-editor").hidden=!draft;
    if (!draft) return;
    $("pack-origin").textContent=`${draft.grammar} · source ${draft.origin.model || "user-written/imported"}. Original proposal provenance stays attached when you edit.`;
    $("pack-name").value=draft.name; $("pack-notes").value=draft.notes;
    $("pack-rules").replaceChildren(...draft.proposal.rules.map((r,i)=>{
      const card=element("fieldset","pack-card");card.append(element("legend","",`Rule ${i+1}`));
      field(card,"Word",r.surface,v=>r.surface=v);field(card,"Rule identifier",r.name,v=>r.name=v);
      field(card,"Analysis and limits",r.explanation,v=>r.explanation=v,true);
      field(card,"IF · all conditions",r.when.join("\n"),v=>r.when=lines(v),true);
      field(card,"THEN · DS actions",r.then.join("\n"),v=>r.then=lines(v),true);
      card.append(button("Remove rule",()=>{draft.proposal.rules.splice(i,1);dirty();renderEditor();}));return card;
    }));
    $("pack-declarations").replaceChildren(...draft.proposal.declarations.map((d,i)=>{
      const card=element("fieldset","pack-card");card.append(element("legend","",`Declaration ${i+1}`));
      field(card,"Symbol",d.name,v=>d.name=v);choice(card,"Kind",["sort","constant","predicate","modifier"].map(x=>[x,x]),d.kind,v=>d.kind=v);
      field(card,"Domains",d.domains.join(", "),v=>d.domains=v.split(",").map(x=>x.trim()).filter(Boolean));
      card.append(button("Remove declaration",()=>{draft.proposal.declarations.splice(i,1);dirty();renderEditor();}));return card;
    }));
    $("pack-tests").replaceChildren(...draft.tests.map((t,i)=>{
      const card=element("fieldset","pack-card");card.append(element("legend","",`Example ${i+1}`));
      field(card,"Sentence",t.sentence,v=>t.sentence=v,true);
      choice(card,"Expected result",[["true","Complete derivation"],["false","Incomplete derivation"]],String(t.complete),v=>{t.complete=v==="true";if(!t.complete)t.meaning="";renderEditor();});
      if(t.complete)field(card,"Expected normalized meaning · optional",t.meaning,v=>t.meaning=v,true);
      card.append(button("Remove example",()=>{draft.tests.splice(i,1);dirty();renderEditor();}));return card;
    }));
  }
  function load(pack, report=null) { draft=JSON.parse(JSON.stringify(pack));checked=report;renderEditor();renderChecks();dialog.showModal(); }
  function refreshSaved(index="") {
    $("personal-pack").replaceChildren(element("option","","Choose a saved grammar…"));$("personal-pack").firstChild.value="";
    saved.forEach((item,i)=>{const o=element("option","",`${item.pack.name} · ${item.pack.grammar.replace("2026-","")}`);o.value=String(i);$("personal-pack").append(o);});
    $("personal-pack").value=String(index);refresh();
  }
  function refresh() {
    const p=selected(), eligible=p && p.grammar===$("grammar").value && state.inputMode==="sentence";
    const ai=$("llm-enabled").checked || $("jev-enabled").checked;
    if(!eligible || ai) $("personal-enabled").checked=false;
    $("personal-pack").hidden=!saved.length;$("personal-enabled").closest("label").hidden=!saved.length;
    $("personal-state").hidden=!saved.length;
    $("personal-pack").disabled=state.busy;$("personal-enabled").disabled=state.busy || !eligible;
    $("grammar-workshop-open").disabled=state.busy;
    $("personal-state").textContent=active()?"Personal grammar ON · no model calls":!p?"Saved on this device":!eligible?"Choose this pack’s grammar and Sentence mode":ai?"Personal grammar paused · enable Use my rules to turn AI off":"Personal grammar OFF";
    if(active()) $("n-best").disabled=true;
  }
  function persist() {
    localStorage.setItem(storageKey,JSON.stringify(saved));
  }
  function renderChecks() {
    $("pack-checks").replaceChildren();
    if(!checked)return;
    if(!checked.compiles){status(`Rules did not compile: ${checked.message}`);return;}
    status(`${checked.cases.filter(c=>c.status==="matched").length}/${checked.cases.length} examples matched. ${checked.has_positive&&checked.has_negative?"Positive and negative examples supplied.":"Add both positive and negative examples before shared review."} No model calls.`);
    if(checked.notice)$("pack-checks").append(element("p","",checked.notice));
    for(const row of checked.cases){const item=element("details","pack-check");item.append(element("summary","",`${row.status} · ${row.example.sentence}`));item.append(element("pre","",JSON.stringify(row,null,2)));$("pack-checks").append(item);}
  }
  function freeze(value) { busy=value; for(const c of dialog.querySelectorAll("button,input,select,textarea"))c.disabled=value; }
  async function check() {
    if(!draft||busy)return null;
    freeze(true);status("Checking the edited grammar and examples with DS. No model request…");
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),55000);
    try {
      const response=await fetch("/api/parse",{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,
        body:JSON.stringify({sentence:draft.seed_sentence,grammar:draft.grammar,grammar_pack:draft,grammar_pack_check:true,lexical_mode:"off",allow_model_fallback:false})});
      const result=await response.json();if(result.error)throw new Error(result.error);
      checked=result;renderChecks();return result;
    } catch(e){checked=null;status(e.name==="AbortError"?"Checks reached the time limit; no passing result was recorded.":e.message);return null;}
    finally{clearTimeout(timeout);freeze(false);}
  }
  function download() {
    if(!draft)return;
    const blob=new Blob([JSON.stringify({pack:draft,check_report:checked},null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);
    const a=element("a");a.href=url;a.download="ds-grammar-contribution.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status("Downloaded rules, edits, provenance and example expectations. The check report is evidence for review; it does not publish or approve the grammar.");
  }
  function inspectShape(pack) {
    if(pack?.version!==1||typeof pack.name!=="string"||typeof pack.grammar!=="string"||typeof pack.notes!=="string"||!pack.origin||!Array.isArray(pack.tests)||!Array.isArray(pack.proposal?.rules)||!Array.isArray(pack.proposal?.declarations))throw new Error("Import a version 1 DS grammar contribution pack.");
    if(!pack.proposal.rules.every(r=>typeof r.surface==="string"&&typeof r.name==="string"&&typeof r.explanation==="string"&&Array.isArray(r.when)&&Array.isArray(r.then))||!pack.proposal.declarations.every(d=>typeof d.name==="string"&&Array.isArray(d.domains))||!pack.tests.every(t=>typeof t.sentence==="string"&&typeof t.meaning==="string"&&typeof t.complete==="boolean"))throw new Error("The pack has malformed editable fields.");
  }
  $("grammar-workshop-open").addEventListener("click",()=>{
    const item=saved[Number($("personal-pack").value)];
    if($("personal-pack").value!==""&&item)load(item.pack,item.report);
    else {draft=null;checked=null;renderEditor();$("pack-checks").replaceChildren();status("Choose Edit & keep rules on an experimental result, or import a contribution pack.");dialog.showModal();}
  });
  $("workshop-close").addEventListener("click",()=>dialog.close());
  $("pack-name").addEventListener("input",()=>{draft.name=$("pack-name").value;dirty();});
  $("pack-notes").addEventListener("input",()=>{draft.notes=$("pack-notes").value;dirty();});
  $("pack-add-rule").addEventListener("click",()=>{draft.proposal.rules.push({surface:"",name:"",explanation:"",when:[],then:[]});dirty();renderEditor();});
  $("pack-add-declaration").addEventListener("click",()=>{draft.proposal.declarations.push({name:"",kind:"predicate",domains:["object"]});dirty();renderEditor();});
  for(const [id,complete] of [["pack-add-positive",true],["pack-add-negative",false]])$(id).addEventListener("click",()=>{draft.tests.push({sentence:"",complete,meaning:""});dirty();renderEditor();});
  $("pack-check").addEventListener("click",check);
  $("pack-save").addEventListener("click",async()=>{
    const report=checked||await check();if(!report?.compiles)return;
    const index=saved.findIndex(x=>x.pack.name===draft.name&&x.pack.grammar===draft.grammar);
    if(index<0&&saved.length>=10){status("Up to ten personal packs can be saved. Export and remove one first.");return;}
    const item={pack:JSON.parse(JSON.stringify(draft)),report};const next=saved.slice();if(index<0)next.push(item);else next[index]=item;
    const before=saved;saved=next;
    try{persist();$("personal-enabled").checked=false;refreshSaved(index<0?saved.length-1:index);status("Saved on this device. Close the workshop and enable Use my rules to apply it. Shared grammar remains unchanged.");}catch{saved=before;status("Browser storage is unavailable or full. Download the contribution pack instead.");}
  });
  $("pack-export").addEventListener("click",download);
  $("pack-delete").addEventListener("click",()=>{
    if(!draft)return;const next=saved.filter(x=>x.pack.name!==draft.name||x.pack.grammar!==draft.grammar),before=saved;saved=next;
    try{persist();$("personal-enabled").checked=false;refreshSaved();status("Saved copy removed from this device. The open draft can still be exported.");}catch{saved=before;status("Could not update browser storage.");}
  });
  $("pack-import").addEventListener("click",()=>$("pack-file").click());
  $("pack-file").addEventListener("change",async()=>{try{const file=$("pack-file").files[0];if(!file)return;if(file.size>64000)throw new Error("Import a pack smaller than 64 KB.");const data=JSON.parse(await file.text()),pack=data.pack||data;inspectShape(pack);draft=pack;checked=null;renderEditor();dirty();status("Imported as an unchecked draft. Check it with this server before saving.");}catch(e){status(e.message);}finally{$("pack-file").value="";}});
  $("personal-pack").addEventListener("change",()=>{$("personal-enabled").checked=false;refresh();renderJevControls();});
  $("personal-enabled").addEventListener("change",()=>{if($("personal-enabled").checked){useDictionariesOnly();$("n-best").value="1";$("compare-jev").checked=false;}refresh();renderJevControls();renderMethodMode();});
  window.grammarWorkshop={active,refresh,
    apply(payload){if(active()){payload.grammar_pack=selected();payload.lexical_mode="off";payload.allow_model_fallback=false;payload.experimental_rules=false;payload.decision_mode="off";payload.compare_jev=false;payload.n_best=1;payload.reading_traces=false;}},
    edit(result,attempt){
      const exp=result.experimental_grammar;
      load({version:1,name:`${result.grammar.includes("smg")?"Greek":"English"} rule proposal`,grammar:result.grammar,base_hash:exp.grammar_hash,seed_sentence:result.sentence,proposal:attempt.proposal,notes:"",tests:[{sentence:result.sentence,complete:true,meaning:attempt.status==="complete"?result.words.at(-1).normalized||"":""}],origin:{model:attempt.model||"",proposal_hash:exp.proposal_hash||""}});
      status("Edit the rule conditions, actions or meanings. Add counterexamples, then check with DS. This makes no new model request.");
    },
    renderResult(result){
      const p=result.personal_grammar,panel=$("personal-report");panel.hidden=!p;panel.replaceChildren();if(!p)return;
      panel.append(element("h3","",`${result.complete?"Complete":"Incomplete"} · personal grammar: ${p.name}`),element("p","",p.notice),element("p","",p.blocked_by_reviewed_constraint?"The original grammar diagnosed a constraint violation; your rules were not applied.":`Original grammar: ${p.baseline.complete?"complete":"incomplete"}. Selected personal rules: ${p.selected_rule_ids.join(", ")||"none on the displayed path"}. No model requests.`),button("Edit this grammar",()=>load(p.pack)));
      for(const r of p.rules){const d=element("details");d.append(element("summary","",`${r.surface} · ${r.rule_id}`),element("pre","",r.program.join("\n")));panel.append(d);}
    }
  };
  refreshSaved();
})();
