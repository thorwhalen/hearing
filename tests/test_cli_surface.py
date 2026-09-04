"""Characterization tests for the ``hearing`` command-line surface.

Written during the argh -> ``cw`` migration. Every assertion was recorded from
the argh implementation *before* the swap, so this file fences the published
grammar rather than describing the new one.

The load-bearing one is :meth:`TestNamingPolicy.test_live_takes_an_optional_positional_file`.
``hearing`` explicitly selected argh's ``BY_NAME_IF_KWONLY`` name-mapping policy,
and it is the only thing standing between ``hearing live [FILE]`` and
``hearing live [-p PATH]``: under the legacy rule (a default makes it an option)
``live``'s ``path`` parameter becomes a flag. Flipping the convention in
``hearing/cli.py`` makes that test fail — which is how we know it can.
"""

import subprocess
import sys

import pytest

from hearing import cli


COMMANDS = ("transcribe", "summarize", "live", "serve", "meetings", "info")


def usage_of(stdout):
    """The ``usage:`` block, whitespace-collapsed — width-independent."""
    lines = []
    for line in stdout.splitlines():
        if not line.strip():
            break
        lines.append(line.strip())
    return " ".join(lines)


def run_cli(*argv):
    """Run ``python -m hearing.cli`` in a subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "hearing.cli", *argv],
        capture_output=True,
        text=True,
        env={"COLUMNS": "100", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        timeout=180,
    )


class TestGrammar:
    def test_top_level_help_lists_every_command(self):
        proc = run_cli("--help")
        assert proc.returncode == 0
        for name in COMMANDS:
            assert name in proc.stdout
        assert "meeting transcription & AI agents" in proc.stdout

    @pytest.mark.parametrize("command", COMMANDS)
    def test_each_subcommand_has_help(self, command):
        proc = run_cli(command, "--help")
        assert proc.returncode == 0
        assert proc.stdout.startswith(f"usage: cli.py {command}")


class TestNamingPolicy:
    """``BY_NAME_IF_KWONLY`` — positional params stay positional."""

    def test_live_takes_an_optional_positional_file(self):
        """`hearing live [FILE]`, NOT `hearing live [-p PATH]`.

        ``live``'s ``path`` is a positional-or-keyword parameter with a default.
        Under argh's legacy rule that would make it an option; under
        ``BY_NAME_IF_KWONLY`` it stays an optional positional. This is the one
        command in the CLI where the two policies disagree.
        """
        usage = usage_of(run_cli("live", "--help").stdout)
        assert usage.endswith("[path]")
        assert "--path" not in usage

    def test_transcribe_takes_a_required_positional_path(self):
        usage = usage_of(run_cli("transcribe", "--help").stdout)
        assert usage.endswith(" path")
        assert "--path" not in usage

    def test_keyword_only_params_are_options(self):
        usage = run_cli("transcribe", "--help").stdout
        for fragment in ("-e ENGINE", "--engine ENGINE", "-m MODEL", "--fmt FMT"):
            assert fragment in usage


class TestExitCodes:
    def test_no_arguments_prints_usage_to_stdout_and_exits_zero(self):
        """argh's behaviour, which plain argparse does NOT reproduce."""
        proc = run_cli()
        assert proc.returncode == 0
        assert proc.stdout.startswith("usage:")
        assert proc.stderr == ""

    def test_unknown_command_exits_two(self):
        proc = run_cli("no-such-command")
        assert proc.returncode == 2
        assert "invalid choice" in proc.stderr

    def test_unknown_flag_exits_two(self):
        proc = run_cli("info", "--no-such-flag")
        assert proc.returncode == 2

    def test_missing_required_positional_exits_two(self):
        proc = run_cli("transcribe")
        assert proc.returncode == 2

    def test_bad_int_option_value_exits_two(self):
        """``--block-ms`` is typed ``int`` by inference from its default."""
        proc = run_cli("live", "--block-ms", "abc")
        assert proc.returncode == 2
        assert "invalid int value" in proc.stderr

    def test_main_raises_systemexit_carrying_the_code(self):
        """The ``raise SystemExit(...)`` in ``cli.main`` is load-bearing.

        ``cw.run`` returns the exit code where argh's ``parser.dispatch`` exited
        by itself; without the raise, every argument error would exit 0.
        """
        with pytest.raises(SystemExit) as exc:
            cli.main(["no-such-command"])
        assert exc.value.code == 2
