"""Command-line entry point: `reentry run` / `reentry list-cases`."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from pydantic import ValidationError
import typer

from reentry.generator.boundary import generate_all
from reentry.harness.config import RunConfig
from reentry.harness.profiles import TargetProfile
from reentry.harness.runner import Runner
from reentry.report.json_report import to_json
from reentry.report.junit_report import to_junit_xml
from reentry.report.baseline import compare_reports
from reentry.report.provenance import build_provenance

app = typer.Typer(add_completion=False)


def _config_error_message(config: Path, error: ValidationError) -> str:
    details = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    )
    return f"invalid configuration {config}: {details}"


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, help="Path to a RunConfig TOML file"),
    profile: TargetProfile | None = typer.Option(
        None,
        "--profile",
        help="Named target profile; cannot be combined with category filters in the config",
    ),
    json_out: Path | None = typer.Option(None, "--json", help="Write JSON report to this path"),
    junit_out: Path | None = typer.Option(None, "--junit", help="Write JUnit XML report to this path"),
) -> None:
    """Run the boundary-condition suite against a target and report findings."""
    try:
        run_config = RunConfig.from_toml(config)
    except ValidationError as error:
        raise typer.BadParameter(
            _config_error_message(config, error), param_hint="--config"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise typer.BadParameter(
            f"invalid TOML in {config}: {error}", param_hint="--config"
        ) from error
    except OSError as error:
        raise typer.BadParameter(
            f"cannot read config {config}: {error}", param_hint="--config"
        ) from error
    if profile is not None:
        if run_config.include_categories is not None or run_config.exclude_categories:
            raise typer.BadParameter(
                "cannot be combined with include_categories or exclude_categories in the config",
                param_hint="--profile",
            )
        run_config = run_config.with_profile(profile)
    try:
        findings = Runner(run_config).run()
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--config or --profile") from error

    provenance = build_provenance(run_config)

    if json_out is not None:
        json_out.write_text(
            to_json(findings, profile=run_config.profile, provenance=provenance)
        )
    if junit_out is not None:
        junit_out.write_text(
            to_junit_xml(findings, profile=run_config.profile, provenance=provenance)
        )

    unsafe = [f for f in findings if f.verdict.is_unsafe]
    for f in unsafe:
        typer.echo(f"[{f.verdict.value}] {f.case.name}: {f.detail}", err=True)
    profile_summary = f" [{run_config.profile.value}]" if run_config.profile else ""
    typer.echo(f"{len(findings)} cases run, {len(unsafe)} unsafe findings{profile_summary}")

    raise typer.Exit(code=1 if unsafe else 0)


@app.command("list-cases")
def list_cases() -> None:
    """Print every generated test case name and category without running anything."""
    for case in generate_all():
        typer.echo(f"{case.category}\t{case.name}")


@app.command()
def compare(
    baseline: Path = typer.Option(..., "--baseline", exists=True, help="Known-good JSON report"),
    actual: Path = typer.Option(..., "--actual", exists=True, help="New JSON report to compare"),
    json_out: Path | None = typer.Option(None, "--json", help="Write comparison details to this path"),
) -> None:
    """Compare two JSON reports and fail when cases or verdicts differ."""
    try:
        baseline_report = json.loads(baseline.read_text())
        actual_report = json.loads(actual.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise typer.BadParameter(f"cannot read JSON report: {error}") from error

    try:
        differences = compare_reports(baseline_report, actual_report)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--baseline/--actual") from error
    result = {"differences": differences, "difference_count": len(differences)}
    if json_out is not None:
        json_out.write_text(json.dumps(result, indent=2) + "\n")
    if differences:
        for difference in differences:
            typer.echo(
                f"[{difference['kind']}] {difference['name']}: "
                f"{difference['baseline']} -> {difference['actual']}",
                err=True,
            )
        raise typer.Exit(code=1)
    typer.echo("baseline comparison passed: no case or verdict differences")


if __name__ == "__main__":
    app()
