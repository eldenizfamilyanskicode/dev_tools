from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from base_pydantic_schemas import ImmutableDTO

CliCommandHandler = Callable[[argparse.Namespace], int]
CliMenuItemHandler = Callable[["CliMenuContext"], int]


class CliMenuContext(ImmutableDTO):
    requested_project_root: Path | None


class CliMenuItem(ImmutableDTO):
    title: str
    order: int
    handler: CliMenuItemHandler
