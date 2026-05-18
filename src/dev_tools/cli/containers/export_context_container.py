from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.export_context.application_service import ExportContextService
from dev_tools.export_context.file_chunker import FileChunker
from dev_tools.export_context.file_collector import FileCollector
from dev_tools.export_context.path_matcher import PathMatcher
from dev_tools.tree_generation.directory_tree_generator import DirectoryTreeGenerator


class ExportContextContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_context: ProjectContextContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    path_matcher = Factory(PathMatcher)
    file_chunker = Factory(FileChunker)
    directory_tree_generator = Factory(DirectoryTreeGenerator)

    file_collector = Factory(
        FileCollector,
        path_matcher=path_matcher,
        file_system=shared.file_system,
    )

    export_context_service = Factory(
        ExportContextService,
        context_loader=project_context.context_loader,
        file_system=shared.file_system,
        file_collector=file_collector,
        file_chunker=file_chunker,
        directory_tree_generator=directory_tree_generator,
    )
