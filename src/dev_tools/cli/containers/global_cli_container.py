from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.global_cli.application_service import GlobalCliSetupService
from dev_tools.global_cli.layout_resolver import GlobalCliLayoutResolver
from dev_tools.global_cli.user_environment_adapter import WindowsUserEnvironmentAdapter
from dev_tools.global_cli.vscode_settings_jsonc_editor import (
    VsCodeSettingsJsoncEditor,
)
from dev_tools.global_cli.vscode_user_settings_path_resolver import (
    DefaultVsCodeUserSettingsPathResolver,
)
from dev_tools.global_cli.vscode_user_settings_setup_operation_builder import (
    VsCodeUserSettingsSetupOperationBuilder,
)


class GlobalCliContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    layout_resolver = Factory(GlobalCliLayoutResolver)
    user_environment_adapter = Factory(WindowsUserEnvironmentAdapter)
    vscode_user_settings_path_resolver = Factory(DefaultVsCodeUserSettingsPathResolver)
    vscode_settings_jsonc_editor = Factory(VsCodeSettingsJsoncEditor)
    vscode_user_settings_setup_operation_builder = Factory(
        VsCodeUserSettingsSetupOperationBuilder,
        file_system=shared.file_system,
        vscode_user_settings_path_resolver=vscode_user_settings_path_resolver,
        vscode_settings_jsonc_editor=vscode_settings_jsonc_editor,
    )
    global_cli_setup_service = Factory(
        GlobalCliSetupService,
        layout_resolver=layout_resolver,
        file_system=shared.file_system,
        user_environment_adapter=user_environment_adapter,
        vscode_user_settings_setup_operation_builder=(
            vscode_user_settings_setup_operation_builder
        ),
    )
