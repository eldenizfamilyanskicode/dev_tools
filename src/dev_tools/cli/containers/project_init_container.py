from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.include_generation_container import (
    IncludeGenerationContainer,
)
from dev_tools.cli.containers.project_bootstrap_container import (
    ProjectBootstrapContainer,
)
from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.project_init.application_service import ProjectInitService
from dev_tools.project_init.git_exclude import GitExcludeService
from dev_tools.project_init.template_writer import ProjectContextTemplateWriter


class ProjectInitContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_context: ProjectContextContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    include_generation: IncludeGenerationContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_bootstrap: ProjectBootstrapContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    template_writer = Factory(
        ProjectContextTemplateWriter,
        file_system=shared.file_system,
    )

    git_exclude_service = Factory(
        GitExcludeService,
        file_system=shared.file_system,
    )

    project_init_service = Factory(
        ProjectInitService,
        project_root_resolver=project_context.project_root_resolver,
        file_system=shared.file_system,
        template_writer=template_writer,
        git_exclude_service=git_exclude_service,
        include_file_update_service=include_generation.include_file_update_service,
        project_bootstrap_service=project_bootstrap.project_bootstrap_service,
    )
