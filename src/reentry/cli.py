"""Command-line entry point: `reentry run` / `reentry list-cases`."""

from __future__ import annotations

from pathlib import Path

import typer

from reentry.generator.boundary import generate_all
from reentry.harness.config import RunConfig
from reentry.harness.runner import Runner
from reentry.report.json_report import to_json
from reentry.report.junit_report import to_junit_xml

app = typer.Typer(add_completion=False)


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, help="Path to a RunConfig TOML file"),
    json_out: Path | None = typer.Option(None, "--json", help="Write JSON report to this path"),
    junit_out: Path | None = typer.Option(None, "--junit", help="Write JUnit XML report to this path"),
) -> None:
    """Run the boundary-condition suite against a target and report findings."""
    run_config = RunConfig.from_toml(config)
    findings = Runner(run_config).run()

    if json_out is not None:
        json_out.write_text(to_json(findings))
    if junit_out is not None:
        junit_out.write_text(to_junit_xml(findings))

    unsafe = [f for f in findings if f.verdict.is_unsafe]
    for f in unsafe:
        typer.echo(f"[{f.verdict.value}] {f.case.name}: {f.detail}", err=True)
    typer.echo(f"{len(findings)} cases run, {len(unsafe)} unsafe findings")

    raise typer.Exit(code=1 if unsafe else 0)


@app.command("list-cases")
def list_cases() -> None:
    """Print every generated test case name and category without running anything."""
    for case in generate_all():
        typer.echo(f"{case.category}\t{case.name}")


if __name__ == "__main__":
    app()
