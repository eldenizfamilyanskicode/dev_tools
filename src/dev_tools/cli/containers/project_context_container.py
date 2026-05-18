from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.project_context.context_loader import ProjectContextLoader
from dev_tools.project_context.project_root_resolver import ProjectRootResolver


class ProjectContextContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    project_root_resolver = Singleton(ProjectRootResolver)

    context_loader = Factory(
        ProjectContextLoader,
        project_root_resolver=project_root_resolver,
        toml_reader=shared.toml_reader,
    )
