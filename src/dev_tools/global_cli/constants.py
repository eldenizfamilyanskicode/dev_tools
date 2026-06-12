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

GLOBAL_CLI_LAYOUT_README_CONTENT = """# Global CLI

This directory is the canonical machine-local layout for globally installed CLI
tools managed from this workstation.

- `bin/` is the only directory from this layout that should be added to `PATH`.
- `uv_tools/` stores uv-managed tool environments.

Use `uv tool install` as the canonical installation mechanism for Python CLI
tools. Do not manually move virtual environments or executable shims into this
layout.
"""
