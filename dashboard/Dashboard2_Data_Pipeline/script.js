(function () {
  const DATA = typeof DASHBOARD_DATA !== "undefined" ? DASHBOARD_DATA : {};

  const plotLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#f0f6ff", size: 11 },
    margin: { l: 10, r: 10, t: 10, b: 10 },
    xaxis: { gridcolor: "rgba(45,212,191,0.12)", zerolinecolor: "rgba(45,212,191,0.12)" },
    yaxis: { gridcolor: "rgba(45,212,191,0.12)", zerolinecolor: "rgba(45,212,191,0.12)" },
  };

  const pieLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#e8f1fb", size: 11 },
    margin: { l: 0, r: 0, t: 0, b: 0 },
    showlegend: true,
    legend: {
      orientation: "v",
      x: 1,
      xanchor: "left",
      y: 0.5,
      yanchor: "middle",
    },
  };

  function renderMeta() {
    document.getElementById("meta-generated").textContent = DATA.generated_at || "—";
    document.getElementById("meta-dataset").textContent = DATA.dataset_name || "—";
    document.getElementById("meta-source").textContent = DATA.source_file || "—";
    const qs = DATA.quality_summary || {};
    const statusEl = document.getElementById("meta-status");
    const fails = qs.checks_failed || 0;
    statusEl.innerHTML =
      `<span class="status-dot" style="background:${fails ? "#f87171" : "#34d399"}"></span> ` +
      (fails ? `${fails} check(s) failed` : "All checks passed");
    statusEl.style.color = fails ? "#f87171" : "#34d399";
  }

  function renderValidationCards() {
    const cards = DATA.validation_cards || [];
    const pass = cards.filter(c => c.status === "pass").length;
    document.getElementById("validation-summary").textContent =
      `${pass} / ${cards.length} checks passed`;
    document.getElementById("validation-cards").innerHTML = cards.map(c => `
      <article class="val-card ${c.status}">
        <div class="val-status">${c.status}</div>
        <div class="val-title">${c.title}</div>
        <div class="val-headline">${c.headline}</div>
        <div class="val-detail">${c.detail}</div>
      </article>`).join("");
  }

  function renderKPIs() {
    const m = DATA.metrics || {};
    const dr = m.date_range || {};
    const rangeText = dr.min && dr.max ? `${dr.min} → ${dr.max}` : "N/A";
    document.getElementById("kpi-row").innerHTML = `
      <div class="kpi"><div class="kpi-label">Total Records</div><div class="kpi-value">${(m.total_records||0).toLocaleString()}</div><div class="kpi-foot">Integrated incidents</div></div>
      <div class="kpi"><div class="kpi-label">Unique IDs</div><div class="kpi-value">${(m.unique_incidents||0).toLocaleString()}</div><div class="kpi-foot">Incident_ID count</div></div>
      <div class="kpi"><div class="kpi-label">Source Types</div><div class="kpi-value">${m.source_types||0}</div><div class="kpi-foot">${m.event_types||0} event types</div></div>
      <div class="kpi"><div class="kpi-label">Mean Confidence</div><div class="kpi-value">${(m.avg_confidence||0).toFixed(2)}</div><div class="kpi-foot">Median ${(m.median_confidence||0).toFixed(2)}</div></div>
      <div class="kpi"><div class="kpi-label">Parseable Dates</div><div class="kpi-value">${(m.parseable_dates||0).toLocaleString()}</div><div class="kpi-foot">Of ${(m.total_records||0).toLocaleString()} total</div></div>
      <div class="kpi"><div class="kpi-label">Date Range</div><div class="kpi-value" style="font-size:16px">${rangeText}</div><div class="kpi-foot">From parseable Date_Time</div></div>`;
  }

  function renderSources() {
    const si = DATA.source_integration || {};
    const total = (si.values || []).reduce((a, b) => a + b, 0);
    document.getElementById("source-total").textContent = `${total.toLocaleString()} records`;
    Plotly.newPlot("chart-sources", [{
      type: "bar",
      x: si.labels || [],
      y: si.values || [],
      marker: { color: si.colors || "#14b8a6" },
    }], { ...plotLayout, margin: { l: 40, r: 10, t: 10, b: 60 } }, { responsive: true, displayModeBar: false });
  }

  function renderSchema() {
    const sch = DATA.schema || {};
    const rows = (sch.required_columns || []).map(col => {
      const present = sch.column_types && sch.column_types[col] !== "missing";
      const dtype = (sch.column_types || {})[col] || "—";
      return `<tr><td>${col}</td><td>${present ? '<span class="pill-ok">Present</span>' : '<span class="pill-fail">Missing</span>'}</td><td>${dtype}</td></tr>`;
    }).join("");
    document.getElementById("schema-table").innerHTML =
      `<table><thead><tr><th>Column</th><th>Status</th><th>Type</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderMissing() {
    const rows = (DATA.missing_values || []).map(r => {
      const cls = r.total_issues === 0 ? "pill-ok" : r.total_issues < 50 ? "pill-warn" : "pill-fail";
      return `<tr><td>${r.column}</td><td>${r.missing}</td><td>${r.blank}</td><td class="${cls}">${r.total_issues}</td><td>${r.pct_clean}%</td></tr>`;
    }).join("");
    document.getElementById("missing-table").innerHTML =
      `<table><thead><tr><th>Column</th><th>Null</th><th>Blank</th><th>Issues</th><th>% Clean</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderDuplicates() {
    const m = DATA.metrics || {};
    const dup = m.duplicate_ids || 0;
    if (dup === 0) {
      document.getElementById("duplicate-panel").innerHTML = `
        <div class="dup-ok">
          <div class="dup-icon">✓</div>
          <div class="dup-msg">No Duplicates Found</div>
          <div class="dup-sub">${(m.unique_incidents||0).toLocaleString()} unique Incident_ID values across ${(m.total_records||0).toLocaleString()} records</div>
        </div>`;
    } else {
      document.getElementById("duplicate-panel").innerHTML = `
        <div class="dup-ok">
          <div class="dup-icon" style="color:#f87171">✗</div>
          <div class="dup-msg" style="color:#f87171">${dup.toLocaleString()} Duplicate IDs</div>
          <div class="dup-sub">Primary key integrity compromised</div>
        </div>`;
    }
  }

  function renderConfStats() {
    const s = (DATA.confidence || {}).stats || {};
    const bySrc = (DATA.confidence || {}).by_source || {};
    const srcRows = Object.entries(bySrc).map(([k, v]) =>
      `<div class="stage-item"><span>${k}</span><span class="stage-count">${v.toFixed(3)}</span></div>`
    ).join("");
    document.getElementById("conf-stats").innerHTML = `
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-label">Mean</div><div class="stat-value">${(s.mean||0).toFixed(3)}</div></div>
        <div class="stat-item"><div class="stat-label">Median</div><div class="stat-value">${(s.median||0).toFixed(3)}</div></div>
        <div class="stat-item"><div class="stat-label">Std Dev</div><div class="stat-value">${(s.std||0).toFixed(3)}</div></div>
        <div class="stat-item"><div class="stat-label">Min</div><div class="stat-value">${(s.min||0).toFixed(3)}</div></div>
        <div class="stat-item"><div class="stat-label">Max</div><div class="stat-value">${(s.max||0).toFixed(3)}</div></div>
        <div class="stat-item"><div class="stat-label">IQR</div><div class="stat-value">${(s.q25||0).toFixed(2)}–${(s.q75||0).toFixed(2)}</div></div>
      </div>
      <div style="margin-top:14px"><div class="stat-label" style="margin-bottom:6px">Mean by Source</div>${srcRows}</div>`;
  }

  function renderConfChart() {
    const h = (DATA.confidence || {}).histogram || {};
    Plotly.newPlot("chart-confidence", [{
      type: "bar",
      x: h.labels || [],
      y: h.values || [],
      marker: {
        color: (h.values || []).map((_, i) =>
          ["#14b8a6","#2dd4bf","#22d3ee","#818cf8","#a78bfa","#f472b6","#fb923c","#fbbf24","#6ee7b7","#34d399"][i % 10]
        ),
      },
    }], { ...plotLayout, margin: { l: 40, r: 10, t: 10, b: 50 } }, { responsive: true, displayModeBar: false });
  }

  function renderSeverity() {
    const sev = DATA.severity || {};
    Plotly.newPlot("chart-severity", [{
      type: "pie",
      labels: sev.labels || [],
      values: sev.values || [],
      marker: { colors: sev.colors || [] },
      textinfo: "label+percent",
      hole: 0.4,
      domain: { x: [0, 0.72], y: [0.02, 0.98] },
    }], { ...pieLayout, height: 272 }, { responsive: true, displayModeBar: false });

    const criticalTypes = sev.critical_event_types || [];
    const criticalBlock = criticalTypes.length
      ? `<div class="rule-box"><strong>Critical Event_Type set (${criticalTypes.length} types):</strong><br/>${criticalTypes.join(", ")}</div>`
      : "";
    document.getElementById("severity-rules").innerHTML = `
      <div class="rule-box"><strong>Derivation rule:</strong> ${sev.rule || ""}</div>
      ${criticalBlock}
      <div class="rule-box"><strong>Actionable logic:</strong> ${sev.actionable_rule || ""}</div>
      <div class="rule-box"><strong>Non-actionable Event_Type labels (${(DATA.non_actionable||[]).length}):</strong><br/>${(DATA.non_actionable||[]).join(", ")}</div>`;
  }

  function renderPrefixVerification() {
    const p = DATA.id_prefix || {};
    const statusClass = p.status === "Met" ? "prefix-status-met"
      : p.status === "Warning" ? "prefix-status-warn" : "prefix-status-fail";
    document.getElementById("prefix-status-label").innerHTML =
      `<span class="${statusClass}">${p.status || "—"}</span>`;

    const rows = (p.prefix_counts || []).map(r => {
      const cls = r.count === 0 ? "" : (r.expected ? "pill-ok" : "pill-warn");
      const tag = r.expected ? "Expected" : "Other";
      return `<tr>
        <td>${r.prefix}</td>
        <td>${tag}</td>
        <td class="${cls}">${(r.count || 0).toLocaleString()}</td>
      </tr>`;
    }).join("");

    const warning = p.warning_message
      ? `<div class="prefix-warning"><strong>Warning:</strong> ${p.warning_message}</div>`
      : "";

    document.getElementById("prefix-verification").innerHTML = `
      ${warning}
      <div class="prefix-summary">
        <div class="prefix-stat">
          <div class="prefix-stat-label">Expected Prefix Format</div>
          <div class="prefix-stat-value">${p.expected_format || "—"}</div>
        </div>
        <div class="prefix-stat">
          <div class="prefix-stat-label">Actual Prefix(es) Found</div>
          <div class="prefix-stat-value">${(p.actual_prefixes || []).join(", ") || "—"}</div>
        </div>
        <div class="prefix-stat">
          <div class="prefix-stat-label">Status</div>
          <div class="prefix-stat-value ${statusClass}">${p.status || "—"}</div>
        </div>
        <div class="prefix-stat">
          <div class="prefix-stat-label">Unique Incident_IDs</div>
          <div class="prefix-stat-value">${(p.unique_ids || 0).toLocaleString()} / ${(p.total_records || 0).toLocaleString()}</div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Prefix</th><th>Category</th><th>Record Count</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function renderPipeline() {
    const stages = DATA.pipeline_stages || [];
    document.getElementById("pipeline-diagram").innerHTML =
      `<div class="pipeline-flow">${stages.map(st => `
        <div class="pipeline-stage">
          <div class="stage-name">${st.stage}</div>
          ${(st.items||[]).map(it => `
            <div class="stage-item"><span>${it.label}</span><span class="stage-count">${it.count.toLocaleString()}</span></div>
          `).join("")}
        </div>`).join("")}</div>`;
  }

  function renderQuality() {
    const q = DATA.quality_summary || {};
    document.getElementById("quality-grade").textContent = `Grade ${q.grade || "—"}`;
    document.getElementById("quality-summary").innerHTML = `
      <div class="quality-score">
        <div class="quality-big">${q.overall_score || 0}%</div>
        <div class="quality-grade">${q.grade || "—"}</div>
        <div class="quality-text">${q.summary_text || ""}</div>
      </div>
      <div class="quality-breakdown">
        <span class="qb-item pass">${q.checks_passed || 0} Passed</span>
        <span class="qb-item warn">${q.checks_warn || 0} Warnings</span>
        <span class="qb-item fail">${q.checks_failed || 0} Failed</span>
        <span class="qb-item">${q.total_checks || 0} Total Checks</span>
      </div>`;
  }

  function init() {
    renderMeta();
    renderValidationCards();
    renderKPIs();
    renderSources();
    renderSchema();
    renderMissing();
    renderDuplicates();
    renderPrefixVerification();
    renderConfStats();
    renderConfChart();
    renderSeverity();
    renderPipeline();
    renderQuality();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
