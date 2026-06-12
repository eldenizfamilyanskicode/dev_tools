from __future__ import annotations

import argparse

from dev_tools.cli.help_formatter import DevToolsHelpFormatter
from dev_tools.cli.models import CliMenuItem
from dev_tools.cli.shared_arguments import CliArgumentReader
from dev_tools.global_cli.application_service import GlobalCliSetupService


class GlobalCliCliContribution:
    def __init__(
        self,
        cli_argument_reader: CliArgumentReader,
        global_cli_setup_service: GlobalCliSetupService,
    ) -> None:
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader
        self.global_cli_setup_service: GlobalCliSetupService = global_cli_setup_service

    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        global_cli_parser: argparse.ArgumentParser = subparsers.add_parser(
            "global-cli",
            help="Configure the canonical global CLI layout.",
            description="Configure the canonical global CLI layout.",
            formatter_class=DevToolsHelpFormatter,
        )
        global_cli_subparsers = global_cli_parser.add_subparsers(
            dest="global_cli_command",
            required=True,
        )

        setup_parser: argparse.ArgumentParser = global_cli_subparsers.add_parser(
            "setup",
            help="Prepare global_cli directories and user-level uv environment.",
            description=(
                "Prepare global_cli directories and user-level uv environment."
            ),
            formatter_class=DevToolsHelpFormatter,
        )
        setup_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the global CLI setup plan without modifying the system.",
        )
        setup_parser.set_defaults(command_handler=self.handle_setup_command)

        status_parser: argparse.ArgumentParser = global_cli_subparsers.add_parser(
            "status",
            help="Show the canonical global CLI setup status.",
            description="Show the canonical global CLI setup status.",
            formatter_class=DevToolsHelpFormatter,
        )
        status_parser.set_defaults(command_handler=self.handle_status_command)

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        return ()

    def handle_setup_command(self, arguments: argparse.Namespace) -> int:
        dry_run: bool = self.cli_argument_reader.get_bool_argument(
            arguments=arguments,
            argument_name="dry_run",
        )
        print(self.global_cli_setup_service.setup_global_cli(dry_run=dry_run), end="")
        return 0

    def handle_status_command(self, arguments: argparse.Namespace) -> int:
        print(self.global_cli_setup_service.render_global_cli_status(), end="")
        return 0
