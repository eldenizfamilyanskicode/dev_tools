from __future__ import annotations

from base_typed_string import BaseTypedString


class ProjectName(BaseTypedString):
    pass


class FileName(BaseTypedString):
    pass


class DirectoryName(BaseTypedString):
    pass


class RelativePathString(BaseTypedString):
    pass


class FileExtension(BaseTypedString):
    pass


class FileSeparator(BaseTypedString):
    pass


class EmptyFileMarker(BaseTypedString):
    pass


class ChunkFilePrefix(BaseTypedString):
    pass


class ChunkFileExtension(BaseTypedString):
    pass


class GitExcludeLine(BaseTypedString):
    pass
