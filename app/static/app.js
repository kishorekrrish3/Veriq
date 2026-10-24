/**
 * VERIQ Developer Workbench — Core Client Application
 * Tagline: Code is generated. Proof is earned.
 */

let activeRunId = null;
let eventSource = null;
let currentClaimsData = [];
let currentFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initForms();
  initFilters();
  initActionButtons();
  loadOverviewMetrics();
  loadRecentRuns();
  checkProviderStatus();
  loadBenchmarks();
});

// Toast notification helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'success' ? 'toast-success' : type === 'error' ? 'toast-error' : ''}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Navigation and Tab Switching
function initNavigation() {
  const navButtons = document.querySelectorAll('.nav-item');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      switchTab(tabId);
    });
  });

  const quickNewRun = document.getElementById('btn-quick-new-run');
  if (quickNewRun) {
    quickNewRun.addEventListener('click', () => switchTab('new-run'));
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  const activeBtn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  const pageTitle = document.getElementById('page-title');
  const titles = {
    'overview': 'System Overview',
    'new-run': 'New Engineering Run',
    'workspace': 'Active Run Workspace',
    'history': 'Run History',
    'ledger': 'Verification Ledger',
    'benchmarks': 'Reproducible Benchmarks',
    'settings': 'Settings & Infrastructure',
  };
  if (pageTitle) pageTitle.textContent = titles[tabId] || 'VERIQ';

  if (tabId === 'history') loadHistoryRuns();
  if (tabId === 'overview') {
    loadOverviewMetrics();
    loadRecentRuns();
  }
  if (tabId === 'benchmarks') loadBenchmarks();
}

// Form Handlers
function initForms() {
  const form = document.getElementById('new-run-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-submit-run');
    btn.disabled = true;
    btn.textContent = 'Initializing Run...';

    const payload = {
      title: document.getElementById('run-title').value.trim(),
      description: document.getElementById('run-desc').value.trim(),
      sample_name: document.getElementById('run-sample').value,
      enable_research: document.getElementById('run-research').checked,
      max_repair_attempts: parseInt(document.getElementById('run-repairs').value, 10),
      mode: document.getElementById('run-mode').value,
    };

    try {
      const resp = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.message || 'Failed to start run');
      }

      const run = await resp.json();
      showToast(`Run ${run.run_id} started successfully!`, 'success');
      btn.disabled = false;
      btn.textContent = 'Launch Evidence-Driven Run';

      // Open workspace for this run
      openRunWorkspace(run.run_id);
    } catch (err) {
      showToast(err.message, 'error');
      btn.disabled = false;
      btn.textContent = 'Launch Evidence-Driven Run';
    }
  });
}

// Open Workspace for a specific run and attach SSE
async function openRunWorkspace(runId) {
  activeRunId = runId;
  switchTab('workspace');

  // Reset workspace UI
  document.getElementById('active-run-id').textContent = runId;
  document.getElementById('active-run-title').textContent = 'Loading run metadata...';
  document.getElementById('timeline-container').innerHTML = '<div class="empty-state">Subscribing to live events...</div>';
  document.getElementById('diff-code-block').innerHTML = '<code>Waiting for patch generation...</code>';
  document.getElementById('routing-decisions-container').innerHTML = '<div class="empty-state">Awaiting model selection...</div>';
  document.getElementById('workspace-ledger-claims').innerHTML = '<div class="empty-state">Registering claims...</div>';

  await fetchAndDisplayRun(runId);
  subscribeToRunEvents(runId);
}

// Subscribe to SSE stream for live updates
function subscribeToRunEvents(runId) {
  if (eventSource) {
    eventSource.close();
  }

  const timelineContainer = document.getElementById('timeline-container');
  timelineContainer.innerHTML = '';

  eventSource = new EventSource(`/api/runs/${runId}/events`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      appendTimelineEvent(data);
      handleLiveEventData(data);
    } catch (e) {
      console.error('Error parsing SSE event:', e);
    }
  };

  eventSource.onerror = (err) => {
    console.warn('SSE stream closed or disconnected.');
    if (eventSource) {
      eventSource.close();
    }
  };
}

function appendTimelineEvent(ev) {
  const container = document.getElementById('timeline-container');
  const item = document.createElement('div');
  item.className = 'timeline-event-item';

  const isError = ev.event_type.includes('FAIL') || ev.event_type.includes('ERROR');
  const isSuccess = ev.event_type.includes('COMPLETE') || ev.event_type.includes('VALIDATED');

  item.innerHTML = `
    <div class="timeline-dot ${isError ? 'error' : isSuccess ? 'success' : ''}"></div>
    <div class="timeline-content">
      <div class="timeline-time">${new Date(ev.timestamp).toLocaleTimeString()} · <span class="font-mono text-cyan">${ev.event_type}</span></div>
      <div class="timeline-msg">${escapeHtml(ev.message)}</div>
    </div>
  `;
  container.appendChild(item);
  container.scrollTop = container.scrollHeight;

  const countBadge = document.getElementById('active-event-count');
  if (countBadge) {
    const total = container.querySelectorAll('.timeline-event-item').length;
    countBadge.textContent = `${total} events`;
  }
}

function handleLiveEventData(ev) {
  if (ev.event_type === 'MODEL_SELECTED' && ev.data) {
    renderRoutingDecision(ev.data);
  } else if (ev.event_type === 'PATCH_VALIDATED') {
    fetchRunDiff(activeRunId);
  } else if (ev.event_type === 'TESTS_EXECUTED' || ev.event_type === 'REPAIR_COMPLETED' || ev.event_type === 'VERIFICATION_COMPLETED') {
    fetchRunLedger(activeRunId);
    fetchRunDiff(activeRunId);
  } else if (ev.event_type === 'RUN_COMPLETED' || ev.event_type === 'RUN_FAILED') {
    fetchAndDisplayRun(activeRunId);
    loadOverviewMetrics();
  }
}

// Fetch run details and update UI
async function fetchAndDisplayRun(runId) {
  try {
    const resp = await fetch(`/api/runs/${runId}`);
    if (!resp.ok) return;
    const run = await resp.json();

    document.getElementById('active-run-id').textContent = run.run_id;
    document.getElementById('active-run-title').textContent = run.task_title;
    document.getElementById('active-run-dur').textContent = `${run.duration_seconds}s`;
    document.getElementById('active-run-files').textContent = run.changed_files ? run.changed_files.length : 0;
    document.getElementById('active-run-mode').textContent = run.execution_mode.toUpperCase();

    const statusBadge = document.getElementById('active-run-status');
    statusBadge.textContent = run.status;
    statusBadge.className = `status-badge status-${run.status.toLowerCase()}`;

    // Render diff
    if (run.unified_diff) {
      renderDiff(run.unified_diff);
    }

    // Render routing decisions
    if (run.routing_history && run.routing_history.length > 0) {
      const container = document.getElementById('routing-decisions-container');
      container.innerHTML = '';
      run.routing_history.forEach(renderRoutingDecision);
    }

    // Load ledger
    fetchRunLedger(runId);
  } catch (e) {
    console.error('Failed to fetch run details:', e);
  }
}

async function fetchRunDiff(runId) {
  try {
    const resp = await fetch(`/api/runs/${runId}/diff`);
    if (resp.ok) {
      const diffText = await resp.text();
      renderDiff(diffText);
    }
  } catch (e) {}
}

function renderDiff(diffText) {
  const codeBlock = document.getElementById('diff-code-block');
  if (!diffText || diffText.trim() === '' || diffText.includes('No modifications applied')) {
    codeBlock.innerHTML = '<code>No patch modifications applied yet.</code>';
    return;
  }

  const lines = diffText.split('\n');
  const formattedLines = lines.map(line => {
    const safeLine = escapeHtml(line);
    if (line.startsWith('+') && !line.startsWith('+++')) {
      return `<div class="diff-line-add">${safeLine}</div>`;
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      return `<div class="diff-line-del">${safeLine}</div>`;
    } else if (line.startsWith('@@')) {
      return `<div class="diff-line-hunk">${safeLine}</div>`;
    }
    return `<div>${safeLine}</div>`;
  });

  codeBlock.innerHTML = formattedLines.join('');
}

function renderRoutingDecision(decision) {
  const container = document.getElementById('routing-decisions-container');
  if (container.querySelector('.empty-state')) {
    container.innerHTML = '';
  }

  const card = document.createElement('div');
  card.className = 'provider-row mt-4';
  card.style.flexDirection = 'column';
  card.style.alignItems = 'flex-start';

  const tierBadgeClass = decision.tier === 'FAST' ? 'badge-cyan' : decision.tier === 'STANDARD' ? 'badge-blue' : 'badge-escalate';

  card.innerHTML = `
    <div style="display:flex; justify-content:space-between; width:100%; align-items:center; margin-bottom:6px;">
      <span class="badge ${tierBadgeClass}">${decision.tier} TIER</span>
      <span class="text-muted font-mono text-sm">Attempt #${decision.attempt}</span>
    </div>
    <div class="font-mono text-cyan" style="font-size:12px; font-weight:600;">${decision.model_id}</div>
    <div class="text-muted" style="font-size:12px; margin:4px 0;">${escapeHtml(decision.reason)}</div>
    <div style="display:flex; gap:12px; font-size:11px; color:var(--text-secondary); margin-top:4px;">
      <span>Latency: <strong class="font-mono">${decision.latency_ms || 0}ms</strong></span>
      <span>Tokens: <strong class="font-mono">${decision.total_tokens || 0}</strong></span>
      <span>Est. Cost: <strong class="font-mono">$${(decision.estimated_cost_usd || 0).toFixed(5)}</strong></span>
    </div>
  `;
  container.appendChild(card);
}

// Verification Ledger fetching and filtering
async function fetchRunLedger(runId) {
  try {
    const resp = await fetch(`/api/runs/${runId}/ledger`);
    if (!resp.ok) return;
    const ledger = await resp.json();
    currentClaimsData = ledger.claims || [];

    // Calculate verification rate
    const vRate = ledger.total_claims > 0 
      ? ((ledger.verified_count / ledger.total_claims) * 100).toFixed(1)
      : '0.0';
    const rateEl = document.getElementById('active-run-vrate');
    if (rateEl) rateEl.textContent = `${vRate}%`;

    renderLedgerClaims(currentClaimsData, 'workspace-ledger-claims', ledger.evidence || []);
  } catch (e) {
    console.error('Failed to load ledger:', e);
  }
}

function initFilters() {
  document.querySelectorAll('.ledger-filter-pills').forEach(group => {
    group.querySelectorAll('.pill').forEach(pill => {
      pill.addEventListener('click', () => {
        group.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentFilter = pill.dataset.filter;

        const targetId = group.id === 'workspace-ledger-filters' 
          ? 'workspace-ledger-claims' 
          : 'standalone-ledger-claims';
        renderFilteredClaims(targetId);
      });
    });
  });
}

function renderFilteredClaims(containerId) {
  let filtered = currentClaimsData;
  if (currentFilter !== 'ALL') {
    filtered = currentClaimsData.filter(c => c.status === currentFilter);
  }
  renderLedgerClaims(filtered, containerId);
}

function renderLedgerClaims(claims, containerId, evidenceList = []) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!claims || claims.length === 0) {
    container.innerHTML = '<div class="empty-state">No claims match the selected filter.</div>';
    return;
  }

  container.innerHTML = '';
  claims.forEach(claim => {
    const card = document.createElement('div');
    card.className = 'claim-card';

    const statusClass = `status-${claim.status.toLowerCase()}`;
    const backingEv = evidenceList.filter(e => (claim.evidence_ids || []).includes(e.evidence_id));

    let evHtml = '';
    backingEv.forEach(ev => {
      evHtml += `
        <div class="evidence-box">
          <div class="evidence-header">
            <span>[${escapeHtml(ev.evidence_id)}] Check: ${escapeHtml(ev.check_type)}</span>
            <span class="status-badge status-${ev.status.toLowerCase()}">${ev.status}</span>
          </div>
          ${ev.command ? `<div><strong>Command:</strong> <code>${escapeHtml(ev.command)}</code></div>` : ''}
          ${ev.exit_code !== null ? `<div><strong>Exit Code:</strong> ${ev.exit_code} · <strong>Duration:</strong> ${ev.duration_ms}ms</div>` : ''}
          ${ev.stdout ? `<div style="margin-top:4px;"><strong>Stdout:</strong> <pre style="white-space:pre-wrap; color:var(--text-secondary);">${escapeHtml(ev.stdout)}</pre></div>` : ''}
          ${ev.stderr ? `<div style="margin-top:4px; color:var(--status-failed);"><strong>Stderr:</strong> <pre style="white-space:pre-wrap;">${escapeHtml(ev.stderr)}</pre></div>` : ''}
        </div>
      `;
    });

    let limitationsHtml = '';
    if (claim.limitations && claim.limitations.length > 0) {
      limitationsHtml = `
        <div style="margin-top:8px;">
          <strong style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Explicit Limitations:</strong>
          <ul style="margin-left:18px; color:var(--text-secondary);">
            ${claim.limitations.map(l => `<li><em>${escapeHtml(l)}</em></li>`).join('')}
          </ul>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="claim-card-header">
        <div class="claim-title-group">
          <span class="claim-id">${claim.claim_id}</span>
          <span class="claim-title">${escapeHtml(claim.title)}</span>
          <span class="badge badge-outline" style="font-size:10px;">${claim.category}</span>
        </div>
        <span class="status-badge ${statusClass}">${claim.status}</span>
      </div>
      <div class="text-muted" style="margin-top:6px; font-size:12.5px;">${escapeHtml(claim.description)}</div>
      <div class="claim-details">
        ${limitationsHtml}
        <div style="margin-top:10px;">
          <strong style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Backing Proof & Evidence Records (${backingEv.length}):</strong>
          ${evHtml || '<div class="text-muted text-sm" style="margin-top:4px;">No concrete evidence records attached.</div>'}
        </div>
      </div>
    `;

    card.addEventListener('click', () => {
      card.classList.toggle('expanded');
    });

    container.appendChild(card);
  });
}

// Download action buttons
function initActionButtons() {
  document.getElementById('btn-download-report-md')?.addEventListener('click', () => {
    if (!activeRunId) return showToast('No active run selected', 'error');
    window.open(`/api/runs/${activeRunId}/report?format=markdown`, '_blank');
  });

  document.getElementById('btn-download-report-json')?.addEventListener('click', () => {
    if (!activeRunId) return showToast('No active run selected', 'error');
    window.open(`/api/runs/${activeRunId}/report?format=json`, '_blank');
  });

  document.getElementById('btn-refresh-runs')?.addEventListener('click', () => {
    loadOverviewMetrics();
    loadRecentRuns();
    showToast('Telemetry refreshed', 'info');
  });

  document.getElementById('btn-run-benchmark')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-benchmark');
    btn.disabled = true;
    btn.textContent = 'Executing Benchmark Suite...';
    try {
      const resp = await fetch('/api/benchmarks/run', { method: 'POST' });
      if (resp.ok) {
        showToast('Benchmark suite executed successfully!', 'success');
        loadBenchmarks();
      }
    } catch (e) {
      showToast('Benchmark execution failed', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Re-run Benchmark Harness';
    }
  });
}

// Load Overview Metrics
async function loadOverviewMetrics() {
  try {
    const resp = await fetch('/api/metrics/overview');
    if (!resp.ok) return;
    const data = await resp.json();

    document.getElementById('metric-verif-rate').textContent = `${data.verification_rate_percent}%`;
    document.getElementById('metric-total-runs').textContent = data.total_runs;
    document.getElementById('overview-verified').textContent = data.verified_claims;
    document.getElementById('overview-supported').textContent = data.supported_claims;
    document.getElementById('overview-failed').textContent = data.failed_claims;
    document.getElementById('overview-unresolved').textContent = data.unresolved_claims;
  } catch (e) {}
}

// Load Recent Runs into Overview Table
async function loadRecentRuns() {
  try {
    const resp = await fetch('/api/runs?limit=10');
    if (!resp.ok) return;
    const runs = await resp.json();

    const tbody = document.getElementById('overview-runs-body');
    if (!runs || runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No runs recorded yet. Start a run above!</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    runs.forEach(r => {
      const tr = document.createElement('tr');
      const vClaims = r.ledger_summary ? `${r.ledger_summary.verified_count}/${r.ledger_summary.total_claims}` : '0/0';
      tr.innerHTML = `
        <td><strong class="font-mono text-cyan">${r.run_id}</strong></td>
        <td>${escapeHtml(r.task_title)}</td>
        <td><span class="status-badge status-${r.status.toLowerCase()}">${r.status}</span></td>
        <td><span class="badge badge-outline">${r.execution_mode}</span></td>
        <td class="font-mono">${vClaims}</td>
        <td class="font-mono">${r.duration_seconds}s</td>
        <td class="text-muted">${new Date(r.created_at).toLocaleTimeString()}</td>
        <td>
          <button class="btn btn-sm btn-outline btn-inspect" data-run-id="${r.run_id}">Inspect</button>
        </td>
      `;
      tr.querySelector('.btn-inspect').addEventListener('click', () => openRunWorkspace(r.run_id));
      tbody.appendChild(tr);
    });
  } catch (e) {}
}

// Load Full History Table
async function loadHistoryRuns() {
  try {
    const resp = await fetch('/api/runs?limit=50');
    if (!resp.ok) return;
    const runs = await resp.json();

    const tbody = document.getElementById('history-runs-body');
    if (!runs || runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No runs stored in SQLite database.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    runs.forEach(r => {
      const tr = document.createElement('tr');
      const vClaims = r.ledger_summary ? `${r.ledger_summary.verified_count}/${r.ledger_summary.total_claims}` : '0/0';
      tr.innerHTML = `
        <td><strong class="font-mono text-cyan">${r.run_id}</strong></td>
        <td>${escapeHtml(r.task_title)}</td>
        <td><span class="status-badge status-${r.status.toLowerCase()}">${r.status}</span></td>
        <td><span class="badge badge-outline">${r.execution_mode}</span></td>
        <td class="font-mono">${vClaims}</td>
        <td class="font-mono">${r.duration_seconds}s</td>
        <td class="text-muted">${r.completed_at ? new Date(r.completed_at).toLocaleTimeString() : 'In Progress'}</td>
        <td>
          <button class="btn btn-sm btn-outline btn-inspect-hist" data-run-id="${r.run_id}">Inspect</button>
        </td>
      `;
      tr.querySelector('.btn-inspect-hist').addEventListener('click', () => openRunWorkspace(r.run_id));
      tbody.appendChild(tr);
    });
  } catch (e) {}
}

// Check Infrastructure & Provider Health
async function checkProviderStatus() {
  try {
    const healthResp = await fetch('/api/health');
    if (healthResp.ok) {
      const hData = await healthResp.json();
      const modeBadge = document.getElementById('mode-badge');
      if (hData.modes.live_inference_configured) {
        modeBadge.textContent = 'Live Inference';
        modeBadge.className = 'badge badge-pill badge-cyan';
      } else {
        modeBadge.textContent = 'Recorded Replay';
        modeBadge.className = 'badge badge-pill badge-outline';
      }

      const sbBadge = document.getElementById('settings-sandbox-badge');
      const sbDesc = document.getElementById('settings-sandbox-desc');
      if (hData.sandbox.docker_available) {
        sbBadge.textContent = 'HARDENED CONTAINER';
        sbBadge.className = 'status-badge status-verified';
        sbDesc.textContent = 'Docker engine connected; executing in isolated container.';
      } else {
        sbBadge.textContent = 'RESTRICTED PROCESS FALLBACK';
        sbBadge.className = 'status-badge status-unresolved';
        sbDesc.textContent = 'Docker unavailable; running in stripped-environment process sandbox.';
      }
    }

    const provResp = await fetch('/api/providers/status');
    if (provResp.ok) {
      const pData = await provResp.json();
      const nBadge = document.getElementById('settings-nebius-badge');
      if (pData.nebius.status === 'healthy') {
        nBadge.textContent = 'CONNECTED';
        nBadge.className = 'status-badge status-verified';
      } else {
        nBadge.textContent = 'UNCONFIGURED (REPLAY READY)';
        nBadge.className = 'status-badge status-not-run';
      }

      const tBadge = document.getElementById('settings-tavily-badge');
      if (pData.tavily.status === 'healthy') {
        tBadge.textContent = 'CONNECTED';
        tBadge.className = 'status-badge status-verified';
      } else {
        tBadge.textContent = 'UNCONFIGURED (REPLAY READY)';
        tBadge.className = 'status-badge status-not-run';
      }
    }
  } catch (e) {}
}

// Load Benchmark Experiment Results
async function loadBenchmarks() {
  try {
    const resp = await fetch('/api/benchmarks');
    if (!resp.ok) return;
    const bm = await resp.json();

    document.getElementById('bm-base-rate').textContent = `${bm.baseline_pass_rate}%`;
    document.getElementById('bm-routed-rate').textContent = `${bm.routed_pass_rate}%`;

    const tbody = document.getElementById('bm-table-body');
    tbody.innerHTML = '';
    (bm.tasks || []).forEach(t => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong class="font-mono text-cyan">${t.task_id}</strong></td>
        <td>${escapeHtml(t.task_name)}</td>
        <td><span class="status-badge ${t.baseline_passed ? 'status-verified' : 'status-failed'}">${t.baseline_passed ? 'PASS' : 'FAIL'}</span></td>
        <td class="font-mono">${t.baseline_latency_ms}ms</td>
        <td><span class="status-badge ${t.routed_passed ? 'status-verified' : 'status-failed'}">${t.routed_passed ? 'PASS' : 'FAIL'}</span></td>
        <td><span class="badge ${t.routed_tier_used === 'FAST' ? 'badge-cyan' : t.routed_tier_used === 'STANDARD' ? 'badge-blue' : 'badge-escalate'}">${t.routed_tier_used}</span></td>
        <td>${t.repair_triggered ? '<span class="status-badge status-verified">YES (REPAIRED)</span>' : '<span class="text-muted">No</span>'}</td>
        <td class="font-mono">${t.routed_latency_ms}ms</td>
        <td class="font-mono">$${t.routed_cost_usd.toFixed(5)}</td>
      `;
      tbody.appendChild(tr);
    });

    const concList = document.getElementById('bm-conclusions');
    if (concList && bm.conclusions) {
      concList.innerHTML = bm.conclusions.map(c => `<li>${escapeHtml(c)}</li>`).join('');
    }
  } catch (e) {}
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
