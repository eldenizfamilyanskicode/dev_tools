from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuContext, CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_init.application_service import ProjectInitService


class ProjectInitCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        project_init_service: ProjectInitService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.project_init_service: ProjectInitService = project_init_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        init_parser: argparse.ArgumentParser = subparsers.add_parser(
            "init",
            help="Create local .dev_tools context for current git project.",
            description="Create local .dev_tools context for current git project.",
            epilog=self.build_init_examples(),
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(init_parser)
        init_parser.add_argument(
            "about_file_path",
            nargs="?",
            default=None,
            metavar="ABOUT_FILE_PATH",
            help=(
                "Optional about-current-project markdown path. "
                "Defaults to .dev_tools/about_current_project.md."
            ),
        )
        init_parser.add_argument(
            "--about-file",
            type=str,
            default=None,
            dest="about_file_path_option",
            help="Explicit about-current-project markdown path.",
        )
        init_parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing .dev_tools config files.",
        )
        init_parser.add_argument(
            "--application-type",
            choices=self.build_application_type_choices(),
            default=ApplicationType.FULL.value,
            help="Project application profile.",
        )
        init_parser.add_argument(
            "--toolset",
            action="append",
            default=None,
            help=(
                "Bootstrap tools. Repeat the option or pass comma-separated values: "
                "mypy, ruff, pyright, prettier, all."
            ),
        )
        init_parser.add_argument(
            "--strictness",
            choices=self.build_strictness_choices(),
            default=StrictnessLevel.HIGH.value,
            help="Generated bootstrap strictness level.",
        )
        init_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the project bootstrap plan without modifying files.",
        )
        init_parser.set_defaults(command_handler=self.handle_init_command)

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return (
            CliMenuItem(
                title="Initialize project context",
                order=10,
                handler=self.handle_init_menu_item,
            ),
        )

    def handle_init_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        force: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="force",
        )
        about_file_path: Path | None
        about_file_path = self.cli_argument_reader.resolve_optional_about_file_path(
            arguments=arguments,
        )
        application_type: ApplicationType = self.resolve_application_type(arguments)
        tool_names: tuple[ToolName, ...] = self.resolve_tool_names(arguments)
        strictness_level: StrictnessLevel = self.resolve_strictness_level(arguments)
        dry_run: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="dry_run",
        )

        if dry_run:
            plan_text: str = self.project_init_service.render_initialization_plan(
                requested_project_root=requested_project_root,
                force=force,
                application_type=application_type,
                tool_names=tool_names,
                strictness_level=strictness_level,
            )
            print(plan_text, end="")
            return 0

        self.initialize_project(
            requested_project_root=requested_project_root,
            force=force,
            about_file_path=about_file_path,
            application_type=application_type,
            tool_names=tool_names,
            strictness_level=strictness_level,
        )
        return 0

    def handle_init_menu_item(self, menu_context: CliMenuContext) -> int:
        self.initialize_project(
            requested_project_root=menu_context.requested_project_root,
            force=False,
            about_file_path=None,
            application_type=ApplicationType.FULL,
            tool_names=(ToolName.ALL,),
            strictness_level=StrictnessLevel.HIGH,
        )
        return 0

    def initialize_project(
        self,
        requested_project_root: Path | None,
        force: bool,
        about_file_path: Path | None,
        application_type: ApplicationType,
        tool_names: tuple[ToolName, ...],
        strictness_level: StrictnessLevel,
    ) -> Path:
        initialized_project_root: Path = self.project_init_service.initialize_project(
            requested_project_root=requested_project_root,
            force=force,
            about_file_path=about_file_path,
            application_type=application_type,
            tool_names=tool_names,
            strictness_level=strictness_level,
            dry_run=False,
        )
        print(f"Initialized dev tools context: {initialized_project_root}")
        print("Applied project bootstrap templates/settings")
        print("Updated include catalog: .dev_tools/include.toml")
        return initialized_project_root

    def resolve_application_type(
        self,
        arguments: argparse.Namespace,
    ) -> ApplicationType:
        raw_application_type: str | None = (
            self.cli_argument_reader.get_optional_string_argument(
                arguments=arguments,
                argument_name="application_type",
            )
        )

        if raw_application_type is None:
            return ApplicationType.FULL

        return ApplicationType(raw_application_type)

    def resolve_strictness_level(
        self,
        arguments: argparse.Namespace,
    ) -> StrictnessLevel:
        raw_strictness_level: str | None = (
            self.cli_argument_reader.get_optional_string_argument(
                arguments=arguments,
                argument_name="strictness",
            )
        )

        if raw_strictness_level is None:
            return StrictnessLevel.HIGH

        return StrictnessLevel(raw_strictness_level)

    def resolve_tool_names(self, arguments: argparse.Namespace) -> tuple[ToolName, ...]:
        argument_value: object | None = getattr(arguments, "toolset", None)

        if argument_value is None:
            return (ToolName.ALL,)

        if not isinstance(argument_value, list):
            raise TypeError("Expected `toolset` to be list or None.")

        raw_groups: list[str] = []

        for argument_item in argument_value:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(argument_item, str):
                raise TypeError("Expected each `toolset` value to be a string.")

            raw_groups.append(argument_item)

        tool_names: list[ToolName] = []
        accepted_values: list[str] = []

        for tool_name in ToolName:
            accepted_values.append(tool_name.value)

        for raw_group in raw_groups:
            raw_values: list[str] = raw_group.split(",")

            for raw_value in raw_values:
                normalized_value: str = raw_value.strip().lower()

                if normalized_value == "":
                    continue

                if normalized_value not in accepted_values:
                    accepted_text: str = ", ".join(accepted_values)
                    raise ValueError(
                        f"Unsupported --toolset value `{normalized_value}`. "
                        f"Accepted values: {accepted_text}"
                    )

                resolved_tool_name: ToolName = ToolName(normalized_value)

                if resolved_tool_name not in tool_names:
                    tool_names.append(resolved_tool_name)

        if not tool_names:
            return (ToolName.ALL,)

        return tuple(tool_names)

    def build_application_type_choices(self) -> tuple[str, ...]:
        choices: list[str] = []

        for application_type in ApplicationType:
            choices.append(application_type.value)

        return tuple(choices)

    def build_strictness_choices(self) -> tuple[str, ...]:
        choices: list[str] = []

        for strictness_level in StrictnessLevel:
            choices.append(strictness_level.value)

        return tuple(choices)

    def build_init_examples(self) -> str:
        return """examples:
  dev-tools init
  dev-tools init --dry-run
  dev-tools init --application-type python --toolset ruff,pyright --strictness high
  dev-tools init .dev_tools/about_current_project.md
  dev-tools init --about-file docs/about_current_project.md
  dev-tools init --project-root /absolute/project/path
"""
