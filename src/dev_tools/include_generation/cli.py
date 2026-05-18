from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuContext, CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.include_generation.application_service import IncludeFileUpdateService


class IncludeGenerationCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        include_file_update_service: IncludeFileUpdateService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar: CliSharedArgumentRegistrar
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.include_file_update_service: IncludeFileUpdateService
        self.include_file_update_service = include_file_update_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        update_include_files_parser: argparse.ArgumentParser = subparsers.add_parser(
            "update-include-files",
            help="Refresh .dev_tools/include.toml with a commented file catalog.",
            description=(
                "Refresh .dev_tools/include.toml with a commented file catalog."
            ),
            epilog=self.build_update_include_files_examples(),
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(
            update_include_files_parser,
        )
        update_include_files_parser.set_defaults(
            command_handler=self.handle_update_include_files_command,
        )

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return (
            CliMenuItem(
                title="Update include files catalog",
                order=200,
                handler=self.handle_update_include_files_menu_item,
            ),
        )

    def handle_update_include_files_command(
        self,
        arguments: argparse.Namespace,
    ) -> int:
        requested_project_root: Path | None
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        self.update_include_files(requested_project_root)
        return 0

    def handle_update_include_files_menu_item(
        self,
        menu_context: CliMenuContext,
    ) -> int:
        self.update_include_files(menu_context.requested_project_root)
        return 0

    def update_include_files(self, requested_project_root: Path | None) -> Path:
        include_file_path: Path = self.include_file_update_service.update_include_file(
            requested_project_root=requested_project_root,
        )
        print(f"Updated include catalog: {include_file_path}")
        return include_file_path

    def build_update_include_files_examples(self) -> str:
        return """examples:
  dev-tools update-include-files
  dev-tools update-include-files --project-root /absolute/project/path
"""
