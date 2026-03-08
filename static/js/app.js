/* ═══════════════════════════════════════════════════════════
   TECHXORA 26 – Shared JS Utilities
   ═══════════════════════════════════════════════════════════ */

// ── Particles ──────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById('particles-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  const COLORS = ['#00f5ff', '#a855f7', '#3b82f6', '#22c55e'];
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 1.5 + 0.5,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      alpha: Math.random() * 0.5 + 0.2,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.fill();
    });
    // Draw connections
    ctx.globalAlpha = 1;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 100) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = particles[i].color;
          ctx.globalAlpha = (1 - d / 100) * 0.08;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Toast Notifications ────────────────────────────────────
window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <span class="toast-msg">${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4200);
};

// ── Flash → Toast (convert server flash to toast on load) ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash-msg[data-auto-toast]').forEach(el => {
    const type = el.dataset.autoToast;
    showToast(el.textContent.trim(), type);
    el.style.display = 'none';
  });
});

// ── Sidebar Mobile Toggle ──────────────────────────────────
const hamburger = document.getElementById('hamburger');
const sidebar   = document.querySelector('.sidebar');
if (hamburger && sidebar) {
  hamburger.addEventListener('click', () => sidebar.classList.toggle('open'));
}

// ── Scanner Handler ─────────────────────────────────────────
window.initScanner = function({ formId, uidInputId, modeInputId, resultId, processUrl }) {
  const form     = document.getElementById(formId);
  const uidInput = document.getElementById(uidInputId);
  const resultEl = document.getElementById(resultId);
  if (!form) return;

  // Auto-focus scanner input
  if (uidInput) uidInput.focus();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const uid  = uidInput ? uidInput.value.trim().toUpperCase() : '';
    const mode = document.getElementById(modeInputId)?.value || 'entry';
    if (!uid) { showToast('Please enter a participant ID.', 'error'); return; }

    try {
      const res = await fetch(processUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ uid, mode }),
      });
      const data = await res.json();

      if (resultEl) {
        resultEl.className = `scanner-result show ${data.success ? 'success' : 'error'}`;
        resultEl.innerHTML = buildResultHTML(data);
      }
      showToast(data.message, data.success ? 'success' : 'error');
      if (data.success && uidInput) uidInput.value = '';
    } catch (err) {
      showToast('Network error. Please try again.', 'error');
    }
  });

  function buildResultHTML(data) {
    if (!data.success) return `<span style="font-size:1.5rem">⚠️</span><div><div style="font-weight:700;color:var(--neon-red)">${data.message}</div></div>`;
    const p = data.participant;
    return `
      <span style="font-size:2rem">${data.success ? '✅' : '❌'}</span>
      <div>
        <div style="font-weight:700;margin-bottom:4px">${p.name}</div>
        <div style="font-size:0.8rem;color:var(--text-secondary)">${p.unique_id} · ${p.team || 'No team'}</div>
        <div style="margin-top:6px;display:flex;gap:8px;flex-wrap:wrap">
          <span class="badge ${p.is_inside ? 'badge-inside' : 'badge-outside'}">
            <span class="badge-dot"></span>${p.is_inside ? 'Inside' : 'Outside'}
          </span>
          <span class="badge ${p.food_issued ? 'badge-food' : 'badge-nofood'}">
            <span class="badge-dot"></span>${p.food_issued ? `Food ×${p.food_count}` : 'No Food Yet'}
          </span>
        </div>
      </div>`;
  }
};

// ── QR Modal ────────────────────────────────────────────────
window.openQRModal = function(uid, qrPath, name) {
  const modal = document.getElementById('qr-modal');
  if (!modal) return;
  modal.querySelector('#modal-qr-img').src = `/static/${qrPath}`;
  modal.querySelector('#modal-qr-id').textContent = uid;
  modal.querySelector('#modal-qr-name').textContent = name;
  modal.classList.add('active');
};
document.addEventListener('click', e => {
  if (e.target.closest('#qr-modal') && !e.target.closest('.modal-box')) {
    document.getElementById('qr-modal')?.classList.remove('active');
  }
  if (e.target.id === 'qr-modal-close' || e.target.closest('#qr-modal-close')) {
    document.getElementById('qr-modal')?.classList.remove('active');
  }
});

// ── Live Stats Poll ──────────────────────────────────────────
window.startStatsPoll = function(interval = 10000) {
  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      ['total', 'inside', 'food', 'events'].forEach(key => {
        const el = document.getElementById(`stat-${key}`);
        if (el) el.textContent = data[key] ?? '–';
      });
    } catch (_) {}
  }
  fetchStats();
  setInterval(fetchStats, interval);
};

// ── CSV Export ──────────────────────────────────────────────
window.exportTableCSV = function(tableId, filename = 'export.csv') {
  const table = document.getElementById(tableId);
  if (!table) return;
  let csv = '';
  table.querySelectorAll('tr').forEach(row => {
    const cols = [...row.querySelectorAll('th, td')].map(c => `"${c.innerText.replace(/"/g, '""')}"`);
    csv += cols.join(',') + '\n';
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
};

// ── Countdown Timer ─────────────────────────────────────────
window.startCountdown = function(targetISO) {
  const target = new Date(targetISO).getTime();
  function update() {
    const now  = Date.now();
    const diff = Math.max(0, target - now);
    const h = Math.floor(diff / 3.6e6);
    const m = Math.floor((diff % 3.6e6) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    const el = id => document.getElementById(`cd-${id}`);
    if (el('h')) el('h').textContent = String(h).padStart(2, '0');
    if (el('m')) el('m').textContent = String(m).padStart(2, '0');
    if (el('s')) el('s').textContent = String(s).padStart(2, '0');
    if (diff > 0) requestAnimationFrame(update);
  }
  update();
};

// ── Zoho Timeline Builder ────────────────────────────────────
window.buildTimeline = function(containerId, events, dayHours) {
  // events: [{date, action, time}]
  // Groups by date and renders timeline rows
  const container = document.getElementById(containerId);
  if (!container) return;

  const EVENT_START_HOUR = 9;
  const EVENT_END_HOUR   = 21; // 24h so we cover late hackathons too
  const TOTAL_HOURS      = EVENT_END_HOUR - EVENT_START_HOUR;

  const grouped = {};
  events.forEach(ev => {
    if (!grouped[ev.date]) grouped[ev.date] = [];
    grouped[ev.date].push(ev);
  });

  const sorted = Object.keys(grouped).sort();
  if (sorted.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;padding:20px">No attendance records yet.</p>`;
    return;
  }

  let html = `
    <div class="timeline-header-row">
      <div>Date</div>
      <div>
        <div class="timeline-time-axis">
          ${Array.from({length: TOTAL_HOURS + 1}, (_, i) => {
            const h = EVENT_START_HOUR + i;
            return `<span>${h < 12 ? h + 'AM' : h === 12 ? '12PM' : (h-12) + 'PM'}</span>`;
          }).join('')}
        </div>
      </div>
      <div style="text-align:right">Hours</div>
    </div>`;

  const today = new Date().toISOString().slice(0, 10);

  sorted.forEach(date => {
    const dayEvents = grouped[date].sort((a, b) => a.time.localeCompare(b.time));
    const hrs = dayHours[date] || '00:00';
    const isToday = date === today;

    // Build dot positions
    const dots = dayEvents.map(ev => {
      const [h, m] = ev.time.split(':').map(Number);
      const totalMins = (h + m / 60 - EVENT_START_HOUR) / TOTAL_HOURS;
      const pct = Math.min(Math.max(totalMins * 100, 0), 100);
      const dotClass = ev.action === 'entry' ? 'dot-entry' : ev.action === 'exit' ? 'dot-exit' : 'dot-food';
      return { pct, dotClass, time: ev.time, action: ev.action };
    });

    // Build segments (entry → exit pairs)
    let segments = [];
    let entryPct = null;
    dayEvents.forEach(ev => {
      const [h, m] = ev.time.split(':').map(Number);
      const pct = Math.min(Math.max(((h + m / 60 - EVENT_START_HOUR) / TOTAL_HOURS) * 100, 0), 100);
      if (ev.action === 'entry') entryPct = pct;
      else if (ev.action === 'exit' && entryPct !== null) {
        segments.push({ left: entryPct, width: pct - entryPct });
        entryPct = null;
      }
    });
    // If still inside
    if (entryPct !== null) {
      const nowH = new Date().getHours() + new Date().getMinutes() / 60;
      const nowPct = Math.min(((nowH - EVENT_START_HOUR) / TOTAL_HOURS) * 100, 100);
      segments.push({ left: entryPct, width: nowPct - entryPct, ongoing: true });
    }

    // Grid lines HTML (one per hour)
    const gridLines = Array.from({length: TOTAL_HOURS - 1}, () =>
      `<div class="tl-gridline"></div>`).join('');

    const segHTML = segments.map(s =>
      `<div class="timeline-segment${s.ongoing ? ' ongoing' : ''}"
         style="left:${s.left.toFixed(2)}%;width:${Math.max(s.width, 0).toFixed(2)}%;
         ${s.ongoing ? 'opacity:0.6;background:linear-gradient(90deg,var(--neon-cyan),rgba(0,245,255,0.3))' : ''}"></div>`
    ).join('');

    const dotHTML = dots.map(d =>
      `<div class="tl-event-dot ${d.dotClass}" style="left:${d.pct.toFixed(2)}%">
         <div class="tl-tooltip">${d.action.toUpperCase()} · ${d.time}</div>
       </div>`
    ).join('');

    const d = new Date(date + 'T00:00:00');
    const weekday = d.toLocaleDateString('en-US', { weekday: 'short' });
    const ddMM    = d.toLocaleDateString('en-US', { day: '2-digit', month: 'short' });

    html += `
      <div class="timeline-row ${isToday ? 'tl-today' : ''}">
        <div class="timeline-day-label">
          <span class="tl-weekday">${isToday ? 'Today' : weekday}</span>
          <span class="tl-date">${ddMM}</span>
        </div>
        <div class="timeline-bar-wrap">
          <div class="timeline-grid-lines">${gridLines}</div>
          <div class="timeline-bar-track"></div>
          ${segHTML}
          ${dotHTML}
        </div>
        <div class="tl-hours">
          ${hrs}
          <span class="tl-hours-label">Hrs worked</span>
        </div>
      </div>`;
  });

  container.innerHTML = html;
};

// ── Print Badge ──────────────────────────────────────────────
window.printBadge = function() { window.print(); };

// ── Participant search filter ────────────────────────────────
window.filterTable = function(inputId, tableId) {
  const val = document.getElementById(inputId)?.value.toLowerCase() || '';
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(val) ? '' : 'none';
  });
};
