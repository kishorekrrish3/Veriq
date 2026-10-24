/**
 * VERIQ — Verification Engine Client
 * Aesthetic: Industrial Precision Instrument
 */

let activeRunId = null;
let eventSource = null;
let currentClaimsData = [];
let currentFilter = 'ALL';
let currentDiffText = '';
let runTimerInterval = null;
let runStartTime = null;

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initForms();
  initFilters();
  initActionButtons();
  initPresets();
  loadOverviewMetrics();
  loadRecentRuns();
  checkProviderStatus();
  loadBenchmarks();
});

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const pill = document.createElement('div');
  pill.className = `toast-pill ${type === 'success' ? 'success' : type === 'error' ? 'error' : ''}`;
  pill.textContent = message;
  container.appendChild(pill);
  setTimeout(() => {
    pill.style.opacity = '0';
    pill.style.transition = 'opacity 200ms ease';
    setTimeout(() => pill.remove(), 200);
  }, 3500);
}

// Navigation & Tab Switching
function initNavigation() {
  const tabs = document.querySelectorAll('.deck-tab[data-tab]');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      if (targetId) switchTab(targetId);
    });
  });

  const quickNewRun = document.getElementById('btn-quick-new-run');
  if (quickNewRun) {
    quickNewRun.addEventListener('click', () => switchTab('new-run'));
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.deck-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

  const activeTab = document.querySelector(`.deck-tab[data-tab="${tabId}"]`);
  if (activeTab) activeTab.classList.add('active');

  const targetSection = document.getElementById(`tab-${tabId}`);
  if (targetSection) targetSection.classList.add('active');

  if (tabId === 'history') loadHistoryRuns();
  if (tabId === 'overview') {
    loadOverviewMetrics();
    loadRecentRuns();
  }
  if (tabId === 'benchmarks') loadBenchmarks();
  if (tabId === 'ledger') loadStandaloneLedger();
}

// Presets
function initPresets() {
  const presets = {
    'std-dev': {
      title: 'Add Standard Deviation Calculation with Boundary Safeguards',
      desc: 'Implement standard_deviation(numbers) calculating population standard deviation. Ensure empty list raises ValueError. Preserve all existing mathematical and regression assertions without breaking existing tests.',
      repairs: 1,
    },
    'div-zero': {
      title: 'Add Safe Division with ZeroDivisionError Safeguards',
      desc: 'Implement divide(a, b) with strict float precision. When b == 0, raise ZeroDivisionError with explicit error message "Division by zero is undefined". Ensure negative dividend handling.',
      repairs: 1,
    },
    'factorial': {
      title: 'Enforce Factorial Negative Input Validation',
      desc: 'Update factorial(n) in calculator.py to raise ValueError when n < 0. Ensure 0! returns 1 and positive integers compute accurate factorials.',
      repairs: 2,
    }
  };

  document.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const key = chip.dataset.preset;
      const data = presets[key];
      if (data) {
        document.getElementById('run-title').value = data.title;
        document.getElementById('run-desc').value = data.desc;
        document.getElementById('run-repairs').value = data.repairs;
        showToast(`Loaded preset: ${chip.textContent.trim()}`, 'info');
      }
    });
  });
}

// Form Submission
function initForms() {
  const form = document.getElementById('new-run-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-submit-run');
    btn.disabled = true;
    btn.textContent = 'Launching run...';

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
      showToast(`Run ${run.run_id} initiated`, 'success');
      btn.disabled = false;
      btn.textContent = 'Launch verification run';
      openRunWorkspace(run.run_id);
    } catch (err) {
      showToast(err.message, 'error');
      btn.disabled = false;
      btn.textContent = 'Launch verification run';
    }
  });
}

// Open Workspace
async function openRunWorkspace(runId) {
  activeRunId = runId;
  switchTab('workspace');

  const navPill = document.getElementById('nav-active-pill');
  if (navPill) {
    navPill.textContent = 'ACTIVE';
    navPill.style.color = '#38BDF8';
  }

  document.getElementById('active-run-id').textContent = runId;
  document.getElementById('active-run-title').textContent = 'Loading task specification...';
  document.getElementById('timeline-container').innerHTML = '<div style="color:var(--ink-dim); text-align:center; padding:24px;">Connecting to event stream...</div>';
  document.getElementById('diff-code-block').innerHTML = '<code>Waiting for candidate patch...</code>';
  document.getElementById('routing-decisions-container').innerHTML = '<div style="color:var(--ink-dim);">Awaiting model selection...</div>';
  document.getElementById('workspace-ledger-claims').innerHTML = '<div style="color:var(--ink-dim);">Registering claims...</div>';

  startLiveTimer();
  await fetchAndDisplayRun(runId);
  subscribeToRunEvents(runId);
}

function startLiveTimer() {
  clearInterval(runTimerInterval);
  runStartTime = Date.now();
  runTimerInterval = setInterval(() => {
    const durEl = document.getElementById('active-run-dur');
    if (durEl) {
      const elapsed = ((Date.now() - runStartTime) / 1000).toFixed(1);
      durEl.textContent = `${elapsed}s`;
    }
  }, 100);
}

function stopLiveTimer() {
  clearInterval(runTimerInterval);
}

// Server-Sent Events (SSE)
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
    if (eventSource) {
      eventSource.close();
    }
  };
}

function appendTimelineEvent(ev) {
  const container = document.getElementById('timeline-container');
  const entry = document.createElement('div');
  entry.className = 'event-entry';

  const isError = ev.event_type.includes('FAIL') || ev.event_type.includes('ERROR');
  const isSuccess = ev.event_type.includes('COMPLETE') || ev.event_type.includes('VALIDATED');

  entry.innerHTML = `
    <div class="event-marker ${isError ? 'error' : isSuccess ? 'success' : ''}"></div>
    <div class="event-body">
      <div class="event-header">${new Date(ev.timestamp).toLocaleTimeString()} · ${ev.event_type}</div>
      <div class="event-title">${escapeHtml(ev.message)}</div>
    </div>
  `;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;

  const countEl = document.getElementById('active-event-count');
  if (countEl) {
    const total = container.querySelectorAll('.event-entry').length;
    countEl.textContent = `${total} events recorded`;
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
    stopLiveTimer();
    fetchAndDisplayRun(activeRunId);
    loadOverviewMetrics();
    const navPill = document.getElementById('nav-active-pill');
    if (navPill) {
      navPill.textContent = ev.event_type === 'RUN_COMPLETED' ? 'DONE' : 'FAILED';
      navPill.style.color = ev.event_type === 'RUN_COMPLETED' ? 'var(--truth-verified-ink)' : 'var(--truth-failed-ink)';
    }
  }
}

// Fetch Run Details
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
    statusBadge.className = `status-tag ${
      run.status === 'COMPLETED' ? 'status-tag-verified' : 
      run.status === 'FAILED' ? 'status-tag-failed' : 'status-tag-supported'
    }`;

    if (run.status === 'COMPLETED' || run.status === 'FAILED') {
      stopLiveTimer();
    }

    if (run.unified_diff) {
      currentDiffText = run.unified_diff;
      renderDiff(run.unified_diff);
    }

    if (run.routing_history && run.routing_history.length > 0) {
      const container = document.getElementById('routing-decisions-container');
      container.innerHTML = '';
      run.routing_history.forEach(renderRoutingDecision);
    }

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
      currentDiffText = diffText;
      renderDiff(diffText);
    }
  } catch (e) {}
}

// Unified Diff Viewer with Line Numbers
function renderDiff(diffText) {
  const codeBlock = document.getElementById('diff-code-block');
  if (!codeBlock) return;
  if (!diffText || diffText.trim() === '' || diffText.includes('No modifications applied')) {
    codeBlock.innerHTML = '<code>No modifications applied yet.</code>';
    return;
  }

  const lines = diffText.split('\n');
  let lineNum = 1;
  const rows = lines.map(line => {
    const safeLine = escapeHtml(line);
    let rowClass = '';
    let isCode = true;

    if (line.startsWith('+') && !line.startsWith('+++')) {
      rowClass = 'diff-row-add';
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      rowClass = 'diff-row-del';
    } else if (line.startsWith('@@')) {
      rowClass = 'diff-row-hunk';
      isCode = false;
    }

    const numStr = isCode ? lineNum++ : '··';
    return `<div class="diff-row ${rowClass}"><span class="diff-num">${numStr}</span><span class="diff-text">${safeLine}</span></div>`;
  });

  codeBlock.innerHTML = rows.join('');
}

function renderRoutingDecision(decision) {
  const container = document.getElementById('routing-decisions-container');
  if (container.querySelector('div') && container.innerText.includes('No routing')) {
    container.innerHTML = '';
  }

  const card = document.createElement('div');
  card.style.cssText = 'background:var(--surface-terminal); border:1px solid var(--rule-subtle); padding:10px 14px; border-radius:4px; margin-bottom:8px;';

  const tierTag = decision.tier === 'FAST' ? 'status-tag-supported' : decision.tier === 'STANDARD' ? 'status-tag-verified' : 'status-tag-failed';

  card.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <span class="status-tag ${tierTag}">${decision.tier} tier</span>
      <span style="font-family:var(--font-mono); font-size:11px; color:var(--ink-dim);">Attempt #${decision.attempt}</span>
    </div>
    <div style="font-family:var(--font-mono); font-size:12px; font-weight:600; color:var(--ink-primary);">${decision.model_id}</div>
    <div style="font-size:12px; color:var(--ink-muted); margin:4px 0;">${escapeHtml(decision.reason)}</div>
    <div style="font-family:var(--font-mono); font-size:11px; color:var(--ink-dim); display:flex; gap:16px; margin-top:6px; border-top:1px solid var(--rule-subtle); padding-top:4px;">
      <span>Latency: ${decision.latency_ms || 0}ms</span>
      <span>Tokens: ${decision.total_tokens || 0}</span>
      <span>Cost: $${(decision.estimated_cost_usd || 0).toFixed(5)}</span>
    </div>
  `;
  container.appendChild(card);
}

// Verification Ledger
async function fetchRunLedger(runId) {
  try {
    const resp = await fetch(`/api/runs/${runId}/ledger`);
    if (!resp.ok) return;
    const ledger = await resp.json();
    currentClaimsData = ledger.claims || [];

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
  document.querySelectorAll('.filter-bar').forEach(group => {
    group.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;

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
    container.innerHTML = '<div style="color:var(--ink-dim); font-size:12px; padding:16px;">No claims match the filter.</div>';
    return;
  }

  container.innerHTML = '';
  claims.forEach(claim => {
    const card = document.createElement('div');
    card.className = 'claim-panel';

    const statusTag = `status-tag-${claim.status.toLowerCase()}`;
    const backingEv = evidenceList.filter(e => (claim.evidence_ids || []).includes(e.evidence_id));

    let evHtml = '';
    backingEv.forEach(ev => {
      evHtml += `
        <div class="evidence-terminal">
          <div class="evidence-meta-row">
            <span>[${escapeHtml(ev.evidence_id)}] Check: ${escapeHtml(ev.check_type)}</span>
            <span class="status-tag status-tag-${ev.status.toLowerCase()}">${ev.status}</span>
          </div>
          ${ev.command ? `<div style="margin-bottom:4px;"><strong>Command:</strong> <code>${escapeHtml(ev.command)}</code></div>` : ''}
          ${ev.exit_code !== null ? `<div style="margin-bottom:4px;"><strong>Exit code:</strong> ${ev.exit_code} · <strong>Duration:</strong> ${ev.duration_ms}ms · <strong>Sandbox:</strong> ${escapeHtml(ev.sandbox_type || 'CONTAINER')}</div>` : ''}
          ${ev.stdout ? `<div style="margin-top:6px;"><strong>Stdout:</strong> <pre style="white-space:pre-wrap; background:rgba(0,0,0,0.5); padding:6px; border-radius:3px; max-height:140px; overflow-y:auto; color:var(--ink-secondary);">${escapeHtml(ev.stdout)}</pre></div>` : ''}
          ${ev.stderr ? `<div style="margin-top:6px; color:var(--truth-failed-ink);"><strong>Stderr:</strong> <pre style="white-space:pre-wrap; background:rgba(220,38,38,0.1); padding:6px; border-radius:3px; max-height:140px; overflow-y:auto;">${escapeHtml(ev.stderr)}</pre></div>` : ''}
        </div>
      `;
    });

    let limitationsHtml = '';
    if (claim.limitations && claim.limitations.length > 0) {
      limitationsHtml = `
        <div style="margin-top:8px;">
          <strong style="font-size:11px; color:var(--ink-muted); text-transform:uppercase;">Explicit limitations:</strong>
          <ul style="margin-left:18px; color:var(--ink-secondary); margin-top:2px; font-size:12px;">
            ${claim.limitations.map(l => `<li><em>${escapeHtml(l)}</em></li>`).join('')}
          </ul>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="claim-top">
        <div class="claim-title-bar">
          <span class="claim-code">${claim.claim_id}</span>
          <span class="claim-name">${escapeHtml(claim.title)}</span>
          <span class="claim-category-tag">${claim.category}</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="status-tag ${statusTag}">${claim.status}</span>
          <span style="font-size:11px; color:var(--ink-dim);">▼</span>
        </div>
      </div>
      <div class="claim-desc">${escapeHtml(claim.description)}</div>
      <div class="claim-expanded-area">
        ${limitationsHtml}
        <div style="margin-top:10px;">
          <strong style="font-size:11px; color:var(--ink-muted); text-transform:uppercase;">Deterministic evidence records (${backingEv.length}):</strong>
          ${evHtml || '<div style="color:var(--ink-dim); font-size:11px; margin-top:4px;">No concrete evidence records attached.</div>'}
        </div>
      </div>
    `;

    card.addEventListener('click', () => {
      card.classList.toggle('open');
    });

    container.appendChild(card);
  });
}

// Action Buttons
function initActionButtons() {
  document.getElementById('btn-download-report-md')?.addEventListener('click', () => {
    if (!activeRunId) return showToast('No active run selected', 'error');
    window.open(`/api/runs/${activeRunId}/report?format=markdown`, '_blank');
  });

  document.getElementById('btn-download-report-json')?.addEventListener('click', () => {
    if (!activeRunId) return showToast('No active run selected', 'error');
    window.open(`/api/runs/${activeRunId}/report?format=json`, '_blank');
  });

  document.getElementById('btn-copy-diff')?.addEventListener('click', () => {
    if (!currentDiffText || currentDiffText.trim() === '') {
      return showToast('No patch generated to copy', 'error');
    }
    navigator.clipboard.writeText(currentDiffText).then(() => {
      showToast('Unified diff copied to clipboard', 'success');
    }).catch(() => {
      showToast('Failed to copy to clipboard', 'error');
    });
  });

  document.getElementById('btn-refresh-runs')?.addEventListener('click', () => {
    loadOverviewMetrics();
    loadRecentRuns();
    showToast('Overview telemetry refreshed', 'info');
  });

  document.getElementById('btn-run-benchmark')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-benchmark');
    btn.disabled = true;
    btn.textContent = 'Executing benchmark suite...';
    try {
      const resp = await fetch('/api/benchmarks/run', { method: 'POST' });
      if (resp.ok) {
        showToast('Benchmark suite executed successfully', 'success');
        loadBenchmarks();
      }
    } catch (e) {
      showToast('Benchmark execution failed', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Re-run benchmark harness';
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
  } catch (e) {}
}

// Load Recent Runs
async function loadRecentRuns() {
  try {
    const resp = await fetch('/api/runs?limit=10');
    if (!resp.ok) return;
    const runs = await resp.json();

    const tbody = document.getElementById('overview-runs-body');
    if (!runs || runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--ink-dim); padding:24px;">No runs recorded. Start a new run to begin.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    runs.forEach(r => {
      const tr = document.createElement('tr');
      const vClaims = r.ledger_summary ? `${r.ledger_summary.verified_count}/${r.ledger_summary.total_claims}` : '0/0';
      const statusTag = `status-tag-${r.status.toLowerCase()}`;
      tr.innerHTML = `
        <td><code style="color:#93C5FD;">${r.run_id}</code></td>
        <td>${escapeHtml(r.task_title)}</td>
        <td><span class="status-tag ${statusTag}">${r.status}</span></td>
        <td><span style="font-family:var(--font-mono); font-size:11px; color:var(--ink-dim);">${r.execution_mode}</span></td>
        <td style="font-family:var(--font-mono); color:var(--truth-verified-ink);">${vClaims}</td>
        <td style="font-family:var(--font-mono);">${r.duration_seconds}s</td>
        <td style="color:var(--ink-dim);">${new Date(r.created_at).toLocaleTimeString()}</td>
        <td>
          <button class="btn btn-default btn-sm btn-inspect" data-run-id="${r.run_id}">Inspect</button>
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
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--ink-dim); padding:24px;">No runs stored in database.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    runs.forEach(r => {
      const tr = document.createElement('tr');
      const vClaims = r.ledger_summary ? `${r.ledger_summary.verified_count}/${r.ledger_summary.total_claims}` : '0/0';
      const statusTag = `status-tag-${r.status.toLowerCase()}`;
      tr.innerHTML = `
        <td><code style="color:#93C5FD;">${r.run_id}</code></td>
        <td>${escapeHtml(r.task_title)}</td>
        <td><span class="status-tag ${statusTag}">${r.status}</span></td>
        <td><span style="font-family:var(--font-mono); font-size:11px; color:var(--ink-dim);">${r.execution_mode}</span></td>
        <td style="font-family:var(--font-mono); color:var(--truth-verified-ink);">${vClaims}</td>
        <td style="font-family:var(--font-mono);">${r.duration_seconds}s</td>
        <td style="color:var(--ink-dim);">${r.completed_at ? new Date(r.completed_at).toLocaleTimeString() : 'Active'}</td>
        <td>
          <button class="btn btn-default btn-sm btn-inspect-hist" data-run-id="${r.run_id}">Inspect</button>
        </td>
      `;
      tr.querySelector('.btn-inspect-hist').addEventListener('click', () => openRunWorkspace(r.run_id));
      tbody.appendChild(tr);
    });
  } catch (e) {}
}

// Standalone Ledger
async function loadStandaloneLedger() {
  if (activeRunId) {
    fetchRunLedger(activeRunId);
  } else {
    try {
      const resp = await fetch('/api/runs?limit=1');
      if (resp.ok) {
        const runs = await resp.json();
        if (runs.length > 0) {
          const runId = runs[0].run_id;
          const ledgerResp = await fetch(`/api/runs/${runId}/ledger`);
          if (ledgerResp.ok) {
            const ledger = await ledgerResp.json();
            currentClaimsData = ledger.claims || [];
            renderLedgerClaims(currentClaimsData, 'standalone-ledger-claims', ledger.evidence || []);
          }
        }
      }
    } catch (e) {}
  }
}

// Provider & Infrastructure Status
async function checkProviderStatus() {
  try {
    const healthResp = await fetch('/api/health');
    if (healthResp.ok) {
      const hData = await healthResp.json();
      const deckText = document.getElementById('deck-status-text');
      if (deckText) {
        deckText.textContent = hData.modes.live_inference_configured ? 'Live inference' : 'Recorded replay';
      }

      const sbBadge = document.getElementById('settings-sandbox-badge');
      const sbDesc = document.getElementById('settings-sandbox-desc');
      const overviewTag = document.getElementById('overview-sandbox-tag');

      if (hData.sandbox.docker_available) {
        if (sbBadge) {
          sbBadge.textContent = 'HARDENED CONTAINER';
          sbBadge.className = 'status-tag status-tag-verified';
        }
        if (sbDesc) sbDesc.textContent = 'Docker engine connected; tests run in isolated container.';
        if (overviewTag) overviewTag.textContent = 'Docker Container';
      } else {
        if (sbBadge) {
          sbBadge.textContent = 'PROCESS FALLBACK';
          sbBadge.className = 'status-tag status-tag-unresolved';
        }
        if (sbDesc) sbDesc.textContent = 'Process sandbox fallback active.';
        if (overviewTag) overviewTag.textContent = 'Process Sandbox';
      }
    }

    const provResp = await fetch('/api/providers/status');
    if (provResp.ok) {
      const pData = await provResp.json();
      const nBadge = document.getElementById('settings-nebius-badge');
      if (nBadge) {
        if (pData.nebius.status === 'healthy') {
          nBadge.textContent = 'CONNECTED';
          nBadge.className = 'status-tag status-tag-verified';
        } else {
          nBadge.textContent = 'UNCONFIGURED';
          nBadge.className = 'status-tag status-tag-notrun';
        }
      }

      const tBadge = document.getElementById('settings-tavily-badge');
      if (tBadge) {
        if (pData.tavily.status === 'healthy') {
          tBadge.textContent = 'CONNECTED';
          tBadge.className = 'status-tag status-tag-verified';
        } else {
          tBadge.textContent = 'UNCONFIGURED';
          tBadge.className = 'status-tag status-tag-notrun';
        }
      }
    }
  } catch (e) {}
}

// Benchmark Suite Results
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
        <td><code style="color:#93C5FD;">${t.task_id}</code></td>
        <td>${escapeHtml(t.task_name)}</td>
        <td><span class="status-tag ${t.baseline_passed ? 'status-tag-verified' : 'status-tag-failed'}">${t.baseline_passed ? 'PASS' : 'FAIL'}</span></td>
        <td style="font-family:var(--font-mono);">${t.baseline_latency_ms}ms</td>
        <td><span class="status-tag ${t.routed_passed ? 'status-tag-verified' : 'status-tag-failed'}">${t.routed_passed ? 'PASS' : 'FAIL'}</span></td>
        <td><span class="status-tag ${t.routed_tier_used === 'FAST' ? 'status-tag-supported' : 'status-tag-verified'}">${t.routed_tier_used}</span></td>
        <td>${t.repair_triggered ? '<span class="status-tag status-tag-verified">Repaired</span>' : '<span style="color:var(--ink-dim);">No</span>'}</td>
        <td style="font-family:var(--font-mono);">${t.routed_latency_ms}ms</td>
        <td style="font-family:var(--font-mono); color:#93C5FD;">$${t.routed_cost_usd.toFixed(5)}</td>
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
