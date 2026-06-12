from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.json_operation_builder import JsonOperationBuilder
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.pyproject_operation_builder import (
    PyprojectOperationBuilder,
)
from dev_tools.project_bootstrap.template_content_builder import TemplateContentBuilder
from dev_tools.project_bootstrap.template_plan_builder import TemplatePlanBuilder
from dev_tools.project_bootstrap.toml_section_merge_service import (
    TomlSectionMergeService,
)
from dev_tools.project_bootstrap.toml_section_parser import TomlSectionParser


class ProjectBootstrapContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    managed_block_service = Factory(ManagedBlockService)
    json_merge_service = Factory(JsonMergeService)
    toml_section_parser = Factory(TomlSectionParser)
    toml_section_merge_service = Factory(
        TomlSectionMergeService,
        toml_section_parser=toml_section_parser,
    )
    template_content_builder = Factory(TemplateContentBuilder)

    bootstrap_file_writer = Factory(
        BootstrapFileWriter,
        file_system=shared.file_system,
    )

    pyproject_operation_builder = Factory(
        PyprojectOperationBuilder,
        toml_section_merge_service=toml_section_merge_service,
        bootstrap_file_writer=bootstrap_file_writer,
    )
    json_operation_builder = Factory(
        JsonOperationBuilder,
        json_merge_service=json_merge_service,
        bootstrap_file_writer=bootstrap_file_writer,
    )

    template_plan_builder = Factory(
        TemplatePlanBuilder,
        managed_block_service=managed_block_service,
        json_operation_builder=json_operation_builder,
        template_content_builder=template_content_builder,
        pyproject_operation_builder=pyproject_operation_builder,
        bootstrap_file_writer=bootstrap_file_writer,
    )

    project_bootstrap_service = Factory(
        ProjectBootstrapService,
        template_plan_builder=template_plan_builder,
        bootstrap_file_writer=bootstrap_file_writer,
    )
