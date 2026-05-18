from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuContext, CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.project_init.application_service import ProjectInitService


class ProjectInitCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        project_init_service: ProjectInitService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar: CliSharedArgumentRegistrar
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

        self.initialize_project(
            requested_project_root=requested_project_root,
            force=force,
            about_file_path=about_file_path,
        )
        return 0

    def handle_init_menu_item(self, menu_context: CliMenuContext) -> int:
        self.initialize_project(
            requested_project_root=menu_context.requested_project_root,
            force=False,
            about_file_path=None,
        )
        return 0

    def initialize_project(
        self,
        requested_project_root: Path | None,
        force: bool,
        about_file_path: Path | None,
    ) -> Path:
        initialized_project_root: Path = self.project_init_service.initialize_project(
            requested_project_root=requested_project_root,
            force=force,
            about_file_path=about_file_path,
        )
        print(f"Initialized dev tools context: {initialized_project_root}")
        print("Updated include catalog: .dev_tools/include.toml")
        return initialized_project_root

    def build_init_examples(self) -> str:
        return """examples:
  dev-tools init
  dev-tools init .dev_tools/about_current_project.md
  dev-tools init --about-file docs/about_current_project.md
  dev-tools init --project-root /absolute/project/path
"""
