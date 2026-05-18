from __future__ import annotations

import argparse
from pathlib import Path

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuContext, CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.tree_generation.application_service import TreeGenerationService


class TreeGenerationCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        tree_generation_service: TreeGenerationService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar: CliSharedArgumentRegistrar
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.tree_generation_service: TreeGenerationService = tree_generation_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        tree_parser: argparse.ArgumentParser = subparsers.add_parser(
            "tree",
            help="Generate project directory tree using local context.",
            description="Generate project directory tree using local context.",
            epilog=self.build_tree_examples(),
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(tree_parser)
        tree_parser.add_argument(
            "--print",
            action="store_true",
            dest="should_print",
            help="Print tree to terminal.",
        )
        tree_parser.add_argument(
            "--write",
            action="store_true",
            dest="should_write",
            help="Write tree to .dev_tools/output/tree.txt.",
        )
        tree_parser.set_defaults(command_handler=self.handle_tree_command)

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return (
            CliMenuItem(
                title="Show project tree",
                order=100,
                handler=self.handle_show_tree_menu_item,
            ),
        )

    def handle_tree_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root: Path | None
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        should_write: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="should_write",
        )
        should_print: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="should_print",
        )
        self.generate_tree(
            requested_project_root=requested_project_root,
            should_write=should_write,
            should_print=should_print,
        )
        return 0

    def handle_show_tree_menu_item(self, menu_context: CliMenuContext) -> int:
        self.generate_tree(
            requested_project_root=menu_context.requested_project_root,
            should_write=False,
            should_print=True,
        )
        return 0

    def generate_tree(
        self,
        requested_project_root: Path | None,
        should_write: bool,
        should_print: bool,
    ) -> str:
        tree_content: str = self.tree_generation_service.generate_tree(
            requested_project_root=requested_project_root,
            should_write=should_write,
        )

        if should_print or not should_write:
            print(tree_content)

        return tree_content

    def build_tree_examples(self) -> str:
        return """examples:
  dev-tools tree
  dev-tools tree --print
  dev-tools tree --write
  dev-tools tree --project-root /absolute/project/path --print
"""
