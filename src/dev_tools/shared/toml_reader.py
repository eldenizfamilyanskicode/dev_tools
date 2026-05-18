from __future__ import annotations

import tomllib
from pathlib import Path

TomlData = dict[str, object]


class TomlReader:
    def read_toml_file(self, file_path: Path) -> TomlData:
        if not file_path.exists():
            raise FileNotFoundError(f"TOML file not found: {file_path}")

        with file_path.open("rb") as file_handler:
            loaded_data: TomlData = tomllib.load(file_handler)

        return loaded_data
