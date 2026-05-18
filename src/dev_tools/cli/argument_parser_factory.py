from __future__ import annotations

import argparse

from dev_tools.cli.contracts import CliContribution
from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.menu_runner import InteractiveMenuRunner
from dev_tools.cli.models import CliMenuContext
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar


class CliArgumentParserFactory:
    def __init__(
        self,
        cli_contributions: list[CliContribution],
        cli_argument_reader: CliArgumentReader,
        cli_shared_argument_registrar: CliSharedArgumentRegistrar,
        interactive_menu_runner: InteractiveMenuRunner,
    ) -> None:
        self.cli_contributions: tuple[CliContribution, ...]
        self.cli_contributions = tuple(cli_contributions)
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.cli_shared_argument_registrar = cli_shared_argument_registrar
        self.interactive_menu_runner: InteractiveMenuRunner = interactive_menu_runner

    def build_argument_parser(self) -> argparse.ArgumentParser:
        argument_parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog="dev-tools",
            description="Private project-aware development tools.",
            formatter_class=DevToolsHelpFormatter,
        )
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser]  # pyright: ignore[reportPrivateUsage]
        subparsers = argument_parser.add_subparsers(dest="command", required=True)

        self.register_menu_command(subparsers)

        for cli_contribution in self.cli_contributions:
            cli_contribution.register_commands(subparsers)

        return argument_parser

    def register_menu_command(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        menu_parser: argparse.ArgumentParser = subparsers.add_parser(
            "menu",
            help="Open numbered interactive menu.",
            description="Open numbered interactive menu.",
            formatter_class=DevToolsHelpFormatter,
        )
        self.cli_shared_argument_registrar.add_project_root_argument(menu_parser)
        menu_parser.set_defaults(command_handler=self.handle_menu_command)

    def handle_menu_command(self, arguments: argparse.Namespace) -> int:
        requested_project_root = self.cli_argument_reader.resolve_optional_project_root(
            arguments=arguments,
        )
        menu_context: CliMenuContext = CliMenuContext(
            requested_project_root=requested_project_root,
        )
        return self.interactive_menu_runner.run_menu(menu_context)
