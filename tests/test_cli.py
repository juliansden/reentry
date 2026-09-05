import json

from typer.testing import CliRunner

from reentry.cli import app
from reentry.generator.cases import PacketCase
from reentry.harness.runner import Finding
from reentry.oracle.base import Verdict


def _write_config(path):
    path.write_text(
        """[transport]
host = "127.0.0.1"
port = 1234
"""
    )


def test_run_profile_is_propagated_to_reports(tmp_path, monkeypatch):
    config = tmp_path / "reentry.toml"
    json_out = tmp_path / "report.json"
    _write_config(config)
    finding = Finding(
        case=PacketCase("ci_lab_noop", "known_good", b"packet", False, expect_accept=True),
        verdict=Verdict.CLEAN_ACCEPT,
        detail="accepted",
        evidence={"before": {"command": 0}, "after": {"command": 1}},
    )
    captured = {}

    def fake_run(self):
        captured["profile"] = self._config.profile
        return [finding]

    monkeypatch.setattr("reentry.cli.Runner.run", fake_run)
    result = CliRunner().invoke(
        app,
        ["run", "--config", str(config), "--profile", "smoke", "--json", str(json_out)],
    )

    assert result.exit_code == 0, result.output
    assert captured["profile"].value == "smoke"
    report = json.loads(json_out.read_text())
    assert report["profile"] == "smoke"
    assert report["findings"][0]["evidence"] == finding.evidence
    assert "[smoke]" in result.output


def test_run_profile_does_not_hide_unexpected_accept(tmp_path, monkeypatch):
    config = tmp_path / "reentry.toml"
    _write_config(config)
    finding = Finding(
        case=PacketCase("bad_checksum", "command_malformed", b"packet", True),
        verdict=Verdict.UNEXPECTED_ACCEPT,
        detail="accepted malformed command",
    )
    monkeypatch.setattr("reentry.cli.Runner.run", lambda self: [finding])

    result = CliRunner().invoke(app, ["run", "--config", str(config), "--profile", "stock-cfs"])

    assert result.exit_code == 1
    assert "[unexpected_accept] bad_checksum" in result.output


def test_run_rejects_unknown_profile(tmp_path):
    config = tmp_path / "reentry.toml"
    _write_config(config)

    result = CliRunner().invoke(app, ["run", "--config", str(config), "--profile", "unknown"])

    assert result.exit_code == 2
    assert "Invalid value" in result.output
    assert "unknown" in result.output
    assert "stock-cfs" in result.output


def test_run_rejects_profile_with_config_category_filters(tmp_path):
    config = tmp_path / "reentry.toml"
    config.write_text(
        """include_categories = ["known_good"]

[transport]
host = "127.0.0.1"
port = 1234
"""
    )

    result = CliRunner().invoke(app, ["run", "--config", str(config), "--profile", "smoke"])

    assert result.exit_code == 2
    assert "Invalid value" in result.output
    assert "cannot be combined with include_categories" in result.output
    assert "exclude_categories in the config" in result.output


def test_run_reports_invalid_configuration_without_traceback(tmp_path):
    config = tmp_path / "reentry.toml"
    config.write_text(
        """[transport]
host = "127.0.0.1"
port = 0
"""
    )

    result = CliRunner().invoke(app, ["run", "--config", str(config)])

    assert result.exit_code == 2
    assert "invalid configuration" in result.output
    assert "port" in result.output
    assert "between 1 and 65535" in result.output
    assert "Traceback" not in result.output


def test_run_reports_invalid_toml_without_traceback(tmp_path):
    config = tmp_path / "reentry.toml"
    config.write_text("[transport\n")

    result = CliRunner().invoke(app, ["run", "--config", str(config)])

    assert result.exit_code == 2
    assert "invalid TOML" in result.output
    assert config.name in result.output
    assert "Traceback" not in result.output


def test_run_rejects_hardened_profile_without_adapter_capability(tmp_path):
    config = tmp_path / "reentry.toml"
    _write_config(config)

    result = CliRunner().invoke(app, ["run", "--config", str(config), "--profile", "hardened-cfs"])

    assert result.exit_code == 2
    assert "enforces_hardened_policy" in result.output
    assert "Traceback" not in result.output


def test_compare_reports_passes_identical_reports(tmp_path):
    baseline = tmp_path / "baseline.json"
    actual = tmp_path / "actual.json"
    content = {"findings": [{"name": "case", "verdict": "clean_reject"}]}
    baseline.write_text(json.dumps(content))
    actual.write_text(json.dumps(content))

    result = CliRunner().invoke(
        app, ["compare", "--baseline", str(baseline), "--actual", str(actual)]
    )

    assert result.exit_code == 0
    assert "comparison passed" in result.output


def test_compare_reports_fails_on_verdict_change_and_writes_details(tmp_path):
    baseline = tmp_path / "baseline.json"
    actual = tmp_path / "actual.json"
    comparison = tmp_path / "comparison.json"
    baseline.write_text(json.dumps({"findings": [{"name": "case", "verdict": "clean_reject"}]}))
    actual.write_text(json.dumps({"findings": [{"name": "case", "verdict": "hang"}]}))

    result = CliRunner().invoke(
        app,
        [
            "compare",
            "--baseline",
            str(baseline),
            "--actual",
            str(actual),
            "--json",
            str(comparison),
        ],
    )

    assert result.exit_code == 1
    assert "verdict_changed" in result.output
    assert json.loads(comparison.read_text())["difference_count"] == 1


def test_compare_reports_rejects_invalid_report_schema_without_traceback(tmp_path):
    baseline = tmp_path / "baseline.json"
    actual = tmp_path / "actual.json"
    baseline.write_text(json.dumps({"findings": [{"name": "case", "verdict": "clean_reject"}]}))
    actual.write_text(json.dumps({"findings": [{}]}))

    result = CliRunner().invoke(
        app, ["compare", "--baseline", str(baseline), "--actual", str(actual)]
    )

    assert result.exit_code == 2
    assert "Invalid value for --baseline/--actual" in result.output
    assert "actual finding at index 0" in result.output
    assert "Traceback" not in result.output
