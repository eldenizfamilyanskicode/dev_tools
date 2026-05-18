from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dev_tools.cli.argument_parser_factory import CliArgumentParserFactory
from dev_tools.cli.models import CliCommandHandler
from dev_tools.cli.shared_arguments import CliArgumentReader


class DevToolsCliApplication:
    def __init__(
        self,
        cli_argument_parser_factory: CliArgumentParserFactory,
        cli_argument_reader: CliArgumentReader,
    ) -> None:
        self.cli_argument_parser_factory: CliArgumentParserFactory
        self.cli_argument_parser_factory = cli_argument_parser_factory
        self.cli_argument_reader: CliArgumentReader = cli_argument_reader

    def run(self, raw_arguments: Sequence[str] | None = None) -> int:
        argument_parser: argparse.ArgumentParser
        argument_parser = self.cli_argument_parser_factory.build_argument_parser()
        arguments: argparse.Namespace = argument_parser.parse_args(args=raw_arguments)

        try:
            command_handler: CliCommandHandler
            command_handler = self.cli_argument_reader.get_command_handler(arguments)
            return command_handler(arguments)
        except KeyboardInterrupt:
            return 130
        except Exception as error:
            print(f"dev-tools error: {error}", file=sys.stderr)
            return 1
