from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import Singleton

from dev_tools.shared.file_system import FileSystem
from dev_tools.shared.toml_reader import TomlReader


class SharedContainer(containers.DeclarativeContainer):
    file_system = Singleton(FileSystem)
    toml_reader = Singleton(TomlReader)
