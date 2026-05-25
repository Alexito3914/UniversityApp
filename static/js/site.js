/* =========================================================
   UCJC Horarios — site.js (shared interactive behaviour)
   ========================================================= */

/* ---------- Notifications bell ---------- */
function _notifData(){
  try { return JSON.parse(document.getElementById("notif-data").textContent || "[]"); }
  catch(e){ return []; }
}
function notifIcon(t){
  const m = {ok:{ic:"✓",cls:"ok"},warn:{ic:"!",cls:"warn"},err:{ic:"✕",cls:"err"},info:{ic:"i",cls:"info"}}[t] || {ic:"i",cls:"info"};
  return `<div class="ic-circle ${m.cls}" style="width:36px;height:36px;font-size:14px;font-weight:700;">${m.ic}</div>`;
}
function renderBell(){
  const ul = document.getElementById("bellList");
  if (!ul) return;
  const data = _notifData();
  ul.innerHTML = data.slice(0,3).map(n => `
    <li class="${n.read?'':'unread'}">
      ${notifIcon(n.type)}
      <div><div class="msg">${n.msg}</div><div class="when">${n.when}</div></div>
      <span class="pill ${n.read?'read':'unread'}" style="font-size:10px;padding:2px 7px;">${n.read?'Leída':'Nueva'}</span>
    </li>
  `).join("") || `<li><div class="body" style="padding:8px 0;color:var(--ink-soft);">Sin notificaciones</div></li>`;
}
function closeBell(){ const m = document.getElementById("bellMenu"); if (m) m.classList.remove("open"); }
function markAllRead(){
  // best-effort POST to mark all as read
  const csrf = document.cookie.split("; ").find(r => r.startsWith("csrftoken="));
  fetch("/notificaciones/marcar-todas/", {
    method: "POST",
    headers: { "X-CSRFToken": csrf ? csrf.split("=")[1] : "", "Accept": "application/json" }
  }).then(() => location.reload()).catch(() => location.reload());
}
document.addEventListener("DOMContentLoaded", () => {
  const bell = document.getElementById("bellBtn");
  if (bell){
    bell.addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById("bellMenu").classList.toggle("open");
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#bellMenu") && !e.target.closest("#bellBtn")) closeBell();
    });
    renderBell();
    // hide badge if 0
    const c = document.getElementById("bellCount");
    if (c && c.textContent.trim() === "0") c.style.display = "none";
  }

  /* counters animation on dashboard */
  document.querySelectorAll(".metric .num[data-target]").forEach(el => {
    const target = +el.dataset.target;
    const dur = 800;
    const start = performance.now();
    el.textContent = "0";
    function step(now){
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased);
      if (t < 1) requestAnimationFrame(step); else el.classList.add("counted");
    }
    requestAnimationFrame(step);
  });
});

/* ---------- Helpers exposed for inline handlers ---------- */
window.markAllRead = markAllRead;
window.closeBell   = closeBell;
