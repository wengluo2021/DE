(function () {
  "use strict";

  const STORE_KEY = "derag.frontend.preview.v1";
  const routePaths = { chat: "/", documents: "/documents", compare: "/compare", evaluation: "/evaluation" };
  const routeNames = { chat: "问答", documents: "文档库", compare: "分块对照", evaluation: "评估" };
  const conditions = {
    f400: { label: "固定窗口 · 400", kind: "fixed", size: 400 },
    s400: { label: "法条结构 · 400", kind: "structured", size: 400 },
    f800: { label: "固定窗口 · 800", kind: "fixed", size: 800 },
    s800: { label: "法条结构 · 800", kind: "structured", size: 800 }
  };
  const demoDocs = [
    {
      id: "demo-method",
      title: "分块方法说明（界面演示）",
      source: "DERag 前端样本",
      importedAt: "2026-11-17T08:00:00",
      kind: "demo",
      text: "第一章 分块方法\n第十条 固定窗口从文档开头按固定字数连续切分。到达长度上限时直接切开，因此可能把一句话或一条规定分到两个块里。它是简单、可复现的基线。\n第十一条 法条结构感知先识别章和条的边界，尽量把完整条文保留在一个块里。相邻短条文可以合并；单条过长时再按句拆分。\n第十二条 两种方法使用同一份原文、同一个向量模型和同一批问题。比较时要记录检索命中、回答正确性、引用准确性与返回文本长度。\n第二章 引用\n第十三条 每条事实性回答都要附来源编号。编号应能定位到文档、条文、文本块和原文片段。只有编号存在并不代表引用内容支持结论。"
    },
    {
      id: "demo-eval",
      title: "评估口径说明（界面演示）",
      source: "DERag 前端样本",
      importedAt: "2026-11-17T08:00:00",
      kind: "demo",
      text: "第一章 问题集\n第一条 评估集由可作答题和应拒答题组成。可作答题需要人工参考答案和标准证据区间，应拒答题用于检查系统是否编造。\n第二条 问题与标准证据应在查看不同分块方案的检索结果之前确定。\n第二章 指标\n第三条 检索命中率检查前几块是否共同覆盖标准证据。回答正确率由人工对照原文判断。引用准确率逐条核查回答的事实性结论是否由所引文本支持。"
    }
  ];
  const demoCitations = {
    chunking: [
      { n: 1, documentId: "demo-method", title: "分块方法说明（界面演示）", article: "第十条", chunkId: "demo-f400-1", text: "固定窗口从文档开头按固定字数连续切分。到达长度上限时直接切开，因此可能把一句话或一条规定分到两个块里。", source: "DERag 前端样本" },
      { n: 2, documentId: "demo-method", title: "分块方法说明（界面演示）", article: "第十一条", chunkId: "demo-s400-1", text: "法条结构感知先识别章和条的边界，尽量把完整条文保留在一个块里。相邻短条文可以合并；单条过长时再按句拆分。", source: "DERag 前端样本" }
    ],
    citation: [
      { n: 1, documentId: "demo-method", title: "分块方法说明（界面演示）", article: "第十三条", chunkId: "demo-s400-2", text: "每条事实性回答都要附来源编号。编号应能定位到文档、条文、文本块和原文片段。只有编号存在并不代表引用内容支持结论。", source: "DERag 前端样本" }
    ]
  };
  const demoCases = [
    { id: "D01", question: "固定窗口会切断条文吗？", type: "可作答", f400: true, s400: true, state: "hit", note: "两组都找到了演示文档中的相关片段。" },
    { id: "D02", question: "为什么要保留完整法条？", type: "可作答", f400: false, s400: true, state: "miss", note: "示例中结构感知方案覆盖了完整证据，固定窗口只命中片段。" },
    { id: "D03", question: "引用编号要能定位到哪里？", type: "可作答", f400: true, s400: true, state: "hit", note: "引用需回到文档、条文、块和原文片段。" },
    { id: "D04", question: "真实法规库现在已经建好了吗？", type: "应拒答", f400: null, s400: null, state: "refuse", note: "当前只有界面样本，真实法规索引尚未接入。" }
  ];

  const $ = function (id) { return document.getElementById(id); };
  const esc = function (value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  };
  const icon = function (name, extra) {
    return '<svg class="icon' + (extra ? " " + extra : "") + '"><use href="#i-' + name + '"/></svg>';
  };
  const formatDate = function (value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
  };
  const uid = function (prefix) { return prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7); };
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(STORE_KEY) || "{}"); } catch (_) { saved = {}; }
  const state = {
    route: "chat",
    docs: demoDocs.concat(Array.isArray(saved.docs) ? saved.docs.filter(function (d) { return d && d.kind === "local"; }) : []),
    sessions: Array.isArray(saved.sessions) && saved.sessions.length ? saved.sessions : [{
      id: "demo-session",
      title: "两种分块方法有什么区别？",
      createdAt: "2026-11-17T08:00:00",
      messages: [
        { role: "user", text: "两种分块方法有什么区别？", at: "2026-11-17T08:00:00" },
        { role: "assistant", text: "固定窗口按固定字数切分，可能把一句话或条文切到两个块里[1]。法条结构感知会先识别条文边界，尽量保留完整规定[2]。", citations: demoCitations.chunking, at: "2026-11-17T08:00:00", demo: true }
      ]
    }],
    activeSession: saved.activeSession || "demo-session",
    chatCondition: saved.chatCondition || "s400",
    docSearch: "",
    selectedDoc: "demo-method",
    leftCondition: "f400",
    rightCondition: "s400",
    evalFilter: "all",
    drawerKind: null,
    drawerData: null
  };
  if (!state.sessions.some(function (s) { return s.id === state.activeSession; })) state.activeSession = state.sessions[0].id;
  let toastTimer;

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        docs: state.docs.filter(function (d) { return d.kind === "local"; }),
        sessions: state.sessions,
        activeSession: state.activeSession,
        chatCondition: state.chatCondition
      }));
      return true;
    } catch (_) {
      showToast("浏览器存储空间不足，本次更改无法持久保存。", true);
      return false;
    }
  }

  function showToast(message, error) {
    const element = $("toast");
    element.textContent = message;
    element.classList.toggle("error", Boolean(error));
    element.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { element.classList.remove("show"); }, 3700);
  }

  function activeSession() { return state.sessions.find(function (session) { return session.id === state.activeSession; }); }
  function getDoc(id) { return state.docs.find(function (doc) { return doc.id === id; }); }

  function navigate(route, push) {
    if (!routePaths[route]) route = "chat";
    state.route = route;
    document.title = "DERag · " + routeNames[route];
    $("pageTitle").textContent = routeNames[route];
    document.querySelectorAll("[data-route]").forEach(function (button) {
      const current = button.dataset.route === route;
      button.classList.toggle("active", current);
      if (current) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    document.querySelectorAll(".view").forEach(function (view) {
      const current = view.id === "view-" + route;
      view.classList.toggle("active", current);
      view.hidden = !current;
    });
    if (push !== false && location.pathname !== routePaths[route]) history.pushState({ route: route }, "", routePaths[route]);
    $("sidebar").classList.remove("open");
    $("chatLayout").classList.remove("show-sessions");
    if (!state.drawerKind) $("scrim").hidden = true;
    if (route === "chat") renderChat();
    if (route === "documents") renderDocuments();
    if (route === "compare") renderCompare();
    if (route === "evaluation") renderEvaluation();
  }

  function renderSessions() {
    $("sessionList").innerHTML = state.sessions.map(function (session) {
      return '<div class="session-entry"><button type="button" class="session-row' +
        (session.id === state.activeSession ? ' active' : '') + '" data-session="' + esc(session.id) +
        '">' + icon("message") + '<span class="session-row-main"><strong>' + esc(session.title || "新会话") +
        '</strong><small>' + esc(formatDate(session.createdAt)) + '</small></span></button><button class="session-delete" type="button" data-delete-session="' +
        esc(session.id) + '" aria-label="删除会话" title="删除会话">' + icon("trash") + '</button></div>';
    }).join("");
  }

  function renderTextWithCitations(text, citations, messageIndex) {
    const byNumber = new Map((citations || []).map(function (item) { return [String(item.n), item]; }));
    return String(text || "").split(/(\[\d+\])/g).map(function (part) {
      const match = /^\[(\d+)\]$/.exec(part);
      if (match && byNumber.has(match[1])) {
        return '<button class="cite-button" type="button" data-citation="' + esc(match[1]) + '" data-message-index="' + messageIndex + '" title="查看来源">' + esc(part) + '</button>';
      }
      return esc(part);
    }).join("");
  }

  function renderMessages() {
    const session = activeSession();
    const messages = session ? session.messages : [];
    $("messages").innerHTML = (messages.length ? "" :
      '<div class="chat-intro"><div class="intro-symbol">' + icon("message") +
      '</div><h2>开始新会话</h2><p>当前连接的是界面演示知识库。</p></div>') +
      messages.map(function (message, index) {
        const user = message.role === "user";
        const system = message.role === "system";
        const label = user ? "你" : system ? "系统" : "DERag";
        return '<article class="message ' + (user ? "user" : system ? "system" : "assistant") +
          '"><div class="message-avatar">' + (user ? "我" : "DE") +
          '</div><div class="message-body"><div class="message-label">' + label +
          '</div><div class="message-text">' + renderTextWithCitations(message.text, message.citations, index) +
          '</div><div class="message-meta"><span>' + esc(formatDate(message.at)) +
          '</span>' + (message.demo ? '<span class="status-tag demo">演示回答</span>' : '') +
          '</div>' + (!user && !system ? '<div class="message-tools"><button type="button" class="mini-button" data-copy-message="' + index +
          '">' + icon("copy") + '复制回答</button></div>' : '') + '</div></article>';
      }).join("");
    $("messages").scrollTop = $("messages").scrollHeight;
    $("suggestions").hidden = messages.length > 4;
  }

  function renderChat() {
    $("chatCondition").value = state.chatCondition;
    renderSessions();
    renderMessages();
  }

  function newSession() {
    const session = { id: uid("session"), title: "新会话", createdAt: new Date().toISOString(), messages: [] };
    state.sessions.unshift(session);
    state.activeSession = session.id;
    save();
    renderChat();
    $("chatLayout").classList.remove("show-sessions");
    $("questionInput").focus();
  }

  function demoResponse(question) {
    if (/分块|固定窗口|结构感知|怎么切|切分/.test(question)) {
      return {
        role: "assistant",
        text: "固定窗口按固定字数切分，可能把一句话或条文切到两个块里[1]。法条结构感知会先识别条文边界，尽量保留完整规定[2]。",
        citations: demoCitations.chunking,
        demo: true
      };
    }
    if (/引用|来源|追溯|原文/.test(question)) {
      return {
        role: "assistant",
        text: "引用编号应能定位到文档、条文、文本块和原文片段[1]。编号存在仍需核查它是否真正支持回答。",
        citations: demoCitations.citation,
        demo: true
      };
    }
    return {
      role: "system",
      text: "当前仅提供前端预览，尚未连接真实法规知识库和 LLM。此问题没有演示回答，不能据此作法律判断。"
    };
  }

  function submitQuestion(raw) {
    const question = String(raw || "").trim();
    if (!question) return;
    if (question.length > 1000) { showToast("问题不能超过 1000 字。", true); return; }
    let session = activeSession();
    if (!session) { newSession(); session = activeSession(); }
    if (!session.messages.length) session.title = question.slice(0, 26);
    const now = new Date().toISOString();
    session.messages.push({ role: "user", text: question, at: now });
    session.messages.push(Object.assign(demoResponse(question), { at: new Date().toISOString() }));
    state.sessions = [session].concat(state.sessions.filter(function (item) { return item.id !== session.id; }));
    save();
    $("questionInput").value = "";
    renderChat();
  }

  function statHtml(label, value, extra) {
    return '<div class="stat-item"><span>' + esc(label) + '</span><strong>' + esc(value) + '</strong>' +
      (extra ? '<span>' + esc(extra) + '</span>' : '') + '</div>';
  }

  function renderDocuments() {
    const localCount = state.docs.filter(function (doc) { return doc.kind === "local"; }).length;
    const charCount = state.docs.reduce(function (sum, doc) { return sum + doc.text.length; }, 0);
    $("documentStats").innerHTML = statHtml("文档总数", String(state.docs.length)) +
      statHtml("本地导入", String(localCount)) + statHtml("文本字符", charCount.toLocaleString("zh-CN"));
    $("docSearch").value = state.docSearch;
    const keyword = state.docSearch.trim().toLowerCase();
    const shown = state.docs.filter(function (doc) {
      return !keyword || (doc.title + " " + doc.source).toLowerCase().includes(keyword);
    });
    $("documentRows").innerHTML = shown.map(function (doc) {
      return '<tr><td><span class="table-title">' + icon("file", "small") + ' ' + esc(doc.title) +
        '</span><span class="table-sub">' + esc(doc.id) + '</span></td><td>' + esc(doc.source) +
        '</td><td>' + doc.text.length.toLocaleString("zh-CN") +
        '</td><td><span class="status-tag ' + (doc.kind === "demo" ? "demo" : "") + '">' +
        (doc.kind === "demo" ? "界面样本" : "仅本地") + '</span></td><td>' + esc(formatDate(doc.importedAt)) +
        '</td><td class="action-cell"><button class="table-link" type="button" data-open-doc="' + esc(doc.id) +
        '">查看' + icon("chevron", "small") + '</button></td></tr>';
    }).join("");
    $("documentEmpty").hidden = shown.length !== 0;
    renderCompareOptions();
  }

  async function importFiles(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    let imported = 0;
    for (const file of list) {
      if (!/\.(md|txt)$/i.test(file.name)) { showToast("仅支持 .md 和 .txt 文件。", true); continue; }
      if (file.size > 250000) { showToast(file.name + " 超过 250 KB，未导入。", true); continue; }
      if (state.docs.length >= 20) { showToast("前端预览最多保留 20 份文档。", true); break; }
      const text = await file.text();
      if (!text.trim()) { showToast(file.name + " 是空文件。", true); continue; }
      const doc = { id: uid("local"), title: file.name, source: "浏览器本地导入", importedAt: new Date().toISOString(), kind: "local", text: text };
      state.docs.unshift(doc);
      imported += 1;
    }
    if (imported) {
      save();
      renderDocuments();
      renderCompare();
      showToast("已在浏览器中导入 " + imported + " 份文档。");
    }
    $("fileInput").value = "";
  }

  function splitFixed(text, maxChars) {
    const chunks = [];
    for (let start = 0; start < text.length; start += maxChars) {
      const end = Math.min(start + maxChars, text.length);
      chunks.push({ start: start, end: end, text: text.slice(start, end) });
    }
    return chunks;
  }

  function splitLongUnit(text, start, maxChars) {
    const chunks = [];
    let offset = 0;
    while (offset < text.length) {
      let end = Math.min(offset + maxChars, text.length);
      if (end < text.length) {
        const portion = text.slice(offset + Math.floor(maxChars * .55), end);
        const punctuation = Math.max(portion.lastIndexOf("。"), portion.lastIndexOf("；"), portion.lastIndexOf("！"), portion.lastIndexOf("？"));
        if (punctuation >= 0) end = offset + Math.floor(maxChars * .55) + punctuation + 1;
      }
      chunks.push({ start: start + offset, end: start + end, text: text.slice(offset, end) });
      offset = end;
    }
    return chunks;
  }

  function splitStructured(text, maxChars) {
    const marker = /第[一二三四五六七八九十百千万零〇\d]+[章节条]/g;
    const starts = [0];
    let match;
    while ((match = marker.exec(text)) !== null) if (match.index > 0) starts.push(match.index);
    starts.push(text.length);
    const units = [];
    for (let i = 0; i < starts.length - 1; i += 1) {
      if (starts[i] < starts[i + 1]) units.push({ start: starts[i], end: starts[i + 1], text: text.slice(starts[i], starts[i + 1]) });
    }
    const chunks = [];
    let current = null;
    function flush() { if (current) chunks.push(current); current = null; }
    for (const unit of units) {
      if (/^第[一二三四五六七八九十百千万零〇\d]+章/.test(unit.text)) flush();
      if (unit.text.length > maxChars) {
        flush();
        chunks.push.apply(chunks, splitLongUnit(unit.text, unit.start, maxChars));
      } else if (current && current.text.length + unit.text.length <= maxChars) {
        current.end = unit.end;
        current.text += unit.text;
      } else {
        flush();
        current = { start: unit.start, end: unit.end, text: unit.text };
      }
    }
    flush();
    return chunks;
  }

  function chunksFor(doc, condition) {
    const config = conditions[condition] || conditions.s400;
    return config.kind === "fixed" ? splitFixed(doc.text, config.size) : splitStructured(doc.text, config.size);
  }

  function chunkHtml(chunk, index, condition, docId) {
    const excerpt = chunk.text.length > 270 ? chunk.text.slice(0, 270) + "…" : chunk.text;
    return '<article class="chunk-item"><div class="chunk-top"><span>#' + String(index + 1).padStart(2, "0") +
      '</span><span>' + chunk.text.length + ' 字 · ' + chunk.start + "–" + chunk.end +
      '</span></div><p>' + esc(excerpt) + '</p>' +
      (chunk.text.length > 270 ? '<button class="table-link more" type="button" data-open-chunk="' +
        esc(docId) + '" data-condition="' + esc(condition) + '" data-index="' + index + '">查看全文' +
        icon("chevron", "small") + '</button>' : '') + '</article>';
  }

  function renderCompareOptions() {
    const select = $("compareDocument");
    if (!getDoc(state.selectedDoc)) state.selectedDoc = state.docs[0] ? state.docs[0].id : "";
    select.innerHTML = state.docs.map(function (doc) {
      return '<option value="' + esc(doc.id) + '">' + esc(doc.title) + '</option>';
    }).join("");
    select.value = state.selectedDoc;
  }

  function renderCompare() {
    renderCompareOptions();
    const doc = getDoc(state.selectedDoc);
    $("leftCondition").value = state.leftCondition;
    $("rightCondition").value = state.rightCondition;
    if (!doc) {
      $("compareSummary").innerHTML = "";
      $("leftChunks").innerHTML = '<div class="empty-table">暂无文档</div>';
      $("rightChunks").innerHTML = "";
      return;
    }
    const left = chunksFor(doc, state.leftCondition);
    const right = chunksFor(doc, state.rightCondition);
    const avg = function (chunks) { return chunks.length ? Math.round(chunks.reduce(function (n, c) { return n + c.text.length; }, 0) / chunks.length) : 0; };
    $("leftLabel").textContent = conditions[state.leftCondition].label;
    $("rightLabel").textContent = conditions[state.rightCondition].label;
    $("leftCount").textContent = left.length + " 块";
    $("rightCount").textContent = right.length + " 块";
    $("compareSummary").innerHTML = statHtml("原文字符", doc.text.length.toLocaleString("zh-CN")) +
      statHtml("左 / 右块数", left.length + " / " + right.length) +
      statHtml("左 / 右平均块长", avg(left) + " / " + avg(right));
    $("leftChunks").innerHTML = left.map(function (chunk, index) { return chunkHtml(chunk, index, state.leftCondition, doc.id); }).join("");
    $("rightChunks").innerHTML = right.map(function (chunk, index) { return chunkHtml(chunk, index, state.rightCondition, doc.id); }).join("");
  }

  function renderEvaluation() {
    const answerable = demoCases.filter(function (item) { return item.type === "可作答"; });
    const fHits = answerable.filter(function (item) { return item.f400; }).length;
    const sHits = answerable.filter(function (item) { return item.s400; }).length;
    $("metricGrid").innerHTML = [
      { label: "F400 · Hit@5", value: fHits + " / " + answerable.length, foot: "界面示例" },
      { label: "S400 · Hit@5", value: sHits + " / " + answerable.length, foot: "界面示例" },
      { label: "答案正确率", value: "待核验", foot: "需要人工评分" },
      { label: "引用准确率", value: "待核验", foot: "需要逐条核对" }
    ].map(function (m) {
      return '<div class="metric"><span class="metric-label">' + esc(m.label) + '</span><strong class="metric-value">' +
        esc(m.value) + '</strong><span class="metric-foot">' + esc(m.foot) + '</span></div>';
    }).join("");
    document.querySelectorAll("[data-eval-filter]").forEach(function (button) {
      button.classList.toggle("active", button.dataset.evalFilter === state.evalFilter);
    });
    const cases = demoCases.filter(function (item) { return state.evalFilter === "all" || item.state === state.evalFilter; });
    $("evaluationRows").innerHTML = cases.map(function (item) {
      const statusText = { hit: "已命中", miss: "存在差异", refuse: "应拒答" }[item.state];
      return '<tr><td><strong>' + esc(item.id) + '</strong></td><td>' + esc(item.question) + '</td><td>' +
        esc(item.type) + '</td><td>' + (item.f400 === null ? "—" : item.f400 ? "命中" : "未命中") +
        '</td><td>' + (item.s400 === null ? "—" : item.s400 ? "命中" : "未命中") +
        '</td><td><span class="status-tag ' + esc(item.state) + '">' + esc(statusText) +
        '</span></td><td class="action-cell"><button type="button" class="table-link" data-open-case="' +
        esc(item.id) + '">查看' + icon("chevron", "small") + '</button></td></tr>';
    }).join("");
  }

  function openDrawer(kind, title, body, data) {
    state.drawerKind = kind;
    state.drawerData = data || null;
    $("drawerKicker").textContent = { citation: "SOURCE", document: "DOCUMENT", chunks: "CHUNKS", case: "CASE", about: "STATUS", chunk: "CHUNK" }[kind] || "DETAIL";
    $("drawerTitle").textContent = title;
    $("drawerBody").innerHTML = body;
    $("detailDrawer").classList.add("open");
    $("detailDrawer").setAttribute("aria-hidden", "false");
    $("scrim").hidden = false;
    $("drawerClose").focus();
  }

  function closeDrawer() {
    state.drawerKind = null;
    state.drawerData = null;
    $("detailDrawer").classList.remove("open");
    $("detailDrawer").setAttribute("aria-hidden", "true");
    $("scrim").hidden = !$("sidebar").classList.contains("open");
  }

  function openCitation(number, messageIndex) {
    const session = activeSession();
    if (!session) return;
    const message = session.messages[Number(messageIndex)];
    const citation = message && (message.citations || []).find(function (item) { return String(item.n) === String(number); });
    if (!citation) return;
    const body = '<div class="detail-group"><h3>原文片段</h3><p>' + esc(citation.text) +
      '</p></div><div class="detail-group"><dl class="detail-grid"><dt>文档</dt><dd>' + esc(citation.title) +
      '</dd><dt>条文</dt><dd>' + esc(citation.article) +
      '</dd><dt>文本块</dt><dd>' + esc(citation.chunkId) +
      '</dd><dt>来源</dt><dd>' + esc(citation.source) +
      '</dd></dl></div><div class="detail-group"><span class="status-tag demo">仅供界面演示 · 非真实法规</span></div>';
    openDrawer("citation", "来源 [" + citation.n + "]", body, citation);
  }

  function openDocument(id) {
    const doc = getDoc(id);
    if (!doc) return;
    const body = '<div class="detail-group"><dl class="detail-grid"><dt>来源</dt><dd>' + esc(doc.source) +
      '</dd><dt>文件标识</dt><dd>' + esc(doc.id) +
      '</dd><dt>字符数</dt><dd>' + doc.text.length.toLocaleString("zh-CN") +
      '</dd><dt>导入时间</dt><dd>' + esc(formatDate(doc.importedAt)) +
      '</dd><dt>状态</dt><dd>' + (doc.kind === "demo" ? "界面样本" : "浏览器本地") +
      '</dd></dl></div><div class="detail-group"><h3>文本预览</h3><p class="document-text">' +
      esc(doc.text.slice(0, 3000)) + (doc.text.length > 3000 ? "\n…" : "") +
      '</p></div><div class="drawer-actions"><button type="button" class="button primary" data-preview-doc="' +
      esc(doc.id) + '">' + icon("split") + '预览分块</button>' +
      (doc.kind === "local" ? '<button type="button" class="button danger" data-remove-doc="' + esc(doc.id) +
        '">' + icon("trash") + '移除文档</button>' : "") + '</div>';
    openDrawer("document", doc.title, body, doc.id);
  }

  function openChunks(id, condition) {
    const doc = getDoc(id);
    if (!doc) return;
    const selected = conditions[condition] ? condition : "s400";
    const chunks = chunksFor(doc, selected);
    const options = Object.keys(conditions).map(function (key) {
      return '<option value="' + key + '"' + (key === selected ? " selected" : "") + '>' +
        esc(conditions[key].label) + '</option>';
    }).join("");
    const body = '<div class="detail-group"><label class="sr-only" for="drawerCondition">分块方案</label><select id="drawerCondition" class="select drawer-select" data-doc-id="' +
      esc(id) + '">' + options + '</select><div class="detail-grid"><dt>块数</dt><dd>' + chunks.length +
      '</dd><dt>总字符</dt><dd>' + doc.text.length.toLocaleString("zh-CN") +
      '</dd><dt>处理方式</dt><dd>浏览器本地预览，不代表后端实验</dd></div></div><div class="drawer-chunks">' +
      chunks.map(function (chunk, index) { return chunkHtml(chunk, index, selected, id); }).join("") + '</div>';
    openDrawer("chunks", doc.title, body, { id: id, condition: selected });
  }

  function openChunk(id, condition, index) {
    const doc = getDoc(id);
    if (!doc) return;
    const chunk = chunksFor(doc, condition)[Number(index)];
    if (!chunk) return;
    const body = '<div class="detail-group"><dl class="detail-grid"><dt>文档</dt><dd>' + esc(doc.title) +
      '</dd><dt>方案</dt><dd>' + esc(conditions[condition].label) +
      '</dd><dt>位置</dt><dd>' + chunk.start + "–" + chunk.end +
      '</dd><dt>字符数</dt><dd>' + chunk.text.length + '</dd></dl></div><div class="detail-group"><h3>完整文本</h3><p>' +
      esc(chunk.text) + '</p></div>';
    openDrawer("chunk", "文本块 #" + (Number(index) + 1), body);
  }

  function openCase(id) {
    const item = demoCases.find(function (entry) { return entry.id === id; });
    if (!item) return;
    const body = '<div class="detail-group"><h3>问题</h3><p>' + esc(item.question) +
      '</p></div><div class="detail-group"><dl class="detail-grid"><dt>题型</dt><dd>' + esc(item.type) +
      '</dd><dt>F400</dt><dd>' + (item.f400 === null ? "不适用" : item.f400 ? "示例命中" : "示例未命中") +
      '</dd><dt>S400</dt><dd>' + (item.s400 === null ? "不适用" : item.s400 ? "示例命中" : "示例未命中") +
      '</dd></dl></div><div class="detail-group"><h3>演示备注</h3><p>' + esc(item.note) +
      '</p></div><div class="detail-group"><span class="status-tag demo">仅用于界面检查，不是实验记录</span></div>';
    openDrawer("case", item.id, body);
  }

  function exportDemoReport() {
    const report = { demo: true, message: "前端演示数据，不是课程实验结果", exported_at: new Date().toISOString(), cases: demoCases };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "derag-ui-demo-report.json";
    link.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    showToast("已导出明确标记的演示报告。");
  }

  document.querySelectorAll("[data-route]").forEach(function (button) {
    button.addEventListener("click", function () { navigate(button.dataset.route); });
  });
  $("menuButton").addEventListener("click", function () {
    $("sidebar").classList.add("open");
    $("scrim").hidden = false;
  });
  $("sessionToggle").addEventListener("click", function () { $("chatLayout").classList.toggle("show-sessions"); });
  $("scrim").addEventListener("click", function () { $("sidebar").classList.remove("open"); closeDrawer(); });
  $("drawerClose").addEventListener("click", closeDrawer);
  $("newSessionButton").addEventListener("click", newSession);
  $("chatCondition").addEventListener("change", function (event) {
    state.chatCondition = event.target.value;
    save();
    showToast("已切换到 " + conditions[state.chatCondition].label + "。演示回答不随方案重算。");
  });
  $("askForm").addEventListener("submit", function (event) {
    event.preventDefault();
    submitQuestion($("questionInput").value);
  });
  $("questionInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("askForm").requestSubmit();
    }
  });
  $("suggestions").addEventListener("click", function (event) {
    const button = event.target.closest("[data-question]");
    if (button) submitQuestion(button.dataset.question);
  });
  $("sessionList").addEventListener("click", function (event) {
    const remove = event.target.closest("[data-delete-session]");
    if (remove) {
      const id = remove.dataset.deleteSession;
      state.sessions = state.sessions.filter(function (session) { return session.id !== id; });
      if (!state.sessions.length) state.sessions.push({ id: uid("session"), title: "新会话", createdAt: new Date().toISOString(), messages: [] });
      if (state.activeSession === id) state.activeSession = state.sessions[0].id;
      save(); renderChat(); showToast("会话已从当前浏览器移除。");
      return;
    }
    const button = event.target.closest("[data-session]");
    if (button) {
      state.activeSession = button.dataset.session;
      save(); renderChat(); $("chatLayout").classList.remove("show-sessions");
    }
  });
  $("messages").addEventListener("click", function (event) {
    const citation = event.target.closest("[data-citation]");
    if (citation) { openCitation(citation.dataset.citation, citation.dataset.messageIndex); return; }
    const copy = event.target.closest("[data-copy-message]");
    if (copy) {
      const session = activeSession();
      const message = session && session.messages[Number(copy.dataset.copyMessage)];
      if (message && navigator.clipboard) navigator.clipboard.writeText(message.text).then(function () { showToast("已复制回答。"); }, function () { showToast("复制失败。", true); });
    }
  });
  $("importButton").addEventListener("click", function () { $("fileInput").click(); });
  $("fileInput").addEventListener("change", function (event) { importFiles(event.target.files); });
  $("docSearch").addEventListener("input", function (event) { state.docSearch = event.target.value; renderDocuments(); $("docSearch").focus(); });
  $("documentRows").addEventListener("click", function (event) {
    const button = event.target.closest("[data-open-doc]");
    if (button) openDocument(button.dataset.openDoc);
  });
  $("compareDocument").addEventListener("change", function (event) { state.selectedDoc = event.target.value; renderCompare(); });
  $("leftCondition").addEventListener("change", function (event) { state.leftCondition = event.target.value; renderCompare(); });
  $("rightCondition").addEventListener("change", function (event) { state.rightCondition = event.target.value; renderCompare(); });
  ["leftChunks", "rightChunks"].forEach(function (id) {
    $(id).addEventListener("click", function (event) {
      const button = event.target.closest("[data-open-chunk]");
      if (button) openChunk(button.dataset.openChunk, button.dataset.condition, button.dataset.index);
    });
  });
  $("evaluationRows").addEventListener("click", function (event) {
    const button = event.target.closest("[data-open-case]");
    if (button) openCase(button.dataset.openCase);
  });
  document.querySelectorAll("[data-eval-filter]").forEach(function (button) {
    button.addEventListener("click", function () { state.evalFilter = button.dataset.evalFilter; renderEvaluation(); });
  });
  $("exportReportButton").addEventListener("click", exportDemoReport);
  $("openDesignButton").addEventListener("click", function () { window.open("/project-design", "_blank", "noopener"); });
  $("aboutButton").addEventListener("click", function () {
    openDrawer("about", "当前开发状态",
      '<div class="detail-group"><h3>已完成</h3><p>前端页面、浏览器本地会话、文档导入、分块预览和演示引用。</p></div>' +
      '<div class="detail-group"><h3>待接入</h3><p>官方文档采集、向量数据库、embedding、LLM 问答和真实评估。</p></div>' +
      '<div class="detail-group"><span class="status-tag demo">当前所有指标和演示回答均非课程实验结果</span></div>');
  });
  $("drawerBody").addEventListener("click", function (event) {
    const preview = event.target.closest("[data-preview-doc]");
    if (preview) { openChunks(preview.dataset.previewDoc, "s400"); return; }
    const remove = event.target.closest("[data-remove-doc]");
    if (remove) {
      state.docs = state.docs.filter(function (doc) { return doc.id !== remove.dataset.removeDoc; });
      save(); closeDrawer(); renderDocuments(); renderCompare(); showToast("文档已从当前浏览器移除。");
      return;
    }
    const chunk = event.target.closest("[data-open-chunk]");
    if (chunk) openChunk(chunk.dataset.openChunk, chunk.dataset.condition, chunk.dataset.index);
  });
  $("drawerBody").addEventListener("change", function (event) {
    if (event.target.id === "drawerCondition" && state.drawerData && state.drawerData.id) {
      openChunks(state.drawerData.id, event.target.value);
    }
  });
  window.addEventListener("popstate", function () {
    const route = Object.keys(routePaths).find(function (key) { return routePaths[key] === location.pathname; }) || "chat";
    navigate(route, false);
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      if (state.drawerKind) closeDrawer();
      $("sidebar").classList.remove("open");
      $("chatLayout").classList.remove("show-sessions");
      if (!state.drawerKind) $("scrim").hidden = true;
    }
  });

  const initialRoute = Object.keys(routePaths).find(function (key) { return routePaths[key] === location.pathname; }) || "chat";
  navigate(initialRoute, false);
  fetch("/api/health").catch(function () { showToast("预览服务状态无法读取。", true); });
}());
