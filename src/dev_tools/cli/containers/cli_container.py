from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import (
    DependenciesContainer,
    Factory,
    List,
    Singleton,
)

from dev_tools.cli.application import DevToolsCliApplication
from dev_tools.cli.argument_parser_factory import CliArgumentParserFactory
from dev_tools.cli.containers.export_context_container import ExportContextContainer
from dev_tools.cli.containers.include_generation_container import (
    IncludeGenerationContainer,
)
from dev_tools.cli.containers.project_init_container import ProjectInitContainer
from dev_tools.cli.containers.tree_generation_container import TreeGenerationContainer
from dev_tools.cli.menu_runner import InteractiveMenuRunner
from dev_tools.cli.shared_arguments import CliArgumentReader, CliSharedArgumentRegistrar
from dev_tools.export_context.cli import ExportContextCliContribution
from dev_tools.include_generation.cli import IncludeGenerationCliContribution
from dev_tools.project_init.cli import ProjectInitCliContribution
from dev_tools.tree_generation.cli import TreeGenerationCliContribution


class CliContainer(containers.DeclarativeContainer):
    project_init: ProjectInitContainer
    project_init = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    include_generation: IncludeGenerationContainer
    include_generation = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    tree_generation: TreeGenerationContainer
    tree_generation = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    export_context: ExportContextContainer
    export_context = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    cli_argument_reader = Singleton(CliArgumentReader)
    cli_shared_argument_registrar = Singleton(CliSharedArgumentRegistrar)

    project_init_cli_contribution = Factory(
        ProjectInitCliContribution,
        cli_argument_reader=cli_argument_reader,
        cli_shared_argument_registrar=cli_shared_argument_registrar,
        project_init_service=project_init.project_init_service,
    )

    include_generation_cli_contribution = Factory(
        IncludeGenerationCliContribution,
        cli_argument_reader=cli_argument_reader,
        cli_shared_argument_registrar=cli_shared_argument_registrar,
        include_file_update_service=include_generation.include_file_update_service,
    )

    tree_generation_cli_contribution = Factory(
        TreeGenerationCliContribution,
        cli_argument_reader=cli_argument_reader,
        cli_shared_argument_registrar=cli_shared_argument_registrar,
        tree_generation_service=tree_generation.tree_generation_service,
    )

    export_context_cli_contribution = Factory(
        ExportContextCliContribution,
        cli_argument_reader=cli_argument_reader,
        cli_shared_argument_registrar=cli_shared_argument_registrar,
        export_context_service=export_context.export_context_service,
    )

    cli_contributions = List(
        project_init_cli_contribution,
        tree_generation_cli_contribution,
        include_generation_cli_contribution,
        export_context_cli_contribution,
    )

    interactive_menu_runner = Factory(
        InteractiveMenuRunner,
        cli_contributions=cli_contributions,
    )

    cli_argument_parser_factory = Factory(
        CliArgumentParserFactory,
        cli_contributions=cli_contributions,
        cli_argument_reader=cli_argument_reader,
        cli_shared_argument_registrar=cli_shared_argument_registrar,
        interactive_menu_runner=interactive_menu_runner,
    )

    cli_application = Factory(
        DevToolsCliApplication,
        cli_argument_parser_factory=cli_argument_parser_factory,
        cli_argument_reader=cli_argument_reader,
    )
