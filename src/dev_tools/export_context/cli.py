from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuContext, CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.export_context.application_service import ExportContextService


class ExportContextCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        export_context_service: ExportContextService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.export_context_service: ExportContextService = export_context_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        self.register_run_command(subparsers)
        self.register_export_context_alias(subparsers)

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return (
            CliMenuItem(
                title="Run export with about + tree",
                order=300,
                handler=self.handle_export_with_about_and_tree_menu_item,
            ),
            CliMenuItem(
                title="Run export without about/tree",
                order=310,
                handler=self.handle_export_without_about_and_tree_menu_item,
            ),
            CliMenuItem(
                title="Run export with tree only",
                order=320,
                handler=self.handle_export_with_tree_only_menu_item,
            ),
            CliMenuItem(
                title="Run export with about only",
                order=330,
                handler=self.handle_export_with_about_only_menu_item,
            ),
        )

    def register_run_command(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        run_parser: argparse.ArgumentParser = subparsers.add_parser(
            "run",
            help="Export selected project context.",
            description="Export selected project context.",
            epilog=self.build_run_examples(),
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(run_parser)
        run_parser.add_argument(
            "include_tree_answer",
            nargs="?",
            default=None,
            metavar="INCLUDE_TREE",
            help="Optional y/n value. Controls generated directory tree inclusion.",
        )
        run_parser.add_argument(
            "include_about_answer",
            nargs="?",
            default=None,
            metavar="INCLUDE_ABOUT",
            help="Optional y/n value. Controls about-current-project inclusion.",
        )
        run_parser.add_argument(
            "--include-tree",
            action="store_true",
            help="Include generated directory tree.",
        )
        run_parser.add_argument(
            "--include-about",
            action="store_true",
            help="Include about-current-project markdown.",
        )
        run_parser.set_defaults(command_handler=self.handle_run_command)

    def register_export_context_alias(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        export_context_parser: argparse.ArgumentParser = subparsers.add_parser(
            "export-context",
            help="Backward-compatible alias for `run`.",
            description="Backward-compatible alias for `run`.",
            epilog=self.build_export_context_examples(),
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(
            export_context_parser,
        )
        export_context_parser.add_argument(
            "--include-tree",
            action="store_true",
            help="Include generated directory tree in combined context.",
        )
        export_context_parser.add_argument(
            "--include-about",
            action="store_true",
            help="Include about-current-project markdown.",
        )
        export_context_parser.set_defaults(
            command_handler=self.handle_export_context_alias_command,
        )

    def handle_run_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        include_tree_answer: str | None
        include_tree_answer = self.cli_argument_reader.get_optional_string_argument(
            arguments=arguments,
            argument_name="include_tree_answer",
        )
        include_about_answer: str | None
        include_about_answer = self.cli_argument_reader.get_optional_string_argument(
            arguments=arguments,
            argument_name="include_about_answer",
        )
        include_tree_flag: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_tree",
        )
        include_about_flag: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_about",
        )
        should_include_tree: bool = self.cli_argument_reader.resolve_yes_no_argument(
            value=include_tree_answer,
            fallback_value=include_tree_flag,
        )
        should_include_about: bool = self.cli_argument_reader.resolve_yes_no_argument(
            value=include_about_answer,
            fallback_value=include_about_flag,
        )

        self.export_context(
            requested_project_root=requested_project_root,
            should_include_tree=should_include_tree,
            should_include_about=should_include_about,
        )
        return 0

    def handle_export_context_alias_command(
        self,
        arguments: argparse.Namespace,
    ) -> int:
        requested_project_root: Path | None
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        should_include_tree: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_tree",
        )
        should_include_about: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="include_about",
        )
        self.export_context(
            requested_project_root=requested_project_root,
            should_include_tree=should_include_tree,
            should_include_about=should_include_about,
        )
        return 0

    def handle_export_with_about_and_tree_menu_item(
        self,
        menu_context: CliMenuContext,
    ) -> int:
        self.export_context(
            requested_project_root=menu_context.requested_project_root,
            should_include_tree=True,
            should_include_about=True,
        )
        return 0

    def handle_export_without_about_and_tree_menu_item(
        self,
        menu_context: CliMenuContext,
    ) -> int:
        self.export_context(
            requested_project_root=menu_context.requested_project_root,
            should_include_tree=False,
            should_include_about=False,
        )
        return 0

    def handle_export_with_tree_only_menu_item(
        self,
        menu_context: CliMenuContext,
    ) -> int:
        self.export_context(
            requested_project_root=menu_context.requested_project_root,
            should_include_tree=True,
            should_include_about=False,
        )
        return 0

    def handle_export_with_about_only_menu_item(
        self,
        menu_context: CliMenuContext,
    ) -> int:
        self.export_context(
            requested_project_root=menu_context.requested_project_root,
            should_include_tree=False,
            should_include_about=True,
        )
        return 0

    def export_context(
        self,
        requested_project_root: Path | None,
        should_include_tree: bool,
        should_include_about: bool,
    ) -> list[Path]:
        written_files: list[Path] = self.export_context_service.export_context(
            requested_project_root=requested_project_root,
            should_include_tree=should_include_tree,
            should_include_about=should_include_about,
        )

        for written_file in written_files:
            print(written_file)

        return written_files

    def build_run_examples(self) -> str:
        return """examples:
  dev-tools run y y
  dev-tools run n n
  dev-tools run --include-tree --include-about
  dev-tools run --project-root /absolute/project/path y n

argument values:
  y, yes, true, 1, да, д       include section
  n, no, false, 0, нет, н      skip section
"""

    def build_export_context_examples(self) -> str:
        return """examples:
  dev-tools export-context --include-tree --include-about
  dev-tools export-context --project-root /absolute/project/path --include-tree
"""
