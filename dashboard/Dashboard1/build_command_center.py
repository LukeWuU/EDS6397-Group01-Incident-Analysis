"""Build Incident Command Center index.html with dataset.csv embedded."""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "index.html"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_dataset import build_data, CSV_PATH

data = build_data()
data_block = "const DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
print(f"Embedding {len(data['records'])} records from {CSV_PATH.name}")

CSS = r"""
    :root {
      --bg: #06080f;
      --surface: #0f1520;
      --surface-2: #151d2e;
      --border: #243044;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #f59e0b;
      --accent-red: #ef4444;
      --ok: #22c55e;
      --critical: #dc2626;
      --high: #ea580c;
      --radius: 8px;
      --gap: 20px;
      --section-gap: 28px;
      --shell-pad: 20px;
      --dashboard-max: 1800px;
      --font: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
      --fs-kpi-value: 60px;
      --fs-kpi-label: 18px;
      --fs-kpi-foot: 18px;
      --fs-body: 19px;
      --fs-ui: 18px;
      --fs-sm: 17px;
      --fs-panel-title: 23px;
      --fs-panel-sub: 14px;
      --fs-chart-tick: 13px;
      --chart-axis: #C7D0D9;
      --chart-subtitle: #8FA3B8;
      --chart-grid: rgba(255,255,255,0.08);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html {
      width: 100%;
      overflow-x: clip;
    }
    body {
      width: 100%;
      max-width: 100%;
      overflow-x: clip;
      font-family: var(--font);
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      min-height: 100dvh;
      line-height: 1.45;
    }
    .shell {
      width: min(100%, var(--dashboard-max));
      max-width: 100%;
      min-width: 0;
      margin: 0 auto;
      padding: 0 var(--shell-pad) 24px;
      overflow-x: clip;
    }

    /* ── Command center header ── */
    .command-header {
      background: linear-gradient(180deg, #0c1929 0%, #0a0e17 100%);
      border-bottom: 3px solid var(--accent-red);
      margin: 0 calc(-1 * var(--shell-pad)) var(--section-gap);
      padding: 22px 28px 18px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.35);
      max-width: calc(100% + (2 * var(--shell-pad)));
    }
    .command-title {
      font-size: 38px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #ffffff;
      line-height: 1.15;
      margin-bottom: 10px;
    }
    .command-sub {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px 24px;
      font-size: 18px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
    }
    .command-sub .status-live {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--ok);
      font-weight: 800;
    }
    .status-dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 8px rgba(34,197,94,0.8);
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.45; }
    }
    .command-clock {
      margin-left: auto;
      font-size: 18px;
      font-weight: 700;
      color: var(--text);
      letter-spacing: 0.04em;
      text-transform: none;
    }

    /* ── KPIs ── */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: var(--gap);
      margin-bottom: var(--section-gap);
    }
    @media (max-width: 1100px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .kpi-row { grid-template-columns: 1fr; } }
    .kpi {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
      border-top: 3px solid var(--accent);
    }
    .kpi.critical { border-top-color: var(--medium, #ca8a04); }
    .kpi.high { border-top-color: var(--high); }
    .kpi.action { border-top-color: var(--ok); }
    .kpi.info { border-top-color: #38bdf8; }
    .kpi-label {
      font-size: var(--fs-kpi-label);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
      font-weight: 800;
    }
    .kpi-value { font-size: var(--fs-kpi-value); font-weight: 800; color: var(--text); line-height: 1.05; }
    .kpi-foot { font-size: var(--fs-kpi-foot); color: var(--muted); margin-top: 4px; font-weight: 600; }

    /* ── Filters toolbar ── */
    .filter-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px 20px;
      margin-bottom: var(--section-gap);
      display: flex;
      flex-wrap: wrap;
      gap: 14px 16px;
      align-items: flex-end;
      min-width: 0;
      max-width: 100%;
    }
    .filter-panel label {
      display: flex;
      flex-direction: column;
      gap: 5px;
      font-size: var(--fs-sm);
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 800;
      min-width: 140px;
      flex: 1 1 140px;
    }
    .filter-panel label.filter-label-urgency {
      min-width: 220px;
      flex: 1 1 220px;
      white-space: nowrap;
    }
    .filter-panel select, .filter-panel input {
      background: var(--surface-2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 9px 11px;
      font-size: 20px;
      font-weight: 600;
      width: 100%;
    }
    .btn-reset {
      background: transparent;
      color: var(--accent);
      border: 1px solid var(--accent);
      border-radius: 6px;
      padding: 9px 16px;
      font-size: var(--fs-sm);
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      cursor: pointer;
      white-space: nowrap;
    }
    .btn-reset:hover { background: rgba(245,158,11,0.1); }
    .btn-clear-all {
      background: rgba(239, 68, 68, 0.12);
      color: #f87171;
      border: 1px solid #ef4444;
      border-radius: 6px;
      padding: 9px 16px;
      font-size: var(--fs-sm);
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      cursor: pointer;
      white-space: nowrap;
    }
    .btn-clear-all:hover { background: rgba(239, 68, 68, 0.22); }
    .filter-count {
      font-size: var(--fs-body);
      color: var(--muted);
      margin-left: auto;
      align-self: center;
      white-space: nowrap;
      font-weight: 700;
    }
    .active-filters {
      width: 100%;
      flex-basis: 100%;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding-top: 4px;
    }
    .active-filters-empty {
      font-size: var(--fs-ui);
      color: var(--muted);
      font-style: italic;
      font-weight: 500;
    }
    .filter-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: var(--fs-sm);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #fbbf24;
      background: rgba(251, 191, 36, 0.1);
      border: 1px solid #fbbf24;
      border-radius: 999px;
      padding: 4px 10px;
      white-space: nowrap;
    }
    .filter-chip-label { opacity: 0.85; }
    .filter-chip-value { color: #fde68a; }
    .filter-chip-clear {
      background: none;
      border: none;
      color: #fbbf24;
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
      padding: 0 2px;
      opacity: 0.85;
    }
    .filter-chip-clear:hover { opacity: 1; }

    /* ── Main grid: priority queue sidebar + charts column ── */
    .main-grid {
      display: grid;
      grid-template-columns: minmax(300px, 320px) minmax(0, 1fr);
      gap: var(--gap);
      margin-bottom: var(--section-gap);
      align-items: stretch;
      min-width: 0;
      width: 100%;
      max-width: 100%;
    }
    .main-grid > .queue-panel,
    .main-grid > .charts-col {
      min-height: 0;
      min-width: 0;
      align-self: stretch;
    }
    @media (max-width: 1180px) {
      .main-grid { grid-template-columns: 1fr; }
      .queue-panel {
        max-height: min(420px, 52vh);
      }
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .panel-head {
      padding: 16px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      background: rgba(255,255,255,0.02);
    }
    .charts-col .panel-head h2 {
      color: #FFFFFF;
      font-weight: 600;
      font-size: 23px;
    }
    .charts-col .panel-subtitle,
    .charts-col .panel-head > span {
      color: var(--chart-subtitle);
      font-size: 13px;
      font-weight: 500;
    }
    .charts-col .panel-head h2 .panel-subtitle {
      display: inline;
      letter-spacing: 0.02em;
      text-transform: none;
    }
    .panel-head h2 {
      font-size: var(--fs-panel-title);
      text-transform: uppercase;
      letter-spacing: 0.7px;
      font-weight: 800;
      color: var(--text);
      line-height: 1.25;
    }
    .panel-title-group {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .panel-subtitle {
      font-size: var(--fs-panel-sub);
      font-weight: 500;
      color: #64748b;
      text-transform: none;
      letter-spacing: 0.02em;
      line-height: 1.2;
    }
    .panel-head span { font-size: var(--fs-ui); color: var(--muted); white-space: nowrap; font-weight: 600; }
    .timeline-head { flex-wrap: wrap; }
    .timeline-head-right {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      margin-left: auto;
    }
    .timeline-selection {
      font-size: var(--fs-sm);
      font-weight: 800;
      color: #fbbf24;
      padding: 4px 10px;
      border: 1px solid #fbbf24;
      border-radius: 6px;
      background: rgba(251, 191, 36, 0.1);
      white-space: nowrap;
    }
    .timeline-selection.hidden { display: none; }
    .btn-clear-timeline {
      background: transparent;
      border: 1px solid #38bdf8;
      color: #38bdf8;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: var(--fs-sm);
      font-weight: 800;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }
    .btn-clear-timeline:hover { background: rgba(56, 189, 248, 0.1); }
    .btn-clear-timeline.hidden { display: none; }
    .panel-head .queue-size-label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: var(--fs-ui);
      color: var(--muted);
      font-weight: 700;
    }
    .panel-head .queue-size-label select {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      font-size: var(--fs-ui);
      font-weight: 700;
      cursor: pointer;
    }
    .panel-head .queue-size-label select:focus {
      outline: none;
      border-color: #38bdf8;
    }
    .panel-body { padding: 16px 18px; }

    .queue-panel {
      display: flex;
      flex-direction: column;
      min-height: 0;
      min-width: 0;
      overflow: hidden;
      align-self: stretch;
    }
    .queue-panel .panel-head {
      flex: 0 0 auto;
      flex-shrink: 0;
      flex-wrap: wrap;
      padding: 14px 14px 12px;
      gap: 8px;
    }
    .queue-panel .panel-head h2 {
      flex: 1 1 100%;
      min-width: 0;
      line-height: 1.2;
    }
    .queue-panel .panel-head .queue-size-label {
      flex: 1 1 100%;
      justify-content: flex-end;
      padding-right: 2px;
    }
    .queue-panel .panel-head .queue-size-label select {
      min-width: 4.75rem;
    }
    .queue-panel .panel-body.queue-list {
      flex: 1 1 0;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      align-content: flex-start;
      min-height: 0;
      max-height: 100%;
      padding: 12px 10px 14px 14px;
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
      scrollbar-width: thin;
      scrollbar-color: rgba(100, 116, 139, 0.55) rgba(15, 21, 32, 0.35);
    }
    .queue-panel .panel-body.queue-list::-webkit-scrollbar {
      width: 7px;
    }
    .queue-panel .panel-body.queue-list::-webkit-scrollbar-track {
      background: rgba(15, 21, 32, 0.4);
      border-radius: 4px;
      margin: 2px 0;
    }
    .queue-panel .panel-body.queue-list::-webkit-scrollbar-thumb {
      background: rgba(100, 116, 139, 0.5);
      border-radius: 4px;
      border: 1px solid rgba(36, 48, 68, 0.6);
    }
    .queue-panel:hover .panel-body.queue-list::-webkit-scrollbar-thumb,
    .queue-panel .panel-body.queue-list:hover::-webkit-scrollbar-thumb {
      background: rgba(148, 163, 184, 0.72);
    }
    .queue-list {
      gap: 0;
    }
    .queue-item {
      border: 1px solid var(--border);
      border-radius: 0;
      padding: 12px 14px;
      background: var(--surface-2);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
      flex-shrink: 0;
    }
    .queue-item:first-child { border-radius: 8px 8px 0 0; }
    .queue-item:last-child { border-radius: 0 0 8px 8px; }
    .queue-item:only-child { border-radius: 8px; }
    .queue-item + .queue-item { margin-top: -1px; }
    .queue-item:hover { border-color: #38bdf8; background: rgba(56,189,248,0.06); }
    .queue-item.selected {
      border-color: #fbbf24;
      background: rgba(251, 191, 36, 0.12);
      box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.45);
    }
    .queue-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .queue-id { font-size: var(--fs-body); font-weight: 800; color: #38bdf8; }
    .badge {
      font-size: var(--fs-sm); font-weight: 800; padding: 2px 8px;
      border-radius: 4px; color: white; text-transform: uppercase;
    }
    .queue-event { font-size: 20px; font-weight: 700; margin-bottom: 2px; line-height: 1.35; }
    .queue-meta { font-size: var(--fs-ui); color: var(--muted); line-height: 1.35; font-weight: 600; }

    /* ── Priority queue hover tooltip (data-driven) ── */
    .queue-tooltip {
      position: fixed;
      z-index: 1000;
      display: none;
      width: min(360px, calc(100% - 32px));
      max-height: min(420px, calc(100vh - 32px));
      overflow: auto;
      padding: 14px 16px;
      border: 1px solid #38bdf8;
      border-radius: 8px;
      background: #0f172a;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(56, 189, 248, 0.15);
      pointer-events: none;
    }
    .queue-tooltip.visible { display: block; }
    .queue-tooltip-title {
      font-size: var(--fs-ui);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #38bdf8;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }
    .queue-tooltip-grid {
      display: grid;
      grid-template-columns: 108px 1fr;
      gap: 6px 12px;
      font-size: var(--fs-ui);
      line-height: 1.4;
    }
    .queue-tooltip-grid dt {
      color: var(--muted);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: var(--fs-sm);
      margin: 0;
    }
    .queue-tooltip-grid dd {
      margin: 0;
      color: var(--text);
      font-weight: 600;
      word-break: break-word;
    }
    .queue-tooltip-summary {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--border);
    }
    .queue-tooltip-summary dt {
      color: var(--muted);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: var(--fs-sm);
      margin-bottom: 6px;
    }
    .queue-tooltip-summary dd {
      margin: 0;
      font-size: var(--fs-ui);
      line-height: 1.5;
      color: #cbd5e1;
      white-space: pre-wrap;
      word-break: break-word;
      font-weight: 500;
    }

    /* ── Investigation table summary tooltip ── */
    .summary-tooltip {
      position: fixed;
      z-index: 1001;
      display: none;
      width: min(420px, calc(100% - 32px));
      max-height: min(320px, calc(100vh - 32px));
      overflow: auto;
      padding: 12px 14px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      background: #0f172a;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
      pointer-events: none;
      font-size: var(--fs-sm);
      line-height: 1.5;
      color: #cbd5e1;
      font-weight: 500;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .summary-tooltip.visible { display: block; }

    /* ── Charts column ── */
    .charts-col {
      display: flex;
      flex-direction: column;
      gap: var(--gap);
      min-width: 0;
      min-height: 0;
      overflow: hidden;
    }
    .chart-trio {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--gap);
    }
    @media (max-width: 900px) {
      .chart-trio { grid-template-columns: 1fr; }
    }
    .chart-box {
      height: 280px;
      width: 100%;
      overflow: hidden;
      position: relative;
    }
    .chart-box.tall { height: 280px; min-height: 280px; max-height: 280px; }
    .charts-col > .chart-trio:last-child {
      flex: 0 0 auto;
      min-height: 0;
    }
    .panel .panel-body.chart-box {
      padding: 8px 12px 12px;
      overflow: hidden;
    }
    .charts-col > .panel,
    .chart-trio > .panel {
      overflow: hidden;
    }

    /* ── Primary investigation table ── */
    .primary-table.panel {
      margin-bottom: var(--section-gap);
      margin-top: 0;
      position: relative;
      z-index: 1;
      clear: both;
    }
    .primary-table .panel-head {
      padding: 14px 18px;
      border-bottom: 2px solid var(--border);
    }
    .primary-table .panel-head h2 {
      font-size: 20px;
      letter-spacing: 0.12em;
      font-weight: 800;
    }
    .table-wrap {
      overflow: auto;
      max-height: clamp(12rem, calc(100dvh - 720px), 45rem);
      min-height: 0;
      max-width: 100%;
    }
    @media (max-width: 1100px) {
      .table-wrap { max-height: 480px; min-height: 0; }
    }
    table { width: 100%; border-collapse: collapse; font-size: var(--fs-body); }
    th {
      position: sticky; top: 0; z-index: 2;
      background: #1e293b;
      color: var(--text);
      text-align: left;
      padding: 12px 14px;
      border-bottom: 2px solid var(--border);
      font-size: var(--fs-sm);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 800;
      white-space: nowrap;
    }
    th.sortable {
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }
    th.sortable:hover { background: #243044; }
    th.sortable.sorted { color: #FFFFFF; }
    .sort-indicator {
      display: inline-block;
      min-width: 12px;
      margin-left: 6px;
      font-size: 11px;
      color: #8FA3B8;
      vertical-align: middle;
    }
    td {
      padding: 11px 14px;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      font-weight: 600;
    }
    tr.table-row:hover td { background: rgba(255, 255, 255, 0.04); }
    tr.selected td {
      background: rgba(251, 191, 36, 0.1);
      border-top: 1px solid rgba(251, 191, 36, 0.3);
      border-bottom: 1px solid rgba(251, 191, 36, 0.3);
    }
    tr[data-id] { cursor: pointer; }
    .conf-cell {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 108px;
    }
    .conf-pct {
      min-width: 40px;
      font-weight: 700;
      font-size: var(--fs-sm);
      color: var(--text);
    }
    .conf-bar {
      flex: 1;
      height: 6px;
      max-width: 72px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 3px;
      overflow: hidden;
    }
    .conf-fill {
      height: 100%;
      background: #8FA3B8;
      border-radius: 3px;
      min-width: 2px;
    }
    .summary-cell {
      max-width: min(480px, 30vw);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .primary-table table {
      table-layout: fixed;
      width: 100%;
      font-size: 15px;
    }
    .primary-table th {
      font-size: 14px;
      padding: 10px 12px;
    }
    .primary-table td {
      padding: 9px 12px;
      font-size: 15px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      vertical-align: top;
    }
    .primary-table th:nth-child(1),
    .primary-table td:nth-child(1) { width: 10%; }
    .primary-table th:nth-child(2),
    .primary-table td:nth-child(2) { width: 7%; }
    .primary-table th:nth-child(3),
    .primary-table td:nth-child(3) { width: 11%; }
    .primary-table th:nth-child(4),
    .primary-table td:nth-child(4) { width: 7%; }
    .primary-table th:nth-child(5),
    .primary-table td:nth-child(5) { width: 11%; }
    .primary-table th:nth-child(6),
    .primary-table td:nth-child(6) { width: 9%; }
    .primary-table th:nth-child(7),
    .primary-table td:nth-child(7) { width: 11%; }
    .primary-table th:nth-child(8),
    .primary-table td:nth-child(8) { width: 34%; }
    .primary-table td.summary-cell {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 14px;
      line-height: 1.35;
    }
    .primary-table .table-wrap {
      overflow-x: auto;
      overflow-y: hidden;
      max-height: none;
      min-height: 0;
    }
    .primary-table .panel-body.table-wrap { padding: 0; }

    .primary-table .table-footer {
      border-top: none;
      border-bottom: 1px solid var(--border);
    }

    /* ── Table pagination footer ── */
    .table-footer {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px 16px;
      padding: 8px 18px 10px;
      border-top: 1px solid var(--border);
      background: rgba(255,255,255,0.02);
    }
    .table-footer-left {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px 16px;
      font-size: var(--fs-body);
      color: var(--muted);
      font-weight: 600;
    }
    .table-range {
      font-size: var(--fs-body);
      color: var(--text);
      font-weight: 700;
      white-space: nowrap;
    }
    .page-size-label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: var(--fs-sm);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      font-weight: 800;
    }
    .page-size-label select {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 6px;
      padding: 6px 10px;
      font-size: var(--fs-body);
      font-weight: 700;
      text-transform: none;
      letter-spacing: 0;
      cursor: pointer;
    }
    .page-size-label select:focus {
      outline: none;
      border-color: #38bdf8;
    }
    .pagination {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px;
    }
    .page-btn {
      min-width: 32px;
      height: 32px;
      padding: 0 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--surface-2);
      color: var(--text);
      font-size: var(--fs-body);
      font-weight: 700;
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s, color 0.15s;
    }
    .page-btn:hover:not(:disabled):not(.active) {
      border-color: #38bdf8;
      background: rgba(56,189,248,0.08);
    }
    .page-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .page-btn.active {
      background: #38bdf8;
      border-color: #38bdf8;
      color: #0a0e17;
      font-weight: 800;
    }
    .page-btn.nav-btn {
      padding: 0 14px;
      font-size: var(--fs-sm);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-weight: 700;
    }
    .page-ellipsis {
      min-width: 28px;
      text-align: center;
      font-size: var(--fs-body);
      color: var(--muted);
      user-select: none;
    }
    @media (max-width: 700px) {
      .table-footer { flex-direction: column; align-items: stretch; }
      .table-footer-left { justify-content: space-between; }
      .pagination { justify-content: center; }
    }

    /* ── Responsive containment (no visual redesign at desktop widths) ── */
    .kpi-row,
    .main-grid,
    .charts-col,
    .chart-trio,
    .panel,
    .queue-panel,
    .primary-table.panel,
    .filter-panel {
      min-width: 0;
      max-width: 100%;
    }
    .panel-head,
    .timeline-head-right,
    .command-sub,
    .active-filters,
    .filter-count,
    .table-footer,
    .pagination {
      min-width: 0;
      max-width: 100%;
    }
    .command-title {
      overflow-wrap: anywhere;
    }
    #timeline-note {
      white-space: normal;
      max-width: min(100%, 42rem);
      line-height: 1.35;
    }
    .chart-box .js-plotly-plot,
    .chart-box .plot-container {
      max-width: 100%;
    }
    #chart-high-priority-locations .barlayer path,
    #chart-hotspots .barlayer path,
    #chart-high-priority-events .barlayer path {
      cursor: pointer !important;
    }
    #chart-severity-donut .slice path {
      cursor: pointer !important;
    }
    #chart-severity-donut .slicetext {
      font-weight: 700 !important;
    }

    @media (max-width: 900px) {
      :root { --shell-pad: 14px; }
    }
    @media (max-width: 600px) {
      :root {
        --shell-pad: 10px;
        --section-gap: 16px;
      }
    }
"""

HTML_BODY = """
  <div class="shell">
    <header class="command-header">
      <div class="command-title">National Incident Command Center</div>
      <div class="command-sub">
        <span class="status-live"><span class="status-dot"></span> LIVE OPERATIONS</span>
        <span id="header-records">1,252 incidents monitored</span>
        <span class="command-clock" id="live-clock">—</span>
      </div>
    </header>

    <section class="kpi-row" id="kpi-row"></section>

    <section class="filter-panel">
      <label>Source Type
        <select id="f-source"><option value="">All Sources</option></select>
      </label>
      <label class="filter-label-urgency">Urgency
        <select id="f-urgency-class">
          <option value="">All</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </label>
      <label>Event Type
        <select id="f-event"><option value="">All Events</option></select>
      </label>
      <label>Severity
        <select id="f-severity"><option value="">All Severities</option></select>
      </label>
      <label>Location
        <select id="f-location"><option value="">All Locations</option></select>
      </label>
      <button class="btn-reset" id="btn-reset" type="button">Reset Filters</button>
      <button class="btn-clear-all" id="btn-clear-all" type="button">Clear All Filters</button>
      <div class="filter-count" id="filter-count"></div>
      <div class="active-filters" id="active-filters"></div>
    </section>

    <section class="panel primary-table">
      <div class="panel-head">
        <h2>Incident Investigation Table</h2>
        <span id="table-count"></span>
      </div>
      <div class="table-footer">
        <div class="table-footer-left">
          <span class="table-range" id="table-range">Showing 0 of 0 incidents.</span>
          <label class="page-size-label" for="page-size">
            Rows per page
            <select id="page-size" aria-label="Rows per page">
              <option value="5" selected>5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
        </div>
        <nav class="pagination" id="pagination" aria-label="Table pagination"></nav>
      </div>
      <div class="panel-body table-wrap">
        <table>
          <thead>
            <tr>
              <th class="sortable" data-sort="Incident_ID">Incident ID<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Severity">Severity<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Event_Type">Event Type<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Source_Type">Source<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Date_Time">Date / Time<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Location">Location<span class="sort-indicator"></span></th>
              <th class="sortable" data-sort="Confidence_Score">Confidence<span class="sort-indicator"></span></th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody id="investigation-body"></tbody>
        </table>
      </div>
    </section>

    <div class="main-grid">
      <aside class="panel queue-panel">
        <div class="panel-head">
          <h2>Incident Priority Queue</h2>
          <label class="queue-size-label" for="queue-size">
            <span id="queue-showing">Showing 5</span>
            <select id="queue-size" aria-label="Priority queue size">
              <option value="3">Top 3</option>
              <option value="5" selected>Top 5</option>
              <option value="6">Top 6</option>
              <option value="10">Top 10</option>
              <option value="25">Top 25</option>
              <option value="50">Top 50</option>
            </select>
          </label>
        </div>
        <div class="panel-body queue-list" id="priority-queue"></div>
      </aside>

      <div class="charts-col">
        <div class="chart-trio">
          <div class="panel">
            <div class="panel-head">
              <div class="panel-title-group">
                <h2>High Priority Incident Locations (Top 10)</h2>
                <span class="panel-subtitle">High severity · geographic locations only</span>
              </div>
            </div>
            <div class="panel-body chart-box" id="chart-high-priority-locations"></div>
          </div>
          <div class="panel">
            <div class="panel-head">
              <h2>Top Incident Locations</h2>
              <span>Geographic locations · excludes N/A and CCTV</span>
            </div>
            <div class="panel-body chart-box" id="chart-hotspots"></div>
          </div>
        </div>
        <div class="chart-trio">
          <div class="panel">
            <div class="panel-head">
              <h2>High Priority Incident Types</h2>
            </div>
            <div class="panel-body chart-box" id="chart-high-priority-events"></div>
          </div>
          <div class="panel">
            <div class="panel-head">
              <h2>Incident Priority Levels <span class="panel-subtitle">(Confidence-Based Severity)</span></h2>
            </div>
            <div class="panel-body chart-box" id="chart-severity-donut"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="queue-tooltip" class="queue-tooltip" role="tooltip" aria-hidden="true"></div>
  <div id="summary-tooltip" class="summary-tooltip" role="tooltip" aria-hidden="true"></div>
"""

JS_TAIL = """
    const SEV_COLORS = DATA.severity_colors;
    const SRC_COLORS = DATA.source_colors;

    const CHART_TICK_SIZE = 13;
    const CHART_FONT_SIZE = 13;
    const CHART_HEIGHT = 250;
    const CHART_FONT_FAMILY = "Inter, Segoe UI, system-ui, sans-serif";
    const CHART_AXIS_COLOR = "#C7D0D9";
    const CHART_GRID_COLOR = "rgba(255,255,255,0.08)";
    const CHART_BAR_COUNT = 10;
    const PAGE_SIZE_KEY = "icc_table_page_size_v2";
    const PAGE_SIZE_OPTIONS = [5, 10, 25, 50, 100];
    const PAGE_SIZE_DEFAULT = 5;
    const QUEUE_SIZE_KEY = "icc_queue_size";
    const QUEUE_SIZE_OPTIONS = [3, 5, 6, 10, 25, 50];
    let tableRows = [];
    let tableSourceRows = [];
    let tableSortColumn = null;
    let tableSortDirection = "asc";
    let currentPage = 1;
    let focusIncidentId = null;
    const EVENT_BAR_COLOR = "#4FC3F7";
    const EVENT_BAR_HOVER = "#64D2FF";
    const EVENT_BAR_SELECTED = "#90CAF9";
    const LOCATION_BAR_COLOR = "#F5A623";
    const LOCATION_BAR_HOVER = "#FFB74D";
    const LOCATION_BAR_SELECTED = "#FFD180";
    const HIGH_PRI_LOC_BAR_COLOR = "#7E57C2";
    const HIGH_PRI_LOC_BAR_HOVER = "#9575CD";
    const HIGH_PRI_LOC_BAR_SELECTED = "#B39DDB";
    const HIGH_PRI_EVT_BAR_COLOR = "#4DB6AC";
    const HIGH_PRI_EVT_BAR_HOVER = "#26A69A";
    const HIGH_PRI_EVT_BAR_SELECTED = "#80CBC4";
    const HIGH_PRI_LOC_PALETTE = {
      base: HIGH_PRI_LOC_BAR_COLOR,
      selected: HIGH_PRI_LOC_BAR_SELECTED,
      dim: "rgba(126, 87, 194, 0.28)",
    };
    const HIGH_PRI_EVT_PALETTE = {
      base: HIGH_PRI_EVT_BAR_COLOR,
      selected: HIGH_PRI_EVT_BAR_SELECTED,
      dim: "rgba(77, 182, 172, 0.28)",
    };
    const DONUT_SEV_COLORS = { High: "#E53935", Medium: "#F9A825", Low: "#43A047" };
    const DONUT_SEV_SELECTED = { High: "#EF5350", Medium: "#FFB74D", Low: "#66BB6A" };
    const DONUT_SEGMENT_TEXT_COLOR = "#263238";

    const URGENCY_RANK = { High: 0, Medium: 1, Low: 2 };
    const SEV_RANK = { High: 0, Medium: 1, Low: 2 };

    function comparePriority(a, b) {
      const urgA = URGENCY_RANK[a.Urgency] ?? 9;
      const urgB = URGENCY_RANK[b.Urgency] ?? 9;
      if (urgA !== urgB) return urgA - urgB;
      const sevA = SEV_RANK[a.Severity] ?? 9;
      const sevB = SEV_RANK[b.Severity] ?? 9;
      if (sevA !== sevB) return sevA - sevB;
      return b.Confidence_Score - a.Confidence_Score;
    }

    const incidentById = Object.fromEntries(DATA.records.map(r => [r.Incident_ID, r]));

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function normalizeSummary(value) {
      return String(value ?? "—").split("\\r\\n").join("\\n").trim() || "—";
    }

    function buildQueueTooltip(record) {
      const tooltip = document.getElementById("queue-tooltip");
      tooltip.innerHTML = `
        <div class="queue-tooltip-title">Incident Details</div>
        <dl class="queue-tooltip-grid">
          <dt>Incident ID</dt><dd>${escapeHtml(record.Incident_ID)}</dd>
          <dt>Event Type</dt><dd>${escapeHtml(record.Event_Type)}</dd>
          <dt>Severity</dt><dd>${sevBadge(record.Severity)}</dd>
          <dt>Date &amp; Time</dt><dd>${escapeHtml(record.Date_Time || "—")}</dd>
          <dt>Location</dt><dd>${escapeHtml(record.Location)}</dd>
          <dt>Source Type</dt><dd>${escapeHtml(record.Source_Type)}</dd>
          <dt>Confidence</dt><dd>${Number(record.Confidence_Score).toFixed(2)}</dd>
        </dl>
        <dl class="queue-tooltip-summary">
          <dt>Summary</dt>
          <dd>${escapeHtml(normalizeSummary(record.Summary))}</dd>
        </dl>`;
      return tooltip;
    }

    function positionQueueTooltip(anchorEl) {
      const tooltip = document.getElementById("queue-tooltip");
      const rect = anchorEl.getBoundingClientRect();
      const margin = 12;
      tooltip.classList.add("visible");
      tooltip.setAttribute("aria-hidden", "false");

      const tipRect = tooltip.getBoundingClientRect();
      let left = rect.right + margin;
      let top = rect.top;

      if (left + tipRect.width > window.innerWidth - margin) {
        left = rect.left - tipRect.width - margin;
      }
      if (left < margin) {
        left = Math.max(margin, (window.innerWidth - tipRect.width) / 2);
      }
      if (top + tipRect.height > window.innerHeight - margin) {
        top = window.innerHeight - tipRect.height - margin;
      }
      if (top < margin) top = margin;

      tooltip.style.left = `${Math.round(left)}px`;
      tooltip.style.top = `${Math.round(top)}px`;
    }

    function showQueueTooltip(anchorEl, incidentId) {
      const record = incidentById[incidentId];
      if (!record) return;
      buildQueueTooltip(record);
      positionQueueTooltip(anchorEl);
    }

    function hideQueueTooltip() {
      const tooltip = document.getElementById("queue-tooltip");
      tooltip.classList.remove("visible");
      tooltip.setAttribute("aria-hidden", "true");
      tooltip.style.left = "";
      tooltip.style.top = "";
    }

    function bindQueueTooltip(el) {
      const incidentId = el.dataset.id;
      el.addEventListener("mouseenter", () => showQueueTooltip(el, incidentId));
      el.addEventListener("mousemove", () => positionQueueTooltip(el));
      el.addEventListener("mouseleave", hideQueueTooltip);
      el.addEventListener("click", () => hideQueueTooltip());
    }

    const plotLayout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: CHART_AXIS_COLOR, size: CHART_FONT_SIZE, family: CHART_FONT_FAMILY },
      autosize: false,
      height: CHART_HEIGHT,
      xaxis: {
        gridcolor: CHART_GRID_COLOR,
        zerolinecolor: CHART_GRID_COLOR,
        tickfont: { size: CHART_TICK_SIZE, color: CHART_AXIS_COLOR, family: CHART_FONT_FAMILY },
        rangemode: "tozero",
        showline: false,
      },
      yaxis: {
        gridcolor: CHART_GRID_COLOR,
        zerolinecolor: CHART_GRID_COLOR,
        automargin: true,
        tickfont: { size: CHART_TICK_SIZE, color: CHART_AXIS_COLOR, family: CHART_FONT_FAMILY },
        showline: false,
      },
    };

    function chartAxisMax(values) {
      const maxVal = Math.max(0, ...(values && values.length ? values : [0]));
      if (maxVal <= 0) return 1;
      return maxVal * 1.08;
    }

    function chartLayout(leftMargin, values, height) {
      const xMax = chartAxisMax(values);
      return {
        ...plotLayout,
        height: height || CHART_HEIGHT,
        hoverlabel: {
          bgcolor: "#0f1520",
          bordercolor: "rgba(255,255,255,0.12)",
          font: { size: 13, color: "#FFFFFF", family: CHART_FONT_FAMILY },
        },
        dragmode: false,
        margin: { l: leftMargin, r: 24, t: 8, b: 28 },
        bargap: 0.28,
        bargroupgap: 0.08,
        xaxis: {
          ...plotLayout.xaxis,
          range: [0, xMax],
          fixedrange: true,
          constrain: "domain",
        },
      };
    }

    function resizeCharts() {
      ["chart-high-priority-locations", "chart-hotspots", "chart-high-priority-events", "chart-severity-donut"].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) Plotly.Plots.resize(el);
      });
    }

    function getFocusRecord() {
      return focusIncidentId ? incidentById[focusIncidentId] : null;
    }

    function clearAllFilters() {
      ["f-source", "f-urgency-class", "f-event", "f-severity", "f-location"].forEach(id => {
        document.getElementById(id).value = "";
      });
      focusIncidentId = null;
      refresh();
    }

    function toggleSelectFilter(selectId, value) {
      const sel = document.getElementById(selectId);
      sel.value = sel.value === value ? "" : value;
      focusIncidentId = null;
      refresh();
    }

    function selectIncident(id, scroll = true) {
      focusIncidentId = focusIncidentId === id ? null : id;
      refresh();
      if (focusIncidentId && scroll) {
        requestAnimationFrame(() => scrollToIncident(focusIncidentId));
      }
    }

    function updateActiveFiltersUI() {
      const container = document.getElementById("active-filters");
      const chips = [];
      const addChip = (label, value, onClear) => {
        chips.push({ label, value, onClear });
      };

      const src = document.getElementById("f-source").value;
      const urg = document.getElementById("f-urgency-class").value;
      const evt = document.getElementById("f-event").value;
      const sev = document.getElementById("f-severity").value;
      const loc = document.getElementById("f-location").value;
      if (src) addChip("Source", src, () => { document.getElementById("f-source").value = ""; refresh(); });
      if (urg) addChip("Urgency", urg, () => { document.getElementById("f-urgency-class").value = ""; refresh(); });
      if (evt) addChip("Event Type", evt, () => { document.getElementById("f-event").value = ""; refresh(); });
      if (sev) addChip("Severity", sev, () => { document.getElementById("f-severity").value = ""; refresh(); });
      if (loc) addChip("Location", loc, () => { document.getElementById("f-location").value = ""; refresh(); });
      if (focusIncidentId) {
        addChip("Incident", focusIncidentId, () => { focusIncidentId = null; refresh(); });
      }

      if (!chips.length) {
        container.innerHTML = `<span class="active-filters-empty">No active filters — click any chart, queue item, or table row to link views</span>`;
        return;
      }

      container.innerHTML = chips.map(chip => `
        <span class="filter-chip">
          <span class="filter-chip-label">${escapeHtml(chip.label)}:</span>
          <span class="filter-chip-value">${escapeHtml(chip.value)}</span>
          <button type="button" class="filter-chip-clear" data-chip-clear="${escapeHtml(chip.label)}" aria-label="Remove ${escapeHtml(chip.label)} filter">×</button>
        </span>`).join("");

      container.querySelectorAll(".filter-chip-clear").forEach((btn, idx) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          chips[idx].onClear();
        });
      });
    }

    function barHighlightColor(label, selectedValue, focusRecord, focusField, dimUnselected) {
      const isLocation = focusField === "Location";
      const selectedColor = isLocation ? LOCATION_BAR_SELECTED : EVENT_BAR_SELECTED;
      const defaultColor = isLocation ? LOCATION_BAR_COLOR : EVENT_BAR_COLOR;
      const dimColor = isLocation ? "rgba(245, 166, 35, 0.28)" : "rgba(79, 195, 247, 0.28)";
      if (focusRecord && focusRecord[focusField] === label) return selectedColor;
      if (selectedValue && selectedValue === label) return selectedColor;
      if (dimUnselected && selectedValue) return dimColor;
      return defaultColor;
    }

    function barHighlightColorPalette(label, selectedValue, focusRecord, focusField, palette, dimUnselected) {
      if (focusRecord && focusRecord[focusField] === label) return palette.selected;
      if (selectedValue && selectedValue === label) return palette.selected;
      if (dimUnselected && selectedValue) return palette.dim;
      return palette.base;
    }

    function barMarker(colors, outlines) {
      return {
        color: colors,
        line: { width: outlines, color: "rgba(15, 21, 32, 0.35)" },
        cornerradius: 4,
      };
    }

    function bindBarHover(chartId, kind) {
      const el = document.getElementById(chartId);
      if (!el || !el.on || !el.data || !el.data[0]) return;
      if (el.removeAllListeners) el.removeAllListeners("plotly_hover");
      if (el.removeAllListeners) el.removeAllListeners("plotly_unhover");
      const hoverColor = {
        location: LOCATION_BAR_HOVER,
        event: EVENT_BAR_HOVER,
        highPriLoc: HIGH_PRI_LOC_BAR_HOVER,
        highPriEvt: HIGH_PRI_EVT_BAR_HOVER,
      }[kind] || EVENT_BAR_HOVER;
      const baseColors = [...el.data[0].marker.color];
      el.on("plotly_hover", (eventData) => {
        const point = eventData.points && eventData.points[0];
        if (!point || point.pointNumber == null) return;
        const colors = [...baseColors];
        colors[point.pointNumber] = hoverColor;
        Plotly.restyle(el, { "marker.color": [colors] });
      });
      el.on("plotly_unhover", () => {
        Plotly.restyle(el, { "marker.color": [baseColors] });
      });
    }

    function barOutlineWidth(label, selectedValue, focusRecord, focusField) {
      if (selectedValue && selectedValue === label) return 2;
      if (focusRecord && focusRecord[focusField] === label) return 2;
      return 0;
    }

    function getRowsForChart(excludeDimension) {
      const src = document.getElementById("f-source").value;
      const urg = document.getElementById("f-urgency-class").value;
      const evt = document.getElementById("f-event").value;
      const sev = document.getElementById("f-severity").value;
      const loc = document.getElementById("f-location").value;
      let rows = DATA.records.filter(r => {
        if (excludeDimension !== "source" && src && r.Source_Type !== src) return false;
        if (excludeDimension !== "urgency" && urg && r.Urgency !== urg) return false;
        if (excludeDimension !== "event" && evt && r.Event_Type !== evt) return false;
        if (excludeDimension !== "severity" && sev && r.Severity !== sev) return false;
        if (excludeDimension !== "location" && loc && r.Location !== loc) return false;
        return true;
      });
      if (focusIncidentId) {
        rows = rows.filter(r => r.Incident_ID === focusIncidentId);
      }
      return rows;
    }

    function getFilteredWithoutFocus() {
      return getDropdownFiltered();
    }

    function getFiltered() {
      let rows = getFilteredWithoutFocus();
      if (focusIncidentId) {
        rows = rows.filter(r => r.Incident_ID === focusIncidentId);
      }
      return rows;
    }

    function sevBadge(sev) {
      const TABLE_SEV = { High: "#E53935", Medium: "#F9A825", Low: "#43A047" };
      const c = TABLE_SEV[sev] || SEV_COLORS[sev] || "#64748B";
      return `<span class="badge" style="background:${c}">${sev}</span>`;
    }

    function formatConfidenceCell(score) {
      const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
      return `<div class="conf-cell"><span class="conf-pct">${pct}%</span><div class="conf-bar"><div class="conf-fill" style="width:${pct}%"></div></div></div>`;
    }

    function truncateSummary(text, maxLen = 160) {
      const flat = normalizeSummary(text).replace(/\\s+/g, " ");
      if (flat.length <= maxLen) return flat;
      return flat.slice(0, maxLen) + "…";
    }

    const TABLE_SEV_SORT = { High: 0, Medium: 1, Low: 2 };

    function tableSortValue(record, column) {
      switch (column) {
        case "Incident_ID": return record.Incident_ID || "";
        case "Severity": return TABLE_SEV_SORT[record.Severity] ?? 9;
        case "Event_Type": return record.Event_Type || "";
        case "Source_Type": return record.Source_Type || "";
        case "Date_Time": return record.Date_Time || "";
        case "Location": return record.Location || "";
        case "Confidence_Score": return record.Confidence_Score ?? 0;
        default: return "";
      }
    }

    function applyTableSort(rows) {
      if (!tableSortColumn) return [...rows].sort(comparePriority);
      const mul = tableSortDirection === "asc" ? 1 : -1;
      return [...rows].sort((a, b) => {
        const va = tableSortValue(a, tableSortColumn);
        const vb = tableSortValue(b, tableSortColumn);
        let cmp = 0;
        if (typeof va === "number" && typeof vb === "number") {
          cmp = va - vb;
        } else {
          cmp = String(va).localeCompare(String(vb), undefined, { numeric: true, sensitivity: "base" });
        }
        if (cmp !== 0) return cmp * mul;
        return comparePriority(a, b);
      });
    }

    function updateSortIndicators() {
      document.querySelectorAll("th.sortable").forEach(th => {
        const ind = th.querySelector(".sort-indicator");
        const col = th.dataset.sort;
        if (col === tableSortColumn) {
          ind.textContent = tableSortDirection === "asc" ? "▲" : "▼";
          th.classList.add("sorted");
        } else {
          ind.textContent = "";
          th.classList.remove("sorted");
        }
      });
    }

    function initTableSorting() {
      document.querySelectorAll("th.sortable").forEach(th => {
        th.addEventListener("click", () => {
          const col = th.dataset.sort;
          if (tableSortColumn === col) {
            tableSortDirection = tableSortDirection === "asc" ? "desc" : "asc";
          } else {
            tableSortColumn = col;
            tableSortDirection = "asc";
          }
          tableRows = applyTableSort(tableSourceRows);
          currentPage = 1;
          updateSortIndicators();
          renderTableBody();
        });
      });
      updateSortIndicators();
    }

    function showSummaryTooltip(anchorEl, text) {
      const tooltip = document.getElementById("summary-tooltip");
      tooltip.textContent = normalizeSummary(text);
      tooltip.classList.add("visible");
      tooltip.setAttribute("aria-hidden", "false");
      const rect = anchorEl.getBoundingClientRect();
      const margin = 12;
      tooltip.style.left = `${Math.round(rect.left)}px`;
      let top = rect.bottom + margin;
      const tipRect = tooltip.getBoundingClientRect();
      if (top + tipRect.height > window.innerHeight - margin) {
        top = rect.top - tipRect.height - margin;
      }
      if (top < margin) top = margin;
      tooltip.style.top = `${Math.round(top)}px`;
      if (rect.left + tipRect.width > window.innerWidth - margin) {
        tooltip.style.left = `${Math.round(window.innerWidth - tipRect.width - margin)}px`;
      }
    }

    function hideSummaryTooltip() {
      const tooltip = document.getElementById("summary-tooltip");
      tooltip.classList.remove("visible");
      tooltip.setAttribute("aria-hidden", "true");
      tooltip.style.left = "";
      tooltip.style.top = "";
    }

    function bindSummaryTooltip(cell, fullText) {
      const summary = normalizeSummary(fullText);
      if (!summary || summary === "—") return;
      cell.addEventListener("mouseenter", () => showSummaryTooltip(cell, summary));
      cell.addEventListener("mousemove", () => showSummaryTooltip(cell, summary));
      cell.addEventListener("mouseleave", hideSummaryTooltip);
    }

    const NON_ACTIONABLE_EVENT_TYPES = new Set([
      "", "n/a", "unknown", "false alarm", "no activity detected",
      "person walking / present", "person walking/present",
    ]);

    function isActionable(record) {
      const eventType = (record.Event_Type || "").trim().toLowerCase();
      return !NON_ACTIONABLE_EVENT_TYPES.has(eventType);
    }

    function getDropdownFiltered() {
      const src = document.getElementById("f-source").value;
      const urg = document.getElementById("f-urgency-class").value;
      const evt = document.getElementById("f-event").value;
      const sev = document.getElementById("f-severity").value;
      const loc = document.getElementById("f-location").value;
      return DATA.records.filter(r => {
        if (src && r.Source_Type !== src) return false;
        if (urg && r.Urgency !== urg) return false;
        if (evt && r.Event_Type !== evt) return false;
        if (sev && r.Severity !== sev) return false;
        if (loc && r.Location !== loc) return false;
        return true;
      });
    }

    function computeMetrics(rows) {
      const medium = rows.filter(r => r.Severity === "Medium").length;
      const high = rows.filter(r => r.Severity === "High").length;
      const priority = rows.filter(r => isActionable(r) && r.Severity === "High").length;
      return { total: rows.length, medium, high, priority };
    }

    function renderKPIs(m) {
      document.getElementById("kpi-row").innerHTML = `
        <div class="kpi info"><div class="kpi-label">Total Incidents</div><div class="kpi-value">${m.total.toLocaleString()}</div><div class="kpi-foot">Filtered set</div></div>
        <div class="kpi critical"><div class="kpi-label">Medium Priority</div><div class="kpi-value">${m.medium.toLocaleString()}</div><div class="kpi-foot">Severity = Medium</div></div>
        <div class="kpi high"><div class="kpi-label">High Priority</div><div class="kpi-value">${m.high.toLocaleString()}</div><div class="kpi-foot">Severity = High</div></div>
        <div class="kpi action"><div class="kpi-label">Actionable Queue</div><div class="kpi-value">${m.priority.toLocaleString()}</div><div class="kpi-foot">Actionable + High</div></div>`;
    }

    function getQueueSize() {
      const sel = document.getElementById("queue-size");
      return parseInt(sel.value, 10) || 5;
    }

    function loadQueueSize() {
      const saved = parseInt(localStorage.getItem(QUEUE_SIZE_KEY), 10);
      return QUEUE_SIZE_OPTIONS.includes(saved) ? saved : 5;
    }

    function saveQueueSize(size) {
      localStorage.setItem(QUEUE_SIZE_KEY, String(size));
    }

    function initQueueSize() {
      document.getElementById("queue-size").value = String(loadQueueSize());
    }

    function adjustQueueLayout() {
      const list = document.getElementById("priority-queue");
      const chartsCol = document.querySelector(".charts-col");
      const queuePanel = document.querySelector(".queue-panel");
      if (!list) return;
      list.classList.remove("distribute");
      if (chartsCol && queuePanel && window.matchMedia("(min-width: 1181px)").matches) {
        queuePanel.style.maxHeight = `${chartsCol.offsetHeight}px`;
      } else if (queuePanel) {
        queuePanel.style.maxHeight = "";
      }
    }

    function renderQueue(rows) {
      const limit = getQueueSize();
      const sorted = [...rows]
        .sort(comparePriority)
        .slice(0, limit);
      document.getElementById("queue-showing").textContent = `Showing ${sorted.length}`;
      document.getElementById("priority-queue").innerHTML = sorted.length ? sorted.map(r => `
        <div class="queue-item${focusIncidentId === r.Incident_ID ? " selected" : ""}" data-id="${r.Incident_ID}">
          <div class="queue-top"><span class="queue-id">${r.Incident_ID}</span>${sevBadge(r.Severity)}</div>
          <div class="queue-event">${r.Event_Type}</div>
          <div class="queue-meta">${r.Location} · ${r.Source_Type} · Conf ${r.Confidence_Score.toFixed(2)}</div>
        </div>`).join("") : `<div class="queue-meta" style="padding:12px">No incidents in current filter.</div>`;
      document.querySelectorAll(".queue-item").forEach(el => {
        bindQueueTooltip(el);
        el.addEventListener("click", () => {
          hideQueueTooltip();
          selectIncident(el.dataset.id);
        });
      });
      requestAnimationFrame(adjustQueueLayout);
    }

    function groupCount(rows, key) {
      const m = {};
      rows.forEach(r => { m[r[key]] = (m[r[key]] || 0) + 1; });
      return m;
    }

    function cleanLocation(value) {
      return String(value ?? "").replace(/\\u200b/g, "").trim();
    }

    function isExcludedLocation(loc) {
      const v = cleanLocation(loc);
      const upper = v.toUpperCase();
      if (!v || upper === "N/A" || upper === "NA" || upper === "UNKNOWN") return true;
      if (upper.startsWith("CCTV")) return true;
      return false;
    }

    function isGeographicRecord(record) {
      return !isExcludedLocation(record.Location);
    }

    function geographicRows(rows) {
      return rows.filter(isGeographicRecord);
    }

    function topEntries(map, n, asc=false) {
      const entries = Object.entries(map).sort((a, b) => asc ? a[1] - b[1] : b[1] - a[1]);
      return entries.slice(0, n);
    }

    function topEntriesWithPin(map, n, pinLabel, asc=false) {
      if (!pinLabel || map[pinLabel] == null) return topEntries(map, n, asc);
      const pinned = [pinLabel, map[pinLabel]];
      const rest = Object.entries(map)
        .filter(e => e[0] !== pinLabel)
        .sort((a, b) => asc ? a[1] - b[1] : b[1] - a[1])
        .slice(0, Math.max(0, n - 1));
      return [...rest, pinned].sort((a, b) => asc ? a[1] - b[1] : b[1] - a[1]);
    }

    function onHighPriorityEventClick(eventData) {
      const point = eventData.points && eventData.points[0];
      if (!point || point.y == null) return;
      toggleSelectFilter("f-event", String(point.y));
    }

    function onSeverityDonutClick(eventData) {
      const point = eventData.points && eventData.points[0];
      if (!point || point.label == null) return;
      toggleSelectFilter("f-severity", String(point.label));
    }

    function onEventChartClick(eventData) {
      const point = eventData.points && eventData.points[0];
      if (!point || point.y == null) return;
      toggleSelectFilter("f-event", String(point.y));
    }

    function onLocationChartClick(eventData) {
      const point = eventData.points && eventData.points[0];
      if (!point || point.y == null) return;
      toggleSelectFilter("f-location", String(point.y));
    }

    function bindChartClick(chartId, handler) {
      const chartEl = document.getElementById(chartId);
      if (!chartEl) return;
      if (chartEl.removeAllListeners) chartEl.removeAllListeners("plotly_click");
      chartEl.on("plotly_click", handler);
    }

    function donutLayout() {
      return {
        ...plotLayout,
        height: CHART_HEIGHT,
        margin: { l: 24, r: 24, t: 8, b: 28 },
        showlegend: true,
        legend: {
          orientation: "v",
          font: { size: CHART_TICK_SIZE, color: CHART_AXIS_COLOR, family: CHART_FONT_FAMILY },
        },
        hoverlabel: {
          bgcolor: "#0f1520",
          bordercolor: "rgba(255,255,255,0.12)",
          font: { size: 13, color: "#FFFFFF", family: CHART_FONT_FAMILY },
        },
      };
    }

    function renderBottomCharts(dropdownRows) {
      const focusRecord = getFocusRecord();
      const selectedEvent = document.getElementById("f-event").value;
      const selectedSeverity = document.getElementById("f-severity").value;
      const SEVERITY_ORDER = ["High", "Medium", "Low"];

      const highPriRows = getRowsForChart("event").filter(r => r.Severity === "High");
      const highEvtMap = groupCount(highPriRows, "Event_Type");
      const highEvtTop = topEntriesWithPin(highEvtMap, CHART_BAR_COUNT, selectedEvent).reverse();
      const highEvtValues = highEvtTop.map(e => e[1]);
      const highEvtColors = highEvtTop.map(e => barHighlightColorPalette(
        e[0], selectedEvent, focusRecord, "Event_Type", HIGH_PRI_EVT_PALETTE, !!selectedEvent
      ));
      const highEvtOutlines = highEvtTop.map(e => barOutlineWidth(e[0], selectedEvent, focusRecord, "Event_Type"));
      if (highEvtTop.length) {
        Plotly.newPlot("chart-high-priority-events", [{
          type: "bar",
          orientation: "h",
          y: highEvtTop.map(e => e[0]),
          x: highEvtValues,
          marker: barMarker(highEvtColors, highEvtOutlines),
          cliponaxis: true,
          hovertemplate: "<b>%{y}</b><br>Count: %{x}<extra></extra>",
        }], chartLayout(168, highEvtValues), { responsive: true, displayModeBar: false });
        bindChartClick("chart-high-priority-events", onHighPriorityEventClick);
        bindBarHover("chart-high-priority-events", "highPriEvt");
      } else {
        Plotly.newPlot("chart-high-priority-events", [], {
          ...chartLayout(168, [1]),
          annotations: [{
            text: dropdownRows.length
              ? "No High severity incidents in the current filtered selection"
              : "No incidents match the current filters",
            xref: "paper", yref: "paper", x: 0.5, y: 0.5,
            showarrow: false, font: { color: "#94a3b8", size: 16 },
          }],
        }, { responsive: true, displayModeBar: false });
      }

      const sevRows = getRowsForChart("severity");
      const sevCounts = SEVERITY_ORDER.map(label => ({
        label,
        count: sevRows.filter(r => r.Severity === label).length,
      }));
      const sevValues = sevCounts.map(s => s.count);
      const sevLabels = sevCounts.map(s => s.label);
      const sevColors = sevLabels.map(label => {
        if (focusRecord && focusRecord.Severity === label) return DONUT_SEV_SELECTED[label];
        if (selectedSeverity && selectedSeverity === label) return DONUT_SEV_SELECTED[label];
        if (selectedSeverity) return DONUT_SEV_COLORS[label] + "47";
        return DONUT_SEV_COLORS[label] || "#64748B";
      });
      const hasSeverityData = sevValues.some(v => v > 0);
      if (hasSeverityData) {
        Plotly.newPlot("chart-severity-donut", [{
          type: "pie",
          hole: 0.45,
          labels: sevLabels,
          values: sevValues,
          sort: false,
          direction: "clockwise",
          marker: {
            colors: sevColors,
            line: { color: "rgba(15, 21, 32, 0.5)", width: 1 },
          },
          textinfo: "label+percent",
          textfont: { size: CHART_TICK_SIZE, color: DONUT_SEGMENT_TEXT_COLOR, family: CHART_FONT_FAMILY, weight: 700 },
          hovertemplate: "<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        }], donutLayout(), { responsive: true, displayModeBar: false });
        bindChartClick("chart-severity-donut", onSeverityDonutClick);
      } else {
        Plotly.newPlot("chart-severity-donut", [], {
          ...donutLayout(),
          annotations: [{
            text: dropdownRows.length
              ? "No severity data in the current filtered selection"
              : "No incidents match the current filters",
            xref: "paper", yref: "paper", x: 0.5, y: 0.5,
            showarrow: false, font: { color: "#94a3b8", size: 16 },
          }],
        }, { responsive: true, displayModeBar: false });
      }
    }

    function renderCharts(dropdownRows, displayRows) {
      const focusRecord = getFocusRecord();
      const selectedLocation = document.getElementById("f-location").value;

      const highPriLocRows = geographicRows(
        getRowsForChart("location").filter(r => r.Severity === "High")
      );
      const highLocMap = groupCount(highPriLocRows, "Location");
      const highLocTop = topEntriesWithPin(highLocMap, CHART_BAR_COUNT, selectedLocation).reverse();
      const highLocValues = highLocTop.map(e => e[1]);
      const highLocColors = highLocTop.map(e => barHighlightColorPalette(
        e[0], selectedLocation, focusRecord, "Location", HIGH_PRI_LOC_PALETTE, !!selectedLocation
      ));
      const highLocOutlines = highLocTop.map(e => barOutlineWidth(e[0], selectedLocation, focusRecord, "Location"));
      if (highLocTop.length) {
        Plotly.newPlot("chart-high-priority-locations", [{
          type: "bar",
          orientation: "h",
          y: highLocTop.map(e => e[0]),
          x: highLocValues,
          marker: barMarker(highLocColors, highLocOutlines),
          cliponaxis: true,
          hovertemplate: "<b>%{y}</b><br>Count: %{x}<extra></extra>",
        }], chartLayout(188, highLocValues), { responsive: true, displayModeBar: false });
        bindChartClick("chart-high-priority-locations", onLocationChartClick);
        bindBarHover("chart-high-priority-locations", "highPriLoc");
      } else {
        Plotly.newPlot("chart-high-priority-locations", [], {
          ...chartLayout(188, [1]),
          annotations: [{
            text: dropdownRows.length
              ? "No High severity geographic locations in the current filtered selection"
              : "No incidents match the current filters",
            xref: "paper", yref: "paper", x: 0.5, y: 0.5,
            showarrow: false, font: { color: "#94a3b8", size: 16 },
          }],
        }, { responsive: true, displayModeBar: false });
      }

      const locationChartRows = geographicRows(
        getRowsForChart("location").filter(r => r.Severity === "High" || r.Severity === "Medium")
      );
      const hotMap = groupCount(locationChartRows, "Location");
      const hotTop = topEntriesWithPin(hotMap, CHART_BAR_COUNT, selectedLocation).reverse();
      const hotValues = hotTop.map(e => e[1]);
      const hotColors = hotTop.map(e => barHighlightColor(
        e[0], selectedLocation, focusRecord, "Location", !!selectedLocation
      ));
      const hotOutlines = hotTop.map(e => barOutlineWidth(e[0], selectedLocation, focusRecord, "Location"));
      Plotly.newPlot("chart-hotspots", [{
        type: "bar",
        orientation: "h",
        y: hotTop.map(e => e[0]),
        x: hotValues,
        marker: barMarker(hotColors, hotOutlines),
        cliponaxis: true,
        hovertemplate: "<b>%{y}</b><br>Count: %{x}<extra></extra>",
      }], chartLayout(188, hotValues), { responsive: true, displayModeBar: false });
      bindChartClick("chart-hotspots", onLocationChartClick);
      bindBarHover("chart-hotspots", "location");

      renderBottomCharts(dropdownRows);
      requestAnimationFrame(resizeCharts);
    }

    function loadPageSize() {
      const saved = parseInt(localStorage.getItem(PAGE_SIZE_KEY), 10);
      return PAGE_SIZE_OPTIONS.includes(saved) ? saved : PAGE_SIZE_DEFAULT;
    }

    function savePageSize(size) {
      localStorage.setItem(PAGE_SIZE_KEY, String(size));
    }

    function getPageSize() {
      const sel = document.getElementById("page-size");
      return parseInt(sel.value, 10) || 10;
    }

    function initPageSize() {
      const size = loadPageSize();
      document.getElementById("page-size").value = String(size);
    }

    function pageWindow(current, total) {
      if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
      const pages = new Set([1, total, current]);
      if (current > 2) pages.add(current - 1);
      if (current < total) pages.add(current + 1);
      if (current <= 3) { pages.add(2); pages.add(3); }
      if (current >= total - 2) { pages.add(total - 1); pages.add(total - 2); }
      const sorted = [...pages].sort((a, b) => a - b);
      const out = [];
      let prev = 0;
      sorted.forEach(p => {
        if (prev && p - prev > 1) out.push("…");
        out.push(p);
        prev = p;
      });
      return out;
    }

    function renderPagination(totalRows, page, pageSize) {
      const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
      const nav = document.getElementById("pagination");
      if (totalRows === 0) {
        nav.innerHTML = "";
        return;
      }
      const items = [
        `<button type="button" class="page-btn nav-btn" data-page="prev" ${page <= 1 ? "disabled" : ""}>Previous</button>`,
        ...pageWindow(page, totalPages).map(p =>
          p === "…"
            ? `<span class="page-ellipsis">…</span>`
            : `<button type="button" class="page-btn${p === page ? " active" : ""}" data-page="${p}">${p}</button>`
        ),
        `<button type="button" class="page-btn nav-btn" data-page="next" ${page >= totalPages ? "disabled" : ""}>Next</button>`,
      ];
      nav.innerHTML = items.join("");
      nav.querySelectorAll(".page-btn[data-page]").forEach(btn => {
        btn.addEventListener("click", () => {
          const action = btn.dataset.page;
          if (action === "prev" && currentPage > 1) currentPage--;
          else if (action === "next" && currentPage < totalPages) currentPage++;
          else if (action !== "prev" && action !== "next") currentPage = parseInt(action, 10);
          renderTableBody();
        });
      });
    }

    function updateTableRange(totalRows, page, pageSize) {
      const rangeEl = document.getElementById("table-range");
      if (totalRows === 0) {
        rangeEl.textContent = "Showing 0 of 0 incidents.";
        return;
      }
      const start = (page - 1) * pageSize + 1;
      const end = Math.min(page * pageSize, totalRows);
      rangeEl.textContent =
        `Showing ${start.toLocaleString()}–${end.toLocaleString()} of ${totalRows.toLocaleString()} incidents.`;
    }

    function scrollToIncident(id) {
      const idx = tableRows.findIndex(r => r.Incident_ID === id);
      if (idx < 0) return;
      const pageSize = getPageSize();
      currentPage = Math.floor(idx / pageSize) + 1;
      renderTableBody();
      requestAnimationFrame(() => {
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }

    function renderTableBody() {
      const pageSize = getPageSize();
      const totalRows = tableRows.length;
      const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
      if (currentPage > totalPages) currentPage = totalPages;
      if (currentPage < 1) currentPage = 1;

      const start = (currentPage - 1) * pageSize;
      const pageRows = tableRows.slice(start, start + pageSize);

      document.getElementById("table-count").textContent = `${totalRows.toLocaleString()} incidents`;
      document.getElementById("investigation-body").innerHTML = pageRows.length ? pageRows.map(r => `
        <tr data-id="${r.Incident_ID}" class="table-row${focusIncidentId === r.Incident_ID ? " selected" : ""}">
          <td>${escapeHtml(r.Incident_ID)}</td>
          <td>${sevBadge(r.Severity)}</td>
          <td>${escapeHtml(r.Event_Type)}</td>
          <td>${escapeHtml(r.Source_Type)}</td>
          <td>${escapeHtml(r.Date_Time || "—")}</td>
          <td>${escapeHtml(r.Location)}</td>
          <td>${formatConfidenceCell(r.Confidence_Score)}</td>
          <td class="summary-cell">${escapeHtml(truncateSummary(r.Summary))}</td>
        </tr>`).join("") : `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--muted)">No incidents match the current filters.</td></tr>`;

      document.querySelectorAll("#investigation-body tr[data-id]").forEach(row => {
        row.addEventListener("click", () => selectIncident(row.dataset.id, false));
      });

      document.querySelectorAll("#investigation-body .summary-cell").forEach((cell, idx) => {
        if (pageRows[idx]) bindSummaryTooltip(cell, pageRows[idx].Summary);
      });

      updateSortIndicators();
      updateTableRange(totalRows, currentPage, pageSize);
      renderPagination(totalRows, currentPage, pageSize);
      adjustInvestigationTableScroll(pageSize);
    }

    function adjustInvestigationTableScroll(pageSize) {
      const wrap = document.querySelector(".primary-table .table-wrap");
      if (!wrap) return;
      if (pageSize <= 5) {
        wrap.style.overflowY = "hidden";
        wrap.style.maxHeight = "none";
      } else {
        wrap.style.overflowY = "auto";
        wrap.style.maxHeight = "23rem";
      }
    }

    function renderTable(rows) {
      tableSourceRows = [...rows];
      tableRows = applyTableSort(tableSourceRows);
      if (focusIncidentId) {
        const idx = tableRows.findIndex(r => r.Incident_ID === focusIncidentId);
        if (idx >= 0) {
          currentPage = Math.floor(idx / getPageSize()) + 1;
        } else {
          currentPage = 1;
        }
      } else {
        currentPage = 1;
      }
      renderTableBody();
    }

    function populateFilters() {
      const fill = (id, items) => {
        const sel = document.getElementById(id);
        items.forEach(v => {
          const o = document.createElement("option");
          o.value = v; o.textContent = v;
          sel.appendChild(o);
        });
      };
      const uniq = (key) => [...new Set(DATA.records.map(r => r[key]))].sort();
      fill("f-source", uniq("Source_Type"));
      fill("f-severity", uniq("Severity"));
      fill("f-location", uniq("Location"));
      updateEventTypeOptions();
    }

    function getRowsForEventTypeOptions() {
      const src = document.getElementById("f-source").value;
      const urg = document.getElementById("f-urgency-class").value;
      const sev = document.getElementById("f-severity").value;
      const loc = document.getElementById("f-location").value;
      return DATA.records.filter(r => {
        if (src && r.Source_Type !== src) return false;
        if (urg && r.Urgency !== urg) return false;
        if (sev && r.Severity !== sev) return false;
        if (loc && r.Location !== loc) return false;
        return true;
      });
    }

    function updateEventTypeOptions() {
      const sel = document.getElementById("f-event");
      const prev = sel.value;
      const types = [...new Set(getRowsForEventTypeOptions().map(r => r.Event_Type))].sort();
      sel.innerHTML = '<option value="">All Events</option>';
      types.forEach(v => {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v;
        sel.appendChild(o);
      });
      sel.value = prev && types.includes(prev) ? prev : "";
    }

    function refresh() {
      updateEventTypeOptions();
      const dropdownRows = getDropdownFiltered();
      const rowsWithoutFocus = getFilteredWithoutFocus();
      if (focusIncidentId && !rowsWithoutFocus.some(r => r.Incident_ID === focusIncidentId)) {
        focusIncidentId = null;
      }
      const rows = getFiltered();
      const m = computeMetrics(rows);
      renderKPIs(m);
      renderQueue(rows);
      renderCharts(dropdownRows, rows);
      renderTable(rows);
      updateActiveFiltersUI();
      let filterText = `Showing ${rows.length.toLocaleString()} of ${DATA.records.length.toLocaleString()}`;
      document.getElementById("filter-count").textContent = filterText;
      document.getElementById("header-records").textContent =
        `${DATA.records.length.toLocaleString()} incidents monitored`;
      requestAnimationFrame(() => {
        resizeCharts();
        adjustQueueLayout();
      });
    }

    function tickClock() {
      const now = new Date();
      document.getElementById("live-clock").textContent =
        now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
        + "  ·  " + now.toLocaleTimeString("en-US", { hour12: false });
    }

    document.getElementById("btn-reset").addEventListener("click", clearAllFilters);
    document.getElementById("btn-clear-all").addEventListener("click", clearAllFilters);
    ["f-source","f-urgency-class","f-event","f-severity","f-location"].forEach(id => {
      document.getElementById(id).addEventListener("input", refresh);
      document.getElementById(id).addEventListener("change", refresh);
    });

    document.getElementById("page-size").addEventListener("change", (e) => {
      const size = parseInt(e.target.value, 10);
      savePageSize(size);
      currentPage = 1;
      renderTableBody();
    });

    document.getElementById("queue-size").addEventListener("change", (e) => {
      const size = parseInt(e.target.value, 10);
      saveQueueSize(size);
      renderQueue(getFiltered());
    });

    populateFilters();
    initPageSize();
    initQueueSize();
    initTableSorting();
    refresh();
    tickClock();
    setInterval(tickClock, 1000);
    window.addEventListener("resize", () => {
      resizeCharts();
      adjustQueueLayout();
    });
    window.addEventListener("load", () => {
      requestAnimationFrame(() => {
        resizeCharts();
        adjustQueueLayout();
      });
    });
    window.addEventListener("scroll", hideQueueTooltip, true);
    window.addEventListener("scroll", hideSummaryTooltip, true);
"""

OUT.write_text(
    "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
    "  <meta charset=\"utf-8\"/>\n"
    "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
    "  <title>National Incident Command Center — EDS6397 Group 01</title>\n"
    "  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\"/>\n"
    "  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin/>\n"
    "  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap\" rel=\"stylesheet\"/>\n"
    "  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>\n"
    "  <style>" + CSS + "\n  </style>\n</head>\n<body>\n"
    + HTML_BODY
    + "\n  <script>\n    "
    + data_block
    + JS_TAIL
    + "\n  </script>\n</body>\n</html>\n",
    encoding="utf-8",
)
print(f"Wrote {OUT} ({len(data['records'])} records embedded)")
