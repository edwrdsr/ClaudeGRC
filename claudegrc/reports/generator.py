"""PDF report generator using Jinja2 templates + WeasyPrint."""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template
from rich.console import Console

from claudegrc.evidence.store import EvidenceStore
from claudegrc.utils import REPORTS_DIR

console = Console()

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ClaudeGRC Compliance Report</title>
<style>
  @page { size: letter; margin: 1in 0.75in; }
  * { box-sizing: border-box; }
  body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #1a1a2e;
    font-size: 11pt;
    line-height: 1.5;
  }
  .header {
    border-bottom: 3px solid #d4a574;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }
  .header h1 {
    font-size: 22pt;
    margin: 0 0 4px 0;
    color: #1a1a2e;
    letter-spacing: -0.5px;
  }
  .header .subtitle {
    font-size: 10pt;
    color: #666;
  }
  .summary-grid {
    display: flex;
    gap: 16px;
    margin-bottom: 28px;
  }
  .summary-card {
    flex: 1;
    padding: 14px 18px;
    border-radius: 6px;
    text-align: center;
  }
  .summary-card .count { font-size: 28pt; font-weight: 700; margin: 0; }
  .summary-card .label { font-size: 9pt; text-transform: uppercase; letter-spacing: 1px; }
  .card-pass   { background: #ecfdf5; color: #065f46; }
  .card-fail   { background: #fef2f2; color: #991b1b; }
  .card-partial{ background: #fffbeb; color: #92400e; }
  .card-na     { background: #f3f4f6; color: #374151; }
  h2 {
    font-size: 14pt;
    color: #1a1a2e;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 6px;
    margin-top: 28px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    margin-top: 10px;
  }
  th {
    background: #1a1a2e;
    color: #fff;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
  }
  td {
    padding: 8px 10px;
    border-bottom: 1px solid #e5e7eb;
    vertical-align: top;
  }
  tr:nth-child(even) td { background: #f9fafb; }
  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 8.5pt;
    font-weight: 600;
    text-transform: uppercase;
  }
  .badge-pass    { background: #d1fae5; color: #065f46; }
  .badge-fail    { background: #fee2e2; color: #991b1b; }
  .badge-partial { background: #fef3c7; color: #92400e; }
  .badge-na      { background: #e5e7eb; color: #374151; }
  .evidence-section { margin-top: 28px; }
  .footer {
    margin-top: 36px;
    padding-top: 12px;
    border-top: 1px solid #d1d5db;
    font-size: 8pt;
    color: #9ca3af;
    text-align: center;
  }
</style>
</head>
<body>
<div class="header">
  <h1>ClaudeGRC Compliance Report</h1>
  <div class="subtitle">Generated {{ generated_at }} · {{ total_controls }} controls assessed · Evidence records: {{ evidence_count }}</div>
</div>
<div class="summary-grid">
  <div class="summary-card card-pass">
    <p class="count">{{ pass_count }}</p>
    <p class="label">Pass</p>
  </div>
  <div class="summary-card card-fail">
    <p class="count">{{ fail_count }}</p>
    <p class="label">Fail</p>
  </div>
  <div class="summary-card card-partial">
    <p class="count">{{ partial_count }}</p>
    <p class="label">Partial</p>
  </div>
  <div class="summary-card card-na">
    <p class="count">{{ na_count }}</p>
    <p class="label">Not Assessed</p>
  </div>
</div>
<h2>Control Assessments</h2>
<table>
  <thead>
    <tr>
      <th style="width:10%">Control</th>
      <th style="width:12%">Status</th>
      <th style="width:42%">Finding</th>
      <th style="width:36%">Recommendation</th>
    </tr>
  </thead>
  <tbody>
    {% for row in analysis_rows %}
    <tr>
      <td><strong>{{ row.control_id }}</strong></td>
      <td>
        {% if row.status == 'PASS' %}
          <span class="status-badge badge-pass">PASS</span>
        {% elif row.status == 'FAIL' %}
          <span class="status-badge badge-fail">FAIL</span>
        {% elif row.status == 'PARTIAL' %}
          <span class="status-badge badge-partial">PARTIAL</span>
        {% else %}
          <span class="status-badge badge-na">N/A</span>
        {% endif %}
      </td>
      <td>{{ row.finding }}</td>
      <td>{{ row.recommendation or '—' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<div class="evidence-section">
  <h2>Evidence Summary</h2>
  <table>
    <thead>
      <tr>
        <th style="width:8%">ID</th>
        <th style="width:18%">Type</th>
        <th style="width:30%">Source</th>
        <th style="width:24%">SHA-256 (first 16)</th>
        <th style="width:20%">Collected</th>
      </tr>
    </thead>
    <tbody>
      {% for ev in evidence_rows %}
      <tr>
        <td>{{ ev.id }}</td>
        <td>{{ ev.evidence_type }}</td>
        <td>{{ ev.source }}</td>
        <td><code>{{ ev.sha256[:16] }}…</code></td>
        <td>{{ ev.collected_at[:19] }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
<div class="footer">
  ClaudeGRC v0.1.0 · AI-Powered Governance, Risk &amp; Compliance · github.com/Edwrdsr/claudegrc
</div>
</body>
</html>
"""


def generate_report(
    store: EvidenceStore, output_name: str = "compliance_report.pdf"
) -> Path:
    """Render analysis + evidence from DuckDB into a PDF report. Returns output path."""
    try:
        from weasyprint import HTML as WeasyHTML
    except ImportError:
        # Fallback: generate HTML only if WeasyPrint is not available
        console.print(
            "[yellow]WeasyPrint not installed — generating HTML report instead.[/yellow]"
        )
        return _generate_html_fallback(store, output_name)

    analysis_rows = store.get_all_analysis()
    evidence_rows = store.get_all_evidence()
    statuses = [r["status"] for r in analysis_rows]

    context = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_controls": len(analysis_rows),
        "evidence_count": len(evidence_rows),
        "pass_count": statuses.count("PASS"),
        "fail_count": statuses.count("FAIL"),
        "partial_count": statuses.count("PARTIAL"),
        "na_count": statuses.count("NOT_ASSESSED"),
        "analysis_rows": analysis_rows,
        "evidence_rows": evidence_rows,
    }

    html_str = Template(HTML_TEMPLATE).render(**context)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / output_name
    WeasyHTML(string=html_str).write_pdf(str(out_path))
    return out_path


def _generate_html_fallback(store: EvidenceStore, output_name: str) -> Path:
    """Fallback: write HTML report when WeasyPrint is unavailable."""
    analysis_rows = store.get_all_analysis()
    evidence_rows = store.get_all_evidence()
    statuses = [r["status"] for r in analysis_rows]

    context = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_controls": len(analysis_rows),
        "evidence_count": len(evidence_rows),
        "pass_count": statuses.count("PASS"),
        "fail_count": statuses.count("FAIL"),
        "partial_count": statuses.count("PARTIAL"),
        "na_count": statuses.count("NOT_ASSESSED"),
        "analysis_rows": analysis_rows,
        "evidence_rows": evidence_rows,
    }

    html_str = Template(HTML_TEMPLATE).render(**context)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    html_name = output_name.replace(".pdf", ".html")
    out_path = REPORTS_DIR / html_name
    out_path.write_text(html_str)
    return out_path
