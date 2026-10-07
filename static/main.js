/* =============================================================
   main.js — Refrigerator Vision System
   Shared JavaScript for all pages
   ============================================================= */

/* ─────────────────────────────────────────────
   1. DEVTOOLS PROTECTION (runs on every page)
───────────────────────────────────────────── */
(function () {
  function redirectBlocked() {
    window.location.href = '/blocked';
  }

  function initDevToolsProtection() {
    document.addEventListener('contextmenu', e => e.preventDefault());

    document.addEventListener('keydown', e => {
      if (
        e.key === 'F12' ||
        (e.ctrlKey && e.shiftKey && (e.key.toUpperCase() === 'I' || e.key.toUpperCase() === 'J')) ||
        (e.ctrlKey && e.key.toUpperCase() === 'U')
      ) {
        e.preventDefault();
        e.stopPropagation();
        redirectBlocked();
        return false;
      }
    });

    setInterval(() => {
      const widthDiff  = window.outerWidth  - window.innerWidth;
      const heightDiff = window.outerHeight - window.innerHeight;
      if (widthDiff > 160 || heightDiff > 160) redirectBlocked();
    }, 500);

    const check = () => {
      const start = performance.now();
      debugger;
      if (performance.now() - start > 50) redirectBlocked();
    };
    setInterval(check, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDevToolsProtection);
  } else {
    initDevToolsProtection();
  }
})();


/* ─────────────────────────────────────────────
   2. SHARED UTILITIES
───────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

function showToast(message, cls) {
  const t = $('toast');
  if (!t) return;
  t.className = 'toast ' + (cls || '');
  t.textContent = message;
  t.style.display = 'block';
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { t.style.display = 'none'; }, 2200);
}

function escapeHtml(str) {
  return String(str || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}


/* ─────────────────────────────────────────────
   3. STATION STATUS FLAGS (index.html)
───────────────────────────────────────────── */
function setFlag(flagEl, dotEl, textEl, state, text) {
  flagEl.classList.remove('flag-pass', 'flag-fail', 'flag-idle', 'flag-arrived', 'flag-waiting');
  dotEl.classList.remove('dot-pass', 'dot-fail', 'dot-idle', 'dot-arrived', 'dot-waiting', 'pulse-active');
  flagEl.classList.add('flag-' + state);
  dotEl.classList.add('dot-' + state);
  if (state === 'pass') dotEl.classList.add('pulse-active');
  textEl.textContent = text;
}

function setInfo(el, value) {
  if (el === null) return;
  const s = String(value ?? '').trim();
  if (s === '' || s === 'None' || s === 'null' || s === 'undefined') {
    el.textContent = '—';
    el.classList.add('empty');
  } else {
    el.textContent = s;
    el.classList.remove('empty');
  }
}

function normalizePassFail(result) {
  if (result === true)  return 'PASS';
  if (result === false) return 'FAIL';
  if (result === null || result === undefined) return '';
  return String(result).trim().toUpperCase();
}

/* ─────────────────────────────────────────────
   3b. REALTIME (Socket.IO)
   السيرفر بيبعت التغييرات لوحده بدل ما نسأل كل ثانية.
   لو socket.io مش متحمّل (المكتبة ناقصة)، بنرجع للـ polling القديم
   أوتوماتيكيًا — فمفيش حاجة بتتكسر.
───────────────────────────────────────────── */
const RT = {
  socket: null,
  connected: false,
  handlers: {},

  // مهم: io() بيرجع أوبچكت *فورًا* حتى لو الاتصال فشل تمامًا
  // (مكتبة ناقصة على السيرفر، بورت مقفول... إلخ).
  // فالتحقق من `RT.socket` لوحده بيخدع الصفحة إنها تفتكر إن الـ push شغال
  // وتوقف الـ polling، وتفضل مستنية أحداث مش هتيجي أبدًا.
  // isLive() بتتحقق من الاتصال الحقيقي.
  isLive() {
    return !!(this.socket && this.socket.connected);
  },

  on(event, fn) {
    (this.handlers[event] = this.handlers[event] || []).push(fn);
    if (this.socket) this.socket.on(event, fn);
  },
  init() {
    if (typeof io === 'undefined') {
      console.warn('socket.io not available — falling back to HTTP polling');
      return false;
    }
    this.socket = io({ transports: ['websocket', 'polling'] });

    this.socket.on('connect',    () => { this.connected = true; });
    this.socket.on('disconnect', () => { this.connected = false; });

    for (const [event, fns] of Object.entries(this.handlers)) {
      fns.forEach(fn => this.socket.on(event, fn));
    }
    return true;
  }
};

// بنشغّله فورًا (مش في DOMContentLoaded) لأن السكربتات اللي جوه القوالب
// بتشتغل قبل الحدث ده، ولازم تلاقي RT.socket جاهز عشان تقرر
// هتستخدم push ولا polling.
RT.init();

function renderFailedTests(n, info) {
  // info = { dummy, result: 'PASS'/'FAIL', tests: [...] } — آخر نتيجة للمحطة
  const box = $('s' + n + '-failed-tests');
  if (!box) return;
  const dummyEl = $('s' + n + '-failed-dummy');
  const key = JSON.stringify(info ?? null);
  if (box.dataset.key === key) return;   // مفيش تغيير — منرسمش تاني
  box.dataset.key = key;
  box.innerHTML = '';
  if (dummyEl) dummyEl.textContent = info && info.dummy ? 'Dummy: ' + info.dummy : '';

  const chip = (text, cls) => {
    const el = document.createElement('span');
    el.className = 'text-xs font-semibold px-2 py-0.5 rounded-md border ' + cls;
    el.textContent = text;
    box.appendChild(el);
  };

  const tests = (info && Array.isArray(info.tests)) ? info.tests : [];
  if (tests.length) {
    tests.forEach(t => chip(t, 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800'));
  } else if (info && normalizePassFail(info.result) === 'PASS') {
    chip('All tests passed', 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800');
  } else {
    const el = document.createElement('span');
    el.className = 'info-value empty';
    el.textContent = '—';
    box.appendChild(el);
  }
}

// زرار الـ CSV في Saved Programs — السيرفر بيفتح الملف علطول من مجلد
// Programs اللي جنب الـ exe (نفس الجهاز اللي شغال عليه البرنامج).
function showProgramData(name) {
  fetch('/open_program', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  })
    .then(r => r.json())
    .then(d => { if (!d.ok) alert('Could not open ' + name + ': ' + (d.msg || 'unknown error')); })
    .catch(e => alert('Could not open ' + name + ': ' + e.message));
}

function applyStation1(data) {
      const arrivedFlag = $('s1-arrived-flag');
      if (!arrivedFlag) return;
      const arrivedDot  = arrivedFlag.querySelector('.flag-dot');
      const arrivedText = $('s1-arrived-text');
      if (data.arrived === true) {
        setFlag(arrivedFlag, arrivedDot, arrivedText, 'arrived', 'Fridge Arrived');
      } else {
        setFlag(arrivedFlag, arrivedDot, arrivedText, 'waiting', 'Waiting...');
      }

      const resultFlag = $('s1-result-flag');
      const resultDot  = resultFlag.querySelector('.flag-dot');
      const resultText = $('s1-result-text');
      const r1 = normalizePassFail(data.result);
      if (r1 === 'PASS')      setFlag(resultFlag, resultDot, resultText, 'pass', 'PASS');
      else if (r1 === 'FAIL') setFlag(resultFlag, resultDot, resultText, 'fail', 'FAIL');
      else                    setFlag(resultFlag, resultDot, resultText, 'idle', 'No Result Yet');

      setInfo($('s1-dummy'), data.dummy_number);
      setInfo($('s1-sku'),   data.sku_number);
      renderFailedTests(1, data.failed_tests);
}

function applyStation2(data) {
      const arrivedFlag = $('s2-arrived-flag');
      if (!arrivedFlag) return;
      const arrivedDot  = arrivedFlag.querySelector('.flag-dot');
      const arrivedText = $('s2-arrived-text');
      if (data.arrived === true) {
        setFlag(arrivedFlag, arrivedDot, arrivedText, 'arrived', 'Fridge Arrived');
      } else {
        setFlag(arrivedFlag, arrivedDot, arrivedText, 'waiting', 'Waiting...');
      }

      const resultFlag = $('s2-result-flag');
      const resultDot  = resultFlag.querySelector('.flag-dot');
      const resultText = $('s2-result-text');
      const r2 = normalizePassFail(data.result);
      if (r2 === 'PASS')      setFlag(resultFlag, resultDot, resultText, 'pass', 'PASS');
      else if (r2 === 'FAIL') setFlag(resultFlag, resultDot, resultText, 'fail', 'FAIL');
      else                    setFlag(resultFlag, resultDot, resultText, 'idle', 'No Result Yet');

      setInfo($('s2-dummy'), data.dummy_number);
      setInfo($('s2-sku'),   data.sku_number);
      renderFailedTests(2, data.failed_tests);
}

/* ─────────────────────────────────────────────
   ALERT CENTER (bell + red badge + dropdown)
   الـ alerts مابقتش pop-up، بتتجمع تحت الجرس
───────────────────────────────────────────── */
const ALERTS = new Map();   // id -> { title, message, file, time, action, actionLabel }

function fmtAlertTime(d) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function renderAlerts() {
  const list  = $('alertList');
  const badge = $('alertBadge');
  const empty = $('alertEmpty');
  const count = ALERTS.size;

  if (badge) {
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.classList.toggle('hidden', count === 0);
  }
  const countText = $('alertCountText');
  if (countText) countText.textContent = count + (count === 1 ? ' active' : ' active');
  if (empty) empty.classList.toggle('hidden', count !== 0);
  if (!list) return;

  list.innerHTML = '';
  ALERTS.forEach((a, id) => {
    const row = document.createElement('div');
    row.className = 'px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-800/60 transition';

    const head = document.createElement('div');
    head.className = 'flex items-start gap-2';
    head.innerHTML =
      '<span class="mt-1 w-2 h-2 rounded-full bg-red-600 shrink-0"></span>' +
      '<div class="flex-1 min-w-0">' +
        '<div class="flex items-center justify-between gap-2">' +
          '<span class="font-semibold text-sm text-red-600">' + a.title + '</span>' +
          '<span class="text-[11px] text-gray-400 shrink-0">' + fmtAlertTime(a.time) + '</span>' +
        '</div>' +
        '<p class="text-sm text-gray-700 dark:text-gray-300 mt-0.5 break-words">' + a.message + '</p>' +
        (a.file
          ? '<p class="text-xs mt-1 font-mono bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded px-2 py-1 break-all">' + a.file + '</p>'
          : '') +
      '</div>';
    row.appendChild(head);

    if (typeof a.action === 'function') {
      const btnWrap = document.createElement('div');
      btnWrap.className = 'mt-2 pl-4';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'px-3 py-1.5 text-xs font-bold rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition';
      btn.textContent = a.actionLabel || 'OK / Confirm';
      btn.onclick = () => a.action(id);
      btnWrap.appendChild(btn);
      row.appendChild(btnWrap);
    }

    list.appendChild(row);
  });
}

function setAlert(id, data) {
  const prev = ALERTS.get(id);
  ALERTS.set(id, Object.assign({ time: prev ? prev.time : new Date() }, data));
  renderAlerts();
}

function clearAlert(id) {
  if (ALERTS.delete(id)) renderAlerts();
}

function initAlertBell() {
  const btn  = $('alertBellBtn');
  const menu = $('alertMenu');
  if (!btn || !menu) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('hidden');
  });
  menu.addEventListener('click', e => e.stopPropagation());
  document.addEventListener('click', () => menu.classList.add('hidden'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') menu.classList.add('hidden'); });

  renderAlerts();
}

function applyFlags(data, modalId, csvAlertId) {
  const modal = $(modalId);
  if (modal) modal.classList.toggle('hidden', data.manual_scanner !== true);

  // NO CSV → alert في الجرس بدل الـ pop-up
  const station = (csvAlertId === 'noCsv2') ? 2 : 1;
  if (data.no_csv_error === true) {
    setAlert(csvAlertId, {
      title:   'No CSV File',
      message: 'ERROR: THERE IS NO CSV IN ' + (station === 2 ? 'INNER' : 'OUTER') + ' STATION',
      file:    data.no_csv_file ? ('CSV not found: ' + data.no_csv_file) : 'CSV not found: (unknown file name)',
      action:  () => (station === 2 ? submitCsv2() : submitCsv1()),
      actionLabel: 'OK / Confirm'
    });
  } else {
    clearAlert(csvAlertId);
  }

  // Manual mode = OFF -> تريجر من غير سكان: alert بس
  const skipId = 'scanSkipped' + station;
  if (data.scan_skipped === true) {
    const n = data.scan_skipped_count || 1;
    setAlert(skipId, {
      title:   'Scan Failed (Manual mode OFF)',
      message: 'Trigger received in ' + (station === 2 ? 'INNER' : 'OUTER') +
               ' station but scanning failed — the fridge was skipped and the sequence continued.',
      file:    'Skipped fridges: ' + n,
      action:  () => ackScanSkipped(station),
      actionLabel: 'Dismiss'
    });
  } else {
    clearAlert(skipId);
  }
}

async function ackScanSkipped(station) {
  const url = station === 2 ? '/scan_skipped2/ack' : '/scan_skipped/ack';
  try {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (res.ok) clearAlert('scanSkipped' + station);
  } catch (e) { console.error('Network error:', e); }
}

// النسخ دي بتستخدم للـ fallback بس (لما Socket.IO مش متاح)
function pollStation1Status() {
  fetch('/station1_status').then(r => r.json()).then(applyStation1).catch(() => {});
}

function pollStation2Status() {
  fetch('/station2_status').then(r => r.json()).then(applyStation2).catch(() => {});
}

function refreshStatus() {
  if ($('s1-arrived-flag')) pollStation1Status();
  if ($('s2-arrived-flag')) pollStation2Status();
}



/* ─────────────────────────────────────────────
   4. TIME SETTINGS MODAL (index + create_program)
───────────────────────────────────────────── */
const DEFAULT_TIME_SETTINGS = {
  deviceConnectTimeout: 5.0,
  deviceRecvTimeout: 1.0,
  clientSocketTimeout: 1.0,
  reconnectBaseDelay: 0.5,
  maxBackoff: 30,
  reconnectCheckInterval: 1,
  defaultCharDelay: 100,
  s1CharDelay: 100,
  s2CharDelay: 100,
  frameDelay: 1,
  followupDelay: 30,
  statusRefresh: 1500,
  logPolling: 800,
  server4Refresh: 2000,
  sendTimeout: 25,
  autoSendGap: 120,
  dbTimeout: 10,
  ImageTimeout: 10,
  PlcSignal: 0.1,
  duplicateScanWindow: 120
};

let currentTimeSettings = {};

async function loadTimeSettings() {
  try {
    const response = await fetch('/time_settings');
    const data = await response.json();
    currentTimeSettings = data.ok ? data.settings : { ...DEFAULT_TIME_SETTINGS };
  } catch {
    currentTimeSettings = { ...DEFAULT_TIME_SETTINGS };
  }
  populateTimeForm(currentTimeSettings);
}

function populateTimeForm(settings) {
  for (const [key, value] of Object.entries(settings)) {
    const el = $(key);
    if (el) el.value = value;
  }
  if ($('delayS1')) $('delayS1').value = settings.s1CharDelay;
  if ($('delayS2')) $('delayS2').value = settings.s2CharDelay;
  if ($('delay'))   $('delay').value   = settings.defaultCharDelay;
}

function collectTimeSettings() {
  const settings = {};
  for (const key of Object.keys(DEFAULT_TIME_SETTINGS)) {
    const el = $(key);
    if (el) settings[key] = parseFloat(el.value) || DEFAULT_TIME_SETTINGS[key];
  }
  return settings;
}

async function saveTimeSettings(settings) {
  try {
    const response = await fetch('/time_settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    const data = await response.json();
    if (data.ok) {
      showToast('Time settings saved successfully', 'green');
      currentTimeSettings = { ...settings };
      updateUIWithNewTimes();
      return true;
    } else {
      showToast('Failed to save time settings: ' + data.msg, 'red');
      return false;
    }
  } catch (error) {
    showToast('Error saving time settings: ' + error.message, 'red');
    return false;
  }
}

function updateUIWithNewTimes() {
  if ($('delayS1')) $('delayS1').value = currentTimeSettings.s1CharDelay;
  if ($('delayS2')) $('delayS2').value = currentTimeSettings.s2CharDelay;
  if ($('delay'))   $('delay').value   = currentTimeSettings.defaultCharDelay;

  if (window.statusInterval) clearInterval(window.statusInterval);
  const ms = Math.max(200, parseInt(currentTimeSettings.statusRefresh, 10) || DEFAULT_TIME_SETTINGS.statusRefresh);
  window.statusInterval = setInterval(refreshStatus, ms);

  if (window.logInterval) {
    clearInterval(window.logInterval);
    window.logInterval = setInterval(pullLogs, currentTimeSettings.logPolling);
  }
  if (window.server4Interval) {
    clearInterval(window.server4Interval);
    window.server4Interval = setInterval(refreshServer4, currentTimeSettings.server4Refresh);
  }
}


/* ─────────────────────────────────────────────
   5. ERROR MODAL (index.html)
───────────────────────────────────────────── */
let AUTO_SEND_ENABLED = true;

function showErrorPopup() {
  const modal = $('errorModal');
  if (modal) {
    modal.classList.remove('hidden');
    AUTO_SEND_ENABLED = false;
    if ($('autoSwitch')) $('autoSwitch').checked = false;
  }
}

function hideErrorPopup() {
  const modal = $('errorModal');
  if (modal) modal.classList.add('hidden');
}

async function resetErrorCondition() {
  try {
    const response = await fetch('/reset_error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const result = await response.json();
    if (result.ok) {
      showToast('Error condition reset successfully', 'green');
      hideErrorPopup();
      AUTO_SEND_ENABLED = true;
      if ($('autoSwitch')) $('autoSwitch').checked = true;
    } else {
      showToast('Reset failed: ' + result.msg, 'red');
    }
  } catch (error) {
    showToast('Reset error: ' + error.message, 'red');
  }
}


/* ─────────────────────────────────────────────
   6. I/O MAPPING (index.html)
───────────────────────────────────────────── */
const ioDefaultMapping = {
  LIGHTING_S1: 8, LIGHTING_S2: 1, BUZZER_S1: 2, BUZZER_S2: 3,
  SCANNER_S1: 4, SCANNER_S2: 5, TESTDONE_S1: 6, TESTDONE_S2: 7, FAILURE: 16,
  READ_DI0: 0, READ_DI1: 1, READ_INPUTS_REG: 34
};

const ioOutputs = {
  LIGHTING_S1: 'Lighting S1 (D0)', LIGHTING_S2: 'Lighting S2 (D1)',
  BUZZER_S1: 'Buzzer S1 (D2)',     BUZZER_S2: 'Buzzer S2 (D3)',
  SCANNER_S1: 'Scanner S1 (D4)',   SCANNER_S2: 'Scanner S2 (D5)',
  TESTDONE_S1: 'Test Done S1 (D6)',TESTDONE_S2: 'Test Done S2 (D7)',
  FAILURE: 'Failure (D10)'
};

const ioInputs = {
  READ_DI0: 'Read DI0', READ_DI1: 'Read DI1', READ_INPUTS_REG: 'Read Registers'
};

function loadIoSettings() {
  const saved = localStorage.getItem('io_mapping_v2');
  return saved ? JSON.parse(saved) : ioDefaultMapping;
}

function createIoSelectGroup(funcId, funcName, currentValue) {
  const div = document.createElement('div');
  div.className = 'flex justify-between items-center text-sm';

  const label = document.createElement('label');
  label.className = 'text-gray-700 dark:text-gray-300 font-medium';
  label.innerText = funcName;

  const select = document.createElement('select');
  select.name = funcId;
  select.className = 'border border-gray-300 dark:border-gray-600 rounded p-1.5 ml-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 w-32';

  for (let i = 0; i <= 40; i++) {
    const option = document.createElement('option');
    option.value = i;
    option.text = `Pin/Reg ${i}`;
    if (currentValue === i) option.selected = true;
    select.appendChild(option);
  }

  div.appendChild(label);
  div.appendChild(select);
  return div;
}

function renderIoForm(mapping) {
  const outContainer = $('mapping-outputs-container');
  const inContainer  = $('mapping-inputs-container');
  if (!outContainer || !inContainer) return;
  outContainer.innerHTML = '';
  inContainer.innerHTML  = '';
  for (const [id, name] of Object.entries(ioOutputs)) outContainer.appendChild(createIoSelectGroup(id, name, mapping[id]));
  for (const [id, name] of Object.entries(ioInputs))  inContainer.appendChild(createIoSelectGroup(id, name, mapping[id]));
}

function resetIoMapping() {
  if (confirm('Are you sure you want to revert to default I/O mappings?')) renderIoForm(ioDefaultMapping);
}

function turnOffAllIO() {
  fetch('/off_all', { method: 'POST' })
    .then(res => res.json())
    .then(() => showToast('OFF ALL command sent!', 'green'))
    .catch(() => showToast('Failed to send OFF ALL', 'red'));
}


/* ─────────────────────────────────────────────
   6a-2. DEVICE ADDRESSES — IP / PORT (Developer mode only)

   العناوين دي كانت متكتوبة بإيد في ClientsClass.py. دلوقتي بتيجي من
   /endpoints وبتترسم أوتوماتيك، فأي جهاز جديد يتضاف في
   ioSetting.default_endpoints بيظهر هنا لوحده من غير تعديل JS.
───────────────────────────────────────────── */
let EP_LABELS   = {};
let EP_DEFAULTS = {};

function endpointRow(key, label, entry, fallback) {
  const row = document.createElement('div');
  row.className = 'grid grid-cols-12 gap-2 items-center';
  row.innerHTML = `
    <label class="col-span-4 text-gray-700 dark:text-gray-300 font-medium truncate" title="${escapeHtml(label)}">
      ${escapeHtml(label)}
    </label>
    <input type="text" data-ep="${escapeHtml(key)}" data-field="ip" spellcheck="false"
      value="${escapeHtml(entry.ip || '')}" placeholder="${escapeHtml(fallback.ip || '')}"
      class="col-span-5 min-w-0 border border-gray-300 dark:border-gray-600 rounded p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-amber-500">
    <input type="number" min="1" max="65535" data-ep="${escapeHtml(key)}" data-field="port"
      value="${escapeHtml(String(entry.port == null ? '' : entry.port))}"
      placeholder="${escapeHtml(String(fallback.port == null ? '' : fallback.port))}"
      class="col-span-3 min-w-0 border border-gray-300 dark:border-gray-600 rounded p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-amber-500">
  `;
  return row;
}

function renderEndpointsForm(eps) {
  const box = $('endpointsContainer');
  if (!box) return;
  box.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'grid grid-cols-12 gap-2 text-xs opacity-60 pb-1';
  header.innerHTML =
    '<span class="col-span-4">Device</span>' +
    '<span class="col-span-5">IP / Host</span>' +
    '<span class="col-span-3">Port</span>';
  box.appendChild(header);

  Object.keys(eps || {}).forEach(key => {
    box.appendChild(endpointRow(key, EP_LABELS[key] || key, eps[key] || {}, EP_DEFAULTS[key] || {}));
  });
}

function showEndpointsResult(ok, message) {
  const box = $('endpointsResult');
  if (!box) return;
  box.classList.remove('hidden');
  box.className = ok
    ? 'text-xs rounded p-3 mt-4 bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
    : 'text-xs rounded p-3 mt-4 bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
  box.textContent = message;
}

async function loadEndpoints() {
  if (!$('endpointsForm')) return;
  try {
    const res = await fetch('/endpoints');
    if (!res.ok) return;
    const data = await res.json();
    EP_LABELS   = data.labels   || {};
    EP_DEFAULTS = data.defaults || {};
    renderEndpointsForm(data.endpoints);
  } catch (err) {
    console.error('Failed to load device addresses:', err);
  }
}

function collectEndpoints() {
  const out = {};
  document.querySelectorAll('#endpointsContainer input[data-ep]').forEach(input => {
    const key = input.dataset.ep;
    out[key] = out[key] || {};
    out[key][input.dataset.field] =
      input.dataset.field === 'port' ? parseInt(input.value, 10) : input.value.trim();
  });
  return out;
}

async function saveEndpoints() {
  try {
    const res  = await fetch('/endpoints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectEndpoints())
    });
    const data = await res.json();

    if (!res.ok || data.status !== 'success') {
      /* السيرفر بيرفض أي IP أو port غلط وبيقول السبب — بنوريه زي ما هو
         بدل ما نحفظ عنوان بايظ وتكتشفه وقت START. */
      showEndpointsResult(false, data.message || 'Failed to save device addresses.');
      showToast('Device addresses not saved', 'red');
      return;
    }

    renderEndpointsForm(data.endpoints);
    showEndpointsResult(true, data.message || 'Saved — press Restart to apply.');
    showToast('Device addresses saved', 'green');
  } catch (err) {
    showEndpointsResult(false, 'Request failed: ' + err);
  }
}

async function resetEndpoints() {
  if (!confirm('Revert all device addresses to the factory defaults?')) return;
  try {
    const res  = await fetch('/endpoints/reset', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) { showEndpointsResult(false, data.message || 'Reset failed.'); return; }
    renderEndpointsForm(data.endpoints);
    showEndpointsResult(true, 'Reverted to defaults — press Restart to apply.');
  } catch (err) {
    showEndpointsResult(false, 'Request failed: ' + err);
  }
}


/* ─────────────────────────────────────────────
   6b. VISIONMASTER PATHS (Developer mode only)
   ملحوظة: مش بنعمل parseInt هنا — دي مسارات نصية مش أرقام بنّات.
───────────────────────────────────────────── */
function renderVmCheck(check) {
  const box = $('vmCheckResult');
  if (!box || !check) return;
  box.classList.remove('hidden');
  if (check.ok) {
    box.className = 'text-xs rounded p-3 bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200';
    const size = check.solution_size ? ` (${check.solution_size.toLocaleString()} bytes)` : '';
    box.innerHTML = `<b>OK</b> — VM.Core.dll found, solution file found${size}.`;
  } else {
    box.className = 'text-xs rounded p-3 bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
    box.innerHTML = '<b>Problems:</b><ul class="list-disc ms-5 mt-1">' +
      (check.errors || []).map(e => `<li>${e}</li>`).join('') + '</ul>';
  }
}

async function loadVisionMasterPaths() {
  if (!$('visionMasterForm')) return;
  try {
    const res = await fetch('/vision_master/paths');
    if (!res.ok) return;
    const data = await res.json();

    $('vmAssemblyDir').value  = data.assembly_dir  || '';
    $('vmSolutionPath').value = data.solution_path || '';

    const detected = $('vmDetectedAssembly');
    if (detected) detected.textContent = data.detected_assembly_dir || 'مفيش VisionMaster متلاقي على الجهاز';

    if (!data.assembly_dir && data.detected_assembly_dir) {
      $('vmAssemblyDir').placeholder = data.detected_assembly_dir;
    }
    if (!data.solution_path && data.detected_solution_path) {
      $('vmSolutionPath').placeholder = data.detected_solution_path;
    }

    renderVmCheck(data.check);
  } catch (err) {
    console.error('Failed to load VisionMaster paths:', err);
  }
}

/* ─────────────────────────────────────────────
   6c. FILE PICKER (server-side browse, dev only)
   بيتصفّح ملفات الجهاز اللي شغال عليه التطبيق مش جهاز المتصفح —
   لأن <input type="file"> بيخفي المسار الكامل، و VisionMaster
   محتاج مسار حقيقي على الديسك.
───────────────────────────────────────────── */
const picker = {
  mode: 'file',      // 'file' | 'dir'
  target: null,      // id of the input to fill
  currentPath: '',
  parentPath: '',    // بيجي من السيرفر (os.path.dirname) — أأمن من التقطيع في JS
  selected: ''
};

function pickerRow(icon, label, sub, onClick, isSelected) {
  const row = document.createElement('button');
  row.type = 'button';
  row.className = 'w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-slate-100 dark:hover:bg-slate-700 transition ' +
    (isSelected ? 'bg-purple-100 dark:bg-purple-900/40' : '');
  row.innerHTML =
    `<span class="shrink-0">${icon}</span>` +
    `<span class="flex-1 min-w-0 truncate font-mono text-xs">${label}</span>` +
    (sub ? `<span class="shrink-0 text-[10px] opacity-60">${sub}</span>` : '');
  row.addEventListener('click', onClick);
  return row;
}

async function pickerLoad(path) {
  const list = $('pickerList');
  const errBox = $('pickerError');
  if (!list) return;

  list.innerHTML = '<div class="px-3 py-4 text-xs opacity-60">Loading…</div>';
  errBox.classList.add('hidden');

  try {
    const qs = new URLSearchParams({ path: path || '', only_dirs: picker.mode === 'dir' });
    const url = '/vision_master/browse?' + qs.toString();
    const res = await fetch(url);

    if (!res.ok) {
      list.innerHTML = '';
      if (res.status === 401 || res.status === 403) {
        errBox.textContent = 'Developer access required (HTTP ' + res.status + ') — سجّل دخول بمستخدم dev';
      } else if (res.status === 404) {
        errBox.textContent =
          'HTTP 404 — الراوت /vision_master/browse مش متسجّل. ' +
          'اقفل السيرفر وشغّله تاني (الراوتس بتتسجّل عند الإقلاع بس).';
      } else {
        errBox.textContent = 'HTTP ' + res.status + ' من ' + url;
      }
      errBox.classList.remove('hidden');
      return;
    }

    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      list.innerHTML = '';
      errBox.textContent = 'الرد مش JSON — غالبًا الراوت مش موجود أو رجّع صفحة HTML.';
      errBox.classList.remove('hidden');
      return;
    }

    picker.currentPath = data.path || '';
    picker.parentPath  = data.parent || '';
    $('pickerPath').value = picker.currentPath;

    const btnUp = $('btnPickerUp');
    if (btnUp) btnUp.disabled = !picker.parentPath;

    // في وضع اختيار مجلد، المجلد الحالي نفسه هو الاختيار الافتراضي
    picker.selected = picker.mode === 'dir' ? picker.currentPath : '';

    // البارتيشنات
    const drives = $('pickerDrives');
    drives.innerHTML = '';
    (data.drives || []).forEach(d => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-xs font-mono py-1 px-2 rounded transition';
      b.textContent = d;
      b.addEventListener('click', () => pickerLoad(d));
      drives.appendChild(b);
    });

    if (data.error) {
      errBox.textContent = data.error;
      errBox.classList.remove('hidden');
    }

    list.innerHTML = '';

    (data.dirs || []).forEach(d => {
      const tag = d.has_vm_core ? 'VM.Core.dll' : '';
      list.appendChild(pickerRow('', d.name, tag, () => pickerLoad(d.path), false));
    });

    (data.files || []).forEach(f => {
      const size = f.size ? `${f.size.toLocaleString()} B` : '';
      list.appendChild(pickerRow('', f.name, size, function () {
        picker.selected = f.path;
        Array.from(list.children).forEach(c => c.classList.remove('bg-purple-100', 'dark:bg-purple-900/40'));
        this.classList.add('bg-purple-100', 'dark:bg-purple-900/40');
      }, false));
    });

    if (!list.children.length && !data.error) {
      list.innerHTML = picker.mode === 'dir'
        ? '<div class="px-3 py-4 text-xs opacity-60">مفيش مجلدات جوه المسار ده</div>'
        : '<div class="px-3 py-4 text-xs opacity-60">مفيش ملفات .sol / .solw هنا — افتح مجلد تاني</div>';
    }
  } catch (err) {
    list.innerHTML = '';
    errBox.textContent = 'Failed to browse: ' + err;
    errBox.classList.remove('hidden');
  }
}

function openFilePicker(mode, targetInputId, title) {
  // أي خطأ هنا كان هيفضل مخفي (الـ DevTools متقفلة في التطبيق)،
  // فبنظهره كـ toast بدل ما الزرار يبان "مش شغال".
  try {
    const modal = $('filePickerModal');
    if (!modal) {
      showToast('File picker modal not found — امسح الكاش (Ctrl+F5) وجرّب تاني', 'red');
      return;
    }

    picker.mode = mode;
    picker.target = targetInputId;
    picker.selected = '';

    const titleEl = $('filePickerTitle');
    if (titleEl) titleEl.textContent = title;

    modal.classList.remove('hidden');

    const input = $(targetInputId);
    pickerLoad(input ? (input.value || '').trim() : '');
  } catch (err) {
    showToast('Browse failed: ' + err.message, 'red');
  }
}

function closeFilePicker() {
  $('filePickerModal').classList.add('hidden');
}

function confirmFilePicker() {
  if (!picker.selected) {
    showToast(picker.mode === 'dir' ? 'اختار مجلد الأول' : 'اختار ملف .sol / .solw الأول', 'red');
    return;
  }
  $(picker.target).value = picker.selected;
  closeFilePicker();
  showToast('Path selected — اضغط Save عشان يتحفظ', 'green');
}

async function saveVisionMasterPaths() {
  const payload = {
    assembly_dir:  $('vmAssemblyDir').value.trim(),
    solution_path: $('vmSolutionPath').value.trim()
  };

  try {
    const res = await fetch('/vision_master/paths', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.status === 403 || res.status === 401) {
      showToast('Developer access required', 'red');
      return;
    }

    const data = await res.json();
    renderVmCheck(data.check);

    if (data.check && data.check.ok) {
      showToast('VisionMaster paths saved!', 'green');
    } else {
      showToast('Saved, but the paths look invalid — check below', 'red');
    }
  } catch (err) {
    showToast('Failed to save VisionMaster paths', 'red');
  }
}


/* ─────────────────────────────────────────────
   7. MANUAL SCANNER MODALS (shared: index + create_program + sql)
───────────────────────────────────────────── */
function startFlagPolling() {
  // بنسجّل مستقبلات الـ push دايمًا...
  RT.on('flags1', d => applyFlags(d, 'manualScannerModal', 'noCsv1'));
  RT.on('flags2', d => applyFlags(d, 'manualScannerModal2', 'noCsv2'));

  // ...والـ polling بيفضل شغال دايمًا كشبكة أمان.
  // الفلاجات دي بتفتح مودالات الأعطال، فلو حدث ضاع المشغّل مش هيشوف
  // إن السكانر فشل. مش هنراهن على ده.
  setInterval(function () {
    fetch('/check-flags')
      .then(r => r.json())
      .then(d => applyFlags(d, 'manualScannerModal', 'noCsv1'))
      .catch(err => console.error('Error fetching flags:', err));
  }, 1000);

  setInterval(function () {
    fetch('/check-flags2')
      .then(r => r.json())
      .then(d => applyFlags(d, 'manualScannerModal2', 'noCsv2'))
      .catch(err => console.error('Error fetching flags:', err));
  }, 1000);
}

async function submitManualData() {
  const val = $('manualInput').value;
  if (!val) return alert('Please enter data');
  const response = await fetch('/api/station', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ station_data: val })
  });
  if (response.ok) {
    $('manualScannerModal').classList.add('hidden');
    $('manualInput').value = '';
    showToast('Data submitted successfully', 'green');
  }
}

async function submitManualData2() {
  const val = $('manualInput2').value;
  if (!val) return alert('Please enter data');
  const response = await fetch('/api/station2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ station_data: val })
  });
  if (response.ok) {
    $('manualScannerModal2').classList.add('hidden');
    $('manualInput2').value = '';
    showToast('Data submitted successfully', 'green');
  }
}

async function submitCsv1() {
  try {
    const res = await fetch('/control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    if (res.ok) clearAlert('noCsv1');
    else console.error('Server error S1:', res.status);
  } catch (e) { console.error('Network error:', e); }
}

async function submitCsv2() {
  try {
    const res = await fetch('/control2', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    if (res.ok) clearAlert('noCsv2');
    else console.error('Server error S2:', res.status);
  } catch (e) { console.error('Network error:', e); }
}


/* ─────────────────────────────────────────────
   8. CREATE PROGRAM — PICKER & OPTIONS EDITOR
───────────────────────────────────────────── */
const defaultFixedOptions = {
  front_logo:       [['None','00'],['Beko','1A'],['Defy','1B'],['Arcelik','1C'],['Ariston','1D'],['Whirlpool','1E']],
  display_logo:     [['None','00'],['Fish screen','1F'],['Second screen','1G'],['Ahmed screen','1H'],['opt3','1I'],['opt4','1J']],
  color:            [['None','00'],['white','6A'],['Black','6B'],['opt3','6C'],['opt4','6D'],['opt5','6E']],
  data_logo:        [['None','00'],['Beko','4A'],['Defy','4B'],['Arcelik','4C'],['Ariston','4D'],['Whirlpool','4E']],
  inverter_logo:    [['None','00'],['Beko','7A'],['Defy','7B'],['Arcelik','7C'],['Ariston','7D'],['Whirlpool','7E']],
  power_logo:       [['None','00'],['Beko','3A'],['Defy','3B'],['Arcelik','3C'],['Ariston','3D'],['Whirlpool','3E']],
  eva_cover:        [['None','00'],['Beko','2A'],['Defy','2B'],['Arcelik','2C'],['Ariston','2D'],['Whirlpool','2E']],
  drawer_printing:  [['None','00'],['Veg','5A'],['Dairy','5B'],['Meat','5C'],['opt3','5D'],['opt5','5E']],
  color_logo:       [['None','00'],['white','6A'],['Black','6B'],['opt3','6C'],['opt4','6D'],['opt5','6E']],
  fan_cover:        [['None','00'],['Beko','8A'],['Defy','8B'],['Arcelik','8C'],['Ariston','8D'],['Whirlpool','8E']],
  shelve_color:     [['None','00'],['white','9A'],['Black','9B'],['opt3','9C'],['opt4','9D'],['opt5','9E']],
};

/* خيارات الاختبارات وأسماؤها بقت في test_options.json على السيرفر بدل
   localStorage بتاع المتصفح — كاش الكروم كان بيتمسح فيضيع كل التعديلات،
   وكل جهاز كان شايف نسخة مختلفة. */
let FIXED_OPTIONS = JSON.parse(JSON.stringify(defaultFixedOptions));
let TEST_LABELS   = {};
let TESTS_MAP = {};

/* ترحيل لمرة واحدة: أي إعدادات قديمة في localStorage بتتنقل للملف
   وبعدين بتتمسح من المتصفح. */
function collectLegacyTestOptions() {
  const payload = { fixed_options: {}, labels: {} };
  let found = false;

  try {
    const saved = localStorage.getItem('saved_fixed_options');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed && typeof parsed === 'object') { payload.fixed_options = parsed; found = true; }
    }
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.indexOf('label_') === 0) {
        payload.labels[k.slice(6)] = localStorage.getItem(k);
        found = true;
      }
    }
  } catch (e) { return null; }

  return found ? payload : null;
}

function clearLegacyTestOptions() {
  try {
    localStorage.removeItem('saved_fixed_options');
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.indexOf('label_') === 0) keys.push(k);
    }
    keys.forEach(k => localStorage.removeItem(k));
  } catch (e) { /* ignore */ }
}

async function saveTestOptions(payload) {
  try {
    const res = await fetch('/test_options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) { showToast('Could not save test options', 'red'); return false; }
    return true;
  } catch (e) {
    showToast('Network error while saving test options', 'red');
    return false;
  }
}

async function loadTestOptions() {
  let data = { fixed_options: {}, labels: {} };
  try {
    // cache-busting: الملف بيتغير من برّه الواجهة كمان
    const res = await fetch('/test_options?t=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    data = await res.json();
    console.log('[test_options] loaded from', data.path || 'server', data);
  } catch (e) {
    console.error('Could not read test_options.json:', e);
    showToast('Could not read test_options.json — using defaults', 'red');
    return;   // مانمسحش اللي محمّل بالفعل بالافتراضي
  }

  const serverFixed  = (data && data.fixed_options) || {};
  const serverLabels = (data && data.labels) || {};
  const serverEmpty  = Object.keys(serverFixed).length === 0 && Object.keys(serverLabels).length === 0;

  if (serverEmpty) {
    const legacy = collectLegacyTestOptions();
    if (legacy) {
      const ok = await saveTestOptions(legacy);
      if (ok) {
        Object.assign(serverFixed,  legacy.fixed_options);
        Object.assign(serverLabels, legacy.labels);
        clearLegacyTestOptions();
        showToast('Test options moved from the browser cache to test_options.json', 'green');
      }
    }
  } else {
    clearLegacyTestOptions();
  }

  FIXED_OPTIONS = JSON.parse(JSON.stringify(defaultFixedOptions));
  Object.keys(serverFixed).forEach(k => { FIXED_OPTIONS[k] = serverFixed[k]; });
  TEST_LABELS = Object.assign({}, serverLabels);
}

function initTestsMap(tests) {
  if (!Array.isArray(tests)) return;
  tests.forEach(t => {
    const key = String(t.name).replace(/\s+/g, '_');
    TESTS_MAP[key] = {
      originalName: t.name,
      station: (t.station || '').toUpperCase(),
      options: Array.isArray(t.options) ? t.options.map(o => ({ name: o.name, code: o.code })) : []
    };
  });
}

function getLabelName(key) {
  return TEST_LABELS[key] ||
    document.querySelector(`[data-key="${key}"]`)?.textContent || key;
}

function ensureHiddenInput(sanitizedKey) {
  let hidden = document.querySelector(`input[name="${sanitizedKey}"]`);
  if (!hidden) {
    hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = sanitizedKey;
    hidden.id   = sanitizedKey;
    document.querySelector('form')?.appendChild(hidden);
  }
  return hidden;
}

let CURRENT_FIELD = null;

/* الافتراضي لكل الاختبارات بقى None بدل "Select…".
   الكود 00 هو نفس اللي موجود في defaultFixedOptions فوق. */
const NONE_OPTION = { name: 'None', code: '00' };
const NONE_VALUE  = NONE_OPTION.name + '|' + NONE_OPTION.code;

/* بيرجع الاسم من صيغة "Label|Code" عشان نكتبه على الـ chip. */
function labelFromValue(value) {
  if (!value) return NONE_OPTION.name;
  return String(value).split('|', 1)[0] || NONE_OPTION.name;
}

/* بيمشي على كل الاختبارات في صفحة create_program (الثابتة والديناميكية):
   - أي حقل فاضي بياخد None|00
   - الـ chip بيتظبط على القيمة الفعلية

   الجزء التاني ده كان ناقص: لو الفورم رجع بأخطاء، القيم كانت بترجع في
   الـ hidden inputs بس كل الـ chips تفضل مكتوب عليها "Select…"، فالمستخدم
   ميعرفش هو مختار إيه. */
function applyNoneDefaults() {
  document.querySelectorAll('.picker-btn').forEach(btn => {
    const key = btn.dataset.test ||
                btn.querySelector('.editable-label')?.getAttribute('data-key');
    if (!key) return;

    const hidden = document.getElementById(key);
    if (!hidden) return;

    if (!hidden.value.trim()) hidden.value = NONE_VALUE;

    const chip = $('selected-' + key) || $('disp_' + key);
    if (chip) chip.textContent = labelFromValue(hidden.value);
  });
}

function openPicker(fieldKey) {
  CURRENT_FIELD = fieldKey;
  $('modalTitle').textContent = 'Choose ' + getLabelName(fieldKey);
  const list = $('modalList');
  list.innerHTML = '';

  const editBtn = document.createElement('button');
  editBtn.textContent = 'Edit options';
  editBtn.className = 'btn mb-3';
  editBtn.onclick = () => openOptionsEditor(fieldKey);
  list.appendChild(editBtn);

  let opts = [];
  if (FIXED_OPTIONS[fieldKey]) {
    opts = FIXED_OPTIONS[fieldKey].map(o => ({ name: o[0], code: o[1] }));
  } else if (TESTS_MAP[fieldKey]) {
    opts = TESTS_MAP[fieldKey].options.map(o => ({ name: o.name, code: o.code }));
  }

  /* لازم يكون فيه None في كل قائمة — من غيرها المستخدم يقدر يختار
     بس ميقدرش يرجّع الاختبار لـ None تاني. الاختبارات الديناميكية
     في tests.json غالبًا مفيهاش None، فبنضيفه هنا. */
  if (!opts.some(o => String(o.name).trim().toLowerCase() === 'none')) {
    opts = [{ ...NONE_OPTION }].concat(opts);
  }

  if (!opts || opts.length === 0) {
    const msg = document.createElement('p');
    msg.className = 'text-sm text-gray-500';
    msg.textContent = 'No options available for this item.';
    list.appendChild(msg);
  } else {
    opts.forEach(opt => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'opt w-full text-left border rounded p-2 hover:bg-gray-100';
      btn.innerHTML = `<div class="font-medium">${escapeHtml(opt.name)}</div><div class="text-xs opacity-70">Code: ${escapeHtml(opt.code)}</div>`;
      btn.addEventListener('click', () => chooseOption(fieldKey, opt.name, opt.code));
      list.appendChild(btn);
    });
  }
  $('modalBackdrop').style.display = 'flex';
}

function closePicker() {
  $('modalBackdrop').style.display = 'none';
  CURRENT_FIELD = null;
}

function chooseOption(fieldKey, name, code) {
  const hidden = ensureHiddenInput(fieldKey);
  if (hidden) hidden.value = `${name}|${code}`;
  const disp = $('selected-' + fieldKey) || $('disp_' + fieldKey);
  if (disp) disp.textContent = name;
  closePicker();
}

function openOptionsEditor(fieldKey) {
  const list = $('modalList');
  list.innerHTML = '';

  const container = document.createElement('div');
  container.innerHTML = `
    <div class="mb-3 flex items-center justify-between">
      <h4 class="font-semibold">Edit options for: ${escapeHtml(getLabelName(fieldKey))}</h4>
      <div class="flex gap-2">
        <button type="button" class="btn" id="addOptionBtn">+ Add</button>
        <button type="button" class="btn" id="cancelEditBtn">Cancel</button>
        <button type="button" class="btn" id="saveEditBtn">Save</button>
      </div>
    </div>
    <div id="optionsEditorList" class="space-y-2 max-h-[50vh] overflow-auto"></div>
  `;
  list.appendChild(container);

  const editorList = container.querySelector('#optionsEditorList');
  let isDynamic = false;
  let optionsArr = [];

  if (FIXED_OPTIONS[fieldKey]) {
    optionsArr = JSON.parse(JSON.stringify(FIXED_OPTIONS[fieldKey]));
  } else if (TESTS_MAP[fieldKey]) {
    isDynamic = true;
    optionsArr = TESTS_MAP[fieldKey].options.map(o => [o.name, o.code]);
  }

  function renderEditorRows() {
    editorList.innerHTML = '';
    optionsArr.forEach(([lbl, cod], idx) => {
      const row = document.createElement('div');
      row.className = 'flex gap-2 items-center';
      row.innerHTML = `
        <input data-idx="${idx}" data-type="label" class="w-1/2 rounded-lg border p-2" value="${escapeHtml(lbl)}"/>
        <input data-idx="${idx}" data-type="code"  class="w-1/4 rounded-lg border p-2" value="${escapeHtml(cod)}"/>
        <button data-del="${idx}" class="btn">Delete</button>
      `;
      editorList.appendChild(row);
      row.querySelector(`[data-del="${idx}"]`).addEventListener('click', () => {
        optionsArr.splice(idx, 1);
        renderEditorRows();
      });
    });
    if (optionsArr.length === 0) {
      const note = document.createElement('p');
      note.className = 'text-sm opacity-70';
      note.textContent = 'No options yet. Add one with + Add';
      editorList.appendChild(note);
    }
  }

  container.querySelector('#addOptionBtn').addEventListener('click', () => {
    optionsArr.push(['New option', '00']);
    renderEditorRows();
  });

  container.querySelector('#saveEditBtn').addEventListener('click', () => {
    const newList = [];
    Array.from(editorList.children).forEach(row => {
      const labelInput = row.querySelector('input[data-type="label"]');
      const codeInput  = row.querySelector('input[data-type="code"]');
      if (!labelInput || !codeInput) return;
      newList.push([labelInput.value.trim() || 'Unnamed', codeInput.value.trim() || '00']);
    });

    if (isDynamic) {
      const t = TESTS_MAP[fieldKey];
      if (t) t.options = newList.map(([n, c]) => ({ name: n, code: c }));
      if (typeof TESTS !== 'undefined') {
        for (let i = 0; i < TESTS.length; i++) {
          if (String(TESTS[i].name).replace(/\s+/g, '_') === fieldKey) {
            TESTS[i].options = newList.map(([n, c]) => ({ name: n, code: c }));
            break;
          }
        }
      }
    } else {
      FIXED_OPTIONS[fieldKey] = newList;
      saveTestOptions({ fixed_options: { [fieldKey]: newList } });
    }
    openPicker(fieldKey);
  });

  container.querySelector('#cancelEditBtn').addEventListener('click', () => openPicker(fieldKey));
  renderEditorRows();
}

function selectOption(testKey, optName, optCode) {
  closePicker();
  const chip = $(`selected-${testKey}`);
  if (chip) chip.textContent = optName;
  const hidden = $(testKey);
  if (hidden) hidden.value = `${optName}|${optCode}`;
}

async function deleteTest(testName) {
  if (!confirm(`Are you sure you want to delete ${testName}?`)) return;
  const res = await fetch('/delete_test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: testName })
  });
  alert(res.ok ? 'Test deleted successfully' : 'Something went wrong');
  if (res.ok) location.reload();
}

async function resetDefaults() {
  if (!confirm('Are you sure you want to delete all Tests?')) return;
  const res = await fetch('/reset_tests', { method: 'POST' });
  alert(res.ok ? 'Tests reset successfully' : 'Something went wrong');
  if (res.ok) location.reload();
}

function validateForm() {
  const sku = $('sku')?.value.trim();
  if (!sku) { alert('Please enter SKU'); return false; }
  if (!($('ModelName')?.value || '').trim()) { alert('Please enter Model Name'); return false; }

  /* الاختبارات مبقتش إجبارية: أي حقل المستخدم مساه زي ما هو بيتبعت None|00
     وبيتكتب في الـ CSV عادي. الـ alert القديم "Please select: X" اتشال. */
  applyNoneDefaults();

  const btn = $('submitBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }
  return true;
}

function initEditableLabels() {
  document.querySelectorAll('.editable-label').forEach(el => {
    const key = el.getAttribute('data-key');
    const savedName = TEST_LABELS[key];
    if (savedName) el.textContent = savedName;

    el.addEventListener('click', e => e.stopPropagation());
    el.addEventListener('blur', function () {
      const name = this.textContent.trim();
      if (!name || name === TEST_LABELS[key]) return;
      TEST_LABELS[key] = name;
      saveTestOptions({ labels: { [key]: name } });
    });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); this.blur(); }
    });
  });
}


/* ─────────────────────────────────────────────
   9. SQL PAGE — STATUS POLLING & DUMMY HANDLERS
───────────────────────────────────────────── */
const SQL_PILL_OK  = 'px-3 py-1 rounded-full text-sm font-semibold border bg-emerald-900/50 text-emerald-300 border-emerald-700/50';
const SQL_PILL_BAD = 'px-3 py-1 rounded-full text-sm font-semibold border bg-red-900/50 text-red-300 border-red-700/50';

function applySqlStatus(data) {
      if (!data) return;
      // DB connection badges
      const db1 = $('db-status1');
      const db2 = $('db-status2');
      if (db1) {
        db1.textContent = data.db1_connected ? 'Connected' : 'Disconnected';
        db1.className = data.db1_connected ? SQL_PILL_OK : SQL_PILL_BAD;
      }
      if (db2) {
        db2.textContent = data.db2_connected ? 'Connected' : 'Disconnected';
        db2.className = data.db2_connected ? SQL_PILL_OK : SQL_PILL_BAD;
      }

      // Helper: update raw/extracted data elements
      function updateDataEl(elId, value, emptyMsg) {
        const el = $(elId);
        if (!el) return;
        if (value && value !== emptyMsg) {
          el.textContent = `"${value}"`;
          el.className = 'text-lg font-mono bg-yellow-100 p-2 rounded border';
        } else {
          el.textContent = value || emptyMsg;
          el.className = 'text-lg font-mono bg-gray-100 p-2 rounded border text-gray-500';
        }
      }

      function updateDbStatusEl(elId, statusText) {
        const el = $(elId);
        if (!el) return;
        el.textContent = statusText;
        if (statusText.includes('') || statusText.includes('Found'))
          el.className = 'text-sm font-mono bg-green-100 p-2 rounded border h-16 overflow-y-auto';
        else if (statusText.includes('') || statusText.includes('Error'))
          el.className = 'text-sm font-mono bg-red-100 p-2 rounded border h-16 overflow-y-auto';
        else
          el.className = 'text-sm font-mono bg-purple-100 p-2 rounded border h-16 overflow-y-auto';
      }

      updateDataEl('raw-data1', data.last_raw_data1, 'No data received yet');
      updateDataEl('dummy-extracted1', data.last_dummy_extracted1, 'No dummy extracted yet');
      updateDbStatusEl('db-operation-status1', data.last_db_status1 || '');

      updateDataEl('raw-data2', data.last_raw_data2, 'No data received yet');
      updateDataEl('dummy-extracted2', data.last_dummy_extracted2, 'No dummy extracted yet');
      updateDbStatusEl('db-operation-status2', data.last_db_status2 || '');

      // Dummy numbers
      ['dummy-number1', 'dummy-number2'].forEach((id, i) => {
        const el = $(id);
        if (!el) return;
        const val = i === 0 ? data.last_dummy_number1 : data.last_dummy_number2;
        el.textContent = val || 'No data received';
        el.className = val
          ? 'text-2xl font-bold text-emerald-400 mt-2'
          : 'text-2xl font-bold text-slate-500 mt-2';
      });
}

// fallback بس — لما Socket.IO مش متاح
function updateSqlStatus() {
  fetch('/sql_status')
    .then(r => r.json())
    .then(applySqlStatus)
    .catch(e => console.error('Error fetching SQL status:', e));
}

function initDummyHandler(inputId, btnId, statusId, endpoint) {
  const input  = $(inputId);
  const btn    = $(btnId);
  const status = $(statusId);
  if (!btn || !input) return;

  btn.addEventListener('click', async () => {
    const value = (input.value || '').trim();
    if (!value) { showToast('Dummy number is empty', 'red'); return; }
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dummy: value })
      });
      const j = await res.json().catch(() => ({}));
      const msg = (j && j.msg) || (res.ok ? 'Dummy accepted' : 'Error processing dummy');
      if (status) status.textContent = msg;
      showToast(msg, res.ok && j.ok ? 'green' : 'red');
    } catch {
      const msg = 'Network error while sending dummy';
      if (status) status.textContent = msg;
      showToast(msg, 'red');
    }
  });
}

/* ─────────────────────────────────────────────
   OPERATION MODES (Manual Scanner Mode ON/OFF)
   بيتحفظ في config.json عن طريق /features
───────────────────────────────────────────── */
function setManualModeStatus(enabled, note) {
  const box = $('manualModeStatus');
  if (!box) return;
  box.textContent = note || (enabled
    ? 'ON — popup + buzzer on scan failure'
    : 'OFF — alert only, sequence continues');
  box.className = 'mt-2 text-xs font-semibold ' +
    (enabled ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400');
}

async function loadFeatures() {
  const toggle = $('manualModeToggle');
  if (!toggle) return;
  try {
    const res  = await fetch('/features');
    const data = await res.json();
    const on   = data.manual_mode !== false;
    toggle.checked = on;
    setManualModeStatus(on);
  } catch (e) {
    setManualModeStatus(true, 'Could not read the current mode');
  }
}

async function saveManualMode(enabled) {
  try {
    const res  = await fetch('/features', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manual_mode: enabled })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setManualModeStatus(!enabled, (data && data.message) || 'Save failed — developer mode only');
      const toggle = $('manualModeToggle');
      if (toggle) toggle.checked = !enabled;
      showToast('Could not save the mode', 'red');
      return;
    }
    const on = !(data.features && data.features.manual_mode === false);
    setManualModeStatus(on);
    showToast('Manual Scanner Mode: ' + (on ? 'ON' : 'OFF'), 'green');
  } catch (e) {
    showToast('Network error while saving the mode', 'red');
  }
}

function initFeatures() {
  const toggle = $('manualModeToggle');
  if (!toggle) return;
  toggle.addEventListener('change', () => saveManualMode(toggle.checked));
  loadFeatures();
}


function toggleAuthFields() {
  const auth     = $('Authentication');
  const login    = $('login');
  const password = $('password');
  if (!auth) return;
  const isWindows = auth.value === 'Windows Authentication';
  if (login)    { login.disabled    = isWindows; if (isWindows) login.value    = ''; }
  if (password) { password.disabled = isWindows; if (isWindows) password.value = ''; }
}


/* ─────────────────────────────────────────────
   10. LOGIN PAGE — PASSWORD TOGGLE
───────────────────────────────────────────── */
function initPasswordToggle() {
  const passwordInput   = $('password');
  const togglePassword  = $('togglePassword');
  if (!passwordInput || !togglePassword) return;

  togglePassword.addEventListener('click', function () {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    this.textContent = type === 'password' ? 'SHOW' : 'HIDE';
  });
}


/* ─────────────────────────────────────────────
   11. DOMContentLoaded — WIRE EVERYTHING UP
───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  // إعادة التحميل بعد إعادة تشغيل السيرفر (بدل ما يتفتح تاب جديد).
  // boot_id بيتغيّر مع كل تشغيلة — أول ما نلاقيه اتغيّر يبقى السيرفر رجع.
  let bootId = null;
  const checkBootId = (data) => {
    if (!data || !data.boot_id) return;
    if (bootId === null) bootId = data.boot_id;
    else if (bootId !== data.boot_id) location.reload();
  };

  RT.on('process_status', checkBootId);

  const watchServerRestart = async () => {
    try {
      const res = await fetch('/process/status', { cache: 'no-store' });
      if (!res.ok) return;
      checkBootId(await res.json());
    } catch (e) {
      /* السيرفر مقفول دلوقتي — هنحاول تاني في الدورة الجاية */
    }
  };
  watchServerRestart();
  setInterval(watchServerRestart, 2000);

  // حالة المحطتين: بنسجّل الـ push دايمًا، والـ polling تحت بيشتغل
  // بس لو الاتصال مش حي
  RT.on('station1', applyStation1);
  RT.on('station2', applyStation2);

  // مربّع اللوج تحت كل محطة (index) — الكود في static/station_log.js
  if (typeof initStationLog === 'function') {
    document.querySelectorAll('.station-log').forEach(el => initStationLog(el));
  }

  // Auto-switch (index)
  const sw = $('autoSwitch');
  if (sw) sw.addEventListener('change', () => { AUTO_SEND_ENABLED = $('autoSwitch').checked; });

  // Error modal reset button (index)
  const resetBtn = $('btnResetError');
  if (resetBtn) resetBtn.addEventListener('click', resetErrorCondition);

  // I/O Mapping (index)
  if ($('ioMappingForm')) {
    renderIoForm(loadIoSettings());

    $('ioMappingForm').addEventListener('submit', function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      const newMapping = {};
      formData.forEach((value, key) => newMapping[key] = parseInt(value));
      localStorage.setItem('io_mapping_v2', JSON.stringify(newMapping));
      fetch('/save_mapping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newMapping)
      }).then(res => res.json())
        .then(() => {
          showToast('I/O Mapping saved successfully!', 'green');
          $('ioMappingModal').classList.add('hidden');
        })
        .catch(() => showToast('Saved locally, but backend sync failed.', 'red'));
    });

    const btnIo    = $('btnIoMapping');
    const btnClose = $('btnCloseIoMapping');
    if (btnIo)    btnIo.addEventListener('click', () => {
      renderIoForm(loadIoSettings());
      loadEndpoints();
      loadVisionMasterPaths();
      loadFeatures();
      $('ioMappingModal').classList.remove('hidden');
    });
    if (btnClose) btnClose.addEventListener('click', () => $('ioMappingModal').classList.add('hidden'));
  }

  // Device addresses (index, developer mode only — the form isn't rendered otherwise)
  if ($('endpointsForm')) {
    $('endpointsForm').addEventListener('submit', function (e) {
      e.preventDefault();
      saveEndpoints();
    });

    const btnResetEp = $('btnResetEndpoints');
    if (btnResetEp) btnResetEp.addEventListener('click', resetEndpoints);
  }

  // VisionMaster paths (index, developer mode only — the form isn't rendered otherwise)
  if ($('visionMasterForm')) {
    $('visionMasterForm').addEventListener('submit', function (e) {
      e.preventDefault();
      saveVisionMasterPaths();
    });

    const btnVmCheck = $('btnVmCheck');
    if (btnVmCheck) btnVmCheck.addEventListener('click', loadVisionMasterPaths);

    const btnBrowseAsm = $('btnBrowseAssembly');
    const btnBrowseSol = $('btnBrowseSolution');
    if (btnBrowseAsm) btnBrowseAsm.addEventListener('click',
      () => openFilePicker('dir', 'vmAssemblyDir', 'Select Assembly Directory'));
    if (btnBrowseSol) btnBrowseSol.addEventListener('click',
      () => openFilePicker('file', 'vmSolutionPath', 'Select Solution File (.solw / .sol)'));
  }

  // File picker (index, developer mode only)
  if ($('filePickerModal')) {
    const btnPickerClose  = $('btnCloseFilePicker');
    const btnPickerCancel = $('btnPickerCancel');
    const btnPickerSelect = $('btnPickerSelect');
    const btnPickerUp     = $('btnPickerUp');
    const btnPickerGo     = $('btnPickerGo');
    const pickerPathInput = $('pickerPath');

    if (btnPickerClose)  btnPickerClose.addEventListener('click', closeFilePicker);
    if (btnPickerCancel) btnPickerCancel.addEventListener('click', closeFilePicker);
    if (btnPickerSelect) btnPickerSelect.addEventListener('click', confirmFilePicker);

    if (btnPickerUp) btnPickerUp.addEventListener('click', () => {
      if (picker.parentPath) pickerLoad(picker.parentPath);
    });

    if (btnPickerGo) btnPickerGo.addEventListener('click', () => pickerLoad(pickerPathInput.value.trim()));
    if (pickerPathInput) pickerPathInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); pickerLoad(pickerPathInput.value.trim()); }
    });

    $('filePickerModal').addEventListener('click', function (e) {
      if (e.target === this) closeFilePicker();
    });
  }

  // Times modal (index + create_program)
  const btnAdjustTimes  = $('btnAdjustTimes');
  const btnCloseTimes   = $('btnCloseTimes');
  const btnCancelTimes  = $('btnCancelTimes');
  const btnResetTimes   = $('btnResetTimes');
  const btnSaveTimes    = $('btnSaveTimes');
  const timesModal      = $('timesModal');

  if (btnAdjustTimes && timesModal) {
    btnAdjustTimes.addEventListener('click', () => { loadTimeSettings(); timesModal.classList.remove('hidden'); });
    if (btnCloseTimes)  btnCloseTimes.addEventListener('click',  () => timesModal.classList.add('hidden'));
    if (btnCancelTimes) btnCancelTimes.addEventListener('click', () => timesModal.classList.add('hidden'));
    timesModal.addEventListener('click', function (e) { if (e.target === this) this.classList.add('hidden'); });

    if (btnResetTimes) btnResetTimes.addEventListener('click', async () => {
      if (confirm('Reset all time settings to defaults?')) {
        populateTimeForm(DEFAULT_TIME_SETTINGS);
        await saveTimeSettings(DEFAULT_TIME_SETTINGS);
      }
    });

    if (btnSaveTimes) btnSaveTimes.addEventListener('click', async () => {
      const success = await saveTimeSettings(collectTimeSettings());
      if (success) timesModal.classList.add('hidden');
    });
  }

  // Picker click delegation (create_program)
  document.addEventListener('click', function (e) {
    const pickerBtn = e.target.closest('.picker-btn');
    if (!pickerBtn) return;
    const testName = pickerBtn.dataset.test;
    if (!testName) return;
    openPicker(testName);
    e.preventDefault();
  });

  // create_program: الخيارات والأسماء بتتقرا من test_options.json الأول
  if (document.querySelectorAll('.picker-btn').length ||
      document.querySelectorAll('.editable-label').length) {
    loadTestOptions().then(() => {
      if (document.querySelectorAll('.editable-label').length) initEditableLabels();
      if (document.querySelectorAll('.picker-btn').length) applyNoneDefaults();
    });
  }

  // SQL status: push لو متاح، وإلا polling.
  // ملحوظة: /sql_status بيفتح اتصال pyodbc حقيقي، فكل تاب كان بيعمل
  // اتصال كل ثانيتين. دلوقتي السيرفر بيعمله مرة واحدة للكل.
  if ($('db-status1') || $('db-status2')) {
    RT.on('sql_status', applySqlStatus);
    updateSqlStatus();
    setInterval(updateSqlStatus, 2000);

    initDummyHandler('dummyStation1', 'btnDummyStation1', 'dummyStation1Status', '/manual_dummy_station1');
    initDummyHandler('dummyStation2', 'btnDummyStation2', 'dummyStation2Status', '/manual_dummy_station2');
  }

  // Login page
  initPasswordToggle();

  // Manual scanner modals (shared)
  initAlertBell();
  initFeatures();
  if ($('manualScannerModal') || $('manualScannerModal2')) startFlagPolling();

  // Station status (index) — polling دايمًا، والـ push بيسرّعه بس
  if ($('s1-arrived-flag') || $('s2-arrived-flag')) {
    const ms = Math.max(200, DEFAULT_TIME_SETTINGS.statusRefresh);
    window.statusInterval = setInterval(refreshStatus, ms);
    refreshStatus();
  }
});