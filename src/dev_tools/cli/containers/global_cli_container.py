from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.global_cli.application_service import GlobalCliSetupService
from dev_tools.global_cli.layout_resolver import GlobalCliLayoutResolver
from dev_tools.global_cli.user_environment_adapter import WindowsUserEnvironmentAdapter


class GlobalCliContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    layout_resolver = Factory(GlobalCliLayoutResolver)
    user_environment_adapter = Factory(WindowsUserEnvironmentAdapter)
    global_cli_setup_service = Factory(
        GlobalCliSetupService,
        layout_resolver=layout_resolver,
        file_system=shared.file_system,
        user_environment_adapter=user_environment_adapter,
    )
