from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Protocol

from dev_tools.global_cli.constants import (
    LINUX_CONFIGURATION_ENVIRONMENT_VARIABLE_NAME,
    LINUX_FALLBACK_CONFIGURATION_DIRECTORY_NAME,
    MACOS_CONFIGURATION_PATH_PARTS,
    VSCODE_APPLICATION_DIRECTORY_NAME,
    VSCODE_SETTINGS_FILE_NAME,
    VSCODE_USER_DIRECTORY_NAME,
    WINDOWS_APPLICATION_DATA_ENVIRONMENT_VARIABLE_NAME,
    WINDOWS_FALLBACK_APPLICATION_DATA_PATH_PARTS,
)


class VsCodeUserSettingsPathResolver(Protocol):
    def resolve_settings_file_path(self) -> Path:
        raise NotImplementedError


class DefaultVsCodeUserSettingsPathResolver:
    def resolve_settings_file_path(self) -> Path:
        user_configuration_directory_path: Path
        user_configuration_directory_path = (
            self.resolve_user_configuration_directory_path()
        )
        return (
            user_configuration_directory_path
            / VSCODE_APPLICATION_DIRECTORY_NAME
            / VSCODE_USER_DIRECTORY_NAME
            / VSCODE_SETTINGS_FILE_NAME
        )

    def resolve_user_configuration_directory_path(self) -> Path:
        operating_system_name: str = platform.system()

        if operating_system_name == "Windows":
            return self.resolve_windows_configuration_directory_path()

        if operating_system_name == "Darwin":
            return self.resolve_macos_configuration_directory_path()

        return self.resolve_linux_configuration_directory_path()

    def resolve_windows_configuration_directory_path(self) -> Path:
        application_data_directory: str | None = os.environ.get(
            WINDOWS_APPLICATION_DATA_ENVIRONMENT_VARIABLE_NAME
        )
        if application_data_directory is not None:
            return Path(application_data_directory)

        configuration_directory_path: Path = Path.home()
        for path_part in WINDOWS_FALLBACK_APPLICATION_DATA_PATH_PARTS:
            configuration_directory_path = configuration_directory_path / path_part

        return configuration_directory_path

    def resolve_macos_configuration_directory_path(self) -> Path:
        configuration_directory_path: Path = Path.home()
        for path_part in MACOS_CONFIGURATION_PATH_PARTS:
            configuration_directory_path = configuration_directory_path / path_part

        return configuration_directory_path

    def resolve_linux_configuration_directory_path(self) -> Path:
        configuration_directory: str | None = os.environ.get(
            LINUX_CONFIGURATION_ENVIRONMENT_VARIABLE_NAME
        )
        if configuration_directory is not None:
            return Path(configuration_directory)

        return Path.home() / LINUX_FALLBACK_CONFIGURATION_DIRECTORY_NAME
