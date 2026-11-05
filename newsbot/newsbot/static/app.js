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
  filter: { level: "", watched: 0, q: "" },
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
  $("#ask").hidden = section !== "feed";
  if (section === "feed") {
    $("#feed-title").textContent = view === "mine" ? "내가 맡은 건" : "오늘의 피드";
    $("#briefing").hidden = view === "mine";
    loadFeed(true);
  }
  if (view === "settings") renderSettings();
  if (view === "admin") renderAdmin();
}

function route() {
  const h = location.hash.slice(1);
  if (h.startsWith("join/")) return showAuth(h.slice(5));
  if (!state.me) return;
  if (h.startsWith("d/")) {
    if (state.view !== "feed") setView("feed");
    return openDetail(h.slice(2));
  }
  setView(["feed", "mine", "settings", "admin"].includes(h) ? h : "feed");
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
  if (chip.dataset.watched !== undefined) {
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
  const claimBtn = d.claimed_by && !mine
    ? el("button", { class: "btn", type: "button", disabled: true, text: `${d.claimed_name} 기자가 맡음` })
    : el("button", { class: mine ? "btn" : "btn primary", type: "button", onclick: toggleClaim, text: mine ? "맡기 취소" : "내가 쓸게요 (C)" });
  $("#detail .detail-inner").replaceChildren(
    el("div", { class: "row", style: "justify-content:space-between" }, badge(d),
      el("button", { class: "btn ghost small", type: "button", onclick: closeDetail, "aria-label": "닫기", text: "닫기 (Esc)" })),
    el("div", {}, el("div", { class: "muted small", text: d.watched ? "★ 감시 기업" : "보건의료 업종" }), el("h2", { text: d.corp_name })),
    el("p", { style: "margin:0;font-weight:600", text: d.report_nm }),
    el("a", { class: "source", href: d.url, target: "_blank", rel: "noopener noreferrer" }, "DART 원문 열기", el("span", { "aria-hidden": "true", text: "↗" })),
    el("dl", { class: "kv" },
      el("dt", { text: "접수일" }), el("dd", { text: fmtDate(d.rcept_dt) }),
      el("dt", { text: "접수번호" }), el("dd", { text: d.rcept_no }),
      el("dt", { text: "제출인" }), el("dd", { text: d.flr_nm || "-" }),
      el("dt", { text: "비고" }), el("dd", { text: d.rm || "-" }),
      el("dt", { text: "분류 근거" }), el("dd", { text: d.keyword ? `제목에 '${d.keyword}' 포함` : "키워드 없음 (일반)" }),
      el("dt", { text: "처음 확인" }), el("dd", { text: fmtSeen(d.first_seen_at) + " · DART 공개는 제출 후 약 15분 뒤" })),
    el("div", { class: "row" }, claimBtn,
      el("button", { class: "btn", type: "button", disabled: true, title: "AI API 키 연결 후 5~6주차에 켜집니다", text: "기사 초안 (준비 중)" })),
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
  if (typing || state.view === "settings" || state.view === "admin") return;
  if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
  else if (e.key === "j") select(Math.min(state.selected + 1, state.items.length - 1), false);
  else if (e.key === "k") select(Math.max(state.selected - 1, 0), false);
  else if (e.key === "Enter" && state.selected >= 0) select(state.selected, true);
  else if (e.key === "c" && (state.detail || state.selected >= 0)) toggleClaim();
});

// ---------- 질문창 ----------
$("#ask").addEventListener("submit", (e) => {
  e.preventDefault();
  toast("질문 기능은 AI API 키를 연결한 뒤 켜집니다 (3~4주차).");
});

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
}

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
  const [st, us] = await Promise.all([api("/api/admin/status"), api("/api/admin/users")]);
  $("#admin-status").replaceChildren(
    el("dt", { text: "수집 상태" }), el("dd", { text: st.dart_status }),
    el("dt", { text: "마지막 수집" }), el("dd", { text: st.last_poll_at ? fmtSeen(st.last_poll_at) : "-" }),
    el("dt", { text: "오늘 DART 호출" }), el("dd", { text: `${st.dart_calls_today}건` }),
    el("dt", { text: "알림 모드" }), el("dd", { text: st.alert_mode === "notify" ? "알림 보냄" : "기록만 (.env 의 ALERT_MODE=notify 로 변경)" }));
  $("#users").replaceChildren(...us.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.username }), el("td", { text: u.role === "admin" ? "관리자" : "기자" }),
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
