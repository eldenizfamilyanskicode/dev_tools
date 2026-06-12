from __future__ import annotations

from pathlib import Path

from dev_tools.tree_generation.directory_tree_generator import DirectoryTreeGenerator
from dev_tools.typings.collections import DirectoryNames, FileExtensions, FileNames
from dev_tools.typings.strings import ProjectName


def test_directory_tree_uses_ascii_connectors(tmp_path: Path) -> None:
    source_directory_path: Path = tmp_path / "src"
    source_directory_path.mkdir()
    nested_file_path: Path = source_directory_path / "main.py"
    nested_file_path.write_text("print('ok')\n", encoding="utf-8")
    readme_file_path: Path = tmp_path / "README.md"
    readme_file_path.write_text("# Smoke\n", encoding="utf-8")

    excluded_directory_names: DirectoryNames = ()
    excluded_file_names: FileNames = ()
    excluded_extensions: FileExtensions = ()
    directory_tree_generator: DirectoryTreeGenerator = DirectoryTreeGenerator()

    tree_content: str = directory_tree_generator.generate_directory_tree(
        project_root=tmp_path,
        project_name=ProjectName("smoke"),
        excluded_directory_names=excluded_directory_names,
        excluded_file_names=excluded_file_names,
        excluded_extensions=excluded_extensions,
    )

    expected_tree_content: str = (
        "smoke/\n"
        "+-- src/\n"
        "|   `-- main.py\n"
        "`-- README.md"
    )
    assert tree_content == expected_tree_content
    tree_content.encode("cp1252", errors="strict")
