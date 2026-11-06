// 청년의사 브리핑 — 화면 스크립트 v2
// 원칙: 키보드로 분류(J/K·E·C·O·Z), 명령 팔레트(Ctrl K), 즉시 반영 + 되돌리기, 글자는 textContent로만 넣기(XSS 방지)
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const LV = { red: { label: "중요" }, yellow: { label: "일반" }, gray: { label: "기록" } };
const SPLITS = {
  inbox: { title: "미확인", empty: ["미확인 공시가 없습니다", "새 공시는 수집되는 대로 표시됩니다."], key: "1" },
  red: { title: "중요", empty: ["미확인 중요 공시가 없습니다", "중요 공시는 알림으로도 발송됩니다."], key: "2" },
  beat: { title: "내 출입처", empty: ["해당 공시가 없습니다", "출입처 기업과 키워드는 설정에서 지정합니다."], key: "3" },
  unclaimed: { title: "담당 미지정", empty: ["담당 미지정 중요 공시가 없습니다", "최근 3일 기준입니다."], key: "4" },
  alio: { title: "알리오", empty: ["알리오 공시가 없습니다", "공공기관 공시는 6시간마다 수집합니다."], key: "5" },
  all: { title: "전체", empty: ["수집된 공시가 없습니다", "DART 인증키를 등록하면 수집을 시작합니다."], key: "6" },
  mine: { title: "내 담당", empty: ["담당 공시가 없습니다", "공시를 선택한 뒤 C 키로 담당을 지정합니다."], key: "" },
};

const state = {
  me: null, view: "list", split: "inbox", q: "", items: [], selected: -1, detail: null,
  counts: {}, lastVisit: null, draftSource: null, undo: null, loading: false,
};

// ---------- 공통 ----------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "style") node.style.cssText = v; // CSP: style 속성 대신 CSSOM
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null && c !== false) node.append(c instanceof Node ? c : document.createTextNode(c));
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
  if (!res.ok) throw new Error((data && typeof data.detail === "string" && data.detail) || "요청을 처리하지 못했습니다.");
  return data;
}

const store = {
  get(k, d = null) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};

let toastTimer;
function toast(msg, undo) {
  const t = $("#toast");
  clearTimeout(toastTimer);
  t.replaceChildren(el("span", { text: msg }));
  state.undo = undo || null;
  if (undo) t.append(el("button", { type: "button", text: "실행 취소 Z", onclick: runUndo }), el("span", { class: "bar" }));
  t.hidden = false;
  toastTimer = setTimeout(() => { t.hidden = true; state.undo = null; }, undo ? 5000 : 2600);
}
async function runUndo() {
  const u = state.undo;
  if (!u) return;
  state.undo = null;
  $("#toast").hidden = true;
  try { await u(); toast("실행을 취소했습니다."); } catch (e) { toast(e.message); }
}

function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const hm = d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (d.toDateString() === now.toDateString()) return hm;
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return `어제 ${hm}`;
  return `${d.getMonth() + 1}/${d.getDate()}`;
}
const fmtDate = (s) => (s && s.length === 8 ? `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6)}` : s || "");
const initials = (name) => (name || "?").trim().slice(0, 1);
const won = (v) => (v == null ? "-" : Math.round(v).toLocaleString("ko-KR"));
const isTyping = () => ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);

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
  } catch (err) { $("#auth-error").textContent = err.message; }
});
$("#join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/register", { method: "POST", body: { code: e.target.dataset.code, username: f.get("username"), display_name: f.get("display_name"), password: f.get("password") } });
    location.hash = "#settings";
    await boot();
    toast("계정을 만들었습니다. 알림과 출입처를 설정하세요.");
  } catch (err) { $("#auth-error").textContent = err.message; }
});
$("#logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.hash = "";
  showAuth();
});

// ---------- 화면 전환 ----------
const VIEWS = ["list", "ask", "draft", "finance", "mail", "settings", "admin"];
function setView(view, navKey) {
  if (view === "admin" && state.me?.role !== "admin") view = "list";
  state.view = view;
  VIEWS.forEach((v) => ($(`#view-${v}`).hidden = v !== view));
  $$("[data-nav]").forEach((a) => a.setAttribute("aria-current", a.dataset.nav === navKey ? "page" : "false"));
  $(".sidebar").classList.remove("open");
  if (view !== "list") closeDetail(true);
  if (view === "ask") renderChats();
  if (view === "draft") renderDrafts();
  if (view === "finance") renderFinance();
  if (view === "mail") renderMail();
  if (view === "settings") renderSettings();
  if (view === "admin") renderAdmin();
  window.scrollTo(0, 0);
}

function route() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith("join/")) return showAuth(h.slice(5));
  if (!state.me) return;
  if (h.startsWith("d/")) {
    if (state.view !== "list") { setView("list", `s/${state.split}`); loadList(true); }
    return openDetail(h.slice(2));
  }
  if (h.startsWith("draft/")) {
    const [kind, ...rest] = h.slice(6).split("/");
    state.draftSource = { kind: kind === "m" ? "mail" : "disclosure", ref: rest.join("/") };
    return setView("draft", "draft");
  }
  if (h === "draft") state.draftSource = null;
  if (h.startsWith("s/") && SPLITS[h.slice(2)]) {
    closeDetail(true);  // 뒤로 가기·목록 이동이면 상세(휴대폰에서는 전체 화면)를 닫는다
    const changed = state.split !== h.slice(2) || state.view !== "list";
    state.split = h.slice(2);
    setView("list", h);
    if (changed || !state.items.length) loadList(true);
    return;
  }
  if (["ask", "draft", "finance", "mail", "settings", "admin"].includes(h)) return setView(h, h);
  location.replace("#s/inbox");
}
window.addEventListener("hashchange", route);

// ---------- 개수·오늘 요약 ----------
async function loadCounts() {
  const c = (state.counts = await api("/api/counts"));
  $$("[data-count]").forEach((n) => (n.textContent = c[n.dataset.count] ? c[n.dataset.count] : ""));
  document.title = c.inbox ? `(${c.inbox}) 청년의사 브리핑` : "청년의사 브리핑";
  if (state.view === "list" && state.split === "inbox" && !$("#today").hidden) renderToday().catch(() => {});
  return c;
}

async function renderToday() {
  const box = $("#today");
  if (state.split !== "inbox" || state.q) { box.hidden = true; return; }
  const s = await api("/api/summary");
  const c = state.counts.inbox !== undefined ? state.counts : await api("/api/counts");
  // 한 문장 요약 + 숫자 한 줄 (카드·알약 배지 없이)
  const story = el("p", { class: "story" });
  if (c.red) {
    story.append("미확인 중요 공시 ", el("b", { text: `${c.red}건` }));
    story.append(c.unclaimed ? ` 중 ${c.unclaimed}건이 담당 미지정입니다.` : ". 모두 담당이 지정되어 있습니다.");
  } else if (c.inbox) story.append(`미확인 중요 공시는 없습니다. 일반 공시 ${c.inbox}건이 남아 있습니다.`);
  else story.append("미확인 공시가 없습니다.");
  const fig = (label, n, href) => el("a", { class: "fig", href }, `${label} `, el("span", { class: "num", text: n }));
  const figs = [fig("미확인", c.inbox || 0, "#s/inbox"), fig("중요", c.red || 0, "#s/red"), fig("담당 미지정", c.unclaimed || 0, "#s/unclaimed"),
    fig("내 담당", c.mine || 0, "#s/mine"), fig("오늘 수집 중요", s.red || 0, "#s/all")];
  if (s.mails_today != null) figs.push(fig("오늘 메일", s.mails_today, "#mail"));
  box.replaceChildren(
    story,
    el("p", { class: "figures" }, figs.flatMap((f, i) => (i ? [el("span", { class: "sep", "aria-hidden": "true", text: "·" }), f] : [f]))),
    s.briefing ? el("details", { class: "digest" },
      el("summary", { text: `정기 브리핑 ${s.briefing.slot.slice(11)}${s.briefing.model ? " (AI 요약)" : ""}` }),
      el("p", { text: s.briefing.content })) : null,
  );
  box.hidden = false;
  const banner = $("#mode-banner");
  banner.hidden = s.alert_mode !== "log";
  banner.textContent = "기록 모드입니다. 공시는 수집하지만 알림은 발송하지 않습니다.";
  const st = $("#status-dot");
  const ok = s.dart_status === "정상";
  st.classList.toggle("ok", ok);
  st.classList.toggle("bad", !ok && s.dart_status !== "대기 중");
  $(".status-text", st).textContent = ok ? `DART 정상 · ${fmtTime(s.last_poll_at)} 수집` : s.dart_status;
  st.title = `DART: ${s.dart_status} / 알리오: ${s.alio_status}`;
}

// ---------- 목록 ----------
function listQuery(before = "") {
  const p = new URLSearchParams({ split: state.split });
  if (state.q) p.set("q", state.q);
  if (before) p.set("before", before);
  return `/api/feed?${p}`;
}

async function loadList(reset) {
  const feed = $("#feed");
  if (reset) {
    state.loading = true;
    feed.replaceChildren(...Array.from({ length: 8 }, () => el("div", { class: "skeleton", "aria-hidden": "true" })));
    $("#empty").hidden = true;
    $("#list-title").textContent = SPLITS[state.split].title;
    $("#done-all").hidden = !["inbox", "red", "beat"].includes(state.split);
  }
  const lastItem = reset ? null : state.items.at(-1);
  const before = lastItem ? `${lastItem.first_seen_at}|${lastItem.rcept_no}` : "";
  try {
    const { items } = await api(listQuery(before));
    state.items = reset ? items : [...state.items, ...items];
    if (reset) state.selected = -1;
    $("#more-btn").hidden = items.length < 50;
  } finally { state.loading = false; }
  renderList();
  loadCounts().then(renderListCount).catch(() => {});
  if (reset) renderToday().catch(() => {});
}

function renderListCount() {
  const n = state.counts[state.split];
  $("#list-count").textContent = n ? `${n}건` : state.items.length ? `${state.items.length}건` : "";
}

function bucketOf(it) {
  const t = new Date(it.first_seen_at);
  if (state.lastVisit && t > state.lastVisit && !it.done_at && state.split !== "all") return "새 공시";
  const now = new Date();
  if (t.toDateString() === now.toDateString()) return "오늘";
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (t.toDateString() === y.toDateString()) return "어제";
  return "이전";
}

function rowFor(it, idx, fresh) {
  const lv = LV[it.level] || LV.yellow;
  const unread = state.lastVisit && new Date(it.first_seen_at) > state.lastVisit && !it.done_at;
  // 행 안의 버튼은 마우스용. 키보드는 단축키(O·C·E)로 같은 동작을 하므로 탭 순서와 보조기술에서 뺀다
  const act = (label, title, fn) => el("button", { class: "icon-btn", type: "button", title, tabindex: "-1", "aria-hidden": "true",
    onclick: (e) => { e.stopPropagation(); fn(); } }, label);
  const mine = it.claimed_by === state.me.id;
  return el("div", {
    class: `item${unread ? " unread" : ""}${fresh ? " fresh" : ""}`, role: "option", id: `it-${idx}`, "data-id": it.rcept_no,
    "aria-selected": idx === state.selected ? "true" : "false", style: it.done_at && state.split === "all" ? "opacity:.6" : "",
    onclick: () => select(idx, true),
  },
    el("span", { class: `lv ${it.level}`, text: lv.label }),
    el("span", { class: "who", text: it.corp_name }),
    el("span", { class: "title", text: it.report_nm, title: it.report_nm }),
    el("span", { class: "meta" },
      it.is_correction ? el("span", { class: "tag-s fix", text: "정정" }) : null,
      it.source === "alio" ? el("span", { class: "tag-s alio", text: "알리오" }) : null,
      it.claimed_name ? el("span", { class: "claimed-by", title: `담당: ${it.claimed_name}` },
        el("span", { class: "avatar", text: initials(it.claimed_name) }), it.written_at ? "기사화" : "") : null,
      el("span", { class: "acts" },
        act("원문", "원문 보기 (O)", () => window.open(it.url, "_blank", "noopener")),
        act(mine ? "해제" : "담당", mine ? "담당 해제 (C)" : "담당 지정 (C)", () => toggleClaim(it)),
        it.done_at ? null : act("확인", "확인 처리 (E)", () => markDone(it))),
      el("time", { class: "time", datetime: it.first_seen_at, text: fmtTime(it.first_seen_at) })),
  );
}

function renderList(freshIds = new Set()) {
  const nodes = [];
  let last = null;
  const groups = {};
  state.items.forEach((it) => { const b = bucketOf(it); groups[b] = (groups[b] || 0) + 1; });
  state.items.forEach((it, idx) => {
    const b = bucketOf(it);
    if (b !== last) { nodes.push(el("div", { class: "group-head", role: "presentation" }, b, el("span", { class: "n", text: groups[b] }))); last = b; }
    nodes.push(rowFor(it, idx, freshIds.has(it.rcept_no)));
  });
  $("#feed").replaceChildren(...nodes);
  const empty = $("#empty");
  empty.hidden = state.items.length > 0;
  if (!state.items.length) {
    const [t, s] = state.q ? ["검색 결과가 없습니다", "다른 기업명이나 단어로 검색하세요."] : SPLITS[state.split].empty;
    empty.replaceChildren(
      el("strong", { text: t }), el("span", { text: s }));
  }
  renderListCount();
}

function select(idx, open) {
  if (idx < 0 || idx >= state.items.length) return;
  state.selected = idx;
  $$(".item").forEach((n) => n.setAttribute("aria-selected", n.id === `it-${idx}` ? "true" : "false"));
  $("#feed").setAttribute("aria-activedescendant", `it-${idx}`);
  $(`#it-${idx}`)?.scrollIntoView({ block: "nearest" });
  if (open) location.hash = `#d/${encodeURIComponent(state.items[idx].rcept_no)}`;
  else if (state.detail) openDetail(state.items[idx].rcept_no, true);
}

$("#more-btn").addEventListener("click", () => loadList(false));
let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.q = e.target.value.trim(); loadList(true); }, 250);
});
$("#done-all").addEventListener("click", async () => {
  if (!state.items.length) return;
  const r = await api(`/api/done-all?split=${state.split}`, { method: "POST" });
  const ids = r.ids;
  state.items = [];
  renderList();
  loadCounts().catch(() => {});
  toast(`${r.done}건을 확인 처리했습니다.`, async () => {
    await Promise.all(ids.map((id) => api(`/api/done/${encodeURIComponent(id)}`, { method: "DELETE" })));
    await loadList(true);
    if (state.items.length) select(0, false);
  });
});

// ---------- 동작: 확인·맡기 (즉시 반영 + 되돌리기) ----------
const currentItem = () => state.detail || state.items[state.selected];

async function markDone(it) {
  if (!it || it.done_at) return;
  const idx = state.items.findIndex((x) => x.rcept_no === it.rcept_no);
  $(`.item[data-id="${CSS.escape(it.rcept_no)}"]`)?.classList.add("leaving");
  const removeFromList = !["all", "mine", "alio"].includes(state.split);
  setTimeout(() => {
    if (removeFromList && idx >= 0) {
      state.items.splice(idx, 1);
      state.selected = Math.min(idx, state.items.length - 1);
    } else if (idx >= 0) state.items[idx].done_at = new Date().toISOString();
    renderList();
    if (state.selected >= 0) select(state.selected, false);
  }, 150);
  if (state.detail?.rcept_no === it.rcept_no) closeDetail();
  try {
    await api(`/api/done/${encodeURIComponent(it.rcept_no)}`, { method: "POST" });
    loadCounts().catch(() => {});
    toast("확인 처리했습니다.", async () => { await api(`/api/done/${encodeURIComponent(it.rcept_no)}`, { method: "DELETE" }); await refreshAfterChange(it.rcept_no); });
  } catch (e) { toast(e.message); loadList(true); }
}

async function toggleClaim(it) {
  if (!it) return;
  const mine = it.claimed_by === state.me.id;
  if (it.claimed_by && !mine) { toast(`${it.claimed_name} 기자가 담당하고 있습니다.`); return; }
  try {
    await api(`/api/claims/${encodeURIComponent(it.rcept_no)}`, { method: mine ? "DELETE" : "POST" });
    const undo = async () => { await api(`/api/claims/${encodeURIComponent(it.rcept_no)}`, { method: mine ? "POST" : "DELETE" }); await refreshAfterChange(it.rcept_no); };
    toast(mine ? "담당을 해제했습니다." : "담당으로 지정했습니다.", undo);
    await refreshAfterChange(it.rcept_no);
  } catch (e) { toast(e.message); }
}

async function refreshAfterChange(id) {
  await loadList(true);
  const idx = state.items.findIndex((x) => x.rcept_no === id);
  if (idx >= 0) select(idx, false);
  if (state.detail?.rcept_no === id) openDetail(id, true);
}

// ---------- 상세 ----------
async function openDetail(id, quiet) {
  let d;
  try { d = await api(`/api/disclosures/${encodeURIComponent(id)}`); }
  catch (err) { toast(err.message); return; }
  state.detail = d;
  const idx = state.items.findIndex((i) => i.rcept_no === id);
  if (idx >= 0 && idx !== state.selected) { state.selected = idx; $$(".item").forEach((n) => n.setAttribute("aria-selected", n.id === `it-${idx}` ? "true" : "false")); }
  const lv = LV[d.level] || LV.yellow;
  const mine = d.claimed_by === state.me.id;
  const other = d.claimed_by && !mine;
  const bar = (label, title, fn, opts = {}) => {
    const [text, key] = label.split(" ");
    return el("button", { class: "icon-btn", type: "button", title, "aria-label": title, disabled: opts.disabled, onclick: fn },
      text, key ? el("span", { class: "k", "aria-hidden": "true", text: ` ${key}` }) : null);
  };
  const ask = (q) => { location.hash = "#ask"; setTimeout(() => sendQuestion(q), 50); };
  const meta = [d.source === "alio" ? "알리오" : "DART", d.is_correction ? "정정공시" : null,
    d.watched && d.source !== "alio" ? "감시 기업" : null].filter(Boolean).join(" · ");
  const panel = $("#detail");
  panel.replaceChildren(
    el("div", { class: "d-bar" },
      bar("✕", "닫기 (Esc)", () => closeDetail()),
      el("span", { class: "sp" }),
      bar("확인 E", "확인 처리 (E)", () => markDone(d)),
      bar(mine ? "해제 C" : "담당 C", other ? `담당: ${d.claimed_name}` : mine ? "담당 해제 (C)" : "담당 지정 (C)", () => toggleClaim(d), { disabled: other }),
      bar("원문 O", "원문 보기 (O)", () => window.open(d.url, "_blank", "noopener")),
      bar("초안 D", state.me.llm_ready ? "초안 작성 (D)" : "AI 인증키 등록 후 사용 가능", () => (location.hash = `#draft/d/${encodeURIComponent(d.rcept_no)}`), { disabled: !state.me.llm_ready })),
    el("div", { class: "d-body" },
      el("div", { class: "d-head" },
        el("h2", { class: "d-title", text: d.report_nm }),
        el("p", { class: "d-corp" }, el("strong", { text: d.corp_name }), el("span", { class: `lv ${d.level}`, text: lv.label }), el("span", { class: "muted", text: meta }))),
      el("p", { style: "margin:0" }, el("a", { class: "source", href: d.url, target: "_blank", rel: "noopener noreferrer" }, d.source === "alio" ? "알리오 원문" : "DART 원문")),
      el("dl", { class: "props" },
        el("dt", { text: "접수일" }), el("dd", { text: fmtDate(d.rcept_dt) }),
        el("dt", { text: "제출인" }), el("dd", { text: d.flr_nm || "-" }),
        el("dt", { text: "분류 근거" }), el("dd", { text: d.keyword ? `제목 키워드 ${d.keyword}` : "해당 키워드 없음" }),
        d.rm ? el("dt", { text: "비고" }) : null, d.rm ? el("dd", { text: d.rm }) : null,
        el("dt", { text: "접수번호" }), el("dd", { class: "mono", text: d.rcept_no }),
        el("dt", { text: "수집" }), el("dd", { text: fmtTime(d.first_seen_at) }),
        el("dt", { text: "담당" }), el("dd", { text: d.claimed_name ? `${d.claimed_name} (${fmtTime(d.claimed_at)})` : "미지정" }),
        el("dt", { text: "기사화" }), el("dd", {}, d.written_at ? (d.written_url ? el("a", { href: d.written_url, target: "_blank", rel: "noopener noreferrer", text: fmtTime(d.written_at) }) : fmtTime(d.written_at)) : "-")),
      mine ? el("div", { class: "d-actions" }, el("button", { class: "btn sm", type: "button",
        text: d.written_at ? "기사 URL 수정" : "기사화 기록", onclick: () => markWritten(d) })) : null,
      state.me.llm_ready ? el("section", {}, el("h3", { class: "section-label", text: "AI 질문" }),
        el("ul", { class: "text-list" },
          el("li", {}, el("button", { class: "text-btn", type: "button", text: "핵심 요약", onclick: () => ask(`${d.corp_name} ${d.report_nm}(접수번호 ${d.rcept_no}) 핵심 요약`) })),
          d.source !== "alio" ? el("li", {}, el("button", { class: "text-btn", type: "button", text: "전년 실적 비교", onclick: () => ask(`${d.corp_name} 최근 사업연도 매출액·영업이익·당기순이익 전년 대비`) })) : null,
          el("li", {}, el("button", { class: "text-btn", type: "button", text: "최근 30일 공시", onclick: () => ask(`${d.corp_name} 최근 30일 공시 시간순 정리`) })))) : null,
      d.source !== "alio" ? el("p", { class: "muted small", text: "DART 공개는 제출 후 약 15분 늦습니다." }) : null),
  );
  panel.hidden = false;
  $("#app").classList.add("has-detail");
  if (!quiet) panel.querySelector(".d-bar button")?.focus({ preventScroll: true });
}

async function markWritten(d) {
  const url = prompt("기사 URL을 입력하세요. 없으면 비워 둡니다.", d.written_url || "");
  if (url === null) return;
  try {
    await api(`/api/claims/${encodeURIComponent(d.rcept_no)}/written`, { method: "POST", body: { url } });
    toast("기사화로 기록했습니다.");
    openDetail(d.rcept_no, true);
  } catch (e) { toast(e.message); }
}

function closeDetail(silent) {
  if ($("#detail").hidden) return;
  $("#detail").hidden = true;
  $("#app").classList.remove("has-detail");
  state.detail = null;
  if (!silent && location.hash.startsWith("#d/")) history.replaceState(null, "", `#s/${state.split}`);
  if (!silent) $("#feed").focus({ preventScroll: true });
}

// ---------- 명령 팔레트 ----------
let paletteItems = [];
let paletteIdx = 0;
let paletteReturn = null;
function commands(query) {
  const it = currentItem();
  const go = (h) => () => (location.hash = h);
  const list = [
    ...Object.entries(SPLITS).map(([k, v]) => ({ grp: "이동", label: v.title, key: v.key, run: go(`#s/${k}`) })),
    { grp: "이동", label: "AI 질문", run: go("#ask") },
    { grp: "이동", label: "기사 초안", run: go("#draft") },
    { grp: "이동", label: "공공기관 결산", run: go("#finance") },
    { grp: "이동", label: "보도자료 메일", run: go("#mail") },
    { grp: "이동", label: "설정", run: go("#settings") },
    state.me?.role === "admin" ? { grp: "이동", label: "관리자", run: go("#admin") } : null,
    it ? { grp: "선택한 공시", label: `확인 처리 · ${it.corp_name}`, key: "E", run: () => markDone(it) } : null,
    it ? { grp: "선택한 공시", label: `${it.claimed_by === state.me.id ? "담당 해제" : "담당 지정"} · ${it.corp_name}`, key: "C", run: () => toggleClaim(it) } : null,
    it ? { grp: "선택한 공시", label: "원문 보기", key: "O", run: () => window.open(it.url, "_blank", "noopener") } : null,
    it && state.me.llm_ready ? { grp: "선택한 공시", label: "초안 작성", key: "D", run: go(`#draft/d/${encodeURIComponent(it.rcept_no)}`) } : null,
    { grp: "작업", label: "현재 목록 전체 확인 처리", run: () => $("#done-all").click() },
    { grp: "작업", label: "이 기기 알림 설정", run: () => enablePush().catch((e) => toast(e.message)) },
    { grp: "보기", label: "테마 전환 (시스템, 라이트, 다크)", run: cycleTheme },
    { grp: "보기", label: "목록 밀도 전환 (기본, 촘촘)", run: () => applyDensity(store.get("nb-density") === "compact" ? "comfy" : "compact") },
    { grp: "도움말", label: "단축키 J/K 이동, Enter 열기, E 확인, C 담당, O 원문, D 초안, Z 실행 취소, 1~6 목록 전환", run: () => {} },
  ].filter(Boolean);
  const q = query.trim().toLowerCase();
  const hits = q ? list.filter((c) => c.label.toLowerCase().includes(q) || c.grp.includes(q)) : list;
  if (q) hits.push({ grp: "검색", label: `공시 검색: ${query.trim()}`, run: () => { $("#search").value = query.trim(); state.q = query.trim(); if (location.hash === "#s/all") loadList(true); else location.hash = "#s/all"; } });
  // AI 질문은 비용이 드므로 맨 끝에 둔다 (Enter 한 번에 질문이 나가지 않게)
  if (q && state.me?.llm_ready) hits.push({ grp: "AI", label: `AI에게 질문: ${query.trim()}`, run: () => { location.hash = "#ask"; setTimeout(() => sendQuestion(query.trim()), 50); } });
  return hits;
}
function renderPalette() {
  paletteItems = commands($("#palette-input").value);
  paletteIdx = Math.min(paletteIdx, Math.max(0, paletteItems.length - 1));
  const nodes = [];
  let grp = null;
  paletteItems.forEach((c, i) => {
    if (c.grp !== grp) { nodes.push(el("li", { class: "grp", role: "presentation", text: c.grp })); grp = c.grp; }
    nodes.push(el("li", { class: "opt", role: "option", id: `po-${i}`, "aria-selected": i === paletteIdx ? "true" : "false",
      onclick: () => runPalette(i), onmousemove: () => { if (paletteIdx !== i) { paletteIdx = i; renderPaletteSel(); } } },
      el("span", { class: "lbl", text: c.label }), c.key ? el("kbd", { text: c.key }) : null));
  });
  $("#palette-list").replaceChildren(...nodes);
  $("#palette-input").setAttribute("aria-activedescendant", `po-${paletteIdx}`);
}
function renderPaletteSel() {
  $$("#palette-list .opt").forEach((n) => n.setAttribute("aria-selected", n.id === `po-${paletteIdx}` ? "true" : "false"));
  $(`#po-${paletteIdx}`)?.scrollIntoView({ block: "nearest" });
  $("#palette-input").setAttribute("aria-activedescendant", `po-${paletteIdx}`);
}
function openPalette() {
  paletteReturn = document.activeElement;
  $("#palette").hidden = false;
  $("#palette-input").value = "";
  paletteIdx = 0;
  renderPalette();
  $("#palette-input").focus();
}
function closePalette() {
  $("#palette").hidden = true;
  paletteReturn?.focus?.({ preventScroll: true });
}
function runPalette(i) {
  const c = paletteItems[i];
  closePalette();
  c?.run();
}
$("#palette-btn").addEventListener("click", openPalette);
$("#palette-input").addEventListener("input", () => { paletteIdx = 0; renderPalette(); });
$("#palette-input").addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") { e.preventDefault(); paletteIdx = Math.min(paletteIdx + 1, paletteItems.length - 1); renderPaletteSel(); }
  else if (e.key === "ArrowUp") { e.preventDefault(); paletteIdx = Math.max(paletteIdx - 1, 0); renderPaletteSel(); }
  else if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); runPalette(paletteIdx); }
  else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
  else if (e.key === "Tab") e.preventDefault();
});
$("#palette").addEventListener("click", (e) => { if (e.target.id === "palette") closePalette(); });

// ---------- 키보드 ----------
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k" && state.me && !$("#app").hidden) { e.preventDefault(); $("#palette").hidden ? openPalette() : closePalette(); return; }
  if (!$("#palette").hidden || !state.me || $("#app").hidden) return;
  if (e.key === "Escape") { if (isTyping()) document.activeElement.blur(); else closeDetail(); return; }
  if (isTyping() || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
  if (e.key === ".") { e.preventDefault(); openPalette(); return; }
  if (e.key.toLowerCase() === "z" && state.undo) { e.preventDefault(); runUndo(); return; }
  const n = Object.entries(SPLITS).find(([, v]) => v.key && v.key === e.key);
  if (n) { location.hash = `#s/${n[0]}`; return; }
  if (state.view !== "list") return;
  const it = currentItem();
  switch (e.key.toLowerCase()) {
    case "/": e.preventDefault(); $("#search").focus(); break;
    case "j": case "arrowdown": e.preventDefault(); select(Math.min(state.selected + 1, state.items.length - 1), false); break;
    case "k": case "arrowup": e.preventDefault(); select(Math.max(state.selected - 1, 0), false); break;
    case "enter": if (state.selected >= 0 && !state.detail) select(state.selected, true); break;
    case "e": markDone(it); break;
    case "c": toggleClaim(it); break;
    case "o": if (it) window.open(it.url, "_blank", "noopener"); break;
    case "d": if (it && state.me.llm_ready) location.hash = `#draft/d/${encodeURIComponent(it.rcept_no)}`; break;
  }
});

// ---------- AI 질문 ----------
const TOOL_NAMES = { search_disclosures: "공시 검색", get_disclosure: "공시 원문", company_financials: "DART 재무",
  alio_finance: "알리오 결산", search_newsroom_articles: "기사 검색", search_my_mail: "내 메일" };

function linkify(text) {
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
  if (trace.length) b.append(el("div", { class: "tools" }, [...new Set(trace.map((t) => TOOL_NAMES[t.tool] || t.tool))].map((n) => el("span", { class: "tag-s", text: n }))));
  return b;
}
async function renderChats() {
  const box = $("#chat");
  if (!state.me.llm_ready) {
    box.replaceChildren(el("div", { class: "empty" }, el("strong", { text: "AI 인증키가 등록되지 않았습니다" }), el("span", { text: "관리자가 .env에 인증키를 등록하면 사용할 수 있습니다." })));
    $("#ask-form").hidden = true;
    return;
  }
  $("#ask-form").hidden = false;
  const { items } = await api("/api/chats");
  box.replaceChildren(...items.reverse().flatMap((c) => [el("div", { class: "bubble q", text: c.question }), answerBubble(c.answer, c.trace)]));
  if (!items.length) {
    box.append(el("div", { class: "examples" }, el("p", { class: "muted small", text: "질문 예" }),
      el("ul", { class: "text-list" }, ["이번 주 기술이전 공시 목록", "서울대병원 2025년 의료수익 전년 대비", "유한양행 2025년 매출액과 영업이익"].map((q) =>
        el("li", {}, el("button", { class: "text-btn", type: "button", text: q, onclick: () => sendQuestion(q) }))))));
  }
  box.lastElementChild?.scrollIntoView({ block: "end" });
  $("#ask-input").focus({ preventScroll: true });
}
async function sendQuestion(q) {
  q = (q || "").trim();
  if (!q) return;
  if (!state.me.llm_ready) { toast("AI 인증키 등록 후 사용할 수 있습니다."); return; }
  const input = $("#ask-input");
  input.value = "";
  input.disabled = true;
  $(".examples", $("#chat"))?.remove();
  const pending = el("div", { class: "bubble a muted", text: "자료 검색 중" });
  $("#chat").append(el("div", { class: "bubble q", text: q }), pending);
  pending.scrollIntoView({ block: "end" });
  try {
    const r = await api("/api/ask", { method: "POST", body: { question: q } });
    pending.replaceWith(answerBubble(r.answer, r.trace));
  } catch (err) { pending.textContent = err.message; }
  finally { input.disabled = false; input.focus({ preventScroll: true }); }
}
$("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); sendQuestion($("#ask-input").value); });
$("#ask-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendQuestion(e.target.value); }
});

// ---------- 기사 초안 ----------
async function renderDrafts() {
  const src = state.draftSource;
  const title = $("#draft-form").elements.namedItem("title");
  if (src?.kind === "disclosure") {
    let label = "공시";
    try { const d = await api(`/api/disclosures/${encodeURIComponent(src.ref)}`); label = `${d.corp_name} · ${d.report_nm}`; } catch {}
    $("#draft-source").textContent = `${label}. 공시 원문은 자동으로 첨부됩니다. 취재 메모가 있으면 입력하세요.`;
    title.hidden = true;
  } else if (src?.kind === "mail") {
    $("#draft-source").textContent = "선택한 보도자료 메일을 원자료로 사용합니다.";
    title.hidden = true;
  } else {
    $("#draft-source").textContent = "보도자료나 취재 메모를 입력하세요. 공시 상세에서도 바로 작성할 수 있습니다.";
    title.hidden = false;
  }
  const { items } = await api("/api/drafts");
  $("#draft-list").replaceChildren(...(items.length ? items.map((d) => el("li", {},
    el("button", { type: "button", onclick: () => showDraft(d.id) }, `${fmtTime(d.created_at)} · ${d.source_title || "제목 없음"}`)))
    : [el("li", { class: "muted small", text: "작성한 초안이 없습니다." })]));
}
function renderDraftResult(d) {
  $("#draft-result").hidden = false;
  $("#draft-text").value = d.draft;
  const miss = d.checks.filter((c) => !c.found);
  $("#draft-checks").replaceChildren(
    el("p", { class: "check-head", text: miss.length ? `원자료에서 확인되지 않은 숫자 ${miss.length}개` : "모든 숫자가 원자료와 일치합니다." }),
    el("ul", { class: "checks" }, d.checks.map((c) => el("li", { class: c.found ? "" : "miss", title: c.context, text: `${c.found ? "✓" : "✗"} ${c.number}` }))));
  $("#draft-examples").textContent = d.examples?.length ? "참고 기사: " + d.examples.map((e) => e.title).join(" / ") : "";
  $("#draft-result").scrollIntoView({ block: "start", behavior: "smooth" });
}
async function showDraft(id) { try { renderDraftResult(await api(`/api/drafts/${id}`)); } catch (e) { toast(e.message); } }
$("#draft-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.me.llm_ready) { toast("AI 인증키 등록 후 사용할 수 있습니다."); return; }
  const f = new FormData(e.target);
  const src = state.draftSource;
  const body = src ? { source_kind: src.kind, source_ref: src.ref, text: f.get("text") || "", kind: f.get("kind") }
    : { source_kind: "text", title: f.get("title") || "", text: f.get("text") || "", kind: f.get("kind") };
  const btn = e.target.querySelector("button[type=submit]");
  $("#draft-busy").hidden = false; btn.disabled = true;
  try { renderDraftResult(await api("/api/drafts", { method: "POST", body })); renderDrafts(); }
  catch (err) { toast(err.message); }
  finally { $("#draft-busy").hidden = true; btn.disabled = false; }
});
$("#draft-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#draft-text").value); toast("복사했습니다."); }
  catch { $("#draft-text").select(); toast("Ctrl+C로 복사하세요."); }
});

// ---------- 공공기관 결산 ----------
async function renderFinance() {
  const a = await api("/api/alio");
  $("#alio-status").textContent = a.enabled ? `${a.status}${a.last_poll_at ? " · 마지막 수집 " + fmtTime(a.last_poll_at) : ""}` : "알리오 수집 꺼짐";
  $("#alio-orgs").textContent = a.orgs.length ? a.orgs.map((o) => o.name).join(", ") : "기관 목록을 아직 불러오지 못했습니다.";
  $("#alio-missing").textContent = a.missing.length ? `알리오에 없는 기관명: ${a.missing.join(", ")}. config/alio.toml의 표기를 확인하세요.` : "";
  $("#alio-finance").replaceChildren(...(a.finance.length ? a.finance.map((f) => el("section", { class: "card stack" },
    el("div", { class: "row between" }, el("h2", { class: "h3", text: f.org }),
      el("a", { class: "source", href: f.url, target: "_blank", rel: "noopener noreferrer" }, "알리오 원문")),
    el("p", { class: "muted small", style: "margin:0", text: [f.title, f.unit].filter(Boolean).join(" · ") }),
    el("table", { class: "fin" }, el("thead", {}, el("tr", {}, ["항목", "당기", "전기", "증감", "증감률"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, f.items.map((i) => el("tr", {},
        el("td", { text: i.label + (i.year ? ` (${i.year})` : "") }), el("td", { text: won(i.value) }), el("td", { text: won(i.prev) }),
        el("td", { class: i.change > 0 ? "up" : i.change < 0 ? "down" : "", text: i.change == null ? "-" : (i.change > 0 ? "+" : "") + won(i.change) }),
        el("td", { class: i.pct > 0 ? "up" : i.pct < 0 ? "down" : "", text: i.pct == null ? "-" : `${i.pct > 0 ? "+" : ""}${i.pct}%` })))))))
    : [el("div", { class: "empty" }, el("strong", { text: "수집된 결산이 없습니다" }), el("span", { text: "결산 공시(통상 3~4월)가 올라오면 전년 대비 표가 생성됩니다." }))]));
}

// ---------- 메일 ----------
async function renderMail() {
  const off = !state.me.mail_enabled;
  $("#mail-off").hidden = !off;
  $("#mail-wrap").hidden = off;
  if (off) return;
  const { items } = await api("/api/mail");
  $("#mail-list").replaceChildren(...(items.length ? items.map((m) => el("div", { class: "item", role: "listitem", tabindex: "0",
    onclick: () => openMail(m.id), onkeydown: (e) => { if (e.key === "Enter") openMail(m.id); } },
    el("span", { class: "lv", text: "✉" }), el("span", { class: "who", text: m.sender }), el("span", { class: "title", text: m.subject }),
    el("span", { class: "meta" }, m.embargo ? el("span", { class: "mail-embargo", text: "엠바고" }) : null, el("time", { class: "time", text: fmtTime(m.sent_at || m.first_seen_at) }))))
    : [el("div", { class: "empty" }, el("strong", { text: "수집된 메일이 없습니다" }), el("span", { text: "설정에서 메일을 연결하세요." }))]));
}
async function openMail(id) {
  const m = await api(`/api/mail/${id}`);
  const box = $("#mail-detail");
  box.hidden = false;
  box.replaceChildren(el("div", { class: "muted small", text: `${m.sender} · ${fmtTime(m.sent_at)}` }), el("h2", { class: "h3", text: m.subject }),
    m.embargo ? el("p", { class: "mail-embargo", text: m.embargo }) : null, el("div", { class: "pre", text: m.body }),
    el("div", { class: "row" }, el("button", { class: "btn", type: "button", text: "초안 작성", onclick: () => (location.hash = `#draft/m/${m.id}`) })));
  box.scrollIntoView({ block: "start", behavior: "smooth" });
}

// ---------- 설정 ----------
async function renderSettings() {
  const me = (state.me = await api("/api/me"));
  const kindName = { all: "보건의료 전체", watch: "감시 기업 전체", company: "기업", keyword: "키워드" };
  $("#subs").replaceChildren(...(me.subscriptions.length ? me.subscriptions.map((s) =>
    el("span", { class: "tag" }, `${kindName[s.kind]}${s.value ? ": " + s.value : ""}`,
      el("button", { type: "button", "aria-label": `${s.value || kindName[s.kind]} 삭제`, text: "×", onclick: async () => {
        await api(`/api/subscriptions?kind=${s.kind}&value=${encodeURIComponent(s.value)}`, { method: "DELETE" }); renderSettings(); loadCounts();
      } }))) : [el("span", { class: "muted small", text: "지정된 항목이 없습니다." })]));
  $("#push-state").textContent = `알림 수신 기기 ${me.push_devices}대 · 서버 ${me.alert_mode === "notify" ? "알림 발송 중" : "기록 모드(알림 미발송)"}`;
  $("#font-size").value = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--fs")) || 14;
  $("#theme-select").value = store.get("nb-theme", "auto");
  $("#density-select").value = store.get("nb-density", "comfy");
  $("#reporter-form").reporter_id.value = me.reporter_id || "";
  $("#stylebook-meta").textContent = me.stylebook ? `${fmtTime(me.stylebook.updated_at)} 수정 · 기사 ${me.stylebook.source_count}편 분석` : "없음";
  $("#stylebook").value = (await api("/api/stylebook")).content || "";
  $("#stylebook-build").disabled = !me.llm_ready;
  $("#mail-settings").hidden = !me.mail_enabled;
  const acc = me.mail_account;
  $("#mail-account-state").textContent = acc ? `연결: ${acc.username} · ${acc.folder}${acc.last_error ? " · 오류: " + acc.last_error : ""}` : "연결된 메일 계정이 없습니다.";
  $("#usage").textContent = me.llm_ready ? `이번 달 AI 사용 ${me.spent_krw.toLocaleString("ko-KR")}원 / 한도 ${me.limit_krw.toLocaleString("ko-KR")}원` : "AI 인증키가 등록되지 않았습니다.";
  pollArticles();
}
$("#sub-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try { await api("/api/subscriptions", { method: "POST", body: { kind: f.get("kind"), value: f.get("value") || "" } }); e.target.reset(); renderSettings(); loadCounts(); }
  catch (err) { toast(err.message); }
});
$("#sub-form select").addEventListener("change", (e) => { $("#sub-form input").hidden = ["all", "watch"].includes(e.target.value); });
$("#reporter-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await api("/api/me/reporter", { method: "POST", body: { reporter_id: e.target.reporter_id.value.trim() } }); toast("저장했습니다."); renderSettings(); }
  catch (err) { toast(err.message); }
});
let articlesTimer;
async function pollArticles() {
  clearTimeout(articlesTimer);
  const st = await api("/api/articles/status");
  const j = st.job;
  let msg = `수집한 내 기사 ${st.count}편`;
  if (j?.state === "running") msg += ` · 수집 중 (확인 ${j.checked || 0}건, 추가 ${j.added || 0}건)`;
  else if (j?.state === "done") msg += ` · ${fmtTime(j.at)} 완료 (추가 ${j.added}건)`;
  else if (j?.state === "error") msg += ` · 오류: ${j.error}`;
  $("#articles-state").textContent = msg;
  if (j?.state === "running" && state.view === "settings") articlesTimer = setTimeout(pollArticles, 4000);
}
$("#articles-btn").addEventListener("click", async () => {
  try { const r = await api("/api/articles/collect", { method: "POST" }); toast(r.started ? "기사 수집을 시작했습니다." : r.message); pollArticles(); }
  catch (err) { toast(err.message); }
});
$("#stylebook-build").addEventListener("click", async (e) => {
  e.target.disabled = true;
  toast("스타일북 생성 중");
  try { const r = await api("/api/stylebook/build", { method: "POST" }); $("#stylebook").value = r.content; toast("스타일북을 생성했습니다. 내용을 검토하세요."); renderSettings(); }
  catch (err) { toast(err.message); }
  finally { e.target.disabled = false; }
});
$("#stylebook-save").addEventListener("click", async () => {
  try { await api("/api/stylebook", { method: "PUT", body: { content: $("#stylebook").value } }); toast("저장했습니다."); } catch (err) { toast(err.message); }
});
$("#mail-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await api("/api/mail/account", { method: "PUT", body: Object.fromEntries(new FormData(e.target).entries()) }); e.target.password.value = ""; toast("메일 계정을 연결했습니다."); renderSettings(); }
  catch (err) { toast(err.message); }
});
$("#mail-disconnect").addEventListener("click", async () => {
  if (!confirm("메일 연결을 해제하고 수집된 메일을 삭제합니다. 계속하시겠습니까?")) return;
  await api("/api/mail/account", { method: "DELETE" }); toast("연결을 해제했습니다."); renderSettings();
});
$("#font-size").addEventListener("input", (e) => { document.documentElement.style.setProperty("--fs", `${e.target.value}px`); store.set("nb-fs", e.target.value); });
$("#theme-select").addEventListener("change", (e) => applyTheme(e.target.value));
$("#density-select").addEventListener("change", (e) => applyDensity(e.target.value));

function applyTheme(t) {
  if (t === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
  store.set("nb-theme", t);
}
function cycleTheme() {
  const order = ["auto", "light", "dark"];
  const next = order[(order.indexOf(store.get("nb-theme", "auto")) + 1) % 3];
  applyTheme(next);
  toast({ auto: "테마: 시스템 설정", light: "테마: 라이트", dark: "테마: 다크" }[next]);
}
function applyDensity(d) {
  if (d === "compact") document.documentElement.setAttribute("data-density", "compact");
  else document.documentElement.removeAttribute("data-density");
  store.set("nb-density", d);
}

// ---------- 푸시 알림 ----------
function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}
async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) { toast("이 브라우저는 알림을 지원하지 않습니다. 아이폰은 홈 화면에 추가한 앱에서 설정하세요."); return; }
  const perm = await Notification.requestPermission();
  if (perm !== "granted") { toast("알림 권한이 차단되어 있습니다. 브라우저 설정에서 허용하세요."); return; }
  const reg = await navigator.serviceWorker.register("/sw.js");
  const { key } = await api("/api/push/key");
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
  await api("/api/push/subscribe", { method: "POST", body: sub.toJSON() });
  $("#push-btn").hidden = true;
  toast("이 기기에서 알림을 받습니다.");
  if (state.view === "settings") renderSettings();
}
$("#push-btn").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-enable").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-test").addEventListener("click", async () => {
  try { const { sent } = await api("/api/push/test", { method: "POST" }); toast(sent ? `테스트 알림을 ${sent}대에 보냈습니다.` : "알림 수신 기기가 없습니다. 먼저 알림을 설정하세요."); }
  catch (err) { toast(err.message); }
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
  const kv = (k, v) => [el("dt", { text: k }), el("dd", { text: v })];
  $("#metrics-totals").replaceChildren(...kv("수집 공시", `${t.disclosures}건 (중요 ${t.red}건)`), ...kv("발송 알림", `${t.alerts}건`),
    ...kv("수집 가동률", t.uptime_pct == null ? "DART 인증키 없음" : `${t.uptime_pct}%`), ...kv("AI 비용", `${t.cost_krw.toLocaleString("ko-KR")}원`));
  $("#metrics-users").replaceChildren(...mt.users.map((u) => el("tr", {}, el("td", { text: u.display_name }), el("td", { text: u.claims }),
    el("td", { text: u.written }), el("td", { text: u.questions }), el("td", { text: u.drafts }), el("td", { text: `${u.cost_krw.toLocaleString("ko-KR")}원` }))));
  $("#admin-status").replaceChildren(
    el("dt", { text: "DART" }), el("dd", { text: `${st.dart_status} · 오늘 호출 ${st.dart_calls_today}건` }),
    el("dt", { text: "마지막 수집" }), el("dd", { text: st.last_poll_at ? fmtTime(st.last_poll_at) : "-" }),
    el("dt", { text: "알림 모드" }), el("dd", { text: st.alert_mode === "notify" ? "알림 발송" : "기록 모드 (.env에서 ALERT_MODE=notify로 전환)" }),
    el("dt", { text: "알리오" }), el("dd", { text: st.alio_status }),
    el("dt", { text: "AI" }), el("dd", { text: st.llm }), el("dt", { text: "메일" }), el("dd", { text: st.mail }));
  $("#users").replaceChildren(...us.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.username }), el("td", { text: u.role === "admin" ? "관리자" : "기자" }),
    el("td", {}, `${u.spent_krw.toLocaleString("ko-KR")} / `, el("input", { class: "limit-input", type: "number", min: "0", step: "1000", value: u.limit_krw,
      "aria-label": `${u.display_name} 월 한도(원)`, onchange: async (e) => { await api(`/api/admin/users/${u.id}/limit`, { method: "POST", body: { krw: Number(e.target.value) } }); toast("한도를 변경했습니다."); } }), "원"),
    el("td", { text: u.active ? "활성" : "비활성" }),
    el("td", {}, u.id === state.me.id ? null : el("button", { class: "btn xs", type: "button", text: u.active ? "비활성화" : "활성화",
      onclick: async () => { await api(`/api/admin/users/${u.id}/active?active=${u.active ? 0 : 1}`, { method: "POST" }); renderAdmin(); } })))));
  $("#events").replaceChildren(...st.events.map((ev) => el("li", { text: `${fmtTime(ev.at)} [${ev.kind}] ${ev.detail || ""}` })));
}
$("#invite-btn").addEventListener("click", async () => {
  const r = await api("/api/admin/invites", { method: "POST", body: { role: "reporter" } });
  $("#invite-url").value = r.url;
  $("#invite-url").select();
  try { await navigator.clipboard.writeText(r.url); toast("초대 링크를 복사했습니다."); } catch { toast("초대 링크를 생성했습니다."); }
});

// ---------- 휴대폰 '더보기' ----------
$("#more-tab").addEventListener("click", (e) => { e.stopPropagation(); $(".sidebar").classList.toggle("open"); });
document.addEventListener("click", (e) => {
  const sb = $(".sidebar");
  if (sb.classList.contains("open") && !sb.contains(e.target)) sb.classList.remove("open");
});

// ---------- 실시간 갱신 (1분마다) ----------
async function refresh() {
  if (!state.me || document.hidden) return;
  try {
    await loadCounts();
    if (state.view !== "list" || state.q || state.loading) return;
    const { items } = await api(listQuery());
    const known = new Set(state.items.map((i) => i.rcept_no));
    const fresh = items.filter((i) => !known.has(i.rcept_no));
    if (!fresh.length) return;
    const selId = state.items[state.selected]?.rcept_no;
    state.items = [...fresh, ...state.items];
    state.selected = selId ? state.items.findIndex((i) => i.rcept_no === selId) : -1;
    renderList(new Set(fresh.map((f) => f.rcept_no)));
    toast(`새 공시 ${fresh.length}건`);
    renderToday().catch(() => {});
  } catch {}
}
setInterval(refresh, 60_000);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) store.set("nb-last-visit", new Date().toISOString());
  else refresh();
});

// ---------- 시작 ----------
async function boot() {
  try { state.me = await api("/api/me"); } catch { return; }
  $("#auth").hidden = true;
  $("#app").hidden = false;
  $$(".admin-only").forEach((n) => (n.hidden = state.me.role !== "admin"));
  $("#me-name").textContent = state.me.display_name;
  $("#me-avatar").textContent = initials(state.me.display_name);
  const lv = store.get("nb-last-visit");
  state.lastVisit = lv ? new Date(lv) : new Date(Date.now() - 12 * 3600 * 1000);
  store.set("nb-last-visit", new Date().toISOString());
  checkPushButton().catch(() => {});
  if (!location.hash || location.hash === "#") location.replace("#s/inbox");
  else route();
}

(function init() {
  const fs = store.get("nb-fs");
  if (fs) document.documentElement.style.setProperty("--fs", `${fs}px`);
  applyTheme(store.get("nb-theme", "auto"));
  applyDensity(store.get("nb-density", "comfy"));
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  if (location.hash.startsWith("#join/")) showAuth(location.hash.slice(6));
  else boot();
})();
