from __future__ import annotations

from pathlib import Path

from base_pydantic_schemas._immutable_dto import ImmutableDTO

from dev_tools.typings.strings import RelativePathString


class ExportedFile(ImmutableDTO):
    relative_path: Path
    relative_path_as_string: RelativePathString
    absolute_path: Path
    content: str
