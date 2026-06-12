from __future__ import annotations

import argparse

from dev_tools.cli.shared_arguments import CliArgumentReader
from dev_tools.global_cli.cli import GlobalCliCliContribution


class RecordingGlobalCliSetupService:
    def __init__(self) -> None:
        self.dry_run: bool | None = None
        self.status_was_rendered: bool = False

    def setup_global_cli(self, dry_run: bool = False) -> str:
        self.dry_run = dry_run
        return "setup\n"

    def render_global_cli_status(self) -> str:
        self.status_was_rendered = True
        return "status\n"


def build_global_cli_parser(
    recording_service: RecordingGlobalCliSetupService,
) -> argparse.ArgumentParser:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers = argument_parser.add_subparsers(dest="command", required=True)
    contribution: GlobalCliCliContribution = GlobalCliCliContribution(
        cli_argument_reader=CliArgumentReader(),
        global_cli_setup_service=recording_service,  # type: ignore[arg-type]
    )
    contribution.register_commands(subparsers)
    return argument_parser


def run_global_cli_command(
    raw_arguments: list[str],
) -> RecordingGlobalCliSetupService:
    recording_service: RecordingGlobalCliSetupService = RecordingGlobalCliSetupService()
    argument_parser: argparse.ArgumentParser = build_global_cli_parser(
        recording_service
    )
    arguments: argparse.Namespace = argument_parser.parse_args(raw_arguments)
    result_code: int = arguments.command_handler(arguments)

    assert result_code == 0
    return recording_service


def test_global_cli_setup_sets_dry_run() -> None:
    recording_service: RecordingGlobalCliSetupService = run_global_cli_command(
        ["global-cli", "setup", "--dry-run"]
    )

    assert recording_service.dry_run is True


def test_global_cli_status_renders_status() -> None:
    recording_service: RecordingGlobalCliSetupService = run_global_cli_command(
        ["global-cli", "status"]
    )

    assert recording_service.status_was_rendered is True
