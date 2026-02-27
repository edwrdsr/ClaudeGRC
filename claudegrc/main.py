"""ClaudeGRC — AI-powered GRC automation CLI."""

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from claudegrc.utils import DB_PATH

load_dotenv()

app = typer.Typer(
    name="claudegrc",
    help="AI-powered Governance, Risk & Compliance automation with Claude.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def _get_store():
    from claudegrc.evidence.store import EvidenceStore

    return EvidenceStore(DB_PATH)


@app.command()
def collect(
    mock: bool = typer.Option(
        False, "--mock", help="Load mock evidence from mocks/ instead of live AWS"
    ),
):
    """Collect compliance evidence from AWS (or mock fixtures)."""
    store = _get_store()
    if mock:
        from claudegrc.collectors.aws import collect_mock

        console.print(Panel("[bold]Collecting mock evidence…[/bold]", style="blue"))
        count = collect_mock(store)
        console.print(f"\n[green]✓ {count} evidence records stored in DuckDB[/green]")
    else:
        console.print(
            "[yellow]Live AWS collection not yet implemented. Use --mock for now.[/yellow]"
        )
    store.close()


@app.command()
def analyze(
    ai_rmf: bool = typer.Option(
        False, "--ai-rmf", help="Analyze against NIST AI RMF 1.0"
    ),
    csf: bool = typer.Option(False, "--csf", help="Analyze against NIST CSF 2.0"),
    soc2: bool = typer.Option(False, "--soc2", help="Analyze against SOC 2 TSC 2026"),
    model: str = typer.Option(
        "claude-sonnet-4-20250514", "--model", help="Claude model to use"
    ),
):
    """Run Claude-powered compliance analysis against selected frameworks."""
    from claudegrc.agents.mapper import run_analysis

    store = _get_store()
    if store.count() == 0:
        console.print(
            "[red]No evidence in database. Run 'claudegrc collect --mock' first.[/red]"
        )
        store.close()
        raise typer.Exit(1)

    frameworks = []
    if ai_rmf:
        frameworks.append("ai-rmf")
    if csf:
        frameworks.append("csf")
    if soc2:
        frameworks.append("soc2")
    if not frameworks:
        console.print(
            "[yellow]No framework selected. Use --ai-rmf, --csf, or --soc2.[/yellow]"
        )
        store.close()
        raise typer.Exit(1)

    for fw_key in frameworks:
        console.print(
            Panel(f"[bold]Analyzing: {fw_key.upper()}[/bold]", style="magenta")
        )
        assessed = run_analysis(fw_key, store, model=model)
        console.print(
            f"[green]✓ {assessed} controls assessed for {fw_key.upper()}[/green]\n"
        )

    total = store.analysis_count()
    console.print(f"[bold green]Total analysis records in DB: {total}[/bold green]")
    store.close()


@app.command()
def report(
    output: str = typer.Option(
        "compliance_report.pdf", "--output", "-o", help="Output PDF filename"
    ),
):
    """Generate a PDF compliance report from stored analysis results."""
    from claudegrc.reports.generator import generate_report

    store = _get_store()
    if store.analysis_count() == 0:
        console.print(
            "[red]No analysis results. Run 'claudegrc analyze --ai-rmf' first.[/red]"
        )
        store.close()
        raise typer.Exit(1)

    console.print(Panel("[bold]Generating PDF report…[/bold]", style="green"))
    out_path = generate_report(store, output_name=output)
    console.print(f"[bold green]✓ Report saved to {out_path}[/bold green]")
    store.close()


@app.command()
def status():
    """Show current database status (evidence & analysis counts)."""
    store = _get_store()
    ev = store.count()
    an = store.analysis_count()
    console.print(
        Panel(
            f"Evidence records: [bold]{ev}[/bold]\nAnalysis records: [bold]{an}[/bold]\nDatabase: [dim]{DB_PATH}[/dim]",
            title="ClaudeGRC Status",
            style="blue",
        )
    )
    store.close()


if __name__ == "__main__":
    app()
