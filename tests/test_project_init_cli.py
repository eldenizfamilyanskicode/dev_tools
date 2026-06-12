from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_init.cli import ProjectInitCliContribution


class RecordingProjectInitService:
    def __init__(self) -> None:
        self.initialize_arguments: dict[str, Any] | None = None
        self.plan_arguments: dict[str, Any] | None = None

    def initialize_project(self, **keyword_arguments: Any) -> Path:
        self.initialize_arguments = keyword_arguments
        requested_project_root: Path | None = keyword_arguments[
            "requested_project_root"
        ]

        if requested_project_root is None:
            return Path.cwd()

        return requested_project_root

    def render_initialization_plan(self, **keyword_arguments: Any) -> str:
        self.plan_arguments = keyword_arguments
        return "Project bootstrap plan\n"


def build_init_parser(
    recording_service: RecordingProjectInitService,
) -> argparse.ArgumentParser:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers = argument_parser.add_subparsers(dest="command", required=True)
    contribution: ProjectInitCliContribution = ProjectInitCliContribution(
        cli_argument_reader=CliArgumentReader(),
        cli_shared_argument_registrar=CliSharedArgumentRegistrar(),
        project_init_service=recording_service,  # type: ignore[arg-type]
    )
    contribution.register_commands(subparsers)
    return argument_parser


def run_init_command(raw_arguments: list[str]) -> RecordingProjectInitService:
    recording_service: RecordingProjectInitService = RecordingProjectInitService()
    argument_parser: argparse.ArgumentParser = build_init_parser(recording_service)
    arguments: argparse.Namespace = argument_parser.parse_args(raw_arguments)
    result_code: int = arguments.command_handler(arguments)

    assert result_code == 0
    return recording_service


def test_default_init_resolves_full_all_high() -> None:
    recording_service: RecordingProjectInitService = run_init_command(["init"])

    assert recording_service.initialize_arguments is not None
    assert (
        recording_service.initialize_arguments["application_type"]
        == ApplicationType.FULL
    )
    assert recording_service.initialize_arguments["tool_names"] == (ToolName.ALL,)
    assert (
        recording_service.initialize_arguments["strictness_level"]
        == StrictnessLevel.HIGH
    )


def test_explicit_init_arguments_parse_correctly() -> None:
    recording_service: RecordingProjectInitService = run_init_command(
        [
            "init",
            "--application-type",
            "ts",
            "--toolset",
            "prettier",
            "--strictness",
            "medium",
        ]
    )

    assert recording_service.initialize_arguments is not None
    assert (
        recording_service.initialize_arguments["application_type"]
        == ApplicationType.TYPESCRIPT
    )
    assert recording_service.initialize_arguments["tool_names"] == (ToolName.PRETTIER,)
    assert (
        recording_service.initialize_arguments["strictness_level"]
        == StrictnessLevel.MEDIUM
    )


def test_comma_separated_toolset_parses_correctly() -> None:
    recording_service: RecordingProjectInitService = run_init_command(
        ["init", "--toolset", "ruff,pyright"]
    )

    assert recording_service.initialize_arguments is not None
    assert recording_service.initialize_arguments["tool_names"] == (
        ToolName.RUFF,
        ToolName.PYRIGHT,
    )


def test_repeatable_toolset_parses_correctly() -> None:
    recording_service: RecordingProjectInitService = run_init_command(
        ["init", "--toolset", "ruff", "--toolset", "pyright"]
    )

    assert recording_service.initialize_arguments is not None
    assert recording_service.initialize_arguments["tool_names"] == (
        ToolName.RUFF,
        ToolName.PYRIGHT,
    )


def test_dry_run_prints_plan_without_initializing() -> None:
    recording_service: RecordingProjectInitService = run_init_command(
        ["init", "--dry-run"]
    )

    assert recording_service.plan_arguments is not None
    assert recording_service.initialize_arguments is None
