// ════════════════════════════════════════
//  TECHXORA 24 — app.js
// ════════════════════════════════════════

'use strict';

// ── STATE ──────────────────────────────
let scannerMode = 'entry';
let currentParticipant = null;

function getState() {
  return {
    participants: JSON.parse(localStorage.getItem('hf_participants') || '[]'),
    logs:         JSON.parse(localStorage.getItem('hf_logs')         || '[]'),
    foodTokens:   JSON.parse(localStorage.getItem('hf_food_tokens')  || '[]'),
    counter:      parseInt(localStorage.getItem('hf_counter')        || '0')
  };
}

function saveState(state) {
  if (state.participants !== undefined) localStorage.setItem('hf_participants', JSON.stringify(state.participants));
  if (state.logs         !== undefined) localStorage.setItem('hf_logs',         JSON.stringify(state.logs));
  if (state.foodTokens   !== undefined) localStorage.setItem('hf_food_tokens',  JSON.stringify(state.foodTokens));
  if (state.counter      !== undefined) localStorage.setItem('hf_counter',      state.counter.toString());
}

// ── PARTICLES ──────────────────────────
(function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  const ctx    = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function rand(min, max) { return Math.random() * (max - min) + min; }

  function createParticle() {
    return {
      x: rand(0, W), y: rand(0, H),
      vx: rand(-0.15, 0.15), vy: rand(-0.25, -0.05),
      size: rand(2, 2.5),
      alpha: rand(0.3, 0.5),
      color: Math.random() < 0.6 ? '#00f5c4' : Math.random() < 0.5 ? '#4d9eff' : '#f5c300'
    };
  }

  function initParticleArray() {
    particles = Array.from({ length: 60 }, createParticle);
  }

  function tick() {
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      p.alpha += rand(-0.005, 0.005);
      p.alpha = Math.max(0.05, Math.min(0.55, p.alpha));
      if (p.y < -10) { p.y = H + 10; p.x = rand(0, W); }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(tick);
  }

  resize();
  initParticleArray();
  tick();
  window.addEventListener('resize', () => { resize(); initParticleArray(); });
})();

// ── FOOD TOKENS ────────────────────────
function loadFoodConfig() {
  const { foodTokens } = getState();
  const list = document.getElementById('food-config-list');

  if (!foodTokens.length) {
    list.innerHTML = `<div style="color:var(--muted2);font-family:'Share Tech Mono',monospace;font-size:0.8rem;padding:0.5rem 0;">
      No food tokens configured yet.
    </div>`;
    return;
  }

  list.innerHTML = foodTokens.map((t, i) => `
    <div class="food-token">
      <span>🍽 ${escHtml(t)}</span>
      <button class="delete-btn" onclick="removeFoodToken(${i})" title="Remove">✕</button>
    </div>
  `).join('');

  updateFoodSelect();
}

function updateFoodSelect() {
  const { foodTokens } = getState();
  const sel = document.getElementById('food-select');
  sel.innerHTML = foodTokens.length
    ? foodTokens.map(t => `<option value="${escHtml(t)}">${escHtml(t)}</option>`).join('')
    : '<option value="">No tokens configured</option>';
}

function addFoodToken() {
  const input = document.getElementById('new-food-name');
  const name  = input.value.trim();
  if (!name)              { showToast('Enter a token name!', true); return; }
  const { foodTokens } = getState();
  if (foodTokens.includes(name)) { showToast('Token already exists!', true); return; }
  foodTokens.push(name);
  saveState({ foodTokens });
  input.value = '';
  loadFoodConfig();
  showToast(`Token "${name}" added!`);
}

function removeFoodToken(i) {
  const { foodTokens } = getState();
  foodTokens.splice(i, 1);
  saveState({ foodTokens });
  loadFoodConfig();
  showToast('Token removed.');
}

// ── REGISTRATION ───────────────────────
function generateId(counter) {
  return 'HF-' + String(counter).padStart(4, '0');
}

function registerParticipant() {
  const name    = document.getElementById('reg-name').value.trim();
  const email   = document.getElementById('reg-email').value.trim();
  const phone   = document.getElementById('reg-phone').value.trim();
  const college = document.getElementById('reg-college').value.trim();
  const team    = document.getElementById('reg-team').value.trim();
  const role    = document.getElementById('reg-role').value;

  if (!name || !email || !college) {
    showToast('Please fill in required fields!', true);
    return;
  }

  const state = getState();

  if (state.participants.find(p => p.email === email)) {
    showToast('This email is already registered!', true);
    return;
  }

  const counter = state.counter + 1;
  const id      = generateId(counter);

  const participant = {
    id, name, email, phone, college, team, role,
    registeredAt: new Date().toISOString(),
    status:  'outside',
    entries: [],
    foodUsed: {}
  };

  state.participants.push(participant);
  state.counter = counter;
  saveState({ participants: state.participants, counter });
  addLog('register', `${name} registered as ${id}`, id);

  showRegistrationModal(participant, state.foodTokens);

  // Clear form
  ['reg-name','reg-email','reg-phone','reg-college','reg-team'].forEach(id => {
    document.getElementById(id).value = '';
  });

  updateStats();
  renderTable();
}

function showRegistrationModal(p, foodTokens) {
  currentParticipant = p;
  document.getElementById('modal-pid').textContent = p.id;
  document.getElementById('modal-sub').textContent = `Welcome to TECHXORA, ${p.name}!`;
  document.getElementById('modal-info').innerHTML = `
    <b>ID:</b> ${p.id}<br>
    <b>Name:</b> ${escHtml(p.name)}<br>
    <b>Email:</b> ${escHtml(p.email)}<br>
    <b>College:</b> ${escHtml(p.college)}<br>
    ${p.team ? `<b>Team:</b> ${escHtml(p.team)}<br>` : ''}
    <b>Role:</b> ${escHtml(p.role)}<br>
    ${foodTokens.length ? `<b>Food Tokens:</b> ${foodTokens.map(escHtml).join(', ')}` : ''}
  `;

  const qrContainer = document.getElementById('qr-container');
  qrContainer.innerHTML = '';
  new QRCode(qrContainer, {
    text: p.id,
    width: 160, height: 160,
    colorDark: '#000000', colorLight: '#ffffff',
    correctLevel: QRCode.CorrectLevel.H
  });

  document.getElementById('modal').classList.add('show');
}

function closeModal() {
  document.getElementById('modal').classList.remove('show');
}

function printBadge() {
  if (!currentParticipant) return;
  const p = currentParticipant;
  document.getElementById('print-pid').textContent     = p.id;
  document.getElementById('print-name').textContent    = p.name;
  document.getElementById('print-college').textContent = p.college;
  document.getElementById('print-team').textContent    = p.team ? `Team: ${p.team}` : '';
  document.getElementById('print-role').textContent    = p.role.toUpperCase();

  const printQR = document.getElementById('print-qr');
  printQR.innerHTML = '';
  new QRCode(printQR, {
    text: p.id,
    width: 120, height: 120,
    colorDark: '#000000', colorLight: '#ffffff'
  });

  setTimeout(() => window.print(), 300);
}

// ── SCANNER ────────────────────────────
function setScannerMode(mode) {
  scannerMode = mode;
  document.querySelectorAll('.scanner-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + mode).classList.add('active');
  document.getElementById('food-token-select').style.display = mode === 'food' ? 'block' : 'none';
  document.getElementById('scan-result').classList.remove('show');
  document.getElementById('scan-input').focus();
  updateFoodSelect();
}

function processScan() {
  const input = document.getElementById('scan-input');
  const id    = input.value.trim().toUpperCase();
  input.value = '';
  input.focus();
  if (!id) return;

  const state       = getState();
  const participant = state.participants.find(p => p.id === id);
  const resultEl    = document.getElementById('scan-result');
  const statusEl    = document.getElementById('scan-status-text');
  const detailEl    = document.getElementById('scan-detail-text');
  const timeEl      = document.getElementById('scan-time');
  const now         = new Date();
  const timeStr     = now.toLocaleString();

  resultEl.className = 'scan-result show';

  if (!participant) {
    resultEl.classList.add('error');
    statusEl.textContent = '✕ INVALID ID';
    statusEl.className   = 'scan-status error';
    detailEl.textContent = `ID "${id}" not found in the system.`;
    timeEl.textContent   = timeStr;
    showToast('Participant not found!', true);
    return;
  }

  if (scannerMode === 'entry') {
    participant.status = 'inside';
    participant.entries.push({ type: 'entry', time: now.toISOString() });

    resultEl.classList.add('success');
    statusEl.textContent = '✓ ENTRY GRANTED';
    statusEl.className   = 'scan-status success';
    detailEl.innerHTML   = `<b>${escHtml(participant.name)}</b><br>${escHtml(participant.college)} · ${participant.role}${participant.team ? ` · ${escHtml(participant.team)}` : ''}`;
    timeEl.textContent   = `Entered at ${timeStr}`;
    addLog('entry', `${participant.name} (${id}) entered`, id);
    showToast(`${participant.name} — Entry logged ✓`);

  } else if (scannerMode === 'exit') {
    participant.status = 'outside';
    participant.entries.push({ type: 'exit', time: now.toISOString() });

    resultEl.classList.add('success');
    statusEl.textContent = '↑ EXIT LOGGED';
    statusEl.className   = 'scan-status success';
    detailEl.innerHTML   = `<b>${escHtml(participant.name)}</b><br>${escHtml(participant.college)} · ${participant.role}`;
    timeEl.textContent   = `Exited at ${timeStr}`;
    addLog('exit', `${participant.name} (${id}) exited`, id);
    showToast(`${participant.name} — Exit logged`);

  } else if (scannerMode === 'food') {
    const foodName = document.getElementById('food-select').value;
    if (!foodName) {
      resultEl.classList.add('error');
      statusEl.textContent = '✕ NO TOKEN SELECTED';
      statusEl.className   = 'scan-status error';
      detailEl.textContent = 'Please configure and select a food token first.';
      timeEl.textContent   = timeStr;
      return;
    }

    if (participant.foodUsed[foodName]) {
      const usedTime = new Date(participant.foodUsed[foodName]).toLocaleString();
      resultEl.classList.add('error');
      statusEl.textContent = '✕ TOKEN EXPIRED';
      statusEl.className   = 'scan-status error';
      detailEl.innerHTML   = `<b>${escHtml(participant.name)}</b> already claimed <b>${escHtml(foodName)}</b>`;
      timeEl.textContent   = `Used at ${usedTime}`;
      showToast(`${foodName} already claimed by ${participant.name}!`, true);
    } else {
      participant.foodUsed[foodName] = now.toISOString();
      resultEl.classList.add('success');
      statusEl.textContent = '✓ FOOD DISPENSED';
      statusEl.className   = 'scan-status success';
      detailEl.innerHTML   = `<b>${escHtml(participant.name)}</b> — <b>${escHtml(foodName)}</b> token claimed`;
      timeEl.textContent   = `Claimed at ${timeStr}`;
      addLog('food', `${participant.name} (${id}) claimed ${foodName}`, id);
      showToast(`${foodName} dispensed to ${participant.name} ✓`);
    }
  }

  const idx = state.participants.findIndex(p => p.id === id);
  state.participants[idx] = participant;
  saveState({ participants: state.participants });
  updateStats();
  renderTable();
}

// ── LOGS ───────────────────────────────
function addLog(type, message, pid) {
  const { logs } = getState();
  logs.unshift({ type, message, pid, time: new Date().toISOString() });
  if (logs.length > 500) logs.pop();
  saveState({ logs });
  renderLogs();
}

function renderLogs() {
  const { logs } = getState();
  const el = document.getElementById('log-list');

  if (!logs.length) {
    el.innerHTML = `<div class="empty-state">
      <div class="es-icon">📋</div>
      <div class="es-title">No Events Logged</div>
      Activity will appear here in real-time.
    </div>`;
    return;
  }

  el.innerHTML = logs.map(l => {
    const dotClass = l.type === 'register' ? 'register'
                   : l.type === 'entry'    ? 'entry'
                   : l.type === 'exit'     ? 'exit'
                   : 'food';
    return `
      <div class="log-item">
        <div class="log-dot ${dotClass}"></div>
        <span style="color:var(--text)">${escHtml(l.message)}</span>
        <span class="log-time">${new Date(l.time).toLocaleTimeString()}</span>
      </div>
    `;
  }).join('');
}

function clearLogs() {
  if (!confirm('Clear all logs?')) return;
  saveState({ logs: [] });
  renderLogs();
  showToast('Logs cleared.');
}

// ── TABLE ──────────────────────────────
function renderTable() {
  const { participants } = getState();
  const search = document.getElementById('search-input').value.toLowerCase();
  const tbody  = document.getElementById('participants-tbody');

  const filtered = participants.filter(p =>
    p.name.toLowerCase().includes(search)    ||
    p.id.toLowerCase().includes(search)      ||
    p.college.toLowerCase().includes(search) ||
    (p.team || '').toLowerCase().includes(search)
  );

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="9">
      <div class="empty-state">
        <div class="es-icon">⬡</div>
        <div class="es-title">${participants.length ? 'No Results Found' : 'No Participants Yet'}</div>
        ${participants.length ? 'Try a different search term.' : 'Register someone to get started.'}
      </div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const foodEntries = Object.entries(p.foodUsed || {});
    const entryCount  = (p.entries || []).filter(e => e.type === 'entry').length;

    return `
      <tr>
        <td><span style="font-family:'Share Tech Mono',monospace;color:var(--accent3)">${p.id}</span></td>
        <td>
          <b>${escHtml(p.name)}</b><br>
          <span style="font-size:0.73rem;color:var(--muted2)">${escHtml(p.email)}</span>
        </td>
        <td>${escHtml(p.college)}</td>
        <td>${p.team ? escHtml(p.team) : '<span style="color:var(--muted)">—</span>'}</td>
        <td><span style="font-family:'Share Tech Mono',monospace;font-size:0.73rem">${escHtml(p.role)}</span></td>
        <td>
          <span class="badge badge-${p.status === 'inside' ? 'inside' : 'outside'}">
            ${p.status === 'inside' ? '▲ Inside' : '▼ Outside'}
          </span>
        </td>
        <td>
          ${foodEntries.length
            ? foodEntries.map(([name, time]) =>
                `<span class="badge badge-food-used" title="Used ${new Date(time).toLocaleTimeString()}">✓ ${escHtml(name)}</span> `
              ).join('')
            : '<span style="color:var(--muted);font-size:0.78rem;">—</span>'}
        </td>
        <td style="font-family:'Share Tech Mono',monospace;color:var(--muted2)">${entryCount}×</td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="showParticipantQR('${p.id}')">QR</button>
        </td>
      </tr>
    `;
  }).join('');
}

function showParticipantQR(id) {
  const { participants, foodTokens } = getState();
  const p = participants.find(x => x.id === id);
  if (!p) return;
  showRegistrationModal(p, foodTokens);
}

// ── STATS ──────────────────────────────
function updateStats() {
  const { participants, logs } = getState();
  const inside     = participants.filter(p => p.status === 'inside').length;
  const foodClaimed = participants.reduce((sum, p) => sum + Object.keys(p.foodUsed || {}).length, 0);

  animateNumber('stat-total',  participants.length);
  animateNumber('stat-inside', inside);
  animateNumber('stat-food',   foodClaimed);
  animateNumber('stat-events', logs.length);

  document.getElementById('dash-total').textContent   = participants.length;
  document.getElementById('dash-inside').textContent  = inside;
  document.getElementById('dash-outside').textContent = participants.length - inside;
  document.getElementById('dash-food').textContent    = foodClaimed;
}

function animateNumber(id, target) {
  const el      = document.getElementById(id);
  const current = parseInt(el.textContent) || 0;
  if (current === target) return;
  const step = target > current ? 1 : -1;
  const diff = Math.abs(target - current);
  const delay = diff > 10 ? 20 : 60;
  let val = current;
  const timer = setInterval(() => {
    val += step;
    el.textContent = val;
    if (val === target) clearInterval(timer);
  }, delay);
}

// ── EXPORT ─────────────────────────────
function exportCSV() {
  const { participants } = getState();
  if (!participants.length) { showToast('No data to export!', true); return; }

  const headers = ['ID','Name','Email','Phone','College','Team','Role','Status','Registered At','Food Tokens Used','Entry Count'];
  const rows = participants.map(p => [
    p.id, p.name, p.email, p.phone || '', p.college, p.team || '', p.role,
    p.status,
    new Date(p.registeredAt).toLocaleString(),
    Object.keys(p.foodUsed || {}).join(' | '),
    (p.entries || []).filter(e => e.type === 'entry').length
  ]);

  const csv  = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = 'techxora-participants.csv';
  a.click();
  showToast('CSV exported!');
}

function clearAll() {
  if (!confirm('Clear ALL participant data? This cannot be undone!')) return;
  localStorage.clear();
  updateStats();
  renderTable();
  renderLogs();
  loadFoodConfig();
  showToast('All data cleared.');
}

// ── NAV ────────────────────────────────
function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  if (btn) btn.classList.add('active');

  if (name === 'participants') { updateStats(); renderTable(); }
  if (name === 'logs')         renderLogs();
  if (name === 'scanner') {
    setScannerMode('entry');
    setTimeout(() => document.getElementById('scan-input').focus(), 100);
  }
  if (name === 'home') { updateStats(); loadFoodConfig(); }
}

// ── TOAST ──────────────────────────────
let toastTimer = null;
function showToast(msg, error = false) {
  const toast   = document.getElementById('toast');
  const msgEl   = document.getElementById('toast-msg');
  const iconEl  = document.getElementById('toast-icon');

  msgEl.textContent  = msg;
  iconEl.textContent = error ? '✕' : '✓';
  toast.className    = 'toast show' + (error ? ' error' : '');

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = 'toast'; }, 3200);
}

// ── UTILS ──────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── KEYBOARD SHORTCUTS ─────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ── INIT ───────────────────────────────
updateStats();
loadFoodConfig();
