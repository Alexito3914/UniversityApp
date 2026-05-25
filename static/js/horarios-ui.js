/* UcjcHorarios · UI del prototipo (Django) */

(function applyStoredTweaks() {
  if (window.UhTheme) {
    window.UhTheme.init();
  }
  var root = document.documentElement;
  var body = document.body;
  if (!root || !body) return;
  if (body.classList.contains('login-page')) return;
  var palette = localStorage.getItem('uh_palette') || 'granate';
  var font = localStorage.getItem('uh_font') || 'inter';
  var density = localStorage.getItem('uh_density') || 'regular';
  body.dataset.palette = palette;
  body.dataset.font = font;
  body.dataset.density = density;
  if (density === 'compact') {
    body.classList.add('compact-sched');
    body.classList.remove('ultra-compact-sched');
  } else if (density === 'comfy') {
    body.classList.remove('compact-sched', 'ultra-compact-sched');
  } else {
    body.classList.remove('compact-sched', 'ultra-compact-sched');
  }
})();

var schedToastTimer = null;
function showSchedToast(kind, text) {
  var toast = document.getElementById('schedToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'schedToast';
    toast.className = 'sched-toast';
    document.body.appendChild(toast);
  }
  toast.className = 'sched-toast ' + (kind === 'ok' ? 'ok' : 'err') + ' show';
  toast.textContent = text;
  if (schedToastTimer) window.clearTimeout(schedToastTimer);
  schedToastTimer = window.setTimeout(function () {
    toast.classList.remove('show');
  }, 2200);
}
window.showSchedToast = showSchedToast;

function notifData() {
  try {
    var el = document.getElementById('notif-data');
    return JSON.parse((el && el.textContent) || '[]');
  } catch (e) {
    return [];
  }
}

function renderBell() {
  var ul = document.getElementById('bellList');
  if (!ul) return;
  var data = notifData();
  ul.innerHTML = data.slice(0, 5).map(function (n) {
    var cls = n.read ? '' : ' class="unread"';
    return '<li' + cls + '><div style="flex:1"><div>' + escapeHtml(n.msg) + '</div><div class="muted fs-xs">' + escapeHtml(n.when) + '</div></div></li>';
  }).join('') || '<li><div class="muted" style="padding:8px 0;">Sin notificaciones</div></li>';
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function closeBell() {
  var m = document.getElementById('bellMenu');
  if (m) m.classList.remove('open');
}

function markAllRead() {
  var meta = document.querySelector('meta[name="csrf-token"]');
  var token = meta ? meta.getAttribute('content') : '';
  fetch('/notificaciones/marcar-todas/', {
    method: 'POST',
    headers: { 'X-CSRFToken': token, Accept: 'application/json' },
    credentials: 'same-origin',
  }).then(function () { location.reload(); }).catch(function () { location.reload(); });
}
window.markAllRead = markAllRead;
window.closeBell = closeBell;

function syncThemeTweakButtons(theme) {
  document.querySelectorAll('[data-tweak="theme"] button').forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.value === theme);
  });
}

function updateThemeToggleUI(theme) {
  document.querySelectorAll('.theme-pick[data-set-theme]').forEach(function (btn) {
    var active = btn.dataset.setTheme === theme;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function setTheme(theme) {
  if (window.UhTheme) {
    window.UhTheme.apply(theme);
    return;
  }
  var root = document.documentElement;
  if (!root) return;
  theme = theme === 'dark' ? 'dark' : 'light';
  if (theme === 'dark') {
    root.setAttribute('data-theme', 'dark');
    root.classList.add('theme-dark');
  } else {
    root.removeAttribute('data-theme');
    root.classList.remove('theme-dark');
  }
  localStorage.setItem('uh_theme', theme);
  updateThemeToggleUI(theme);
  syncThemeTweakButtons(theme);
}
window.setTheme = setTheme;

function initThemeToggle() {
  if (window.UhTheme) {
    window.UhTheme.init();
    return;
  }
  var theme = localStorage.getItem('uh_theme') || 'light';
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.documentElement.classList.add('theme-dark');
  }
  updateThemeToggleUI(theme);
  syncThemeTweakButtons(theme);
}

document.addEventListener('click', function (e) {
  var pick = e.target.closest('.theme-pick[data-set-theme]');
  if (!pick || pick.getAttribute('onclick')) return;
  e.preventDefault();
  setTheme(pick.getAttribute('data-set-theme'));
});

function initTweaks() {
  var panel = document.getElementById('tweaksPanel');
  var toggle = document.getElementById('tweaksToggle');
  if (!panel || !toggle) return;

  toggle.addEventListener('click', function () {
    panel.classList.toggle('open');
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('#tweaksPanel') && !e.target.closest('#tweaksToggle')) {
      panel.classList.remove('open');
    }
  });

  var body = document.body;
  var palette = body.dataset.palette || 'granate';
  var font = body.dataset.font || 'inter';
  var density = body.dataset.density || 'regular';
  var theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';

  document.querySelectorAll('[data-tweak="theme"] button').forEach(function (btn) {
    if (btn.dataset.value === theme) btn.classList.add('active');
    btn.addEventListener('click', function () {
      setTheme(btn.getAttribute('data-value'));
    });
  });

  document.querySelectorAll('.tweak-swatch[data-value]').forEach(function (btn) {
    if (btn.dataset.value === palette) btn.classList.add('active');
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tweak-swatch').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      body.dataset.palette = btn.dataset.value;
      localStorage.setItem('uh_palette', btn.dataset.value);
    });
  });

  document.querySelectorAll('[data-tweak="font"] button').forEach(function (btn) {
    if (btn.dataset.value === font) btn.classList.add('active');
    btn.addEventListener('click', function () {
      document.querySelectorAll('[data-tweak="font"] button').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      body.dataset.font = btn.dataset.value;
      localStorage.setItem('uh_font', btn.dataset.value);
    });
  });

  document.querySelectorAll('[data-tweak="density"] button').forEach(function (btn) {
    if (btn.dataset.value === density) btn.classList.add('active');
    btn.addEventListener('click', function () {
      document.querySelectorAll('[data-tweak="density"] button').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      body.dataset.density = btn.dataset.value;
      localStorage.setItem('uh_density', btn.dataset.value);
      body.classList.toggle('compact-sched', btn.dataset.value === 'compact');
      body.classList.remove('ultra-compact-sched');
    });
  });
}

function initGlobalSearch() {
  var input = document.getElementById('globalSearch');
  if (!input) return;
  input.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var q = input.value.trim();
    if (!q) return;
    var table = document.querySelector('.schedule-list-table tbody, table.tbl tbody');
    if (table) {
      var rows = table.querySelectorAll('tr');
      var any = false;
      rows.forEach(function (tr) {
        var text = tr.textContent.toLowerCase();
        var show = text.indexOf(q.toLowerCase()) >= 0;
        tr.style.display = show ? '' : 'none';
        if (show) any = true;
      });
      if (!any) showSchedToast('warn', 'Sin resultados en esta página');
    } else {
      window.location.href = '/horarios/?q=' + encodeURIComponent(q);
    }
  });
}

function initMetricCounters() {
  document.querySelectorAll('.metric .num[data-target]').forEach(function (el) {
    var target = +el.dataset.target;
    var start = performance.now();
    var dur = 800;
    function step(now) {
      var t = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}

.schedule-list-table { overflow: visible; }

function initKebabMenus(){
  document.querySelectorAll('.kebab').forEach(function(kebab){
    kebab.addEventListener('toggle', function(){
      if (!kebab.open) return;
      document.querySelectorAll('.kebab[open]').forEach(function(other){
        if (other !== kebab) other.open = false;
      });
    });
  });
  document.addEventListener('click', function(e){
    if (e.target.closest('.kebab')) return;
    document.querySelectorAll('.kebab[open]').forEach(function(k){ k.open = false; });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  var bell = document.getElementById('bellBtn');
  if (bell) {
    bell.addEventListener('click', function (e) {
      e.stopPropagation();
      document.getElementById('bellMenu').classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('#bellMenu') && !e.target.closest('#bellBtn')) closeBell();
    });
    renderBell();
  }
  initThemeToggle();
  initTweaks();
  initGlobalSearch();
  initMetricCounters();
  initKebabMenus();
});

initThemeToggle();
