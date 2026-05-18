from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CliCommandHandler = Callable[[argparse.Namespace], int]
CliMenuItemHandler = Callable[["CliMenuContext"], int]


@dataclass(frozen=True, slots=True)
class CliMenuContext:
    requested_project_root: Path | None


@dataclass(frozen=True, slots=True)
class CliMenuItem:
    title: str
    order: int
    handler: CliMenuItemHandler
