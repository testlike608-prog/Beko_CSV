/* ─────────────────────────────────────────────
   STATION LOGS — مربّع اللوج بتاع كل محطة
   بيستخدمه الـ Home (تحت كل كارت) وصفحة الـ Pop-out (station_log.html).

   بيسأل /station_logs/<n>?after=<آخر seq> كل ثانية، فمفيش سطر بيضيع
   ولا بيتكرر. الـ Pause بيوقف الـ auto-scroll بس — السطور بتفضل تتجمع.

   تفضيلات كل محطة (حجم الخط، الطول، الفلتر، مقفول/مفتوح) بتتحفظ في
   المتصفح ومشتركة بين الـ Home والـ Pop-out.
───────────────────────────────────────────── */
const STATION_LOG_MAX_LINES = 1000;
const STATION_LOG_FONT = { min: 10, max: 28, def: 13 };

function logLevelClass(level) {
  const lv = String(level || '').toUpperCase();
  if (lv === 'ERROR' || lv === 'FATAL') return 'lv-error';
  if (lv === 'WARNING' || lv === 'WARN') return 'lv-warn';
  return 'lv-info';
}

function initStationLog(root, opts = {}) {
  const station  = root.dataset.station;
  const q        = sel => root.querySelector(sel);
  const body     = q('.station-log-body');
  const filter   = q('.station-log-filter');
  const pauseBtn = q('.station-log-pause');
  const clearBtn = q('.station-log-clear');
  const toggle   = q('.station-log-toggle');
  const badge    = q('.station-log-badge');
  const fontDown = q('.station-log-font-down');
  const fontUp   = q('.station-log-font-up');
  const popBtn   = q('.station-log-popout');
  const prefKey  = 'station_log_' + station;
  // في الـ Pop-out الطول بياخد الشاشة كلها — منحفظوش ومنطبقوش
  const fullPage = !!opts.fullPage;

  let after = 0;
  let paused = false;
  let unseenErrors = 0;

  let pref = {};
  try { pref = JSON.parse(localStorage.getItem(prefKey) || '{}') || {}; } catch (e) {}
  const savePref = () => {
    try { localStorage.setItem(prefKey, JSON.stringify(pref)); } catch (e) {}
  };

  // ---- مقفول / مفتوح ----
  if (!fullPage && pref.collapsed) root.classList.add('collapsed');

  // ---- الفلتر ----
  if (pref.filter) filter.value = pref.filter;
  const applyFilter = () => {
    body.classList.remove('f-warn', 'f-error');
    if (filter.value !== 'all') body.classList.add('f-' + filter.value);
  };
  applyFilter();

  // ---- حجم الخط ----
  let fontSize = parseInt(pref.fontSize, 10) || STATION_LOG_FONT.def;
  const applyFont = () => { body.style.fontSize = fontSize + 'px'; };
  applyFont();
  const changeFont = (delta) => {
    fontSize = Math.min(STATION_LOG_FONT.max, Math.max(STATION_LOG_FONT.min, fontSize + delta));
    applyFont();
    pref.fontSize = fontSize;
    savePref();
  };
  if (fontDown) fontDown.addEventListener('click', () => changeFont(-1));
  if (fontUp)   fontUp.addEventListener('click',   () => changeFont(+1));

  // ---- الطول: بيتسحب من الركن اللي تحت ويتحفظ ----
  if (!fullPage) {
    if (pref.height) body.style.height = pref.height + 'px';
    if (typeof ResizeObserver !== 'undefined') {
      let t = null;
      new ResizeObserver(() => {
        if (root.classList.contains('collapsed')) return;
        clearTimeout(t);
        t = setTimeout(() => {
          const h = Math.round(body.getBoundingClientRect().height);
          if (h > 40 && h !== pref.height) { pref.height = h; savePref(); }
        }, 300);
      }).observe(body);
    }
  }

  // ---- Pop-out: window لوحدها تتحرك وتكبر زي ما انتي عايزة ----
  if (popBtn) {
    popBtn.addEventListener('click', () => {
      const w = window.open(
        '/static/station_log.html?station=' + encodeURIComponent(station),
        'station_log_' + station,
        'popup=yes,width=900,height=600,resizable=yes,scrollbars=yes'
      );
      if (w) w.focus();
    });
  }

  // ---- العرض ----
  const showEmpty = () => {
    body.innerHTML = '<div class="station-log-empty">No logs yet…</div>';
  };
  showEmpty();

  const updateBadge = () => {
    if (!badge) return;
    badge.textContent = unseenErrors;
    badge.classList.toggle('hidden', unseenErrors === 0);
  };

  const append = (lines) => {
    if (!lines.length) return;
    const empty = body.querySelector('.station-log-empty');
    if (empty) empty.remove();

    const frag = document.createDocumentFragment();
    for (const e of lines) {
      const cls = logLevelClass(e.level);
      const row = document.createElement('div');
      row.className = 'station-log-line ' + cls;

      const t = document.createElement('span');
      t.className = 't';
      t.textContent = new Date(e.ts * 1000).toLocaleTimeString([], { hour12: false }) + ' ';
      const src = document.createElement('span');
      src.className = 'src';
      src.textContent = '[' + e.src + '] ';
      row.append(t, src, document.createTextNode('[' + e.level + '] ' + e.msg));
      frag.appendChild(row);

      if (cls === 'lv-error' && root.classList.contains('collapsed')) unseenErrors++;
    }
    body.appendChild(frag);
    while (body.childElementCount > STATION_LOG_MAX_LINES) body.firstElementChild.remove();
    if (!paused) body.scrollTop = body.scrollHeight;
    updateBadge();
  };

  const poll = async () => {
    try {
      const res = await fetch('/station_logs/' + station + '?after=' + after);
      if (!res.ok) return;
      const data = await res.json();
      // السيرفر اتعمل له restart — الترقيم رجع من الأول
      if (data.last < after) { after = 0; showEmpty(); return; }
      append(data.lines || []);
      after = data.last;
    } catch (e) { /* السيرفر مش متاح دلوقتي — هنحاول تاني */ }
  };

  if (toggle) {
    toggle.addEventListener('click', () => {
      root.classList.toggle('collapsed');
      if (!root.classList.contains('collapsed')) {
        unseenErrors = 0;
        updateBadge();
        if (!paused) body.scrollTop = body.scrollHeight;
      }
      pref.collapsed = root.classList.contains('collapsed');
      savePref();
    });
  }
  filter.addEventListener('change', () => { applyFilter(); pref.filter = filter.value; savePref(); });
  pauseBtn.addEventListener('click', () => {
    paused = !paused;
    pauseBtn.textContent = paused ? 'Resume' : 'Pause';
    pauseBtn.classList.toggle('active', paused);
    if (!paused) body.scrollTop = body.scrollHeight;
  });
  clearBtn.addEventListener('click', showEmpty);

  poll();
  setInterval(poll, 1000);
}
