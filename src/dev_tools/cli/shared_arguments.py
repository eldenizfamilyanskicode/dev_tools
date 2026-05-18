from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from dev_tools.cli.models import CliCommandHandler


class CliSharedArgumentRegistrar:
    def add_project_root_argument(
        self,
        argument_parser: argparse.ArgumentParser,
    ) -> None:
        argument_parser.add_argument(
            "--project-root",
            type=str,
            default=None,
            help="Project root. Defaults to nearest .dev_tools or git root.",
        )


class CliArgumentReader:
    def get_command_handler(
        self,
        arguments: argparse.Namespace,
    ) -> CliCommandHandler:
        argument_value: object | None = getattr(arguments, "command_handler", None)

        if argument_value is None:
            raise ValueError("Command handler is not configured.")

        if not callable(argument_value):
            raise TypeError("Command handler must be callable.")

        return cast(CliCommandHandler, argument_value)

    def resolve_optional_project_root(
        self,
        arguments: argparse.Namespace,
    ) -> Path | None:
        project_root_argument: str | None = self.get_optional_string_argument(
            arguments=arguments,
            argument_name="project_root",
        )
        return self.resolve_optional_path(project_root_argument)

    def resolve_optional_path(self, path_argument: str | None) -> Path | None:
        if path_argument is None:
            return None

        return Path(path_argument).resolve()

    def resolve_optional_about_file_path(
        self,
        arguments: argparse.Namespace,
    ) -> Path | None:
        about_file_path_option: str | None = self.get_optional_string_argument(
            arguments=arguments,
            argument_name="about_file_path_option",
        )
        about_file_path_argument: str | None = self.get_optional_string_argument(
            arguments=arguments,
            argument_name="about_file_path",
        )

        if about_file_path_option is not None:
            return Path(about_file_path_option)

        if about_file_path_argument is not None:
            return Path(about_file_path_argument)

        return None

    def resolve_yes_no_argument(
        self,
        value: str | None,
        fallback_value: bool,
    ) -> bool:
        if value is None:
            return fallback_value

        normalized_value: str = value.strip().lower()
        true_values: tuple[str, ...] = ("y", "yes", "true", "1", "да", "д")
        false_values: tuple[str, ...] = ("n", "no", "false", "0", "нет", "н")

        for true_value in true_values:
            if normalized_value == true_value:
                return True

        for false_value in false_values:
            if normalized_value == false_value:
                return False

        raise ValueError(f"Expected y/n value, got: {value}")

    def get_optional_string_argument(
        self,
        arguments: argparse.Namespace,
        argument_name: str,
    ) -> str | None:
        argument_value: object | None = getattr(arguments, argument_name, None)

        if argument_value is None:
            return None

        if not isinstance(argument_value, str):
            raise TypeError(f"Expected `{argument_name}` to be string or None.")

        return argument_value

    def get_bool_argument(
        self,
        arguments: argparse.Namespace,
        argument_name: str,
    ) -> bool:
        argument_value: object | None = getattr(arguments, argument_name, None)

        if not isinstance(argument_value, bool):
            raise TypeError(f"Expected `{argument_name}` to be bool.")

        return argument_value
