"use strict";
const $ = id => document.getElementById(id);
let protocol, saved, index = 0, phase = "idle", onset = 0, interrupted = false;
function interrupt() {if (phase === "context" || phase === "response" || phase === "revealing") interrupted = true;}
document.addEventListener("visibilitychange", () => {if (document.hidden) interrupt();}); window.addEventListener("blur", interrupt);
function next() {
  $("possible").disabled = $("not-possible").disabled = true; $("task-text").textContent = "";
  if (index === protocol.events.length) {phase="complete"; $("task-stage").hidden=true; $("task-status").textContent="Rehearsal complete. Download the local response file."; return;}
  interrupted = document.hidden; const event = protocol.events[index]; phase="context";
  $("task-progress").textContent = `${index+1} / ${protocol.events.length}`;
  $("task-context").textContent = event.observation.left_context || "No preceding context";
  $("reveal").hidden=false; $("reveal").focus();
}
function reveal() {
  if (phase !== "context") return; phase="revealing"; $("reveal").hidden=true;
  requestAnimationFrame(() => {$("task-text").textContent=protocol.events[index].observation.text; onset=performance.now(); phase="response"; $("possible").disabled=$("not-possible").disabled=false;});
}
function respond(possible) {
  if (phase !== "response") return;
  const rt = performance.now()-onset; phase="between";
  saved.events.push({...protocol.events[index], possible, rt_ms:rt, visibility_interrupted:interrupted});
  index++; $("save").disabled=false; next();
}
$("setup").onsubmit=async event => {
  event.preventDefault(); $("start").disabled=true;
  try {
    const response=await fetch(`/api/experiments/schedule?participant=${encodeURIComponent($("participant").value)}`); protocol=await response.json(); if(!response.ok) throw new Error(protocol.error);
    saved={schema:1,data_kind:"rehearsal",study_id:protocol.study_id,study_sha256:protocol.study_sha256,participant:protocol.participant,events:[],timing:"performance.now at requestAnimationFrame; uncalibrated display onset"};
    index=0; $("setup").hidden=true; $("task-stage").hidden=false; $("task-status").textContent="Read the context. Press Space to reveal, then F or J to respond."; next();
  } catch(error) {$("task-status").textContent=error.message; $("start").disabled=false;}
};
$("reveal").onclick=reveal; $("possible").onclick=()=>respond(true); $("not-possible").onclick=()=>respond(false);
document.addEventListener("keydown",event=>{if(event.repeat || phase==="idle" || event.ctrlKey || event.metaKey || event.altKey) return; if(event.code==="Space" && phase==="context") {event.preventDefault(); reveal();} else if(phase==="response" && (event.code==="KeyF" || event.code==="KeyJ")) {event.preventDefault(); respond(event.code==="KeyJ");}});
$("save").onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(saved,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`rehearsal-${saved.participant}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
