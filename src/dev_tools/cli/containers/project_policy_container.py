from __future__ import annotations

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory
from typed_time_provider import Seconds, TimeFormatter, TimePrecision, WallClock

from dev_tools.cli.containers.project_bootstrap_container import (
    ProjectBootstrapContainer,
)
from dev_tools.cli.containers.project_context_container import ProjectContextContainer
from dev_tools.cli.containers.shared_container import SharedContainer
from dev_tools.project_policy.application_service import ProjectPolicyService
from dev_tools.project_policy.manifest_store import ProjectPolicyManifestStore
from dev_tools.project_policy.operation_status_resolver import (
    ProjectPolicyOperationStatusResolver,
)
from dev_tools.project_policy.project_index_store import ProjectIndexStore
from dev_tools.project_policy.report_renderer import ProjectPolicyReportRenderer
from dev_tools.project_policy.timestamp_service import TimestampService


class ProjectPolicyContainer(containers.DeclarativeContainer):
    shared: SharedContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_context: ProjectContextContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]
    project_bootstrap: ProjectBootstrapContainer = DependenciesContainer()  # pyright: ignore[reportAssignmentType]

    wall_clock = Factory(
        WallClock,
        preferred_time_unit_type=Seconds,
    )
    time_formatter = Factory(  # type: ignore[var-annotated]
        TimeFormatter,
        default_time_precision=TimePrecision.SECOND,
    )
    timestamp_service = Factory(
        TimestampService,
        wall_clock=wall_clock,
        time_formatter=time_formatter,
    )

    manifest_store = Factory(
        ProjectPolicyManifestStore,
        file_system=shared.file_system,
    )
    project_index_store = Factory(
        ProjectIndexStore,
        file_system=shared.file_system,
        manifest_store=manifest_store,
    )
    operation_status_resolver = Factory(ProjectPolicyOperationStatusResolver)
    report_renderer = Factory(
        ProjectPolicyReportRenderer,
        operation_status_resolver=operation_status_resolver,
    )
    project_policy_service = Factory(
        ProjectPolicyService,
        project_root_resolver=project_context.project_root_resolver,
        project_bootstrap_service=project_bootstrap.project_bootstrap_service,
        manifest_store=manifest_store,
        project_index_store=project_index_store,
        timestamp_service=timestamp_service,
        operation_status_resolver=operation_status_resolver,
        report_renderer=report_renderer,
    )
