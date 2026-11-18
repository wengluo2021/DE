(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const labels = {f400:"固定窗口 · 400",s400:"法条结构 · 400",f800:"固定窗口 · 800",s800:"法条结构 · 800"};
  const paths = {chat:"/",documents:"/documents",compare:"/compare",evaluation:"/evaluation"};
  const names = {chat:"问答",documents:"文档库",compare:"分块对照",evaluation:"评估"};
  const statuses = {queued:"排队中",running:"运行中",completed:"已完成",failed:"失败",error:"失败",answered:"已回答",insufficient:"证据不足"};
  const errors = {
    OFFICIAL_DATA_NOT_CONFIGURED:"尚未接入A的冻结资料。",RETRIEVAL_NOT_CONFIGURED:"尚未配置正式资料或检索组件。",
    INDEX_NOT_READY:"请先建立当前语料的四组索引。",RETRIEVAL_DEPENDENCIES_NOT_INSTALLED:"检索依赖尚未安装。",
    INVALID_CORPUS_DATA:"冻结资料校验失败，请核对A的manifest、原始快照与处理后正文。",
    INDEX_PATH_TOO_LONG:"Windows索引目录过长，请缩短DERAG_DATA_DIR后重新建库。",
    GOLD_NOT_CONFIGURED:"A的冻结标准题尚未配置。",INVALID_GOLD_DATA:"标准题或其证据、版本校验未通过。",
    VERSION_MISMATCH:"请求版本与当前配置不一致，请刷新状态。",LLM_NOT_CONFIGURED:"尚未配置生成API。",
    LLM_AUTH_ERROR:"生成API未通过认证或模型权限检查。",LLM_RATE_LIMITED:"生成服务限流，请稍后查看状态。",
    EVALUATION_ACTIVE:"评估正在运行，请完成后再问答或建库。",TASK_ALREADY_RUNNING:"已有后台任务，请等待其完成。",
    PROCESS_INTERRUPTED:"上次运行被中断，已保存的结果仍可查看。",NOT_FOUND:"未找到这条已保存记录。",
    INVALID_REVIEW:"评分字段与题型或主张不一致，请检查。",NETWORK_ERROR:"连接中断。已提交的请求可能仍在处理，请先刷新历史或实验，避免重复提交。"
  };
  const state = {health:null,sessions:[],history:[],conversation:null,docs:[],runs:[],run:null,
    filter:"all",pending:false,route:"chat",panels:{left:[],right:[]},task:null,reviewer:""};
  const requests = {history:0,compare:0,run:0,document:0};
  const reviewDrafts=new Map();
  let taskSequence=0,toastTimer,returnFocus=null,reviewCase=null;
  const modeName = () => state.health && (state.health.mode==="test" ? "合成测试模式" : state.health.mode==="formal" ? "正式模式" : "开发模式");
  const corpus = () => state.health.configuration.corpus_version;
  const query = values => "?" + new URLSearchParams(values).toString();
  const version = v => esc(v ? v.slice(0,16) : "未配置");
  const stored = {
    get(key) {try {return JSON.parse(localStorage.getItem(key));} catch (_) {return null;}},
    set(key,value) {try {localStorage.setItem(key,JSON.stringify(value));} catch (_) {}},
    remove(key) {try {localStorage.removeItem(key);} catch (_) {}}
  };
  function errorText(error) {return (errors[error.code] || error.message || "请求未完成。") + (error.code ? " ["+error.code+"]" : "");}
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
      if (!response.ok) throw Object.assign(new Error(body.message || "服务请求失败"),{code:body.code || "HTTP_"+response.status});
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
    try {const parsed=new URL(url);if (!["https:","http:"].includes(parsed.protocol)) return "无有效来源地址";}
    catch (_) {return "无有效来源地址";}
    return '<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">打开原始来源 ↗</a>';
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
  }
  function renderHealth() {
    const h=state.health;
    $("serviceBadge").textContent=h ? modeName()+(h.ready ? " · 已就绪" : " · 未就绪") : "后台未连接";
    $("systemStatus").textContent=h ? modeName() : "后台未连接";
    $("systemMeta").textContent=h ? "语料 "+h.configuration.corpus_version : "请启动服务后刷新";
    let notice="无法读取后台。请确认服务已启动，然后点击右上角刷新。";
    if (h) {
      notice= h.ready ? (h.mode==="test" ? "当前为合成测试，回答与评分均不属于正式法规实验。" : "已连接后台。回答仅依据本轮检索证据；不足时会拒答。") :
        errors[h.components.retrieval.issue] || (!h.components.retrieval.ready ? errors.INDEX_NOT_READY : errors.LLM_NOT_CONFIGURED);
      if (state.task) notice="后台任务正在处理："+(state.task.kind==="evaluation" ? "四组评估" : "四组建库")+"。进度已保存，可刷新后继续查看。";
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
    if (route==="evaluation") loadRuns();
  }
  async function loadSessions() {
    try {state.sessions=(await api("/api/conversations")).items;renderSessions();}
    catch (error) {$("sessionList").innerHTML=empty(errorText(error));}
  }
  function renderSessions() {
    $("sessionList").innerHTML=state.sessions.map(s=>'<button class="session-row '+(s.id===state.conversation ? "active" : "")+'" data-session="'+esc(s.id)+'"><span class="session-row-main"><strong>'+esc(s.title)+'</strong><small>'+esc(new Date(s.updated_at).toLocaleString())+'</small></span></button>').join("") || empty("尚无保存的会话");
  }
  function answerHtml(result) {
    if (result.status==="insufficient") return '<p>'+esc(result.answer)+'</p>';
    return result.claims.map(claim=>'<p>'+esc(claim.text)+claim.citation_numbers.map(n=>
      '<button class="citation-button" type="button" data-ask="'+esc(result.ask_id)+'" data-citation="'+n+'" aria-label="查看本轮引用 '+n+'">['+n+']</button>').join("")+'</p>').join("");
  }
  function renderMessages() {
    $("messages").innerHTML=state.history.map(ask=>{
      const result=ask.result;
      return '<article class="message user"><div class="message-content"><div class="message-label">你 · '+esc(labels[ask.condition])+'</div><div class="message-text">'+esc(ask.question)+'</div></div></article>'+
        '<article class="message assistant"><div class="message-content"><div class="message-label">DERag · '+esc(statuses[ask.state] || ask.state)+'</div><div class="message-text">'+
        (result ? answerHtml(result) : esc(ask.error ? errorText(ask.error) : "请求处理中，请刷新历史查看结果。"))+'</div>'+
        (result ? '<div class="message-meta">'+esc(result.generation.model)+' · '+esc(result.condition)+' · '+version(result.index_version)+'</div>' : "")+'</div></article>';
    }).join("") || empty(state.health && state.health.ready ? "输入一个问题。回答中的引用可以点击，也可以用键盘打开。" : "知识库尚未就绪。先查看上方状态说明；已有会话仍可阅读。");
    if (state.pending) $("messages").insertAdjacentHTML("beforeend",'<div class="task-status" role="status">正在检索并生成，请等待。不要重复发送。</div>');
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
    return '<section class="evidence-card"><h3>'+esc(citation.title || citation.document_id)+'</h3><p>'+esc((citation.article_labels || [citation.article_id]).filter(Boolean).join("、"))+
      ' · ['+esc(citation.start)+', '+esc(citation.end)+')</p>'+block(citation.text)+
      '<p>'+sourceLink(citation.source_url)+'</p><button class="button" type="button" data-source="'+esc(citation.document_id)+'" data-corpus="'+esc(cv)+'" data-start="'+esc(citation.start)+'" data-end="'+esc(citation.end)+'">查看冻结原文</button></section>';
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
      const back=reviewCase ? '<button class="button" data-case="'+esc(reviewCase.case_id)+'" data-condition="'+esc(reviewCase.condition)+'" data-run="'+esc(reviewCase.run_id)+'">返回本题评分</button>' : "";
      openDrawer("冻结原文",doc.title,back+'<p>'+sourceLink(doc.source_url)+'</p><p>语料 '+version(doc.corpus_version)+' · '+esc(doc.articles.length)+' 条文</p><pre class="source-text">'+text+'</pre>');
      if ($("sourceHighlight")) $("sourceHighlight").scrollIntoView({block:"center"});
    } catch (error) {toast(errorText(error)+" 当前已保存的引用快照仍可核验。",true);}
  }
  async function loadDocuments() {
    if (!state.health) return;
    try {
      state.docs=(await api("/api/documents"+query({corpus_version:corpus()}))).items;
      $("documentNotice").textContent="以下为后台冻结资料，点击查看正文和来源。";
    } catch (error) {state.docs=[];$("documentNotice").textContent=errorText(error);}
    renderDocuments();
  }
  function renderDocuments() {
    const keyword=$("docSearch").value.trim().toLowerCase();
    const shown=state.docs.filter(d=>(d.title+" "+d.source_url).toLowerCase().includes(keyword));
    $("documentStats").innerHTML=stat("文档",state.docs.length)+stat("条文",state.docs.reduce((n,d)=>n+d.article_count,0))+stat("字符",state.docs.reduce((n,d)=>n+d.char_count,0));
    $("documentRows").innerHTML=shown.map(d=>'<tr><td><strong>'+esc(d.title)+'</strong></td><td>'+sourceLink(d.source_url)+'</td><td>'+d.char_count+'</td><td>'+d.article_count+'</td><td>'+version(d.corpus_version)+'</td><td><button class="table-link" data-document="'+esc(d.document_id)+'">查看</button></td></tr>').join("");
    $("documentEmpty").hidden=!!shown.length;
    const current=$("compareDocument").value;
    $("compareDocument").innerHTML=state.docs.map(d=>'<option value="'+esc(d.document_id)+'">'+esc(d.title)+'</option>').join("");
    if (state.docs.some(d=>d.document_id===current)) $("compareDocument").value=current;
  }
  function renderPanel(side,items,search) {
    state.panels[side]=items;
    $(side+"Label").textContent=labels[$(side+"Condition").value];
    $(side+"Count").textContent=items.length+(search ? " 个命中" : " 个块");
    $(side+"Chunks").innerHTML=items.map((item,index)=>'<article class="chunk-item"><div class="chunk-top"><span>#'+(item.rank || index+1)+'</span><span>'+esc(item.end-item.start)+' 字 · ['+esc(item.start)+', '+esc(item.end)+')</span></div>'+
      (search ? '<strong>'+esc(item.title)+'</strong><small>相似度 '+esc(item.score)+'</small>' : "")+'<p>'+esc(item.text)+'</p><button class="table-link" data-panel="'+side+'" data-index="'+index+'">查看原文</button></article>').join("") || empty("没有结果");
  }
  async function loadChunks() {
    const seq=++requests.compare;
    state.panels={left:[],right:[]};$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("读取分块中…");
    if (!state.health) {return;}
    if (!state.docs.length) await loadDocuments();
    if (seq!==requests.compare) return;
    const id=$("compareDocument").value;
    if (!id) {$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("没有可读取的冻结文档");return;}
    try {
      const sides=await Promise.all(["left","right"].map(side=>api("/api/documents/"+encodeURIComponent(id)+"/chunks"+query({corpus_version:corpus(),condition:$(side+"Condition").value}))));
      if (seq!==requests.compare) return;
      ["left","right"].forEach((side,i)=>renderPanel(side,sides[i].items,false));
      $("compareNotice").textContent="文档分块：显示后台实际入库的区间，不在浏览器重新切分。";
      $("compareSummary").innerHTML=sides.map((s,i)=>stat(i ? "右侧字符" : "左侧字符",s.items.reduce((n,c)=>n+c.end-c.start,0))).join("");
    } catch (error) {if (seq===requests.compare) {$("compareNotice").textContent=errorText(error);$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty(errorText(error));$("compareSummary").innerHTML="";}}
  }
  async function compare(event) {
    event.preventDefault();if (!state.health) return;
    const question=$("compareQuestion").value.trim();if (!question) return;
    const seq=++requests.compare;
    state.panels={left:[],right:[]};$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty("检索中…");
    try {
      const data=await post("/api/compare",{question,corpus_version:corpus(),left_condition:$("leftCondition").value,right_condition:$("rightCondition").value});
      if (seq!==requests.compare) return;
      ["left","right"].forEach(side=>renderPanel(side,data[side].hits,true));
      $("compareNotice").textContent="同题检索 · 索引 "+data.index_version+"；相似度不是正确概率。";
      $("compareSummary").innerHTML=["left","right"].map((side,i)=>stat(i ? "右侧上下文" : "左侧上下文",data[side].context_chars+" 字",data[side].timing_ms+" ms")).join("");
    } catch (error) {if (seq===requests.compare) {$("compareNotice").textContent=errorText(error);$("leftChunks").innerHTML=$("rightChunks").innerHTML=empty(errorText(error));$("compareSummary").innerHTML="";}}
  }
  function needsReview(row) {
    if (row.state!=="completed" || !row.result) return false;
    const r=row.review || {};
    if (row.gold.answerable ? r.answer_grade==null : r.refusal_correct==null) return true;
    return row.result.claims.some((c,i)=>!(r.claim_reviews || []).some(v=>v.claim_index===i && v.supported!==null));
  }
  function ratio(metric) {
    return metric.value==null ? (metric.denominator ? "待核验" : "不适用") : (metric.value*100).toFixed(1)+"%";
  }
  async function loadRuns(selected) {
    try {
      state.runs=(await api("/api/evaluations")).items;
      const id=selected || (state.run && state.run.run_id) || (state.runs[0] && state.runs[0].run_id);
      $("runSelector").innerHTML=state.runs.map(r=>'<option value="'+esc(r.run_id)+'">'+esc((r.synthetic ? "合成测试 · " : "")+(statuses[r.state] || r.state)+" · "+r.run_id)+'</option>').join("") || '<option value="">暂无实验</option>';
      if (id && state.runs.some(r=>r.run_id===id)) {$("runSelector").value=id;await loadRun(id);}
      else {state.run=null;renderEvaluation();}
    } catch (error) {$("evaluationNotice").textContent=errorText(error);}
  }
  async function loadRun(id) {
    const seq=++requests.run;
    if (state.run && state.run.run_id!==id) {
      state.run=null;renderEvaluation();$("reportMeta").innerHTML=empty("正在读取所选实验…");
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
    if (!run) {$("metricGrid").innerHTML="";$("evaluationRows").innerHTML="";$("reportMeta").innerHTML=empty("暂无实验。配置A的冻结题集与四组索引后再运行。");return;}
    $("evaluationNotice").textContent=(run.synthetic ? "合成测试结果，不属于正式课程实验。" : "")+
      (run.review_complete ? "人工核验已完成，请同时检查失败数和实际配置。" : "人工核验尚未完成，正确率保持待核验。")+
      (run.configuration_warning ? " 警告：实际生成模型发生变化，请保留旧结果并重新建立可比较的实验。" : "");
    $("reportMeta").innerHTML='<div><strong>'+esc(statuses[run.state] || run.state)+' · '+esc(run.cases.length)+' 项 · '+esc(run.run_id)+'</strong><span>语料 '+version(run.corpus_version)+' · 题集 '+version(run.gold_version)+' · 索引 '+version(run.index_version)+'</span></div>'+
      '<details><summary>查看冻结配置</summary>'+block(JSON.stringify(run.config,null,2))+'</details>';
    $("metricGrid").innerHTML=Object.keys(labels).map(condition=>{
      const s=run.summary[condition];
      return '<article class="metric"><h3>'+esc(labels[condition])+'</h3><div class="metric-value">'+ratio(s.answer_accuracy)+'</div><p>答案 '+s.answer_accuracy.numerator+'/'+s.answer_accuracy.denominator+' · 待评 '+s.answer_accuracy.pending+'</p>'+
        '<p>拒答 '+ratio(s.refusal_accuracy)+' ('+s.refusal_accuracy.numerator+'/'+s.refusal_accuracy.denominator+')</p><p>引用 '+ratio(s.citation_accuracy)+' ('+s.citation_accuracy.numerator+'/'+s.citation_accuracy.denominator+')</p>'+
        '<p>失败 '+s.errors+' · 处理中 '+s.processing+'</p><details><summary>命中与性能</summary><p>Hit@1 any/all '+ratio(s.hit_at_1_any)+' / '+ratio(s.hit_at_1_all)+'</p><p>Hit@5 any/all '+ratio(s.hit_at_5_any)+' / '+ratio(s.hit_at_5_all)+'</p>'+
        '<p>partial '+s.partial_answers+' · wrong '+s.wrong_answers+' · 误拒答 '+s.misrefusals+'</p><p>上下文中位数 '+esc(s.context_chars.median)+' 字</p><p>检索/生成中位数 '+esc(s.successful_latency.retrieve_ms_median)+' / '+esc(s.successful_latency.generate_ms_median)+' ms</p>'+
        '<p>已知token '+s.tokens.total_tokens.known_total+'；未知usage尝试 '+s.tokens.total_tokens.unknown_attempts+'</p></details></article>';
    }).join("");
    const hit=v=>v==null ? "—" : v ? "命中" : "未命中";
    $("evaluationRows").innerHTML=run.cases.filter(row=>state.filter==="all" || (state.filter==="pending" && needsReview(row)) ||
      (state.filter==="error" && row.state==="error") || (state.filter==="refuse" && row.result && row.result.status==="insufficient")).map(row=>{
      const score=row.review || {};
      const grade=row.gold.answerable ? ({correct:"正确",partial:"部分正确",wrong:"错误"})[score.answer_grade] : score.refusal_correct==null ? "" : score.refusal_correct ? "拒答正确" : "拒答错误";
      return '<tr><td>'+esc(row.case_id)+'<span class="table-sub">'+esc(row.condition)+'</span></td><td>'+esc(row.gold.question)+'</td><td>'+(row.gold.answerable ? "可答题" : "应拒答")+'</td><td>'+
        hit(row.metrics && row.metrics.hit_at_1.all)+' / '+hit(row.metrics && row.metrics.hit_at_5.all)+'</td><td>'+esc(statuses[row.state] || row.state)+'<span class="table-sub">'+esc(grade || (row.state==="completed" ? "待核验" : ""))+'</span></td>'+
        '<td><button class="table-link" data-case="'+esc(row.case_id)+'" data-condition="'+esc(row.condition)+'" data-run="'+esc(run.run_id)+'">查看 / 评分</button></td></tr>';
    }).join("");
  }
  function selectHtml(name,value,options) {
    return '<select class="select" name="'+name+'">'+options.map(o=>'<option value="'+esc(o[0])+'"'+(o[0]===value ? " selected" : "")+'>'+esc(o[1])+'</option>').join("")+'</select>';
  }
  function openCase(caseId,condition) {
    const row=state.run.cases.find(c=>c.case_id===caseId && c.condition===condition);if (!row) return;
    const score=draftScore(row);
    let html='<p>实验 '+esc(state.run.run_id)+'</p><p>'+esc(row.gold.question)+'</p><p>'+esc(row.condition)+' · '+esc(statuses[row.state])+'</p><h3>系统答案</h3>'+
      (row.result ? answerHtml(row.result) : block(errorText(row.error || {message:"尚未处理"})))+
      '<h3>参考答案与必要事实（不发送给模型）</h3>'+block(row.gold.reference_answer || row.gold.unanswerable_reason)+
      block(row.gold.key_facts.join("\n"))+'<h3>标准证据</h3>'+row.gold.evidence.map(e=>evidenceHtml(e,state.run.corpus_version)).join("")+
      '<h3>本轮检索证据</h3>'+((row.trace && row.trace.retrieval && row.trace.retrieval.hits) || []).map(h=>'<p>['+h.rank+']</p>'+evidenceHtml(h,state.run.corpus_version)).join("");
    if (row.result && row.state==="completed") {
      html+='<form id="reviewForm" class="review-form"><h3>人工核验</h3><label>评审人<input name="reviewer" required maxlength="100" value="'+esc(score.reviewer || state.reviewer)+'"></label>';
      html+=row.gold.answerable ? '<label>答案评分'+selectHtml("answer_grade",score.answer_grade || "",[["","未核验"],["correct","正确且完整"],["partial","部分正确"],["wrong","错误 / 误拒答"]])+'</label>' :
        '<label>拒答是否正确'+selectHtml("refusal_correct",score.refusal_correct==null ? "" : String(score.refusal_correct),[["","未核验"],["true","正确拒答"],["false","拒答错误 / 编造答案"]])+'</label>';
      row.result.claims.forEach((claim,index)=>{
        const review=(score.claim_reviews || []).find(r=>r.claim_index===index) || {};
        html+='<fieldset><legend>主张 '+(index+1)+'</legend><p>'+esc(claim.text)+' · 引用 '+esc(claim.citation_numbers.join(", "))+'</p><label>所引证据能否支持'+
          selectHtml("supported_"+index,review.supported==null ? "" : String(review.supported),[["","未核验"],["true","能支持"],["false","不能支持"]])+'</label><label>核验理由<textarea name="reason_'+index+'" maxlength="1000">'+esc(review.reason || "")+'</textarea></label></fieldset>';
      });
      html+='<label>必要事实核对 / 备注<textarea name="notes" maxlength="2000">'+esc(score.notes || "")+'</textarea></label><button class="button primary" type="submit">保存本题评分</button><p>只修改本条件本题；修改历史会保留。</p></form>';
    }
    if (row.trace) html+='<details><summary>查看已保存的运行记录</summary>'+block(JSON.stringify(row.trace,null,2))+'</details>';
    openDrawer("评估 · "+condition,caseId,html);reviewCase={run_id:state.run.run_id,case_id:caseId,condition,result:row.result,gold:row.gold};
  }
  async function saveReview(event) {
    if (event.target.id!=="reviewForm") return;event.preventDefault();
    const target=reviewCase;if (!target) return;
    const form=event.target,data=new FormData(form),button=form.querySelector("button");
    const body={reviewer:data.get("reviewer").trim(),notes:data.get("notes"),answer_grade:null,refusal_correct:null,claim_reviews:[]};
    if (target.gold.answerable) body.answer_grade=data.get("answer_grade") || null;
    else body.refusal_correct=data.get("refusal_correct")==="" ? null : data.get("refusal_correct")==="true";
    target.result.claims.forEach((claim,i)=>body.claim_reviews.push({claim_index:i,supported:data.get("supported_"+i)==="" ? null : data.get("supported_"+i)==="true",reason:data.get("reason_"+i)}));
    if (body.claim_reviews.some(r=>r.supported!==null && !r.reason.trim())) {toast("每条已判断的主张都需要核验理由。",true);return;}
    button.disabled=true;
    try {
      await api(runPath(target.run_id)+"/cases/"+encodeURIComponent(target.case_id)+query({condition:target.condition}),{method:"PATCH",body:JSON.stringify(body)});
      state.reviewer=body.reviewer;closeDrawer();reviewDrafts.delete(reviewKey(target));
      if (state.run && state.run.run_id===target.run_id) await loadRun(target.run_id);
      toast("评分已保存。");
    } catch (error) {toast(errorText(error),true);button.disabled=false;}
  }
  async function download(format) {
    if (!state.run) return;
    try {
      const response=await fetch(runPath(state.run.run_id)+"/export"+query({format}));
      if (!response.ok) throw Object.assign(new Error("导出失败，请刷新实验后重试。"),{code:"EXPORT_FAILED"});
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
        failures++;$(id).textContent=errorText(error)+" 任务编号："+planned.task_id;
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
    if (c) {const r=findResult(c.dataset.ask),citation=r && r.citations.find(v=>v.n===Number(c.dataset.citation));if (citation) openDrawer("本轮引用 ["+citation.n+"]",citation.title,'<p>问答 '+esc(r.ask_id)+' · '+esc(r.condition)+' · 索引 '+version(r.index_version)+'</p>'+evidenceHtml(citation,r.corpus_version));return;}
    const source=e.target.closest("[data-source]");
    if (source) {openDocument(source.dataset.source,source.dataset.corpus,Number(source.dataset.start),Number(source.dataset.end));return;}
    const doc=e.target.closest("[data-document]");if (doc) {openDocument(doc.dataset.document,corpus());return;}
    const item=e.target.closest("[data-panel]");if (item) {const chunk=state.panels[item.dataset.panel][Number(item.dataset.index)];if (chunk) openDocument(chunk.document_id,chunk.corpus_version,chunk.start,chunk.end);return;}
    const row=e.target.closest("[data-case]");
    if (row && state.run) {
      if (row.dataset.run && row.dataset.run!==state.run.run_id) {toast("实验已切换，请在所选实验中重新打开该题。",true);return;}
      openCase(row.dataset.case,row.dataset.condition);
    }
  });
  $("docSearch").addEventListener("input",renderDocuments);
  $("buildIndexesButton").addEventListener("click",()=>startTask("indexes"));
  ["compareDocument","leftCondition","rightCondition"].forEach(id=>$(id).addEventListener("change",loadChunks));
  $("showChunksButton").addEventListener("click",loadChunks);$("compareForm").addEventListener("submit",compare);
  $("runEvaluationButton").addEventListener("click",()=>startTask("evaluation"));
  $("runSelector").addEventListener("change",()=>{closeDrawer();loadRun($("runSelector").value);});
  $("refreshEvaluationButton").addEventListener("click",()=>loadRuns());
  $("exportReportButton").addEventListener("click",()=>download("json"));$("exportCsvButton").addEventListener("click",()=>download("csv"));
  document.querySelectorAll("[data-eval-filter]").forEach(b=>b.addEventListener("click",()=>{state.filter=b.dataset.evalFilter;document.querySelectorAll("[data-eval-filter]").forEach(v=>v.classList.toggle("active",v===b));renderEvaluation();}));
  $("openDesignButton").addEventListener("click",()=>window.open("/project-design","_blank","noopener"));
  $("aboutButton").addEventListener("click",()=>openDrawer("后台状态","当前配置",state.health ? block(JSON.stringify(state.health,null,2)) : empty("后台未连接，请刷新状态。")));
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
  }
  window.addEventListener("resize",syncPanels);
  syncPanels();configureButtons();renderMessages();
  navigate(Object.keys(paths).find(k=>paths[k]===location.pathname) || "chat",false);
  refresh().then(()=>{const task=stored.get("derag.active-task.v1");if (task && task.task_id && !state.task) watchTask(task);});
})();
