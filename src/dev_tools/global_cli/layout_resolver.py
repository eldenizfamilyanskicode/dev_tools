from __future__ import annotations

from pathlib import Path

from dev_tools.global_cli.constants import (
    CANONICAL_GLOBAL_CLI_ROOT_PATH_PARTS,
    GLOBAL_CLI_BIN_DIRECTORY_NAME,
    GLOBAL_CLI_README_FILE_NAME,
    GLOBAL_CLI_UV_TOOLS_DIRECTORY_NAME,
    NONCANONICAL_UV_TOOL_BIN_PATH_PARTS,
)
from dev_tools.global_cli.models import GlobalCliLayout


class GlobalCliLayoutResolver:
    def __init__(
        self,
        global_cli_root_path: Path | None = None,
        home_directory_path: Path | None = None,
    ) -> None:
        self.global_cli_root_path: Path | None = global_cli_root_path
        self.home_directory_path: Path | None = home_directory_path

    def resolve_layout(self) -> GlobalCliLayout:
        home_directory_path: Path = self.resolve_home_directory_path()
        root_path: Path = self.resolve_root_path(home_directory_path)
        return GlobalCliLayout(
            root_path=root_path,
            bin_directory_path=root_path / GLOBAL_CLI_BIN_DIRECTORY_NAME,
            uv_tool_directory_path=root_path / GLOBAL_CLI_UV_TOOLS_DIRECTORY_NAME,
            readme_file_path=root_path / GLOBAL_CLI_README_FILE_NAME,
            noncanonical_tool_bin_directory_paths=(
                self.resolve_noncanonical_uv_tool_bin_path(home_directory_path),
            ),
        )

    def resolve_home_directory_path(self) -> Path:
        if self.home_directory_path is not None:
            return self.home_directory_path

        return Path.home()

    def resolve_root_path(self, home_directory_path: Path) -> Path:
        if self.global_cli_root_path is not None:
            return self.global_cli_root_path

        root_path: Path = home_directory_path
        for path_part in CANONICAL_GLOBAL_CLI_ROOT_PATH_PARTS:
            root_path = root_path / path_part

        return root_path

    def resolve_noncanonical_uv_tool_bin_path(self, home_directory_path: Path) -> Path:
        bin_path: Path = home_directory_path
        for path_part in NONCANONICAL_UV_TOOL_BIN_PATH_PARTS:
            bin_path = bin_path / path_part

        return bin_path
