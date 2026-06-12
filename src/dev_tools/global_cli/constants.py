CANONICAL_GLOBAL_CLI_ROOT_PATH_PARTS: tuple[str, ...] = (
    "repositories",
    "global_cli",
)
NONCANONICAL_UV_TOOL_BIN_PATH_PARTS: tuple[str, ...] = (
    ".local",
    "bin",
)

GLOBAL_CLI_BIN_DIRECTORY_NAME = "bin"
GLOBAL_CLI_UV_TOOLS_DIRECTORY_NAME = "uv_tools"
GLOBAL_CLI_README_FILE_NAME = "README.md"

UV_TOOL_BIN_ENVIRONMENT_VARIABLE_NAME = "UV_TOOL_BIN_DIR"
UV_TOOL_DIR_ENVIRONMENT_VARIABLE_NAME = "UV_TOOL_DIR"
WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME = "Path"

VSCODE_APPLICATION_DIRECTORY_NAME = "Code"
VSCODE_USER_DIRECTORY_NAME = "User"
VSCODE_SETTINGS_FILE_NAME = "settings.json"
VSCODE_USER_SETTINGS_DISPLAY_PATH = "VS Code user settings"
VSCODE_FILES_EXCLUDE_SETTING_NAME = "files.exclude"
VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS: tuple[str, ...] = (
    "**/__pycache__",
    "**/.pytest_cache",
    "**/.mypy_cache",
    "**/.ruff_cache",
)

WINDOWS_APPLICATION_DATA_ENVIRONMENT_VARIABLE_NAME = "APPDATA"
WINDOWS_FALLBACK_APPLICATION_DATA_PATH_PARTS: tuple[str, ...] = (
    "AppData",
    "Roaming",
)
MACOS_CONFIGURATION_PATH_PARTS: tuple[str, ...] = (
    "Library",
    "Application Support",
)
LINUX_CONFIGURATION_ENVIRONMENT_VARIABLE_NAME = "XDG_CONFIG_HOME"
LINUX_FALLBACK_CONFIGURATION_DIRECTORY_NAME = ".config"

GLOBAL_CLI_LAYOUT_README_CONTENT = """# Global CLI

This directory is the canonical machine-local layout for globally installed CLI
tools managed from this workstation.

- `bin/` is the only directory from this layout that should be added to `PATH`.
- `uv_tools/` stores uv-managed tool environments.

Use `uv tool install` as the canonical installation mechanism for Python CLI
tools. Do not manually move virtual environments or executable shims into this
layout.
"""
