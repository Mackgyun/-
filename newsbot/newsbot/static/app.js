// 청년의사 브리핑 — 화면 스크립트 (프레임워크 없음, 모든 글자는 textContent로 넣어 XSS 방지)
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const LEVEL = {
  red: { label: "중요", cls: "red", icon: "▲" },
  yellow: { label: "일반", cls: "yellow", icon: "●" },
  gray: { label: "기록", cls: "gray", icon: "○" },
};

const state = {
  me: null,
  view: "feed",
  filter: { level: "", watched: 0, q: "", source: "" },
  draftSource: null,
  items: [],
  selected: -1,
  detail: null,
  seen: new Set(),
};

// ---------- 공통 ----------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "style") node.style.cssText = v; // CSP: style 속성 대신 CSSOM 사용
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) node.append(c instanceof Node ? c : document.createTextNode(c));
  return node;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/api/login")) {
    showAuth();
    throw new Error("로그인이 필요합니다.");
  }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error((data && data.detail && (typeof data.detail === "string" ? data.detail : "입력값을 확인해 주세요.")) || `오류 ${res.status}`);
  return data;
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2800);
}

function fmtSeen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  const hm = d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
  return d.toDateString() === today.toDateString() ? hm : `${d.getMonth() + 1}/${d.getDate()} ${hm}`;
}
const fmtDate = (s) => (s && s.length === 8 ? `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6)}` : s || "");

function badge(item) {
  const lv = LEVEL[item.level] || LEVEL.yellow;
  const wrap = el("span", { class: "row", style: "gap:.25rem" });
  wrap.append(el("span", { class: `badge ${lv.cls}` }, el("span", { "aria-hidden": "true", text: lv.icon }), lv.label));
  if (item.is_correction) wrap.append(el("span", { class: "badge fix", text: "정정" }));
  if (item.source === "alio") wrap.append(el("span", { class: "badge src", text: "알리오" }));
  return wrap;
}

// ---------- 인증 ----------
function showAuth(joinCode) {
  $("#app").hidden = true;
  $("#auth").hidden = false;
  $("#login-form").hidden = !!joinCode;
  $("#join-form").hidden = !joinCode;
  $("#join-form").dataset.code = joinCode || "";
  (joinCode ? $("#join-form input") : $("#login-form input")).focus();
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/login", { method: "POST", body: { username: f.get("username"), password: f.get("password") } });
    $("#auth-error").textContent = "";
    await boot();
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
});

$("#join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/register", {
      method: "POST",
      body: { code: e.target.dataset.code, username: f.get("username"), display_name: f.get("display_name"), password: f.get("password") },
    });
    location.hash = "#settings";
    await boot();
    toast("계정을 만들었어요. 이 기기에서 알림을 켜 주세요.");
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
});

$("#logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.hash = "";
  showAuth();
});

// ---------- 화면 전환 ----------
function setView(view) {
  if (view === "admin" && state.me?.role !== "admin") view = "feed";
  state.view = view;
  const section = view === "mine" ? "feed" : view;
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${section}`));
  $$("[data-view]").forEach((a) => a.setAttribute("aria-current", a.dataset.view === view ? "page" : "false"));
  $(".topbar").hidden = section !== "feed";
  $("#ask").hidden = !["feed", "ask"].includes(section);
  if (section === "feed") {
    $("#feed-title").textContent = view === "mine" ? "내가 맡은 건" : "오늘의 피드";
    $("#briefing").hidden = view === "mine";
    loadFeed(true);
  }
  if (view === "settings") renderSettings();
  if (view === "admin") renderAdmin();
  if (view === "ask") renderChats();
  if (view === "draft") renderDrafts();
  if (view === "mail") renderMail();
  if (view === "alio") renderAlio();
}

function route() {
  const h = location.hash.slice(1);
  if (h.startsWith("join/")) return showAuth(h.slice(5));
  if (!state.me) return;
  if (h.startsWith("d/")) {
    if (state.view !== "feed") setView("feed");
    return openDetail(decodeURIComponent(h.slice(2)));
  }
  if (h.startsWith("draft/")) {
    const [kind, ...rest] = h.slice(6).split("/");
    state.draftSource = { kind: kind === "m" ? "mail" : "disclosure", ref: decodeURIComponent(rest.join("/")) };
    closeDetail();
    return setView("draft");
  }
  if (h === "draft") state.draftSource = null; // 메뉴로 들어오면 붙여 넣기 모드
  setView(["feed", "mine", "settings", "admin", "ask", "draft", "mail", "alio"].includes(h) ? h : "feed");
}
window.addEventListener("hashchange", route);

// ---------- 오늘의 브리핑 ----------
async function loadSummary() {
  const s = await api("/api/summary");
  const box = $("#briefing");
  box.replaceChildren(
    el("div", { class: "tile alert" }, el("div", { class: "label", text: "오늘 중요 공시" }), el("div", { class: "num", text: s.red })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "오늘 일반 공시" }), el("div", { class: "num", text: s.yellow })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "담당 미정 (중요)" }), el("div", { class: "num", text: s.unclaimed_top })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "내가 맡은 건" }), el("div", { class: "num", text: s.my_claims })),
    el("div", { class: "tile wide" },
      el("div", { class: "label", text: "지금 확인할 것" }),
      s.top.length
        ? el("ul", { class: "top-list" }, s.top.map((t) =>
            el("li", {}, el("button", { type: "button", onclick: () => (location.hash = `#d/${t.rcept_no}`) },
              badge(t), el("strong", { text: t.corp_name }), el("span", { class: "muted t", text: t.report_nm }),
              t.claimed_name ? el("span", { class: "claimed small", text: `✓ ${t.claimed_name}` }) : null))))
        : el("p", { class: "muted small", text: "오늘은 아직 중요 공시가 없어요." })),
  );
  const dg = $("#digest");
  dg.hidden = !s.briefing || state.view === "mine";
  if (s.briefing) {
    dg.replaceChildren(el("div", { class: "label", text: `정기 브리핑 · ${s.briefing.slot}${s.briefing.model ? " · AI 요약" : ""}` }),
      el("div", { text: s.briefing.content }));
  }
  const banner = $("#mode-banner");
  banner.hidden = s.alert_mode !== "log";
  banner.textContent = "지금은 '기록만' 모드예요. 팝업 없이 수집하면서 알림량을 재고 있어요.";
  const st = $("#status-dot");
  st.classList.toggle("ok", s.dart_status === "정상");
  st.classList.toggle("bad", s.dart_status !== "정상" && s.dart_status !== "대기 중");
  $(".status-text", st).textContent = s.dart_status === "정상" ? `수집 정상 · ${fmtSeen(s.last_poll_at)}` : s.dart_status;
  st.title = s.dart_status;
}

// ---------- 피드 ----------
function feedQuery(before = "") {
  const p = new URLSearchParams();
  if (state.filter.level) p.set("level", state.filter.level);
  if (state.filter.watched) p.set("watched", "1");
  if (state.filter.source) p.set("source", state.filter.source);
  if (state.filter.q) p.set("q", state.filter.q);
  if (state.view === "mine") p.set("mine", "1");
  if (before) p.set("before", before);
  return `/api/feed?${p}`;
}

async function loadFeed(reset) {
  const before = reset ? "" : state.items.at(-1)?.first_seen_at || "";
  const { items } = await api(feedQuery(before));
  if (reset) {
    state.items = items;
    state.selected = -1;
  } else state.items.push(...items);
  items.forEach((i) => state.seen.add(i.rcept_no));
  renderFeed();
  $("#more-btn").hidden = items.length < 50;
  if (state.view === "feed") loadSummary().catch(() => {});
}

function renderFeed(freshIds = new Set()) {
  const list = $("#feed");
  list.replaceChildren(...state.items.map((it, idx) =>
    el("li", {
      class: `item${freshIds.has(it.rcept_no) ? " new" : ""}`, role: "option", id: `it-${idx}`,
      "aria-selected": idx === state.selected ? "true" : "false", onclick: () => select(idx, true),
    },
      badge(it),
      el("div", { style: "min-width:0" },
        el("div", { class: "row", style: "gap:.4rem" },
          it.watched ? el("span", { class: "star", title: "감시 기업", text: "★" }) : null,
          el("span", { class: "who", text: it.corp_name })),
        el("div", { class: "title", text: it.report_nm, title: it.report_nm })),
      el("div", { class: "meta" },
        it.claimed_name ? el("span", { class: "claimed", text: `✓ ${it.claimed_name}` }) : null,
        el("time", { datetime: it.first_seen_at, text: fmtSeen(it.first_seen_at) })))));
  const empty = $("#empty");
  empty.hidden = state.items.length > 0;
  empty.textContent = state.view === "mine" ? "맡은 공시가 없어요. 피드에서 C 키나 [내가 쓸게요]로 맡을 수 있어요." : "조건에 맞는 공시가 없어요.";
}

function select(idx, open) {
  if (idx < 0 || idx >= state.items.length) return;
  state.selected = idx;
  $$(".item").forEach((n, i) => n.setAttribute("aria-selected", i === idx ? "true" : "false"));
  $(`#it-${idx}`)?.scrollIntoView({ block: "nearest" });
  if (open) location.hash = `#d/${state.items[idx].rcept_no}`;
}

$("#more-btn").addEventListener("click", () => loadFeed(false));

$$(".filters .chip").forEach((chip) => chip.addEventListener("click", () => {
  if (chip.dataset.source !== undefined) {
    state.filter.source = state.filter.source ? "" : chip.dataset.source;
    chip.setAttribute("aria-pressed", state.filter.source ? "true" : "false");
  } else if (chip.dataset.watched !== undefined) {
    state.filter.watched = state.filter.watched ? 0 : 1;
    chip.setAttribute("aria-pressed", state.filter.watched ? "true" : "false");
  } else {
    state.filter.level = chip.dataset.level;
    $$(".filters .chip[data-level]").forEach((c) => c.setAttribute("aria-pressed", c === chip ? "true" : "false"));
  }
  loadFeed(true);
}));

let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.filter.q = e.target.value.trim(); loadFeed(true); }, 250);
});

// ---------- 상세 ----------
async function openDetail(rceptNo) {
  let d;
  try { d = await api(`/api/disclosures/${encodeURIComponent(rceptNo)}`); }
  catch (err) { toast(err.message); return; }
  state.detail = d;
  const idx = state.items.findIndex((i) => i.rcept_no === rceptNo);
  if (idx >= 0) select(idx, false);
  const mine = d.claimed_by === state.me.id;
  const writtenBtn = mine
    ? el("button", { class: "btn", type: "button", text: d.written_at ? "✓ 기사화 기록됨" : "기사 썼어요",
        onclick: async () => {
          const url = prompt("쓴 기사 주소가 있으면 붙여 넣으세요 (없으면 비워 두기)", d.written_url || "") ?? null;
          if (url === null) return;
          try { await api(`/api/claims/${encodeURIComponent(d.rcept_no)}/written`, { method: "POST", body: { url } });
            toast("기사화로 기록했어요. 시범사업 성과에 반영됩니다."); openDetail(d.rcept_no); } catch (err) { toast(err.message); }
        } })
    : null;
  const claimBtn = d.claimed_by && !mine
    ? el("button", { class: "btn", type: "button", disabled: true, text: `${d.claimed_name} 기자가 맡음` })
    : el("button", { class: mine ? "btn" : "btn primary", type: "button", onclick: toggleClaim, text: mine ? "맡기 취소" : "내가 쓸게요 (C)" });
  $("#detail .detail-inner").replaceChildren(
    el("div", { class: "row", style: "justify-content:space-between" }, badge(d),
      el("button", { class: "btn ghost small", type: "button", onclick: closeDetail, "aria-label": "닫기", text: "닫기 (Esc)" })),
    el("div", {}, el("div", { class: "muted small", text: d.source === "alio" ? "알리오 · 공공기관" : d.watched ? "★ 감시 기업" : "보건의료 업종" }), el("h2", { text: d.corp_name })),
    el("p", { style: "margin:0;font-weight:600", text: d.report_nm }),
    el("a", { class: "source", href: d.url, target: "_blank", rel: "noopener noreferrer" }, d.source === "alio" ? "알리오 원문 열기" : "DART 원문 열기", el("span", { "aria-hidden": "true", text: "↗" })),
    el("dl", { class: "kv" },
      el("dt", { text: "접수일" }), el("dd", { text: fmtDate(d.rcept_dt) }),
      el("dt", { text: "접수번호" }), el("dd", { text: d.rcept_no }),
      el("dt", { text: "제출인" }), el("dd", { text: d.flr_nm || "-" }),
      el("dt", { text: "비고" }), el("dd", { text: d.rm || "-" }),
      el("dt", { text: "분류 근거" }), el("dd", { text: d.keyword ? `제목에 '${d.keyword}' 포함` : "키워드 없음 (일반)" }),
      el("dt", { text: "처음 확인" }), el("dd", { text: fmtSeen(d.first_seen_at) + (d.source === "alio" ? "" : " · DART 공개는 제출 후 약 15분 뒤") })),
    el("div", { class: "row" }, claimBtn, writtenBtn,
      el("button", { class: "btn", type: "button", text: "기사 초안",
        title: state.me.llm_ready ? "이 공시로 초안 쓰기" : "AI API 키가 연결되면 켜집니다",
        disabled: !state.me.llm_ready, onclick: () => (location.hash = `#draft/d/${encodeURIComponent(d.rcept_no)}`) })),
  );
  $("#detail").hidden = false;
  $("#app").classList.add("has-detail");
}

function closeDetail() {
  $("#detail").hidden = true;
  $("#app").classList.remove("has-detail");
  state.detail = null;
  if (location.hash.startsWith("#d/")) history.replaceState(null, "", state.view === "mine" ? "#mine" : "#feed");
}

async function toggleClaim() {
  const d = state.detail || state.items[state.selected];
  if (!d) return;
  const mine = d.claimed_by === state.me.id;
  try {
    await api(`/api/claims/${encodeURIComponent(d.rcept_no)}`, { method: mine ? "DELETE" : "POST" });
    toast(mine ? "맡기를 취소했어요." : "이 공시를 맡았어요.");
    await loadFeed(true);
    if (state.detail) openDetail(d.rcept_no);
  } catch (err) { toast(err.message); }
}

// ---------- 키보드 ----------
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("#ask-input").focus(); return; }
  const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (e.key === "Escape") { if (typing) document.activeElement.blur(); else closeDetail(); return; }
  if (typing || !["feed", "mine"].includes(state.view)) return;
  if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
  else if (e.key === "j") select(Math.min(state.selected + 1, state.items.length - 1), false);
  else if (e.key === "k") select(Math.max(state.selected - 1, 0), false);
  else if (e.key === "Enter" && state.selected >= 0) select(state.selected, true);
  else if (e.key === "c" && (state.detail || state.selected >= 0)) toggleClaim();
});

// ---------- 질문창 ----------
$("#ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#ask-input");
  const q = input.value.trim();
  if (!q) return;
  if (!state.me.llm_ready) { toast("AI API 키가 연결되면 질문할 수 있어요."); return; }
  if (state.view !== "ask") location.hash = "#ask";
  input.value = "";
  input.disabled = true;
  const pending = el("div", { class: "bubble a", text: "자료를 찾아보는 중…" });
  $("#chat").append(el("div", { class: "bubble q", text: q }), pending);
  pending.scrollIntoView({ block: "end" });
  try {
    const r = await api("/api/ask", { method: "POST", body: { question: q } });
    pending.replaceWith(answerBubble(r.answer, r.trace));
  } catch (err) {
    pending.textContent = err.message;
  } finally {
    input.disabled = false;
    input.focus();
  }
});

const TOOL_NAMES = { search_disclosures: "공시 검색", get_disclosure: "공시 원문", company_financials: "DART 재무",
  alio_finance: "알리오 결산", search_newsroom_articles: "기사 검색", search_my_mail: "내 메일" };

function linkify(text) {
  // URL만 링크로 만들고 나머지는 글자 그대로 (innerHTML 사용 안 함)
  const frag = document.createDocumentFragment();
  let last = 0;
  for (const m of text.matchAll(/https?:\/\/[^\s)\]>]+/g)) {
    frag.append(text.slice(last, m.index));
    frag.append(el("a", { href: m[0], target: "_blank", rel: "noopener noreferrer", text: m[0] }));
    last = m.index + m[0].length;
  }
  frag.append(text.slice(last));
  return frag;
}

function answerBubble(answer, trace = []) {
  const b = el("div", { class: "bubble a" }, linkify(answer));
  if (trace.length) b.append(el("div", { class: "tools", text: "찾아본 자료: " + [...new Set(trace.map((t) => TOOL_NAMES[t.tool] || t.tool))].join(", ") }));
  return b;
}

async function renderChats() {
  const box = $("#chat");
  if (!state.me.llm_ready) {
    box.replaceChildren(el("p", { class: "banner", text: "AI API 키가 아직 연결되지 않았어요. 관리자가 .env 에 키를 넣으면 질문할 수 있어요." }));
    return;
  }
  const { items } = await api("/api/chats");
  box.replaceChildren(...items.reverse().flatMap((c) => [el("div", { class: "bubble q", text: c.question }), answerBubble(c.answer, c.trace)]));
  if (!items.length) box.append(el("p", { class: "muted", text: "예: \"이번 주 기술이전 공시 정리해줘\", \"서울대병원 작년 의료수익 전년 대비?\", \"유한양행 2025년 매출과 영업이익\"" }));
  $("#ask-input").focus();
}

// ---------- 기사 초안 ----------
async function renderDrafts() {
  const src = state.draftSource;
  const form = $("#draft-form");
  if (src) {
    let label = "";
    if (src.kind === "disclosure") {
      try { const d = await api(`/api/disclosures/${encodeURIComponent(src.ref)}`); label = `공시: ${d.corp_name} · ${d.report_nm}`; }
      catch { label = "공시"; }
      $("#draft-source").textContent = `${label} — 원문은 자동으로 가져옵니다. 취재 메모가 있으면 아래에 덧붙이세요.`;
    } else {
      $("#draft-source").textContent = "메일을 원자료로 씁니다.";
    }
    form.elements.namedItem("title").hidden = true;
  } else {
    $("#draft-source").textContent = "보도자료나 메모를 붙여 넣거나, 피드의 공시 상세에서 [기사 초안]을 누르세요.";
    form.elements.namedItem("title").hidden = false;
  }
  const { items } = await api("/api/drafts");
  $("#draft-list").replaceChildren(...items.map((d) => el("li", {},
    el("button", { type: "button", onclick: () => showDraft(d.id) }, `${fmtSeen(d.created_at)} · ${d.source_title || "(제목 없음)"}`))));
  if (!items.length) $("#draft-list").append(el("li", { class: "muted small", text: "아직 없어요." }));
}

function renderDraftResult(d) {
  $("#draft-result").hidden = false;
  $("#draft-text").value = d.draft;
  const miss = d.checks.filter((c) => !c.found);
  $("#draft-checks").replaceChildren(
    el("p", { class: "small", text: miss.length ? `원자료에서 찾지 못한 숫자 ${miss.length}개 — 반드시 확인하세요.` : "초안의 숫자는 모두 원자료에 있어요." }),
    el("ul", { class: "checks" }, d.checks.map((c) => el("li", { class: c.found ? "" : "miss", title: c.context, text: `${c.found ? "✓" : "✗"} ${c.number}` }))));
  $("#draft-examples").textContent = d.examples?.length ? "참고한 내 기사: " + d.examples.map((e) => e.title).join(" / ") : "";
  $("#draft-result").scrollIntoView({ block: "start" });
}

async function showDraft(id) {
  try { renderDraftResult(await api(`/api/drafts/${id}`)); } catch (err) { toast(err.message); }
}

$("#draft-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.me.llm_ready) { toast("AI API 키가 연결되면 초안을 쓸 수 있어요."); return; }
  const f = new FormData(e.target);
  const src = state.draftSource;
  const body = src
    ? { source_kind: src.kind, source_ref: src.ref, text: f.get("text") || "", kind: f.get("kind") }
    : { source_kind: "text", title: f.get("title") || "", text: f.get("text") || "", kind: f.get("kind") };
  $("#draft-busy").hidden = false;
  e.target.querySelector("button[type=submit]").disabled = true;
  try {
    const d = await api("/api/drafts", { method: "POST", body });
    renderDraftResult(d);
    renderDrafts();
  } catch (err) { toast(err.message); }
  finally { $("#draft-busy").hidden = true; e.target.querySelector("button[type=submit]").disabled = false; }
});
$("#draft-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#draft-text").value); toast("초안을 복사했어요. 검수 후 CMS에 붙여 넣으세요."); }
  catch { $("#draft-text").select(); toast("Ctrl+C로 복사하세요."); }
});

// ---------- 메일 ----------
async function renderMail() {
  const off = !state.me.mail_enabled;
  $("#mail-off").hidden = !off;
  $("#mail-wrap").hidden = off;
  if (off) return;
  const { items } = await api("/api/mail");
  $("#mail-list").replaceChildren(...items.map((m) => el("li", { class: "item", onclick: () => openMail(m.id) },
    el("span", { class: "badge yellow", text: "메일" }),
    el("div", { style: "min-width:0" }, el("div", { class: "who", text: m.sender }), el("div", { class: "title", text: m.subject })),
    el("div", { class: "meta" }, m.embargo ? el("span", { class: "mail-embargo", text: "엠바고" }) : null,
      el("time", { text: fmtSeen(m.sent_at || m.first_seen_at) })))));
  if (!items.length) $("#mail-list").append(el("li", { class: "empty", text: "가져온 메일이 없어요. '내 설정'에서 메일을 연결하세요." }));
}

async function openMail(id) {
  const m = await api(`/api/mail/${id}`);
  const box = $("#mail-detail");
  box.hidden = false;
  box.replaceChildren(
    el("div", { class: "muted small", text: `${m.sender} · ${fmtSeen(m.sent_at)}` }), el("h3", { text: m.subject }),
    m.embargo ? el("p", { class: "mail-embargo", text: m.embargo }) : null,
    el("div", { class: "pre", text: m.body }),
    el("div", { class: "row" }, el("button", { class: "btn", type: "button", text: "이 메일로 초안",
      onclick: () => (location.hash = `#draft/m/${m.id}`) })));
  box.scrollIntoView({ block: "start" });
}

// ---------- 알리오 ----------
const won = (v) => (v == null ? "-" : Math.round(v).toLocaleString("ko-KR"));
async function renderAlio() {
  const a = await api("/api/alio");
  $("#alio-status").textContent = a.enabled ? `상태: ${a.status}${a.last_poll_at ? " · 마지막 확인 " + fmtSeen(a.last_poll_at) : ""}` : "알리오 수집이 꺼져 있어요.";
  $("#alio-orgs").textContent = a.orgs.length ? a.orgs.map((o) => o.name).join(", ") : "아직 기관 목록을 받지 못했어요.";
  $("#alio-missing").textContent = a.missing.length ? `알리오에서 찾지 못한 이름: ${a.missing.join(", ")} (config/alio.toml 확인)` : "";
  $("#alio-finance").replaceChildren(...(a.finance.length ? a.finance.map((f) => el("div", { class: "card stack" },
    el("div", { class: "row between" }, el("h3", { text: f.org }),
      el("a", { class: "source", href: f.url, target: "_blank", rel: "noopener noreferrer" }, "알리오 원문 ↗")),
    el("div", { class: "muted small", text: `${f.title || ""} ${f.unit ? "· " + f.unit : ""}` }),
    el("table", { class: "fin" }, el("thead", {}, el("tr", {}, ["항목", "올해", "전년", "증감", "증감률"].map((h) => el("th", { text: h })))),
      el("tbody", {}, f.items.map((i) => el("tr", {},
        el("td", { text: i.label + (i.year ? ` (${i.year})` : "") }), el("td", { text: won(i.value) }), el("td", { text: won(i.prev) }),
        el("td", { class: i.change > 0 ? "up" : i.change < 0 ? "down" : "", text: i.change == null ? "-" : (i.change > 0 ? "+" : "") + won(i.change) }),
        el("td", { class: i.pct > 0 ? "up" : i.pct < 0 ? "down" : "", text: i.pct == null ? "-" : `${i.pct > 0 ? "+" : ""}${i.pct}%` }))))))) :
    [el("p", { class: "muted", text: "아직 수집된 결산이 없어요. 결산 공시가 올라오면(보통 3~4월) 전년 대비 표가 여기에 생깁니다." })]));
}

// ---------- 설정 ----------
async function renderSettings() {
  const me = (state.me = await api("/api/me"));
  const kindName = { all: "보건의료 전체", watch: "감시 기업 전체", company: "기업", keyword: "키워드" };
  $("#subs").replaceChildren(...(me.subscriptions.length ? me.subscriptions.map((s) =>
    el("span", { class: "tag" }, `${kindName[s.kind]}${s.value ? ": " + s.value : ""}`,
      el("button", { type: "button", "aria-label": "삭제", text: "×", onclick: async () => {
        await api(`/api/subscriptions?kind=${s.kind}&value=${encodeURIComponent(s.value)}`, { method: "DELETE" });
        renderSettings();
      } }))) : [el("span", { class: "muted small", text: "아직 없어요. 아래에서 추가하세요." })]));
  $("#push-state").textContent = `알림 받는 기기 ${me.push_devices}대 · 서버 알림 모드: ${me.alert_mode === "notify" ? "알림 보냄" : "기록만 (관리자가 켜면 알림 시작)"}`;
  $("#font-size").value = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--fs")) || 15;
  $("#reporter-form").reporter_id.value = me.reporter_id || "";
  $("#articles-state").textContent = `가져온 내 기사 ${me.my_articles}편`;
  $("#stylebook-meta").textContent = me.stylebook ? `마지막 수정 ${fmtSeen(me.stylebook.updated_at)} · 기사 ${me.stylebook.source_count}편 분석` : "아직 없음";
  const sb = await api("/api/stylebook");
  $("#stylebook").value = sb.content || "";
  $("#stylebook-build").disabled = !me.llm_ready;
  $("#mail-settings").hidden = !me.mail_enabled;
  const acc = me.mail_account;
  $("#mail-account-state").textContent = acc
    ? `연결됨: ${acc.username} · 메일함 '${acc.folder}'${acc.last_error ? " · 오류: " + acc.last_error : ""}`
    : "연결된 메일이 없어요.";
  $("#usage").textContent = me.llm_ready
    ? `이번 달 AI 사용 ${me.spent_krw.toLocaleString("ko-KR")}원 / 한도 ${me.limit_krw.toLocaleString("ko-KR")}원 (${me.llm_provider})`
    : "AI API 키가 아직 연결되지 않았어요.";
  pollArticles();
}

$("#reporter-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await api("/api/me/reporter", { method: "POST", body: { reporter_id: e.target.reporter_id.value.trim() } });
    toast("기자 ID를 저장했어요."); renderSettings(); } catch (err) { toast(err.message); }
});
let articlesTimer;
async function pollArticles() {
  clearTimeout(articlesTimer);
  const st = await api("/api/articles/status");
  const j = st.job;
  let msg = `가져온 내 기사 ${st.count}편`;
  if (j?.state === "running") msg += ` · 가져오는 중 (확인 ${j.checked || 0}건, 추가 ${j.added || 0}건)`;
  else if (j?.state === "done") msg += ` · 마지막 가져오기 ${fmtSeen(j.at)} (추가 ${j.added}건)`;
  else if (j?.state === "error") msg += ` · 오류: ${j.error}`;
  $("#articles-state").textContent = msg;
  if (j?.state === "running" && state.view === "settings") articlesTimer = setTimeout(pollArticles, 4000);
}
$("#articles-btn").addEventListener("click", async () => {
  try { const r = await api("/api/articles/collect", { method: "POST" }); toast(r.started ? "내 기사를 가져오기 시작했어요. 몇 분 걸려요." : r.message); pollArticles(); }
  catch (err) { toast(err.message); }
});
$("#stylebook-build").addEventListener("click", async (e) => {
  e.target.disabled = true;
  toast("스타일북을 만드는 중이에요. 1~2분 걸려요.");
  try { const r = await api("/api/stylebook/build", { method: "POST" }); $("#stylebook").value = r.content; toast("스타일북을 만들었어요. 읽어 보고 고쳐 주세요."); renderSettings(); }
  catch (err) { toast(err.message); }
  finally { e.target.disabled = false; }
});
$("#stylebook-save").addEventListener("click", async () => {
  try { await api("/api/stylebook", { method: "PUT", body: { content: $("#stylebook").value } }); toast("스타일북을 저장했어요."); }
  catch (err) { toast(err.message); }
});
$("#mail-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/mail/account", { method: "PUT", body: Object.fromEntries(f.entries()) });
    e.target.password.value = "";
    toast("메일을 연결했어요."); renderSettings();
  } catch (err) { toast(err.message); }
});
$("#mail-disconnect").addEventListener("click", async () => {
  if (!confirm("메일 연결을 해제하고 가져온 메일을 지울까요?")) return;
  await api("/api/mail/account", { method: "DELETE" }); toast("연결을 해제했어요."); renderSettings();
});

$("#sub-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/subscriptions", { method: "POST", body: { kind: f.get("kind"), value: f.get("value") || "" } });
    e.target.reset();
    renderSettings();
  } catch (err) { toast(err.message); }
});
$("#sub-form select").addEventListener("change", (e) => {
  $("#sub-form input").hidden = ["all", "watch"].includes(e.target.value);
});

$("#font-size").addEventListener("input", (e) => {
  document.documentElement.style.setProperty("--fs", `${e.target.value}px`);
  try { localStorage.setItem("nb-fs", e.target.value); } catch {}
});

// ---------- 푸시 알림 ----------
function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    toast("이 브라우저는 알림을 지원하지 않아요. 아이폰은 홈 화면에 추가한 앱에서 켜 주세요.");
    return;
  }
  const perm = await Notification.requestPermission();
  if (perm !== "granted") { toast("알림 권한이 거부됐어요. 브라우저 설정에서 허용해 주세요."); return; }
  const reg = await navigator.serviceWorker.register("/sw.js");
  const { key } = await api("/api/push/key");
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
  await api("/api/push/subscribe", { method: "POST", body: sub.toJSON() });
  $("#push-btn").hidden = true;
  toast("이 기기에서 알림을 받아요.");
  if (state.view === "settings") renderSettings();
}
$("#push-btn").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-enable").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-test").addEventListener("click", async () => {
  try {
    const { sent } = await api("/api/push/test", { method: "POST" });
    toast(sent ? `테스트 알림을 ${sent}대에 보냈어요.` : "알림 받는 기기가 없어요. 먼저 알림을 켜 주세요.");
  } catch (err) { toast(err.message); }
});

async function checkPushButton() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = reg && (await reg.pushManager.getSubscription());
  $("#push-btn").hidden = !!sub && Notification.permission === "granted";
}

// ---------- 관리자 ----------
async function renderAdmin() {
  const [st, us, mt] = await Promise.all([api("/api/admin/status"), api("/api/admin/users"), api("/api/admin/metrics")]);
  const t = mt.totals;
  $("#metrics-totals").replaceChildren(
    el("dt", { text: "수집 공시" }), el("dd", { text: `${t.disclosures}건 (중요 ${t.red}건)` }),
    el("dt", { text: "보낸 알림" }), el("dd", { text: `${t.alerts}건` }),
    el("dt", { text: "수집 가동률" }), el("dd", { text: t.uptime_pct == null ? "DART 키 없음" : `${t.uptime_pct}% (오류 ${t.poll_errors}건)` }),
    el("dt", { text: "AI 비용" }), el("dd", { text: `${t.cost_krw.toLocaleString("ko-KR")}원` }));
  $("#metrics-users").replaceChildren(...mt.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.claims }), el("td", { text: u.written }),
    el("td", { text: u.questions }), el("td", { text: u.drafts }), el("td", { text: `${u.cost_krw.toLocaleString("ko-KR")}원` }))));
  $("#admin-status").replaceChildren(
    el("dt", { text: "수집 상태" }), el("dd", { text: st.dart_status }),
    el("dt", { text: "마지막 수집" }), el("dd", { text: st.last_poll_at ? fmtSeen(st.last_poll_at) : "-" }),
    el("dt", { text: "오늘 DART 호출" }), el("dd", { text: `${st.dart_calls_today}건` }),
    el("dt", { text: "알림 모드" }), el("dd", { text: st.alert_mode === "notify" ? "알림 보냄" : "기록만 (.env 의 ALERT_MODE=notify 로 변경)" }),
    el("dt", { text: "알리오" }), el("dd", { text: st.alio_status }),
    el("dt", { text: "AI" }), el("dd", { text: st.llm }),
    el("dt", { text: "메일" }), el("dd", { text: st.mail }));
  $("#users").replaceChildren(...us.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.username }), el("td", { text: u.role === "admin" ? "관리자" : "기자" }),
    el("td", {}, `${u.spent_krw.toLocaleString("ko-KR")} / `,
      el("input", { class: "limit-input", type: "number", min: "0", step: "1000", value: u.limit_krw, "aria-label": `${u.display_name} 월 한도(원)`,
        onchange: async (e) => { await api(`/api/admin/users/${u.id}/limit`, { method: "POST", body: { krw: Number(e.target.value) } }); toast("한도를 바꿨어요."); } }), "원"),
    el("td", { text: u.active ? "사용 중" : "비활성" }),
    el("td", {}, u.id === state.me.id ? null : el("button", { class: "btn small", type: "button", text: u.active ? "비활성화" : "다시 사용",
      onclick: async () => { await api(`/api/admin/users/${u.id}/active?active=${u.active ? 0 : 1}`, { method: "POST" }); renderAdmin(); } })))));
  $("#events").replaceChildren(...st.events.map((ev) => el("li", { text: `${fmtSeen(ev.at)} [${ev.kind}] ${ev.detail || ""}` })));
}
$("#invite-btn").addEventListener("click", async () => {
  const r = await api("/api/admin/invites", { method: "POST", body: { role: "reporter" } });
  $("#invite-url").value = r.url;
  $("#invite-url").select();
  try { await navigator.clipboard.writeText(r.url); toast("초대 링크를 복사했어요."); } catch { toast("초대 링크를 만들었어요."); }
});

// ---------- 테마 ----------
function applyTheme(t) {
  if (t === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
  $("#theme-btn").textContent = { auto: "테마: 자동", light: "테마: 밝게", dark: "테마: 어둡게" }[t];
}
$("#theme-btn").addEventListener("click", () => {
  const order = ["auto", "light", "dark"];
  let cur = "auto";
  try { cur = localStorage.getItem("nb-theme") || "auto"; } catch {}
  const next = order[(order.indexOf(cur) + 1) % order.length];
  try { localStorage.setItem("nb-theme", next); } catch {}
  applyTheme(next);
});

// ---------- 실시간 갱신 (1분마다) ----------
async function refresh() {
  if (!state.me || state.view !== "feed" || document.hidden) return;
  try {
    const { items } = await api(feedQuery());
    const fresh = items.filter((i) => !state.seen.has(i.rcept_no));
    if (!fresh.length) return loadSummary();
    fresh.forEach((i) => state.seen.add(i.rcept_no));
    const keep = state.items.filter((i) => !fresh.some((f) => f.rcept_no === i.rcept_no));
    state.items = [...fresh, ...keep];
    if (state.selected >= 0) state.selected += fresh.length;
    renderFeed(new Set(fresh.map((f) => f.rcept_no)));
    toast(`새 공시 ${fresh.length}건`);
    loadSummary();
  } catch {}
}
setInterval(refresh, 60_000);
document.addEventListener("visibilitychange", refresh);

// ---------- 시작 ----------
async function boot() {
  try {
    state.me = await api("/api/me");
  } catch {
    return;
  }
  $("#auth").hidden = true;
  $("#app").hidden = false;
  $$(".admin-only").forEach((n) => (n.hidden = state.me.role !== "admin"));
  checkPushButton().catch(() => {});
  route();
}

(function init() {
  try {
    const fs = localStorage.getItem("nb-fs");
    if (fs) document.documentElement.style.setProperty("--fs", `${fs}px`);
    applyTheme(localStorage.getItem("nb-theme") || "auto");
  } catch { applyTheme("auto"); }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  if (location.hash.startsWith("#join/")) showAuth(location.hash.slice(6));
  else boot();
})();
