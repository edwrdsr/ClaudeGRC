import typer
from rich.console import Console
from dotenv import load_dotenv
from typing import Optional
from claudegrc.collectors.aws import collect_aws_evidence
from claudegrc.agents.mapper import run_agent_pipeline
from claudegrc.reports.generator import generate_report
from claudegrc.evidence.store import EvidenceStore
from claudegrc.config import load_frameworks

load_dotenv()
app = typer.Typer()
console = Console()


@app.command()
def collect(
    cloud: str = "aws",
    frameworks: str = "soc2",
    profile: Optional[str] = None,
    mock: bool = False,
):
    """Collect evidence from cloud provider."""
    evidence = collect_aws_evidence(profile, mock) if cloud == "aws" else {}
    store = EvidenceStore()
    store.save_evidence(evidence)
    console.print("[green]Evidence collected and stored.[/green]")


@app.command()
def analyze(ai_rmf: bool = False, frameworks: str = "soc2"):
    """Run Claude agentic analysis."""
    store = EvidenceStore()
    evidence = store.load_evidence()
    frameworks_list = load_frameworks(frameworks.split(","))
    analysis = run_agent_pipeline(evidence, frameworks_list, ai_rmf)
    store.save_analysis(analysis)
    console.print("[green]Analysis complete.[/green]")


@app.command()
def report(format: str = "pdf"):
    """Generate compliance report."""
    store = EvidenceStore()
    analysis = store.load_analysis()
    generate_report(analysis, format)
    console.print(f"[green]Report generated: compliance_report.{format}[/green]")


if __name__ == "__main__":
    app()
