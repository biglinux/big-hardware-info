"""Tests for inxi output detection and parsing in InxiCollector."""

import subprocess
from unittest.mock import patch

from big_hardware_info.collectors.base_collector import (
    BaseCollector,
    _build_subprocess_env,
)
from big_hardware_info.collectors.inxi_collector import (
    InxiCollector,
    _looks_like_inxi_failure,
)


class TestLooksLikeInxiFailure:
    """Regression guard for the IRC-client detection issue.

    inxi returns exit code 0 AND prints 'You can't run option ...' to stdout
    when it (wrongly) thinks it's running inside an IRC client. Before this
    guard, the collector parsed that text as JSON, failed silently, and the
    UI rendered an empty state for every section.
    """

    def test_irc_client_error_is_failure(self) -> None:
        assert _looks_like_inxi_failure(
            "Error 1: You can't run option help in an IRC client!\n"
        )

    def test_any_irc_client_mention_is_failure(self) -> None:
        assert _looks_like_inxi_failure("IRC client detected, aborting")

    def test_valid_json_array_is_not_failure(self) -> None:
        assert not _looks_like_inxi_failure('[{"System": []}]')

    def test_valid_json_object_is_not_failure(self) -> None:
        assert not _looks_like_inxi_failure('{"foo": 1}')

    def test_empty_output_is_failure(self) -> None:
        assert _looks_like_inxi_failure("")
        assert _looks_like_inxi_failure(None)  # type: ignore[arg-type]

    def test_json_with_leading_whitespace_is_not_failure(self) -> None:
        assert not _looks_like_inxi_failure("\n  [{\"x\": 1}]")


class TestInxiCollectorFailurePaths:
    """Collector must not return bogus 'data' when inxi prints diagnostics."""

    def test_diagnostic_text_triggers_fallback_and_error(self) -> None:
        collector = InxiCollector()
        diag = "Error 1: You can't run option help in an IRC client!"

        with patch.object(collector, "command_exists", return_value=True), \
             patch.object(collector, "run_command", return_value=(True, diag, "")):
            result = collector.collect()

        assert "data" not in result
        assert "error" in result
        assert "inxi returned diagnostic text" in result["error"] or \
               "failed" in result["error"]

    def test_valid_json_returns_data(self) -> None:
        collector = InxiCollector()
        payload = '[{"000#1#0#System": []}]'

        with patch.object(collector, "command_exists", return_value=True), \
             patch.object(collector, "run_command", return_value=(True, payload, "")):
            result = collector.collect()

        assert "data" in result
        assert result["data"] == [{"000#1#0#System": []}]

    def test_missing_inxi_returns_error(self) -> None:
        collector = InxiCollector()
        with patch.object(collector, "command_exists", return_value=False):
            result = collector.collect()
        assert "error" in result
        assert "inxi" in result["error"].lower()


class TestSubprocessEnvironment:
    """Subprocess env/stdin must be defensively normalized."""

    def test_env_forces_c_locale(self) -> None:
        env = _build_subprocess_env()
        assert env["LC_ALL"] == "C"
        assert env["LANG"] == "C"

    def test_env_ensures_sbin_in_path(self) -> None:
        env = _build_subprocess_env()
        path_dirs = env["PATH"].split(":")
        assert "/usr/sbin" in path_dirs
        assert "/sbin" in path_dirs

    def test_run_command_uses_devnull_stdin_and_normalized_env(self) -> None:
        class _TestCollector(BaseCollector):
            def collect(self) -> dict:
                return {}

        collector = _TestCollector()
        fake_result = type("R", (), {
            "returncode": 0, "stdout": "ok\n", "stderr": "",
        })()
        with patch("big_hardware_info.collectors.base_collector.subprocess.run",
                   return_value=fake_result) as mock_run:
            collector.run_command(["echo", "ok"])

        _, kwargs = mock_run.call_args
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["env"]["LC_ALL"] == "C"
