from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.project_policy.cli import ProjectPolicyCliContribution


class RecordingProjectPolicyService:
    def __init__(self) -> None:
        self.plan_arguments: dict[str, Any] | None = None
        self.apply_arguments: dict[str, Any] | None = None

    def render_registered_projects(self, refresh: bool) -> str:
        return f"projects refresh={refresh}\n"

    def render_policy_status(self, **keyword_arguments: Any) -> str:
        return "status\n"

    def render_update_plan(self, **keyword_arguments: Any) -> str:
        self.plan_arguments = keyword_arguments
        return "plan\n"

    def apply_policy_updates(self, **keyword_arguments: Any) -> str:
        self.apply_arguments = keyword_arguments
        return "apply\n"


def build_policy_parser(
    recording_service: RecordingProjectPolicyService,
) -> argparse.ArgumentParser:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers = argument_parser.add_subparsers(dest="command", required=True)
    contribution: ProjectPolicyCliContribution = ProjectPolicyCliContribution(
        cli_argument_reader=CliArgumentReader(),
        cli_shared_argument_registrar=CliSharedArgumentRegistrar(),
        project_policy_service=recording_service,  # type: ignore[arg-type]
    )
    contribution.register_commands(subparsers)
    return argument_parser


def run_policy_command(
    raw_arguments: list[str],
) -> RecordingProjectPolicyService:
    recording_service: RecordingProjectPolicyService = RecordingProjectPolicyService()
    argument_parser: argparse.ArgumentParser = build_policy_parser(recording_service)
    arguments: argparse.Namespace = argument_parser.parse_args(raw_arguments)
    result_code: int = arguments.command_handler(arguments)

    assert result_code == 0
    return recording_service


def test_policies_plan_all_sets_include_all_projects() -> None:
    recording_service: RecordingProjectPolicyService = run_policy_command(
        ["policies", "plan", "--all"]
    )

    assert recording_service.plan_arguments is not None
    assert recording_service.plan_arguments["include_all_projects"] is True
    assert recording_service.plan_arguments["requested_project_root"] is None
    assert recording_service.plan_arguments["force"] is False


def test_policies_plan_force_sets_force() -> None:
    recording_service: RecordingProjectPolicyService = run_policy_command(
        ["policies", "plan", "--force"]
    )

    assert recording_service.plan_arguments is not None
    assert recording_service.plan_arguments["force"] is True


def test_policies_apply_project_root_is_resolved() -> None:
    recording_service: RecordingProjectPolicyService = run_policy_command(
        ["policies", "apply", "--project-root", "."]
    )

    assert recording_service.apply_arguments is not None
    assert recording_service.apply_arguments["include_all_projects"] is False
    assert isinstance(recording_service.apply_arguments["requested_project_root"], Path)
    assert recording_service.apply_arguments["force"] is False


def test_policies_apply_force_sets_force() -> None:
    recording_service: RecordingProjectPolicyService = run_policy_command(
        ["policies", "apply", "--force"]
    )

    assert recording_service.apply_arguments is not None
    assert recording_service.apply_arguments["force"] is True
