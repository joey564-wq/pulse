// Pulse dashboard. Polls /stats, /summary, /alerts/recent every 5s.

const $ = (id) => document.getElementById(id);

function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function dotClass(uptime) {
  if (uptime >= 99) return "ok";
  if (uptime >= 95) return "warn";
  return "bad";
}

function formatLatency(ms) {
  if (ms === null || ms === undefined) return "—";
  return `${Math.round(ms)} ms`;
}

function formatRelativeTime(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  const seconds = Math.round((Date.now() - d.getTime()) / 1000);
  if (seconds < 60)    return `${seconds}s ago`;
  if (seconds < 3600)  return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

// Inline SVG sparkline. Receives an array of numbers (latencies) and renders
// a line normalised to its own min/max — purpose is shape recognition, not
// absolute scale.
function sparkline(points, w = 80, h = 24) {
  if (!points.length) return '<svg class="spark"></svg>';
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const dx = w / Math.max(points.length - 1, 1);
  const d = points
    .map((v, i) => {
      const x = (i * dx).toFixed(1);
      const y = (h - ((v - min) / range) * h).toFixed(1);
      return `${i === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <path d="${d}" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.7"/>
  </svg>`;
}

async function fetchJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

async function refresh() {
  try {
    const [overall, summaries, alerts] = await Promise.all([
      fetchJSON("/stats"),
      fetchJSON("/summary"),
      fetchJSON("/alerts/recent?limit=5"),
    ]);

    $("stats").innerHTML = `
      <div class="stat">
        <div class="stat-label">Services</div>
        <div class="stat-value">${overall.services_tracked}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Checks</div>
        <div class="stat-value">${overall.total_checks.toLocaleString()}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Uptime</div>
        <div class="stat-value">${overall.overall_uptime_pct.toFixed(2)}%</div>
      </div>
      <div class="stat">
        <div class="stat-label">Active alerts</div>
        <div class="stat-value">${overall.active_alerts}</div>
      </div>
    `;

    // Per-service sparkline fetches: N+1 pattern, fine for the demo's ~4
    // services. If we ever had hundreds, a /sparkline-data endpoint would
    // replace this.
    const rows = await Promise.all(summaries.map(async (s) => {
      const hist = await fetchJSON(
        `/history?url=${encodeURIComponent(s.url)}&limit=30`
      );
      const lats = hist.filter((h) => h.ok).map((h) => h.latency_ms).reverse();
      const meta = [
        `avg ${formatLatency(s.avg_latency_ms)}`,
        `${s.total_checks.toLocaleString()} checks`,
        formatRelativeTime(s.last_checked_at),
      ].join(" · ");
      return `
        <div class="service">
          <div class="dot ${dotClass(s.uptime_pct)}"></div>
          <div class="service-info">
            <div class="service-url">${escape(s.url)}</div>
            <div class="service-meta">${meta}</div>
          </div>
          ${sparkline(lats)}
          <div class="service-uptime">${s.uptime_pct.toFixed(1)}%</div>
        </div>
      `;
    }));
    $("services").innerHTML = rows.join("") ||
      '<div class="alert-empty">No services yet. Run <code>pulse monitor</code> to populate.</div>';

    $("alerts").innerHTML = alerts.length
      ? alerts.map((a) => `
          <div class="alert-item">
            <span class="kind ${a.kind}">${a.kind}</span>
            <span>${escape(a.url)}</span>
            <time>${new Date(a.occurred_at).toLocaleString()}</time>
          </div>
        `).join("")
      : '<div class="alert-empty">No alerts yet.</div>';

    $("last-updated").textContent =
      `updated ${new Date().toLocaleTimeString()}`;
  } catch (e) {
    console.error(e);
    $("last-updated").textContent = "connection error";
  }
}

refresh();
setInterval(refresh, 5000);