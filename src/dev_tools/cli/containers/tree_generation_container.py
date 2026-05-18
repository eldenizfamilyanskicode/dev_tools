from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.tree_generation.application_service import TreeGenerationService
from dev_tools.tree_generation.directory_tree_generator import DirectoryTreeGenerator


class TreeGenerationContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_context: ProjectContextContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    directory_tree_generator = Factory(DirectoryTreeGenerator)

    tree_generation_service = Factory(
        TreeGenerationService,
        context_loader=project_context.context_loader,
        file_system=shared.file_system,
        directory_tree_generator=directory_tree_generator,
    )
