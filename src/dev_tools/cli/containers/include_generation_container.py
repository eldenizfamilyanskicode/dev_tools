from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.export_context.path_matcher import PathMatcher
from dev_tools.include_generation.application_service import IncludeFileUpdateService
from dev_tools.include_generation.file_catalog_generator import (
    IncludeFileCatalogGenerator,
)
from dev_tools.include_generation.include_file_template_renderer import (
    IncludeFileTemplateRenderer,
)


class IncludeGenerationContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_context: ProjectContextContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    path_matcher = Factory(PathMatcher)

    file_catalog_generator = Factory(
        IncludeFileCatalogGenerator,
        path_matcher=path_matcher,
    )

    include_file_template_renderer = Factory(
        IncludeFileTemplateRenderer,
    )

    include_file_update_service = Factory(
        IncludeFileUpdateService,
        context_loader=project_context.context_loader,
        file_system=shared.file_system,
        file_catalog_generator=file_catalog_generator,
        include_file_template_renderer=include_file_template_renderer,
    )
