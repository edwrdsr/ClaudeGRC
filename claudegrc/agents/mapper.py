"""Compliance mapper agent — evaluates evidence against framework controls using Claude."""

import json

import yaml
from anthropic import Anthropic
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from claudegrc.agents.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from claudegrc.evidence.store import EvidenceStore
from claudegrc.utils import FRAMEWORKS_DIR, now_iso

console = Console()

FRAMEWORK_FILES: dict = {
    "ai-rmf": "nist_ai_rmf_1.0.yaml",
    "csf": "nist_csf_2.0.yaml",
    "soc2": "soc2_tsc_2026.yaml",
}


def _load_framework(key: str) -> dict:
    filename = FRAMEWORK_FILES.get(key)
    if not filename:
        raise ValueError(
            f"Unknown framework key '{key}'. Choose from: {list(FRAMEWORK_FILES)}"
        )
    path = FRAMEWORKS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Framework file not found: {path}")
    return yaml.safe_load(path.read_text())


def _iter_controls(fw: dict):
    """Yield (control_dict, category_name) for every control in a framework."""
    for func in fw.get("functions", []):
        for cat in func.get("categories", []):
            for ctrl in cat.get("controls", []):
                yield ctrl, func.get("name", "")
    for cat in fw.get("categories", []):
        for ctrl in cat.get("controls", []):
            yield ctrl, cat.get("name", "")


def _gather_evidence(store: EvidenceStore, evidence_types: list) -> str:
    """Pull matching evidence from the store, return as JSON string."""
    combined = []
    for et in evidence_types:
        combined.extend(store.get_by_type(et))
    if not combined:
        return "[]"
    return json.dumps(combined[:20], indent=2, default=str)


def run_analysis(
    framework_key: str,
    store: EvidenceStore,
    model: str = "claude-sonnet-4-20250514",
) -> int:
    """Run the Claude-powered compliance analysis pipeline. Returns count of assessed controls."""
    fw_raw = _load_framework(framework_key)
    fw_meta = fw_raw.get("framework", {})
    fw_name = fw_meta.get("name", framework_key)

    client = Anthropic()

    controls = list(_iter_controls(fw_raw))
    if not controls:
        console.print("[red]No controls found in framework file.[/red]")
        return 0

    console.print(
        f"\n[bold]Analyzing {len(controls)} controls against {fw_name}…[/bold]\n"
    )

    assessed = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Evaluating…", total=len(controls))

        for ctrl, func_name in controls:
            ctrl_id = ctrl["id"]
            progress.update(task, description=f"[cyan]{ctrl_id}[/cyan] — {func_name}")

            evidence_types = ctrl.get("evidence_types", [])
            evidence_json = _gather_evidence(store, evidence_types)

            if evidence_json == "[]":
                store.save_analysis(
                    framework=fw_name,
                    control_id=ctrl_id,
                    status="NOT_ASSESSED",
                    finding="No matching evidence was collected for this control.",
                    recommendation="Collect relevant evidence and re-run analysis.",
                    analyzed_at=now_iso(),
                )
                assessed += 1
                progress.advance(task)
                continue

            user_msg = USER_PROMPT_TEMPLATE.format(
                framework_name=fw_name,
                control_id=ctrl_id,
                control_text=ctrl.get("text", ""),
                check=ctrl.get("check", ""),
                evidence_type=", ".join(evidence_types),
                evidence_json=evidence_json,
            )

            try:
                resp = client.messages.create(
                    model=model,
                    max_tokens=800,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                )
                raw = resp.content[0].text.strip()
                result = json.loads(raw)

                store.save_analysis(
                    framework=fw_name,
                    control_id=result.get("control_id", ctrl_id),
                    status=result.get("status", "NOT_ASSESSED"),
                    finding=result.get("finding", ""),
                    recommendation=result.get("recommendation", ""),
                    analyzed_at=now_iso(),
                )
            except json.JSONDecodeError:
                console.print(
                    f"  [yellow]⚠ Non-JSON response for {ctrl_id} — storing raw[/yellow]"
                )
                store.save_analysis(
                    framework=fw_name,
                    control_id=ctrl_id,
                    status="NOT_ASSESSED",
                    finding=f"Claude returned non-JSON: {raw[:200]}",
                    recommendation="Re-run analysis or review prompt.",
                    analyzed_at=now_iso(),
                )
            except Exception as e:
                console.print(f"  [red]✗ Error on {ctrl_id}: {e}[/red]")
                store.save_analysis(
                    framework=fw_name,
                    control_id=ctrl_id,
                    status="NOT_ASSESSED",
                    finding=f"Analysis error: {e}",
                    recommendation="Check API key and connectivity.",
                    analyzed_at=now_iso(),
                )

            assessed += 1
            progress.advance(task)

    return assessed
