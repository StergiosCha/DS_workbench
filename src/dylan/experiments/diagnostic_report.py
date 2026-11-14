"""Offline interactive report. Imported text is rendered as text, never markup."""

import json


def render(report):
    # Escape HTML-sensitive bytes so source text cannot end the JSON script.
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c")
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agreement and reflexives · literature diagnostic</title>
<style>
:root{font-family:system-ui,sans-serif;color:#203040;background:#f4f6f8}
*{box-sizing:border-box}body{margin:0}main{max-width:1180px;margin:auto;padding:32px 24px 70px}
h1{font-size:clamp(1.8rem,4vw,2.8rem);margin:8px 0 16px;line-height:1.12}h2{margin-top:32px}
p{line-height:1.55;max-width:90ch}.eyebrow{color:#526171;font-size:.9rem;letter-spacing:.05em}
.notice{background:#fff4d8;border-left:4px solid #ad7516;padding:16px 20px}
.panel{background:white;border:1px solid #dbe1e7;border-radius:12px;padding:20px;margin:20px 0}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.91rem}
th,td{text-align:left;padding:12px;border-bottom:1px solid #e1e5ea;vertical-align:top}
th{color:#526171;font-size:.8rem}td:first-child{font-weight:600}code{overflow-wrap:anywhere}
.filters{display:flex;flex-wrap:wrap;gap:16px}.filters label{flex:1;min-width:200px}
select{display:block;width:100%;margin-top:7px;padding:10px;background:white;border:1px solid #abb8c4;border-radius:6px;font:inherit}
.pass{color:#16623c}.fail{color:#9d2929}.unavailable{color:#596979}
.condition{padding:18px 0;border-top:1px solid #dbe1e7}.sentence{font-size:1.08rem;margin:8px 0}
.small{font-size:.86rem;color:#526171}.critical{background:#fff1bd;padding:1px 3px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:12px;font-size:.83rem}
summary{cursor:pointer;padding:8px 0}button{padding:10px 14px;background:#214c75;color:white;border:0;border-radius:6px;font:inherit;cursor:pointer}
a{color:#214c75}.methods li{line-height:1.5;margin:8px 0}
@media(max-width:600px){main{padding:20px 12px}th,td{padding:9px 7px}.panel{padding:14px}}
</style></head><body><main>
<div class="eyebrow">DS WORKBENCH · MODULAR EXPERIMENTS · DEVELOPMENT DIAGNOSTIC</div>
<h1>Agreement and reflexives across an intervening noun</h1>
<p id="inventory"></p>
<p class="notice"><strong>What is scored:</strong> whether a configuration licenses each source sentence.
The original SyntaxGym task compares regional surprisals; those predictions are preserved below and remain unscored.
The lexicon was developed with these materials in view. This is an implementation diagnostic, not held-out accuracy or human evidence.</p>
<div class="panel"><h2 style="margin-top:0">Configuration comparison</h2>
<p class="small">A family passes only if all four conditions are correct. Unknown words, unsupported structures and limits receive no credit for rejecting a negative condition.</p>
<div class="scroll"><table><thead><tr><th>Configuration</th><th>Conditions available</th><th>Families available</th><th>Families correct</th><th>Condition accuracy</th></tr></thead><tbody id="scores"></tbody></table></div>
<p id="intersection" class="small"></p></div>
<div class="panel"><h2 style="margin-top:0">Inspect the source and the decision</h2>
<div class="filters">
<label>Phenomenon<select id="suite"></select></label>
<label>Source family<select id="family"></select></label>
<label>Configuration<select id="engine"></select></label></div>
<p class="small">Highlighted text is the source critical region. Every configuration receives the same sentence, without condition labels or region annotations.</p>
<div id="conditions"></div>
<details><summary>Original source predictions and attribution</summary><pre id="source"></pre></details></div>
<div class="panel methods"><h2 style="margin-top:0">How to interpret this run</h2>
<ul>
<li>The five feature configurations use the same lexical entries and categorial application rules. They differ in agreement, reflexive-number checking, or which nominal controls the check.</li>
<li>The head configuration propagates the subject NP's head through its PP modifiers. The nearest-noun control uses the last noun within that subject instead.</li>
<li>A feature rejection is supported by an otherwise complete derivation and an explicit failed unification. An unexplained failure to parse is unavailable.</li>
<li>Labels follow the source's intended number contrast. This fragment treats <em>themselves</em> as plural-only; singular-they readings are outside this diagnostic.</li>
<li>The original DS and CCG fragments remain unchanged. Compare their coverage separately; a missing common sample prevents a matched accuracy comparison across architectures.</li>
<li>No next-word probabilities, memory parameters, neural representations or human reading times were fitted. Successful licensing does not validate the semantic interpretation of every sentence.</li>
</ul>
<button id="download" type="button">Download this run as JSON</button>
<details><summary>Protocol and source fingerprints</summary><pre id="provenance"></pre></details>
</div></main>
<script type="application/json" id="report-data">__REPORT_JSON__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("report-data").textContent);
const el=id=>document.getElementById(id);
const text=(parent,tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;parent.appendChild(n);return n;};
const option=(parent,value,label)=>{const n=document.createElement("option");n.value=value;n.textContent=label;parent.appendChild(n);};
const percent=v=>v===null?"Unavailable":(100*v).toFixed(1)+"%";
const items=data.dataset.items;
const count=new Set(items.map(i=>i.family)).size;
el("inventory").textContent=count+" published four-condition item sets · "+items.length+" sentences · "+new Set(items.map(i=>i.shared_frame)).size+" shared lexical frames. Source: Hu et al. (2020), SyntaxGym suites number_prep and reflexive_prep_masc.";
for(const [name,entry] of Object.entries(data.summary.engines)){
 const m=entry.overall,row=document.createElement("tr");el("scores").appendChild(row);
 for(const v of [name,m.evaluable_conditions+"/"+m.conditions,m.evaluable_families+"/"+m.families,m.correct_families,percent(m.condition_accuracy)])text(row,"td",String(v));
 option(el("engine"),name,name);
}
el("engine").value="ccg-feature-head-v1";
el("intersection").textContent="Families available to every configuration: "+data.summary.intersections.all_configurations.families+". Families shared by all feature ablations: "+data.summary.intersections.feature_ablations.families+".";
for(const id of Object.keys(data.dataset.protocol.selection))option(el("suite"),id,id);
function families(){
 el("family").replaceChildren();
 for(const id of new Set(items.filter(i=>i.suite===el("suite").value).map(i=>i.family)))option(el("family"),id,id);
 show();
}
function show(){
 el("conditions").replaceChildren();
 const source=data.dataset.sources.find(s=>s.source.id===el("suite").value);
 el("source").textContent=JSON.stringify(source,null,2);
 for(const item of items.filter(i=>i.family===el("family").value)){
  const result=data.runs[el("engine").value][item.id], section=document.createElement("section");section.className="condition";el("conditions").appendChild(section);
  text(section,"strong",item.condition+" · "+item.id);
  const sentence=text(section,"p","","sentence");
  for(const r of item.regions){if(!r.content)continue;const span=text(sentence,"span",r.content,r.number===item.critical_region?"critical":"");span.appendChild(document.createTextNode(" "));}
  const judgement=result.decision===null?"Unavailable":result.decision?"Accept":"Reject";
  const correct=result.decision===null?null:result.decision===item.gold;
  text(section,"p","Expected: "+(item.gold?"accept":"reject")+". Returned: "+judgement+" ("+result.status+").",correct===null?"unavailable":correct?"pass":"fail");
  const records=result.rejections?.length?result.rejections:result.derivations||[];
  const checks=records[0]?.checks||[];
  for(const c of checks)text(section,"p",(c.mechanism==="subject_verb"?"Subject–verb number":"Local reflexive number")+": controller "+c.controller.word+" ["+c.controller.number+"], required ["+c.required_number+"]. "+(c.enabled?(c.passes?"Constraint satisfied.":"Feature conflict."):"Constraint disabled."),"small");
  if(result.failure)text(section,"p","Coverage detail: "+JSON.stringify(result.failure),"small");
  const details=document.createElement("details");section.appendChild(details);text(details,"summary","Inspect returned meaning, derivation and constraints");text(details,"pre",JSON.stringify(result,null,2));
 }
}
el("suite").addEventListener("change",families);el("family").addEventListener("change",show);el("engine").addEventListener("change",show);
el("provenance").textContent=JSON.stringify({generated_at:data.generated_at,protocol:data.dataset.protocol,protocol_sha256:data.dataset.protocol_sha256,items_sha256:data.dataset.items_sha256,git_commit:data.implementation.git_commit,source_sha256:data.implementation.source_sha256},null,2);
el("download").addEventListener("click",()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=u;a.download="literature-diagnostic-results.json";a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
families();
</script></body></html>
"""
    return template.replace("__REPORT_JSON__", payload)
