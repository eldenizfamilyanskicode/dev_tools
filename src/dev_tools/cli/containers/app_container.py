from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import Container

from dev_tools.cli.containers.cli_container import CliContainer
from dev_tools.cli.containers.export_context_container import ExportContextContainer
from dev_tools.cli.containers.include_generation_container import (
    IncludeGenerationContainer,
)
from dev_tools.cli.containers.project_bootstrap_container import (
    ProjectBootstrapContainer,
)
from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.project_init_container import ProjectInitContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.cli.containers.tree_generation_container import TreeGenerationContainer


class AppContainer(containers.DeclarativeContainer):
    shared: SharedContainer = Container(SharedContainer)  # pyright: ignore[reportAssignmentType]

    project_context: ProjectContextContainer = Container(  # pyright: ignore[reportAssignmentType]
        ProjectContextContainer,
        shared=shared,
    )

    include_generation: IncludeGenerationContainer = Container(  # pyright: ignore[reportAssignmentType]
        IncludeGenerationContainer,
        shared=shared,
        project_context=project_context,
    )

    project_bootstrap: ProjectBootstrapContainer = Container(  # pyright: ignore[reportAssignmentType]
        ProjectBootstrapContainer,
        shared=shared,
    )

    project_init: ProjectInitContainer = Container(  # pyright: ignore[reportAssignmentType]
        ProjectInitContainer,
        shared=shared,
        project_context=project_context,
        include_generation=include_generation,
        project_bootstrap=project_bootstrap,
    )

    tree_generation: TreeGenerationContainer = Container(  # pyright: ignore[reportAssignmentType]
        TreeGenerationContainer,
        shared=shared,
        project_context=project_context,
    )

    export_context: ExportContextContainer = Container(  # pyright: ignore[reportAssignmentType]
        ExportContextContainer,
        shared=shared,
        project_context=project_context,
    )

    cli: CliContainer = Container(  # pyright: ignore[reportAssignmentType]
        CliContainer,
        project_init=project_init,
        include_generation=include_generation,
        tree_generation=tree_generation,
        export_context=export_context,
    )
