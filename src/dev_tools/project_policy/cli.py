from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.project_policy.application_service import ProjectPolicyService


class ProjectPolicyCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        project_policy_service: ProjectPolicyService,
    ) -> None:
        self.cli_argument_reader = cli_argument_reader
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.project_policy_service = project_policy_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        self.register_projects_command(subparsers)
        self.register_policies_command(subparsers)

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return ()

    def register_projects_command(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        projects_parser: argparse.ArgumentParser = subparsers.add_parser(
            "projects",
            help="Inspect globally registered dev-tools projects.",
            description="Inspect globally registered dev-tools projects.",
            formatter_class=DevToolsHelpFormatter,
        )
        projects_subparsers = projects_parser.add_subparsers(
            dest="projects_command",
            required=True,
        )
        list_parser: argparse.ArgumentParser = projects_subparsers.add_parser(
            "list",
            help="List projects from the global dev-tools index.",
            description="List projects from the global dev-tools index.",
            formatter_class=DevToolsHelpFormatter,
        )
        list_parser.set_defaults(command_handler=self.handle_projects_list_command)

        doctor_parser: argparse.ArgumentParser = projects_subparsers.add_parser(
            "doctor",
            help="Refresh and list project index statuses.",
            description="Refresh and list project index statuses.",
            formatter_class=DevToolsHelpFormatter,
        )
        doctor_parser.set_defaults(command_handler=self.handle_projects_doctor_command)

    def register_policies_command(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        policies_parser: argparse.ArgumentParser = subparsers.add_parser(
            "policies",
            help="Inspect and apply explicit project policies.",
            description="Inspect and apply explicit project policies.",
            formatter_class=DevToolsHelpFormatter,
        )
        policies_subparsers = policies_parser.add_subparsers(
            dest="policies_command",
            required=True,
        )
        status_parser: argparse.ArgumentParser = policies_subparsers.add_parser(
            "status",
            help="Show applied policy manifest status.",
            description="Show applied policy manifest status.",
            formatter_class=DevToolsHelpFormatter,
        )
        self.add_policy_target_arguments(status_parser)
        status_parser.set_defaults(command_handler=self.handle_policies_status_command)

        plan_parser: argparse.ArgumentParser = policies_subparsers.add_parser(
            "plan",
            help="Print policy update plan without modifying files.",
            description="Print policy update plan without modifying files.",
            formatter_class=DevToolsHelpFormatter,
        )
        self.add_policy_target_arguments(plan_parser)
        plan_parser.set_defaults(command_handler=self.handle_policies_plan_command)

        apply_parser: argparse.ArgumentParser = policies_subparsers.add_parser(
            "apply",
            help="Apply policy updates explicitly.",
            description="Apply policy updates explicitly.",
            formatter_class=DevToolsHelpFormatter,
        )
        self.add_policy_target_arguments(apply_parser)
        apply_parser.set_defaults(command_handler=self.handle_policies_apply_command)

    def add_policy_target_arguments(
        self,
        argument_parser: argparse.ArgumentParser,
    ) -> None:
        self.cli_shared_argument_registrar.add_project_root_argument(argument_parser)
        argument_parser.add_argument(
            "--all",
            action="store_true",
            dest="include_all_projects",
            help="Use all active projects from the global dev-tools index.",
        )

    def handle_projects_list_command(self, arguments: argparse.Namespace) -> int:
        print(
            self.project_policy_service.render_registered_projects(refresh=False),
            end="",
        )
        return 0

    def handle_projects_doctor_command(self, arguments: argparse.Namespace) -> int:
        print(
            self.project_policy_service.render_registered_projects(refresh=True), end=""
        )
        return 0

    def handle_policies_status_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None = (
            self.cli_argument_reader.resolve_optional_project_root(arguments)
        )
        include_all_projects: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_all_projects",
        )
        print(
            self.project_policy_service.render_policy_status(
                requested_project_root=requested_project_root,
                include_all_projects=include_all_projects,
            ),
            end="",
        )
        return 0

    def handle_policies_plan_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None = (
            self.cli_argument_reader.resolve_optional_project_root(arguments)
        )
        include_all_projects: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_all_projects",
        )
        print(
            self.project_policy_service.render_update_plan(
                requested_project_root=requested_project_root,
                include_all_projects=include_all_projects,
            ),
            end="",
        )
        return 0

    def handle_policies_apply_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None = (
            self.cli_argument_reader.resolve_optional_project_root(arguments)
        )
        include_all_projects: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_all_projects",
        )
        print(
            self.project_policy_service.apply_policy_updates(
                requested_project_root=requested_project_root,
                include_all_projects=include_all_projects,
            ),
            end="",
        )
        return 0
