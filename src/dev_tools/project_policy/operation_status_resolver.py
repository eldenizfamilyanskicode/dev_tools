from __future__ import annotations

from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
)
from dev_tools.project_policy.models import PolicyApplicationStatus


class ProjectPolicyOperationStatusResolver:
    def resolve_operation_status(
        self,
        operation: BootstrapFileOperation,
    ) -> PolicyApplicationStatus:
        if operation.action == BootstrapFileAction.CONFLICT:
            return PolicyApplicationStatus.CONFLICT

        if operation.conflict_paths:
            return PolicyApplicationStatus.CONFLICT

        if operation.action in (BootstrapFileAction.CREATE, BootstrapFileAction.UPDATE):
            if operation.preserved_paths:
                return PolicyApplicationStatus.APPLIED_WITH_SKIPS

            return PolicyApplicationStatus.APPLIED

        if operation.reason == "already up to date" and not operation.preserved_paths:
            return PolicyApplicationStatus.ALREADY_SATISFIED

        if "not safe to merge" in operation.reason:
            return PolicyApplicationStatus.CONFLICT

        return PolicyApplicationStatus.SKIPPED_EXISTING

    def count_operations(
        self,
        plan: ProjectBootstrapPlan,
        action: BootstrapFileAction,
    ) -> int:
        operation_count: int = 0

        for operation in plan.operations:
            if operation.action == action:
                operation_count = operation_count + 1

        return operation_count

    def count_conflict_operations(self, plan: ProjectBootstrapPlan) -> int:
        operation_count: int = 0

        for operation in plan.operations:
            if (
                self.resolve_operation_status(operation)
                == PolicyApplicationStatus.CONFLICT
            ):
                operation_count = operation_count + 1

        return operation_count

    def count_applied_operations(self, plan: ProjectBootstrapPlan) -> int:
        operation_count: int = 0

        for operation in plan.operations:
            operation_status: PolicyApplicationStatus = self.resolve_operation_status(
                operation
            )
            if operation_status in (
                PolicyApplicationStatus.APPLIED,
                PolicyApplicationStatus.APPLIED_WITH_SKIPS,
            ):
                operation_count = operation_count + 1

        return operation_count

    def count_skipped_operations(self, plan: ProjectBootstrapPlan) -> int:
        operation_count: int = 0

        for operation in plan.operations:
            operation_status: PolicyApplicationStatus = self.resolve_operation_status(
                operation
            )
            if operation_status in (
                PolicyApplicationStatus.ALREADY_SATISFIED,
                PolicyApplicationStatus.SKIPPED_EXISTING,
            ):
                operation_count = operation_count + 1

        return operation_count
