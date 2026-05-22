from __future__ import annotations

from pathlib import Path

from dev_tools.shared.file_system import FileSystem


class ProjectContextTemplateWriter:
    def __init__(self, file_system: FileSystem) -> None:
        self.file_system = file_system

    def write_templates(
        self,
        project_root: Path,
        force: bool,
        about_file_path: Path | None,
    ) -> Path:
        resolved_about_file_path: Path = self.resolve_about_file_path(
            project_root=project_root,
            about_file_path=about_file_path,
        )
        dev_tools_directory: Path = project_root / ".dev_tools"
        context_file_path: Path = dev_tools_directory / "context.toml"
        include_file_path: Path = dev_tools_directory / "include.toml"
        exclude_file_path: Path = dev_tools_directory / "exclude.toml"

        self.file_system.write_text_if_missing(
            file_path=context_file_path,
            content=self.build_context_template(
                project_root=project_root,
                about_file_path=resolved_about_file_path,
            ),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=include_file_path,
            content=self.build_include_template(),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=exclude_file_path,
            content=self.build_exclude_template(),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=resolved_about_file_path,
            content=self.build_about_template(project_root),
            force=force,
        )

        return resolved_about_file_path

    def resolve_about_file_path(
        self,
        project_root: Path,
        about_file_path: Path | None,
    ) -> Path:
        if about_file_path is None:
            return project_root / ".dev_tools" / "about_current_project.md"

        if about_file_path.is_absolute():
            return about_file_path.resolve()

        return (project_root / about_file_path).resolve()

    def build_context_template(
        self,
        project_root: Path,
        about_file_path: Path,
    ) -> str:
        about_file_path_as_string: str = self.format_context_path(
            project_root=project_root,
            file_path=about_file_path,
        )
        escaped_project_name: str = self.escape_toml_string(project_root.name)
        escaped_about_file_path: str = self.escape_toml_string(
            about_file_path_as_string
        )

        return f"""[project]
name = "{escaped_project_name}"
root_path = "."

[about]
file_path = "{escaped_about_file_path}"

[output]
directory = ".dev_tools/output"
combined_context_file_name = "combined_context.txt"
tree_file_name = "tree.txt"
chunk_file_prefix = "context_"
chunk_file_extension = ".txt"

[export]
file_separator = "--- FILE SEPARATOR ---"
empty_file_marker = "# File is empty"
maximum_lines_per_chunk = 2500
"""

    def build_about_template(self, project_root: Path) -> str:
        return f"""# About current project: {project_root.name}

## Purpose

Describe what this project does.

## Architecture

Describe key modules, boundaries, and data flow.

## Current task context

Describe what you want the model to understand before reading selected files.
"""

    def build_include_template(self) -> str:
        return """# Relative directories from project root.
# Active values include every file inside the directory.
directories = []

# Exact relative file paths from project root.
# Run `dev-tools update-include-files` to generate a commented catalog.
files = []

# Extensions without dot.
# Active values include files by extension unless excluded.
extensions = []
"""

    def build_exclude_template(self) -> str:
        return """# Directory names. Matched against any path part.
directories = [
    ".git",
    ".dev_tools",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".eggs",
]

# Directory suffixes. Matched against any directory name suffix.
directory_suffixes = [
    ".egg-info",
    ".dist-info",
]

# Exact file names.
files = [
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
]

# Extensions without dot.
extensions = [
    # python
    "egg",
    "egg-info",
    "pyc",
    "pyo",
    "pyd",
    "pyi",
    "pyz",

    # images
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "ico",
    "svg",
    "bmp",
    "tiff",
    "avif",
    "heic",
    "psd",
    "ai",

    # documents
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "odt",
    "ods",
    "odp",
    "pages",
    "numbers",
    "key",


    # archives
    "zip",
    "tar",
    "gz",
    "7z",
    "rar",
    "bz2",
    "xz",
    "lz",
    "lz4",
    "zst",
    "iso",

    # audio/video
    "mp3",
    "mp4",
    "mov",
    "wav",
    "ogg",
    "flac",
    "m4a",
    "avi",
    "mkv",
    "webm",
    "wmv",
    "mpeg",
    "mpg",
    "aac",

    # fonts
    "woff",
    "woff2",
    "ttf",
    "otf",
    "eot",


    # env / secrets
    "env",
    "pem",
    "key",
    "crt",
    "p12",
    "pfx",
    "cer",
    "der",
    "csr",
    "pub",
    "asc",

    # databases
    "db",
    "sqlite",
    "sqlite3",
    "mdb",
    "accdb",
    "parquet",


    # logs / runtime
    "log",
    "pid",
    "lock",
    "seed",
    "stackdump",

    # build artifacts
    "class",
    "o",
    "obj",
    "so",
    "dll",
    "exe",
    "dylib",
    "a",
    "lib",

    # package artifacts
    "whl",
    "gem",
    "jar",
    "war",
    "ear",
    "apk",
    "ipa",
    "deb",
    "rpm",
    "msi",

    # caches
    "cache",
    "tmp",
    "temp",


    # notebooks / model artifacts
    "ipynb",
    "onnx",
    "pt",
    "pth",
    "ckpt",
    "safetensors",
    "bin",
]
"""

    def format_context_path(
        self,
        project_root: Path,
        file_path: Path,
    ) -> str:
        try:
            relative_path: Path = file_path.relative_to(project_root)
            return relative_path.as_posix()
        except ValueError:
            return file_path.as_posix()

    def escape_toml_string(self, value: str) -> str:
        escaped_value: str = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return escaped_value
