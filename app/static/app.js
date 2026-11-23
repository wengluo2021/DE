(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const labels = {f400:"Fixed window · 400",s400:"Article structure · 400",f800:"Fixed window · 800",s800:"Article structure · 800"};
  const paths = {chat:"/",documents:"/documents",compare:"/compare",p800:"/p800",evaluation:"/evaluation"};
  const names = {chat:"Chat",documents:"Documents",compare:"Chunk comparison",p800:"P800 retrieval",evaluation:"Evaluation"};
  const statuses = {queued:"Queued",running:"Running",completed:"Completed",failed:"Failed",error:"Failed",answered:"Answered",insufficient:"Insufficient evidence"};
  const errors = {
    OFFICIAL_DATA_NOT_CONFIGURED:"The frozen corpus has not been configured yet.",RETRIEVAL_NOT_CONFIGURED:"The corpus or retrieval service has not been configured yet.",
    INDEX_NOT_READY:"Please build the four index groups for the current corpus first.",RETRIEVAL_DEPENDENCIES_NOT_INSTALLED:"Retrieval dependencies are not installed yet.",
    INVALID_CORPUS_DATA:"Corpus validation failed. Please check the manifest, source snapshots, and processed text.",
    INDEX_PATH_TOO_LONG:"The Windows index directory path is too long. Please shorten DERAG_DATA_DIR and rebuild the database.",
    GOLD_NOT_CONFIGURED:"The frozen benchmark questions have not been configured yet.",INVALID_GOLD_DATA:"Validation of the benchmark questions, their evidence, or their version did not pass.",
    VERSION_MISMATCH:"The request version does not match the current configuration. Please refresh the status.",LLM_NOT_CONFIGURED:"The generation API has not been configured yet.",
    LLM_AUTH_ERROR:"The generation API failed authentication or model permission checks.",LLM_RATE_LIMITED:"The generation service is rate-limited. Please check the status later.",
    EVALUATION_ACTIVE:"An evaluation is running. Please wait for it to finish before using Chat or building the database.",TASK_ALREADY_RUNNING:"A background task already exists. Please wait for it to finish.",
    PROCESS_INTERRUPTED:"The previous run was interrupted. Saved results are still available.",NOT_FOUND:"This saved record was not found.",
    INVALID_REVIEW:"The scoring fields do not match the question type or claim. Please check.",NETWORK_ERROR:"Connection interrupted. Submitted requests may still be processing. Please refresh history or experiments first to avoid duplicate submissions.",
    P800_NOT_BUILT:"The P800 index has not been built yet. Run scripts.build_p800 first.",P800_NOT_READY:"The P800 index is incomplete. Rebuild it with scripts.build_p800.",P800_MANIFEST_INVALID:"The P800 manifest is unreadable."
  };
  const state = {health:null,sessions:[],history:[],conversation:null,docs:[],runs:[],run:null,
    filter:"all",pending:false,route:"chat",panels:{left:[],right:[]},task:null,reviewer:"",p800Status:null};
  const requests = {history:0,compare:0,run:0,document:0};
  const reviewDrafts=new Map();
  let taskSequence=0,toastTimer,returnFocus=null,reviewCase=null;
  const modeName = () => state.health && (state.health.mode==="test" ? "Synthetic test mode" : state.health.mode==="formal" ? "Formal mode" : "Development mode");
  const corpus = () => state.health.configuration.corpus_version;
  const query = values => "?" + new URLSearchParams(values).toString();
  const version = v => esc(v ? v.slice(0,16) : "Not configured");
  const stored = {
    get(key) {try {return JSON.parse(localStorage.getItem(key));} catch (_) {return null;}},
    set(key,value) {try {localStorage.setItem(key,JSON.stringify(value));} catch (_) {}},
    remove(key) {try {localStorage.removeItem(key);} catch (_) {}}
  };
  function errorText(error) {return (errors[error.code] || error.message || "Request not completed.") + (error.code ? " ["+error.code+"]" : "");}
  function toast(message,error) {
    $("toast").textContent=message;
    $("toast").className="toast show"+(error ? " error" : "");
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("toast").classList.remove("show"),6000);
  }
  async function api(path,options) {
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),path==="/api/ask" ? 150000 : 30000);
    try {
      const response=await fetch(path,Object.assign({headers:{"Content-Type":"application/json"},signal:controller.signal},options));
      const body=await response.json();
      if (!response.ok) throw Object.assign(new Error(body.message || "Service request failed"),{code:body.code || "HTTP_"+response.status});
      return body;
    } catch (error) {
      if (error.code) throw error;
      throw Object.assign(new Error(errors.NETWORK_ERROR),{code:"NETWORK_ERROR"});
    } finally {clearTimeout(timer);}
  }
  const post = (path,body) => api(path,{method:"POST",body:JSON.stringify(body)});
  const runPath = id => "/api/evaluations/"+encodeURIComponent(id);
  const docPath = (id,cv) => "/api/documents/"+encodeURIComponent(id)+query({corpus_version:cv});
  function sourceLink(url) {
    try {const parsed=new URL(url);if (!["https:","http:"].includes(parsed.protocol)) return "No valid source address";}
    catch (_) {return "No valid source address";}
    return '<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+"\">Open original source ↗</a>";
  }
  function block(text) {return '<pre class="source-text">'+esc(text)+'</pre>';}
  function stat(label,value,extra) {return '<div class="stat-item"><small>'+esc(label)+'</small><strong>'+esc(value)+'</strong><span>'+esc(extra || "")+'</span></div>';}
  function empty(text) {return '<div class="empty-state">'+esc(text)+'</div>';}
  function configureButtons() {
    const ready=!!(state.health && state.health.ready);
    const busy=!!state.task;
    $("askForm").querySelector("button").disabled=!ready || state.pending || (busy && state.task.kind==="evaluation");
    $("newSessionButton").disabled=state.pending;
    $("chatCondition").disabled=state.pending;
    $("runEvaluationButton").disabled=!ready || !state.health.configuration.gold_version || busy || state.pending;
    $("buildIndexesButton").disabled=!state.health || !!state.health.components.retrieval.issue || busy || state.pending;
    $("exportReportButton").disabled=$("exportCsvButton").disabled=!state.run;
    const p800=$("p800SearchButton");
    if (p800) p800.disabled=!state.p800Status || !state.p800Status.ready;
  }
  function renderHealth() {
    const h=state.health;
    $("serviceBadge").textContent=h ? modeName()+(h.ready ? " · Ready" : " · Not ready") : "Backend not connected";
    $("systemStatus").textContent=h ? modeName() : "Backend not connected";
    $("systemMeta").textContent=h ? "Corpus "+h.configuration.corpus_version : "Please start the service and refresh";
    let notice="Unable to read the backend. Please confirm the service is running, then click refresh in the top right corner.";
    if (h) {
      notice= h.ready ? (h.mode==="test" ? "This is a synthetic test; neither answers nor scores are part of the formal regulatory experiment." : "Connected. Answers use retrieved evidence and include citations. The system declines to answer when evidence is insufficient.") :
        errors[h.components.retrieval.issue] || (!h.components.retrieval.ready ? errors.INDEX_NOT_READY : errors.LLM_NOT_CONFIGURED);
      if (state.task) notice="Background task in progress: "+(state.task.kind==="evaluation" ? "four-condition evaluation" : "four-condition indexing")+". Progress has been saved; refresh to continue viewing.";
    }
    $("serviceNotice").textContent=notice;
    $("serviceNotice").classList.toggle("not-ready",!h || !h.ready);
    configureButtons();
  }
  async function loadHealth() {
    try {state.health=await api("/api/health");}
    catch (error) {state.health=null;toast(errorText(error),true);}
    renderHealth();
  }
  function navigate(route,push) {
    state.route=route;
    if (push) history.pushState({}, "",paths[route]);
    $("pageTitle").textContent=names[route];
    document.querySelectorAll("[data-route]").forEach(b=>{b.classList.toggle("active",b.dataset.route===route);b.setAttribute("aria-current",b.dataset.route===route ? "page" : "false");});
    document.querySelectorAll(".view").forEach(v=>{v.hidden=v.id!=="view-"+route;v.classList.toggle("active",!v.hidden);});
    $("sidebar").classList.remove("open");$("scrim").hidden=!$("detailDrawer").classList.contains("open");
    syncPanels();
    if (route==="documents") loadDocuments();
    if (route==="compare") loadChunks();
    if (route==="p800") loadP800Status();
    if (route==="evaluation") loadRuns();
  }
  async function loadSessions() {
    try {state.sessions=(await api("/api/conversations")).items;renderSessions();}
    catch (error) {$("sessionList").innerHTML=empty(errorText(error));}
  }
  function renderSessions() {
    $("sessionList").innerHTML=state.sessions.map(s=>'<button class="session-row '+(s.id===state.conversation ? "active" : "")+'" data-session="'+esc(s.id)+'"><span class="session-row-main"><strong>'+esc(s.title)+'</strong><small>'+esc(new Date(s.updated_at).toLocaleString("en-GB"))+'</small></span></button>').join("") || empty("No saved conversations yet");
  }
  function answerHtml(result) {
    if (result.status==="insufficient") return '<p>The current knowledge base does not contain enough evidence to answer this question.</p>';
    return result.claims.map(claim=>'<p>'+esc(claim.text)+claim.citation_numbers.map(n=>
      '<button class="citation-button" type="button" data-ask="'+esc(result.ask_id)+'" data-citation="'+n+"\" aria-label=\"View citations for this round "+n+'">['+n+']</button>').join("")+'</p>').join("");
  }
  function renderMessages() {
    $("messages").innerHTML=state.history.map(ask=>{
      const result=ask.result;
      return "<article class=\"message user\"><div class=\"message-content\"><div class=\"message-label\">You · "+esc(labels[ask.condition])+'</div><div class="message-text">'+esc(ask.question)+'</div></div></article>'+
        '<article class="message assistant"><div class="message-content"><div class="message-label">DERag · '+esc(statuses[ask.state] || ask.state)+'</div><div class="message-text">'+
        (result ? answerHtml(result) : esc(ask.error ? errorText(ask.error) : "Request in progress; refresh history to view results."))+'</div>'+
        (result ? '<div class="message-meta">'+esc(result.generation.model)+' · '+esc(result.condition)+' · '+version(result.index_version)+'</div>' : "")+'</div></article>';
    }).join("") || empty(state.health && state.health.ready ? "Enter a question. Citations in answers can be clicked or opened with the keyboard." : "Knowledge base is not ready yet. Check the status note above first; existing conversations can still be read.");
    if (state.pending) $("messages").insertAdjacentHTML("beforeend","<div class=\"task-status\" role=\"status\">Retrieving and generating, please wait. Do not resend.</div>");
    $("messages").scrollTop=$("messages").scrollHeight;
  }
  async function loadHistory(id) {
    const seq=++requests.history;
    try {
      const data=await api("/api/conversations/"+encodeURIComponent(id));
      if (seq!==requests.history || state.conversation!==id) return;
      state.history=data.asks;renderMessages();
    } catch (error) {if (seq===requests.history) {$("messages").innerHTML=empty(errorText(error));}}
  }
  async function ask(event) {
    event.preventDefault();
    const question=$("questionInput").value.trim();
    if (!question || state.pending || !state.health || !state.health.ready) return;
    const conversation=state.conversation;
    const previousSessions=new Set(state.sessions.map(s=>s.id));
    state.pending=true;configureButtons();renderMessages();
    try {
      const result=await post("/api/ask",{question,condition:$("chatCondition").value,corpus_version:corpus(),conversation_id:conversation});
      state.conversation=result.conversation_id;$("questionInput").value="";
    } catch (error) {toast(errorText(error),true);}
    finally {
      state.pending=false;configureButtons();
      await loadSessions();
      if (!state.conversation) {const created=state.sessions.find(s=>!previousSessions.has(s.id));if (created) state.conversation=created.id;}
      if (state.conversation) await loadHistory(state.conversation);else renderMessages();
      renderSessions();
    }
  }
  function syncPanels() {
    $("sidebar").inert=matchMedia("(max-width: 820px)").matches && !$("sidebar").classList.contains("open");
    $("conversationRail").inert=matchMedia("(max-width: 640px)").matches && !$("chatLayout").classList.contains("show-sessions");
    $("menuButton").setAttribute("aria-expanded",String($("sidebar").classList.contains("open")));
    $("sessionToggle").setAttribute("aria-expanded",String($("chatLayout").classList.contains("show-sessions")));
  }
  function reviewKey(row) {return (row.run_id || state.run.run_id)+"/"+row.condition+"/"+row.case_id;}
  function stashReview() {
    const form=$("reviewForm");
    if (form && reviewCase && state.run) reviewDrafts.set(reviewKey(reviewCase),Object.fromEntries(new FormData(form)));
  }
  function draftScore(row) {
    const draft=reviewDrafts.get(reviewKey(row));
    if (!draft) return row.review || {};
    return {reviewer:draft.reviewer,notes:draft.notes,answer_grade:draft.answer_grade || null,
      refusal_correct:!draft.refusal_correct ? null : draft.refusal_correct==="true",
      claim_reviews:(row.result ? row.result.claims : []).map((c,i)=>({claim_index:i,reason:draft["reason_"+i],
        supported:!draft["supported_"+i] ? null : draft["supported_"+i]==="true"}))};
  }
  function openDrawer(kind,title,html) {
    stashReview();
    if (!$("detailDrawer").classList.contains("open")) returnFocus=document.activeElement;
    $("drawerKicker").textContent=kind;$("drawerTitle").textContent=title;$("drawerBody").innerHTML=html;
    $("detailDrawer").inert=false;$("detailDrawer").classList.add("open");
    $("detailDrawer").setAttribute("aria-hidden","false");document.querySelector(".shell").inert=true;
    $("scrim").hidden=false;$("drawerClose").focus();
  }
  function closeDrawer() {
    stashReview();
    requests.document++;
    $("detailDrawer").classList.remove("open");$("detailDrawer").setAttribute("aria-hidden","true");$("detailDrawer").inert=true;
    document.querySelector(".shell").inert=false;
    $("scrim").hidden=!$("sidebar").classList.contains("open");reviewCase=null;
    if (returnFocus && returnFocus.isConnected) returnFocus.focus();
  }
  function evidenceHtml(citation,cv) {
    return '<section class="evidence-card"><h3>'+esc(citation.title || citation.document_id)+'</h3><p>'+esc((citation.article_labels || [citation.article_id || citation.structure_id]).filter(Boolean).join(", "))+
      ' · ['+esc(citation.start)+', '+esc(citation.end)+')</p>'+block(citation.text)+
      '<p>'+sourceLink(citation.source_url)+'</p><button class="button" type="button" data-source="'+esc(citation.document_id)+'" data-corpus="'+esc(cv)+'" data-start="'+esc(citation.start)+'" data-end="'+esc(citation.end)+"\">View frozen source</button></section>";
  }
  function findResult(id) {
    return state.history.map(a=>a.result).concat(state.run ? state.run.cases.map(c=>c.result) : []).find(r=>r && r.ask_id===id);
  }
  async function openDocument(id,cv,start,end) {
    const seq=++requests.document;
    try {
      const doc=await api(docPath(id,cv));if (seq!==requests.document) return;
      const chars=Array.from(doc.text);
      let text=esc(doc.text);
      if (Number.isInteger(start) && Number.isInteger(end) && start>=0 && end<=chars.length && start<end) {
        text=esc(chars.slice(0,start).join(""))+'<mark tabindex="0" id="sourceHighlight">'+esc(chars.slice(start,end).join(""))+'</mark>'+esc(chars.slice(end).join(""));
      }
      const back=reviewCase ? '<button class="button" data-case="'+esc(reviewCase.case_id)+'" data-condition="'+esc(reviewCase.condition)+'" data-run="'+esc(reviewCase.run_id)+"\">Back to question scoring</button>" : "";
      openDrawer("Frozen source",doc.title,back+'<p>'+sourceLink(doc.source_url)+"</p><p>Corpus "+version(doc.corpus_version)+' · '+esc(doc.articles.length)+" articles</p><pre class=\"source-text\">"+text+'</pre>');
      if ($("sourceHighlight")) $("sourceHighlight").scrollIntoView({block:"center"});
    } catch (error) {toast(errorText(error)+" The currently saved citation snapshot can still be verified.",true);}
  }
  async function loadDocuments() {
    if (!state.health) return;
    try {
      state.docs=(await api("/api/documents"+query({corpus_version:corpus()}))).items;
      $("documentNotice").textContent="Browse the frozen corpus. Open a document to inspect its text and official source.";
    } catch (error) {state.docs=[];$("documentNotice").textContent=errorText(error);}
    renderDocuments();
  }
  function renderDocuments() {
    const keyword=$("docSearch").value.trim().toLowerCase();
    const shown=state.docs.filter(d=>(d.title+" "+d.source_url).toLowerCase().includes(keyword));
    $("documentStats").innerHTML=stat("Documents",state.docs.length)+stat("Articles",state.docs.reduce((n,d)=>n+d.article_count,0))+stat("Characters",state.docs.reduce((n,d)=>n+d.char_count,0));
    $("documentRows").innerHTML=shown.map(d=>'<tr><td><strong>'+esc(d.title)+'</strong></td><td>'+sourceLink(d.source_url)+'</td><td>'+d.char_count+'</td><td>'+d.article_count+'</td><td>'+version(d.corpus_version)+'</td><td><button class="table-link" data-document="'+esc(d.document_id)+"\">View</button></td></tr>").join("");
    $("documentEmpty").hidden=!!shown.length;
    const current=$("compareDocument").value;
    $("compareDocument").innerHTML=state.docs.map(d=>'<option value="'+esc(d.document_id)+'">'+esc(d.title)+'</option>').join("");
    if (state.docs.some(d=>d.document_id===current)) $("compareDocument").value=current;
  }
  function renderPanel(side,items,search) {
    state.panels[side]=items;
    $(side+"Label").textContent=labels[$(side+"Condition").value];
    $(side+"Count").textContent=items.length+(search ? " hits" : " chunks");
    $(side+"Chunks").innerHTML=items.map((item,index)=>'<article class="chunk-item"><div class="chunk-top"><span>#'+(item.rank || index+1)+'</span><span>'+esc(item.end-item.start)+" characters · ["+esc(item.start)+', '+esc(item.end)+')</span></div>'+
      (search ? '<strong>'+esc(item.title)+"</strong><small>Similarity "+esc(item.score)+'</small>' : "")+'<p>'+esc(item.text)+'</p><button class="table-link" data-panel="'+side+'" data-index="'+index+"\">View source</button></article>").join("") || empty("No results");
  }
  async function loadChunks() {
    const seq=++requests.compare;
    state.panels={left:[],right:[]};$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("Loading chunks…");
    if (!state.health) {return;}
    if (!state.docs.length) await loadDocuments();
    if (seq!==requests.compare) return;
    const id=$("compareDocument").value;
    if (!id) {$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("No frozen documents available to read");return;}
    try {
      const sides=await Promise.all(["left","right"].map(side=>api("/api/documents/"+encodeURIComponent(id)+"/chunks"+query({corpus_version:corpus(),condition:$(side+"Condition").value}))));
      if (seq!==requests.compare) return;
      ["left","right"].forEach((side,i)=>renderPanel(side,sides[i].items,false));
      $("compareNotice").textContent="Document chunks: shows the intervals actually indexed by the backend; no re-chunking in the browser.";
      $("compareSummary").innerHTML=sides.map((s,i)=>stat(i ? "Right characters" : "Left characters",s.items.reduce((n,c)=>n+c.end-c.start,0))).join("");
    } catch (error) {if (seq===requests.compare) {$("compareNotice").textContent=errorText(error);$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty(errorText(error));$("compareSummary").innerHTML="";}}
  }
  async function compare(event) {
    event.preventDefault();if (!state.health) return;
    const question=$("compareQuestion").value.trim();if (!question) return;
    const seq=++requests.compare;
    state.panels={left:[],right:[]};$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("Retrieving…");
    try {
      const data=await post("/api/compare",{question,corpus_version:corpus(),left_condition:$("leftCondition").value,right_condition:$("rightCondition").value});
      if (seq!==requests.compare) return;
      ["left","right"].forEach(side=>renderPanel(side,data[side].hits,true));
      $("compareNotice").textContent="Same-question retrieval · Index "+data.index_version+"; similarity is not a probability of correctness.";
      $("compareSummary").innerHTML=["left","right"].map((side,i)=>stat(i ? "Right context" : "Left context",data[side].context_chars+" characters",data[side].timing_ms+" ms")).join("");
    } catch (error) {if (seq===requests.compare) {$("compareNotice").textContent=errorText(error);$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty(errorText(error));$("compareSummary").innerHTML="";}}
  }
  function p800StatusHtml(status) {
    if (!status) return "Checking P800 index…";
    if (!status.ready) {
      return '<strong>P800 index not built.</strong> '+(status.message ? esc(status.message)+" " : "")+
        'Run <code>python -m scripts.build_p800 --config config/experiment.formal-a.json</code> first.';
    }
    const counts=status.counts || {};
    return '<strong>P800 index ready.</strong> '+esc(counts.parents || "?")+" parents · "+
      esc(counts.indexed_children || "?")+" indexed children · children "+esc(status.child_chars || "?")+" characters";
  }
  async function loadP800Status() {
    try {state.p800Status=await api("/api/p800/status");}
    catch (error) {state.p800Status={ready:false,message:errorText(error)};}
    $("p800Status").innerHTML=p800StatusHtml(state.p800Status);
    configureButtons();
  }
  function p800HitHtml(hit) {
    const parent=esc(hit.text || "");
    const child=esc(hit.matched_child_text || "");
    const marked=child ? parent.replace(child,"<mark>"+child+"</mark>") : parent;
    const labels=(hit.article_labels || []).filter(Boolean).join(", ") || hit.document_id;
    const score=Number(hit.score);
    return '<article class="chunk-item p800-card"><div class="chunk-top"><span>#'+esc(hit.rank)+'</span><span>'+
      esc(labels)+' · ['+esc(hit.start)+', '+esc(hit.end)+')</span></div>'+
      '<strong>'+esc(hit.title || hit.document_id)+'</strong>'+
      '<small>Parent score '+(Number.isFinite(score) ? score.toFixed(3) : esc(hit.score))+
      ' · matched child '+esc((hit.matched_child_id || "").slice(0,12))+'…</small>'+
      '<p class="p800-parent">'+marked+'</p>'+
      '<p class="p800-child"><strong>Matched child:</strong> '+esc(hit.matched_child_text || "")+'</p>'+
      '<button class="table-link" type="button" data-source="'+esc(hit.document_id)+'" data-corpus="'+esc(hit.corpus_version)+
      '" data-start="'+esc(hit.start)+'" data-end="'+esc(hit.end)+'">View frozen parent</button></article>';
  }
  async function searchP800(event) {
    event.preventDefault();
    const question=$("p800Question").value.trim();
    if (!question || !state.p800Status || !state.p800Status.ready) return;
    const button=$("p800SearchButton");
    button.disabled=true;
    $("p800Results").innerHTML=empty("Retrieving P800 parents…");
    $("p800Summary").innerHTML="";
    try {
      const data=await post("/api/p800/search",{question,corpus_version:corpus(),candidate_k:50});
      $("p800Summary").innerHTML=stat("Top-5 parents",data.hits.length)+
        stat("Context characters",data.hits.reduce((n,h)=>n+(h.end-h.start),0))+
        stat("Retrieval",data.timing_ms+" ms",data.child_count+" child hits");
      $("p800Results").innerHTML=data.hits.map(p800HitHtml).join("") || empty("No parents retrieved");
    } catch (error) {
      $("p800Status").innerHTML=esc(errorText(error));
      $("p800Results").innerHTML=empty(errorText(error));
    } finally {
      button.disabled=!state.p800Status || !state.p800Status.ready;
    }
  }
  function needsReview(row) {
    if (row.state!=="completed" || !row.result) return false;
    const r=row.review || {};
    if (row.gold.answerable ? r.answer_grade==null : r.refusal_correct==null) return true;
    return row.result.claims.some((c,i)=>!(r.claim_reviews || []).some(v=>v.claim_index===i && v.supported!==null));
  }
  function ratio(metric) {
    return metric.value==null ? (metric.denominator ? "Pending review" : "Not applicable") : (metric.value*100).toFixed(1)+"%";
  }
  async function loadRuns(selected) {
    try {
      state.runs=(await api("/api/evaluations")).items;
      const id=selected || (state.run && state.run.run_id) || (state.runs[0] && state.runs[0].run_id);
      $("runSelector").innerHTML=state.runs.map(r=>'<option value="'+esc(r.run_id)+'">'+esc((r.synthetic ? "Synthetic test · " : "")+(statuses[r.state] || r.state)+" · "+r.run_id)+'</option>').join("") || "<option value=\"\">No experiments yet</option>";
      if (id && state.runs.some(r=>r.run_id===id)) {$("runSelector").value=id;await loadRun(id);}
      else {state.run=null;renderEvaluation();}
    } catch (error) {$("evaluationNotice").textContent=errorText(error);}
  }
  async function loadRun(id) {
    const seq=++requests.run;
    if (state.run && state.run.run_id!==id) {
      state.run=null;renderEvaluation();$("reportMeta").innerHTML=empty("Loading selected experiment…");
    }
    try {
      const run=await api(runPath(id));if (seq!==requests.run) return;
      state.run=run;renderEvaluation();
      if (["queued","running"].includes(run.state) && (!state.task || state.task.task_id!==run.task_id)) watchTask({task_id:run.task_id,run_id:run.run_id,kind:"evaluation"});
    } catch (error) {if (seq===requests.run) {state.run=null;renderEvaluation();$("evaluationNotice").textContent=errorText(error);}}
  }
  function renderEvaluation() {
    const run=state.run;
    configureButtons();
    if (!run) {$("metricGrid").innerHTML="";$("evaluationRows").innerHTML="";$("reportMeta").innerHTML=empty("No experiments yet. Configure the frozen question set and build all four indexes, then run an evaluation.");return;}
    $("evaluationNotice").textContent=(run.synthetic ? "Synthetic test results; not part of the formal course experiment." : "")+
      (run.review_complete ? "Review complete. Check reviewer attribution, errors, and the actual configuration." : "Review is incomplete; accuracy remains pending review.")+
      (run.configuration_warning ? " Warning: the actual generation model has changed; keep the old results and rebuild a comparable experiment." : "");
    $("reportMeta").innerHTML='<div><strong>'+esc(statuses[run.state] || run.state)+' · '+esc(run.cases.length)+" items · "+esc(run.run_id)+"</strong><span>Corpus "+version(run.corpus_version)+" · Question set "+version(run.gold_version)+" · Index "+version(run.index_version)+'</span></div>'+
      "<details><summary>View frozen configuration</summary>"+block(JSON.stringify(run.config,null,2))+'</details>';
    $("metricGrid").innerHTML=Object.keys(labels).map(condition=>{
      const s=run.summary[condition];
      return '<article class="metric"><h3>'+esc(labels[condition])+'</h3><div class="metric-value">'+ratio(s.answer_accuracy)+"</div><p>Answers "+s.answer_accuracy.numerator+'/'+s.answer_accuracy.denominator+" · Pending review "+s.answer_accuracy.pending+'</p>'+
        "<p>Refusals "+ratio(s.refusal_accuracy)+' ('+s.refusal_accuracy.numerator+'/'+s.refusal_accuracy.denominator+")</p><p>Citations "+ratio(s.citation_accuracy)+' ('+s.citation_accuracy.numerator+'/'+s.citation_accuracy.denominator+')</p>'+
        "<p>Failures "+s.errors+" · Processing "+s.processing+"</p><details><summary>Hits and performance</summary><p>Hit@1 any/all "+ratio(s.hit_at_1_any)+' / '+ratio(s.hit_at_1_all)+'</p><p>Hit@5 any/all '+ratio(s.hit_at_5_any)+' / '+ratio(s.hit_at_5_all)+'</p>'+
        '<p>partial '+s.partial_answers+' · wrong '+s.wrong_answers+" · Incorrect refusals "+s.misrefusals+"</p><p>Median context "+esc(s.context_chars.median)+" characters</p><p>Median retrieval/generation "+esc(s.successful_latency.retrieve_ms_median)+' / '+esc(s.successful_latency.generate_ms_median)+' ms</p>'+
        "<p>Known tokens "+s.tokens.total_tokens.known_total+"; unknown usage attempts "+s.tokens.total_tokens.unknown_attempts+'</p></details></article>';
    }).join("");
    const hit=v=>v==null ? "—" : v ? "Hit" : "Miss";
    $("evaluationRows").innerHTML=run.cases.filter(row=>state.filter==="all" || (state.filter==="pending" && needsReview(row)) ||
      (state.filter==="error" && row.state==="error") || (state.filter==="refuse" && row.result && row.result.status==="insufficient")).map(row=>{
      const score=row.review || {};
      const grade=row.gold.answerable ? ({correct:"Correct",partial:"Partially correct",wrong:"Incorrect"})[score.answer_grade] : score.refusal_correct==null ? "" : score.refusal_correct ? "Correct refusal" : "Incorrect refusal";
      return '<tr><td>'+esc(row.case_id)+'<span class="table-sub">'+esc(row.condition)+'</span></td><td>'+esc(row.gold.question)+'</td><td>'+(row.gold.answerable ? "Answerable" : "Should refuse")+'</td><td>'+
        hit(row.metrics && row.metrics.hit_at_1.all)+' / '+hit(row.metrics && row.metrics.hit_at_5.all)+'</td><td>'+esc(statuses[row.state] || row.state)+'<span class="table-sub">'+esc(grade || (row.state==="completed" ? "Pending review" : ""))+'</span></td>'+
        '<td><button class="table-link" data-case="'+esc(row.case_id)+'" data-condition="'+esc(row.condition)+'" data-run="'+esc(run.run_id)+"\">View / Score</button></td></tr>";
    }).join("");
  }
  function selectHtml(name,value,options) {
    return '<select class="select" name="'+name+'">'+options.map(o=>'<option value="'+esc(o[0])+'"'+(o[0]===value ? " selected" : "")+'>'+esc(o[1])+'</option>').join("")+'</select>';
  }
  function openCase(caseId,condition) {
    const row=state.run.cases.find(c=>c.case_id===caseId && c.condition===condition);if (!row) return;
    const score=draftScore(row);
    let html="<p>Experiment "+esc(state.run.run_id)+'</p><p>'+esc(row.gold.question)+'</p><p>'+esc(row.condition)+' · '+esc(statuses[row.state])+"</p><h3>System answer</h3>"+
      (row.result ? answerHtml(row.result) : block(errorText(row.error || {message:"Not yet processed"})))+
      "<h3>Reference answer and required facts (not sent to the model)</h3>"+block(row.gold.reference_answer || row.gold.refusal_reference || row.gold.unanswerable_reason)+
      block(row.gold.key_facts.join("\n"))+"<h3>Standard evidence</h3>"+row.gold.evidence.map(e=>evidenceHtml(e,state.run.corpus_version)).join("")+
      "<h3>Retrieved evidence for this round</h3>"+((row.trace && row.trace.retrieval && row.trace.retrieval.hits) || []).map(h=>'<p>['+h.rank+']</p>'+evidenceHtml(h,state.run.corpus_version)).join("");
    if (row.result && row.state==="completed") {
      html+="<form id=\"reviewForm\" class=\"review-form\"><h3>Answer and citation review</h3><label>Reviewer<input name=\"reviewer\" required maxlength=\"100\" value=\""+esc(score.reviewer || state.reviewer)+'"></label>';
      html+=row.gold.answerable ? "<label>Answer score"+selectHtml("answer_grade",score.answer_grade || "",[["","Pending review"],["correct","Correct and complete"],["partial","Partially correct"],["wrong","Incorrect / incorrect refusal"]])+'</label>' :
        "<label>Refusal judgment"+selectHtml("refusal_correct",score.refusal_correct==null ? "" : String(score.refusal_correct),[["","Pending review"],["true","Correct refusal"],["false","Refusal error / fabricated answer"]])+'</label>';
      row.result.claims.forEach((claim,index)=>{
        const review=(score.claim_reviews || []).find(r=>r.claim_index===index) || {};
        html+="<fieldset><legend>Claim "+(index+1)+'</legend><p>'+esc(claim.text)+" · Citation "+esc(claim.citation_numbers.join(", "))+"</p><label>Does the cited evidence support this claim?"+
          selectHtml("supported_"+index,review.supported==null ? "" : String(review.supported),[["","Pending review"],["true","Supported"],["false","Not supported"]])+"</label><label>Review reason<textarea name=\"reason_"+index+'" maxlength="1000">'+esc(review.reason || "")+'</textarea></label></fieldset>';
      });
      html+="<label>Required facts / Notes<textarea name=\"notes\" maxlength=\"2000\">"+esc(score.notes || "")+"</textarea></label><button class=\"button primary\" type=\"submit\">Save review</button><p>Only this question in this condition is modified; modification history is retained.</p></form>";
    }
    if (row.trace) html+="<details><summary>View saved run records</summary>"+block(JSON.stringify(row.trace,null,2))+'</details>';
    openDrawer("Evaluation · "+condition,caseId,html);reviewCase={run_id:state.run.run_id,case_id:caseId,condition,result:row.result,gold:row.gold};
  }
  async function saveReview(event) {
    if (event.target.id!=="reviewForm") return;event.preventDefault();
    const target=reviewCase;if (!target) return;
    const form=event.target,data=new FormData(form),button=form.querySelector("button");
    const body={reviewer:data.get("reviewer").trim(),notes:data.get("notes"),answer_grade:null,refusal_correct:null,claim_reviews:[]};
    if (target.gold.answerable) body.answer_grade=data.get("answer_grade") || null;
    else body.refusal_correct=data.get("refusal_correct")==="" ? null : data.get("refusal_correct")==="true";
    target.result.claims.forEach((claim,i)=>body.claim_reviews.push({claim_index:i,supported:data.get("supported_"+i)==="" ? null : data.get("supported_"+i)==="true",reason:data.get("reason_"+i)}));
    if (body.claim_reviews.some(r=>r.supported!==null && !r.reason.trim())) {toast("Every judged claim requires a verification reason.",true);return;}
    button.disabled=true;
    try {
      await api(runPath(target.run_id)+"/cases/"+encodeURIComponent(target.case_id)+query({condition:target.condition}),{method:"PATCH",body:JSON.stringify(body)});
      state.reviewer=body.reviewer;closeDrawer();reviewDrafts.delete(reviewKey(target));
      if (state.run && state.run.run_id===target.run_id) await loadRun(target.run_id);
      toast("Score saved.");
    } catch (error) {toast(errorText(error),true);button.disabled=false;}
  }
  async function download(format) {
    if (!state.run) return;
    try {
      const response=await fetch(runPath(state.run.run_id)+"/export"+query({format}));
      if (!response.ok) throw Object.assign(new Error("Export failed. Please refresh the experiment and try again."),{code:"EXPORT_FAILED"});
      const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
      a.href=url;a.download=state.run.run_id+"."+format;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch (error) {toast(errorText(error),true);}
  }
  function watchTask(planned) {
    const sequence=++taskSequence;let failures=0;
    state.task=planned;stored.set("derag.active-task.v1",planned);renderHealth();
    const poll=async()=>{
      if (sequence!==taskSequence) return;
      const id=planned.kind==="evaluation" ? "evaluationTaskStatus" : "indexTaskStatus";
      $(id).hidden=false;
      try {
        const task=await api("/api/tasks/"+encodeURIComponent(planned.task_id));if (sequence!==taskSequence) return;
        failures=0;
        $(id).textContent=(statuses[task.state] || task.state)+" · "+task.completed+"/"+task.total+" · "+task.task_id;
        if (planned.run_id && (!$("runSelector").value || $("runSelector").value===planned.run_id)) await loadRun(planned.run_id);
        if (["completed","failed"].includes(task.state)) {
          state.task=null;stored.remove("derag.active-task.v1");renderHealth();
          if (task.error) {$(id).textContent+=" · "+errorText(task.error);toast(errorText(task.error),true);}
          await loadHealth();await loadDocuments();if (planned.run_id) await loadRuns($("runSelector").value || planned.run_id);
          return;
        }
      } catch (error) {
        failures++;$(id).textContent=errorText(error)+" Task ID:"+planned.task_id;
        if (error.code==="NOT_FOUND" || failures>=5) {state.task=null;renderHealth();return;}
      }
      setTimeout(poll,2000);
    };
    poll();
  }
  async function startTask(kind) {
    if (!state.health || state.task) return;
    const button=kind==="evaluation" ? $("runEvaluationButton") : $("buildIndexesButton");
    button.disabled=true;
    try {
      const body={corpus_version:corpus()};
      if (kind==="evaluation") body.gold_version=state.health.configuration.gold_version;
      const planned=await post(kind==="evaluation" ? "/api/evaluations/run" : "/api/indexes/build",body);
      planned.kind=kind;watchTask(planned);if (planned.run_id) await loadRuns(planned.run_id);
    } catch (error) {toast(errorText(error),true);configureButtons();}
  }
  $("askForm").addEventListener("submit",ask);
  $("questionInput").addEventListener("keydown",e=>{if (e.key==="Enter" && !e.shiftKey && !e.isComposing) {e.preventDefault();$("askForm").requestSubmit();}});
  $("newSessionButton").addEventListener("click",()=>{if (state.pending) return;requests.history++;state.conversation=null;state.history=[];renderSessions();renderMessages();$("questionInput").focus();});
  $("sessionList").addEventListener("click",e=>{const b=e.target.closest("[data-session]");if (!b || state.pending) return;state.conversation=b.dataset.session;state.history=[];renderMessages();renderSessions();loadHistory(state.conversation);$("chatLayout").classList.remove("show-sessions");syncPanels();});
  document.querySelectorAll("[data-route]").forEach(b=>b.addEventListener("click",()=>navigate(b.dataset.route,true)));
  $("menuButton").addEventListener("click",()=>{$("sidebar").classList.toggle("open");$("scrim").hidden=!$("sidebar").classList.contains("open");syncPanels();});
  $("sessionToggle").addEventListener("click",()=>{$("chatLayout").classList.toggle("show-sessions");syncPanels();});
  $("scrim").addEventListener("click",()=>{$("sidebar").classList.remove("open");closeDrawer();syncPanels();});
  $("drawerClose").addEventListener("click",closeDrawer);
  $("drawerBody").addEventListener("submit",saveReview);
  document.addEventListener("click",e=>{
    const c=e.target.closest("[data-citation]");
    if (c) {const r=findResult(c.dataset.ask),citation=r && r.citations.find(v=>v.n===Number(c.dataset.citation));if (citation) openDrawer("Citations in this round ["+citation.n+"]",citation.title,"<p>Q&A "+esc(r.ask_id)+' · '+esc(r.condition)+" · Index "+version(r.index_version)+'</p>'+evidenceHtml(citation,r.corpus_version));return;}
    const source=e.target.closest("[data-source]");
    if (source) {openDocument(source.dataset.source,source.dataset.corpus,Number(source.dataset.start),Number(source.dataset.end));return;}
    const doc=e.target.closest("[data-document]");if (doc) {openDocument(doc.dataset.document,corpus());return;}
    const item=e.target.closest("[data-panel]");if (item) {const chunk=state.panels[item.dataset.panel][Number(item.dataset.index)];if (chunk) openDocument(chunk.document_id,chunk.corpus_version,chunk.start,chunk.end);return;}
    const row=e.target.closest("[data-case]");
    if (row && state.run) {
      if (row.dataset.run && row.dataset.run!==state.run.run_id) {toast("The experiment has been switched. Please reopen this question in the selected experiment.",true);return;}
      openCase(row.dataset.case,row.dataset.condition);
    }
  });
  $("docSearch").addEventListener("input",renderDocuments);
  $("buildIndexesButton").addEventListener("click",()=>startTask("indexes"));
  ["compareDocument","leftCondition","rightCondition"].forEach(id=>$(id).addEventListener("change",loadChunks));
  $("showChunksButton").addEventListener("click",loadChunks);$("compareForm").addEventListener("submit",compare);
  $("p800Form").addEventListener("submit",searchP800);
  $("runEvaluationButton").addEventListener("click",()=>startTask("evaluation"));
  $("runSelector").addEventListener("change",()=>{closeDrawer();loadRun($("runSelector").value);});
  $("refreshEvaluationButton").addEventListener("click",()=>loadRuns());
  $("exportReportButton").addEventListener("click",()=>download("json"));$("exportCsvButton").addEventListener("click",()=>download("csv"));
  document.querySelectorAll("[data-eval-filter]").forEach(b=>b.addEventListener("click",()=>{state.filter=b.dataset.evalFilter;document.querySelectorAll("[data-eval-filter]").forEach(v=>v.classList.toggle("active",v===b));renderEvaluation();}));
  $("openDesignButton").addEventListener("click",()=>window.open("/project-design","_blank","noopener"));
  $("aboutButton").addEventListener("click",()=>openDrawer("Backend status","Current configuration",state.health ? block(JSON.stringify(state.health,null,2)) : empty("Backend not connected. Please refresh the status.")));
  $("refreshButton").addEventListener("click",refresh);
  window.addEventListener("popstate",()=>navigate(Object.keys(paths).find(k=>paths[k]===location.pathname) || "chat",false));
  document.addEventListener("keydown",e=>{
    if (e.key==="Escape") {$("sidebar").classList.remove("open");closeDrawer();syncPanels();}
    if (e.key!=="Tab" || !$("detailDrawer").classList.contains("open")) return;
    const focusable=Array.from($("detailDrawer").querySelectorAll('button:not(:disabled),a[href],input,select,textarea,summary,[tabindex="0"]')).filter(v=>v.offsetParent!==null);
    const first=focusable[0],last=focusable[focusable.length-1];
    if (e.shiftKey && document.activeElement===first) {e.preventDefault();last.focus();}
    if (!e.shiftKey && document.activeElement===last) {e.preventDefault();first.focus();}
  });
  async function refresh() {
    await loadHealth();
    const results=await Promise.allSettled([loadSessions(),loadDocuments(),loadRuns()]);
    results.forEach(r=>{if (r.status==="rejected") toast(errorText(r.reason),true);});
    if (state.conversation) await loadHistory(state.conversation);else renderMessages();
    if (state.route==="compare") await loadChunks();
    if (state.route==="p800") await loadP800Status();
  }
  window.addEventListener("resize",syncPanels);
  syncPanels();configureButtons();renderMessages();
  navigate(Object.keys(paths).find(k=>paths[k]===location.pathname) || "chat",false);
  refresh().then(()=>{const task=stored.get("derag.active-task.v1");if (task && task.task_id && !state.task) watchTask(task);});
})();
