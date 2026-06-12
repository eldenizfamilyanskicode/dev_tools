from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path

import pytest

from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.export_context.cli import ExportContextCliContribution


class RecordingExportContextService:
    def __init__(self) -> None:
        self.requested_project_root: Path | None = None
        self.should_include_tree: bool | None = None
        self.should_include_about: bool | None = None

    def export_context(
        self,
        requested_project_root: Path | None,
        should_include_tree: bool,
        should_include_about: bool,
    ) -> list[Path]:
        self.requested_project_root = requested_project_root
        self.should_include_tree = should_include_tree
        self.should_include_about = should_include_about
        return []


def build_export_context_parser(
    recording_service: RecordingExportContextService,
) -> argparse.ArgumentParser:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers = argument_parser.add_subparsers(dest="command", required=True)
    contribution: ExportContextCliContribution = ExportContextCliContribution(
        cli_argument_reader=CliArgumentReader(),
        cli_shared_argument_registrar=CliSharedArgumentRegistrar(),
        export_context_service=recording_service,  # type: ignore[arg-type]
    )
    contribution.register_commands(subparsers)
    return argument_parser


def test_run_help_prints_with_windows_legacy_encoding() -> None:
    recording_service: RecordingExportContextService = RecordingExportContextService()
    argument_parser: argparse.ArgumentParser = build_export_context_parser(
        recording_service,
    )
    output_bytes: io.BytesIO = io.BytesIO()
    output_stream: io.TextIOWrapper = io.TextIOWrapper(
        output_bytes,
        encoding="cp1252",
        errors="strict",
    )

    with (
        contextlib.redirect_stdout(output_stream),
        pytest.raises(SystemExit) as system_exit,
    ):
        argument_parser.parse_args(["run", "--help"])

    output_stream.flush()
    assert system_exit.value.code == 0
