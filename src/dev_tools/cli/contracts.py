from __future__ import annotations

import argparse
from typing import Protocol

from dev_tools.cli.models import CliMenuItem


class CliContribution(Protocol):
    def register_commands(
        self,
        subparsers: argparse._SubParsersAction[argparse.ArgumentParser],  # pyright: ignore[reportPrivateUsage]
    ) -> None:
        raise NotImplementedError

    def get_menu_items(self) -> tuple[CliMenuItem, ...]:
        raise NotImplementedError
