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
    assert "Invalid value for '--profile'" in result.output