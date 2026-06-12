from __future__ import annotations

import os
from pathlib import Path

from dev_tools.global_cli.constants import (
    GLOBAL_CLI_LAYOUT_README_CONTENT,
    UV_TOOL_BIN_ENVIRONMENT_VARIABLE_NAME,
    UV_TOOL_DIR_ENVIRONMENT_VARIABLE_NAME,
    WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME,
)
from dev_tools.global_cli.exceptions import GlobalCliSetupError
from dev_tools.global_cli.layout_resolver import GlobalCliLayoutResolver
from dev_tools.global_cli.models import (
    GlobalCliLayout,
    GlobalCliSetupAction,
    GlobalCliSetupOperation,
    GlobalCliSetupPlan,
    GlobalCliSetupTargetType,
)
from dev_tools.global_cli.user_environment_adapter import UserEnvironmentAdapter
from dev_tools.shared.file_system import FileSystem


class GlobalCliSetupService:
    def __init__(
        self,
        layout_resolver: GlobalCliLayoutResolver,
        file_system: FileSystem,
        user_environment_adapter: UserEnvironmentAdapter,
    ) -> None:
        self.layout_resolver: GlobalCliLayoutResolver = layout_resolver
        self.file_system: FileSystem = file_system
        self.user_environment_adapter: UserEnvironmentAdapter = user_environment_adapter

    def setup_global_cli(self, dry_run: bool = False) -> str:
        plan: GlobalCliSetupPlan = self.build_setup_plan()

        if not dry_run:
            self.apply_setup_plan(plan)

        return self.render_setup_result(plan=plan, dry_run=dry_run)

    def render_global_cli_status(self) -> str:
        plan: GlobalCliSetupPlan = self.build_setup_plan()
        return self.render_setup_result(plan=plan, dry_run=True)

    def build_setup_plan(self) -> GlobalCliSetupPlan:
        layout: GlobalCliLayout = self.layout_resolver.resolve_layout()
        self.validate_layout_paths(layout)

        operations: list[GlobalCliSetupOperation] = []
        operations.append(self.build_directory_operation(layout.root_path))
        operations.append(self.build_directory_operation(layout.bin_directory_path))
        operations.append(self.build_directory_operation(layout.uv_tool_directory_path))
        operations.append(self.build_readme_operation(layout.readme_file_path))
        operations.append(
            self.build_environment_variable_operation(
                variable_name=UV_TOOL_BIN_ENVIRONMENT_VARIABLE_NAME,
                desired_value=str(layout.bin_directory_path),
            )
        )
        operations.append(
            self.build_environment_variable_operation(
                variable_name=UV_TOOL_DIR_ENVIRONMENT_VARIABLE_NAME,
                desired_value=str(layout.uv_tool_directory_path),
            )
        )
        operations.append(self.build_user_path_operation(layout))

        return GlobalCliSetupPlan(layout=layout, operations=tuple(operations))

    def validate_layout_paths(self, layout: GlobalCliLayout) -> None:
        directory_paths: tuple[Path, ...] = (
            layout.root_path,
            layout.bin_directory_path,
            layout.uv_tool_directory_path,
        )

        for directory_path in directory_paths:
            if directory_path.exists() and not directory_path.is_dir():
                raise GlobalCliSetupError(
                    f"Expected directory path, but found a file: {directory_path}"
                )

        if layout.readme_file_path.exists() and not layout.readme_file_path.is_file():
            raise GlobalCliSetupError(
                f"Expected README file path, but found a directory: "
                f"{layout.readme_file_path}"
            )

    def build_directory_operation(
        self,
        directory_path: Path,
    ) -> GlobalCliSetupOperation:
        action: GlobalCliSetupAction = GlobalCliSetupAction.CREATE
        reason: str = "Directory is missing."

        if directory_path.exists():
            action = GlobalCliSetupAction.SKIP
            reason = "Directory already exists."

        return GlobalCliSetupOperation(
            action=action,
            target_type=GlobalCliSetupTargetType.DIRECTORY,
            target_name=str(directory_path),
            target_path=directory_path,
            reason=reason,
        )

    def build_readme_operation(
        self,
        readme_file_path: Path,
    ) -> GlobalCliSetupOperation:
        action: GlobalCliSetupAction = GlobalCliSetupAction.CREATE
        reason: str = "README is missing."

        if readme_file_path.exists():
            action = GlobalCliSetupAction.SKIP
            reason = "README already exists and will be preserved."

        return GlobalCliSetupOperation(
            action=action,
            target_type=GlobalCliSetupTargetType.FILE,
            target_name=str(readme_file_path),
            target_path=readme_file_path,
            reason=reason,
        )

    def build_environment_variable_operation(
        self,
        variable_name: str,
        desired_value: str,
    ) -> GlobalCliSetupOperation:
        current_value: str | None
        current_value = self.user_environment_adapter.get_user_environment_variable(
            variable_name
        )
        action: GlobalCliSetupAction = GlobalCliSetupAction.UPDATE
        reason: str = "User environment variable points outside the canonical layout."

        if current_value is None or current_value == "":
            action = GlobalCliSetupAction.CREATE
            reason = "User environment variable is missing."
        elif current_value == desired_value:
            action = GlobalCliSetupAction.SKIP
            reason = "User environment variable already uses the canonical layout."

        return GlobalCliSetupOperation(
            action=action,
            target_type=GlobalCliSetupTargetType.USER_ENVIRONMENT_VARIABLE,
            target_name=variable_name,
            environment_variable_name=variable_name,
            current_value=current_value,
            desired_value=desired_value,
            reason=reason,
        )

    def build_user_path_operation(
        self,
        layout: GlobalCliLayout,
    ) -> GlobalCliSetupOperation:
        current_value: str | None
        current_value = self.user_environment_adapter.get_user_environment_variable(
            WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME
        )
        desired_value: str = self.build_desired_user_path_value(
            current_value=current_value,
            layout=layout,
        )
        action: GlobalCliSetupAction = GlobalCliSetupAction.UPDATE
        reason: str = (
            "User Path must include only the canonical bin directory from this layout."
        )

        if current_value is None or current_value == "":
            action = GlobalCliSetupAction.CREATE
            reason = "User Path is missing."
        elif current_value == desired_value:
            action = GlobalCliSetupAction.SKIP
            reason = "User Path already contains the canonical bin directory."

        return GlobalCliSetupOperation(
            action=action,
            target_type=GlobalCliSetupTargetType.USER_ENVIRONMENT_VARIABLE,
            target_name=WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME,
            environment_variable_name=WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME,
            current_value=current_value,
            desired_value=desired_value,
            reason=reason,
        )

    def build_desired_user_path_value(
        self,
        current_value: str | None,
        layout: GlobalCliLayout,
    ) -> str:
        path_entries: tuple[str, ...] = self.split_path_entries(current_value)
        desired_path_entries: list[str] = []
        canonical_bin_seen: bool = False
        canonical_bin_key: str = self.normalize_path_for_comparison(
            layout.bin_directory_path
        )
        disallowed_layout_keys: list[str] = [
            self.normalize_path_for_comparison(layout.root_path),
            self.normalize_path_for_comparison(layout.uv_tool_directory_path),
        ]

        for (
            noncanonical_tool_bin_directory_path
        ) in layout.noncanonical_tool_bin_directory_paths:
            disallowed_layout_keys.append(
                self.normalize_path_for_comparison(noncanonical_tool_bin_directory_path)
            )

        for path_entry in path_entries:
            path_entry_key: str = self.normalize_path_entry_for_comparison(path_entry)

            if path_entry_key in disallowed_layout_keys:
                continue

            if path_entry_key == canonical_bin_key:
                if canonical_bin_seen:
                    continue

                canonical_bin_seen = True

            desired_path_entries.append(path_entry)

        if not canonical_bin_seen:
            desired_path_entries.insert(0, str(layout.bin_directory_path))

        return os.pathsep.join(desired_path_entries)

    def split_path_entries(self, current_value: str | None) -> tuple[str, ...]:
        if current_value is None:
            return ()

        path_entries: list[str] = []
        raw_path_entries: list[str] = current_value.split(os.pathsep)

        for raw_path_entry in raw_path_entries:
            normalized_path_entry: str = raw_path_entry.strip().strip('"')

            if normalized_path_entry == "":
                continue

            path_entries.append(normalized_path_entry)

        return tuple(path_entries)

    def normalize_path_entry_for_comparison(self, path_entry: str) -> str:
        expanded_path_entry: str = os.path.expandvars(path_entry)
        return self.normalize_path_for_comparison(Path(expanded_path_entry))

    def normalize_path_for_comparison(self, path: Path) -> str:
        return str(path.resolve(strict=False)).casefold()

    def apply_setup_plan(self, plan: GlobalCliSetupPlan) -> None:
        environment_was_updated: bool = False

        for operation in plan.operations:
            if operation.action == GlobalCliSetupAction.SKIP:
                continue

            match operation.target_type:
                case GlobalCliSetupTargetType.DIRECTORY:
                    self.apply_directory_operation(operation)
                case GlobalCliSetupTargetType.FILE:
                    self.apply_file_operation(operation)
                case GlobalCliSetupTargetType.USER_ENVIRONMENT_VARIABLE:
                    self.apply_environment_variable_operation(operation)
                    environment_was_updated = True

        if environment_was_updated:
            self.user_environment_adapter.notify_environment_changed()

    def apply_directory_operation(self, operation: GlobalCliSetupOperation) -> None:
        if operation.target_path is None:
            raise GlobalCliSetupError("Directory operation is missing target path.")

        self.file_system.ensure_directory(operation.target_path)

    def apply_file_operation(self, operation: GlobalCliSetupOperation) -> None:
        if operation.target_path is None:
            raise GlobalCliSetupError("File operation is missing target path.")

        self.file_system.write_text_if_missing(
            file_path=operation.target_path,
            content=GLOBAL_CLI_LAYOUT_README_CONTENT,
            force=False,
        )

    def apply_environment_variable_operation(
        self,
        operation: GlobalCliSetupOperation,
    ) -> None:
        if operation.environment_variable_name is None:
            raise GlobalCliSetupError(
                "Environment variable operation is missing variable name."
            )

        if operation.desired_value is None:
            raise GlobalCliSetupError(
                "Environment variable operation is missing desired value."
            )

        self.user_environment_adapter.set_user_environment_variable(
            variable_name=operation.environment_variable_name,
            variable_value=operation.desired_value,
        )

    def render_setup_result(
        self,
        plan: GlobalCliSetupPlan,
        dry_run: bool,
    ) -> str:
        lines: list[str] = []
        title: str = "Global CLI setup plan"

        if not dry_run:
            title = "Global CLI setup result"

        lines.append(title)
        lines.append("")
        lines.append(f"Root: {plan.layout.root_path}")
        lines.append(f"Executable bin: {plan.layout.bin_directory_path}")
        lines.append(f"uv tool environments: {plan.layout.uv_tool_directory_path}")
        lines.append("")

        self.append_operation_lines(lines=lines, plan=plan, dry_run=dry_run)

        if not dry_run:
            lines.append("")
            lines.append(
                "Open a new terminal before running uv tool commands so the "
                "updated user environment is loaded."
            )

        return "\n".join(lines).rstrip() + "\n"

    def append_operation_lines(
        self,
        lines: list[str],
        plan: GlobalCliSetupPlan,
        dry_run: bool,
    ) -> None:
        operation_prefixes: dict[GlobalCliSetupAction, str] = {
            GlobalCliSetupAction.CREATE: "Will create" if dry_run else "Created",
            GlobalCliSetupAction.UPDATE: "Will update" if dry_run else "Updated",
            GlobalCliSetupAction.SKIP: "Already configured",
        }

        for operation in plan.operations:
            operation_prefix: str = operation_prefixes[operation.action]
            target_text: str = self.format_operation_target(operation)
            lines.append(f"{operation_prefix}: {target_text}")

    def format_operation_target(self, operation: GlobalCliSetupOperation) -> str:
        match operation.target_type:
            case GlobalCliSetupTargetType.DIRECTORY:
                return f"directory {operation.target_name}"
            case GlobalCliSetupTargetType.FILE:
                return f"file {operation.target_name}"
            case GlobalCliSetupTargetType.USER_ENVIRONMENT_VARIABLE:
                if operation.desired_value is None:
                    raise GlobalCliSetupError(
                        "Environment operation is missing desired value."
                    )

                return (
                    f"user environment "
                    f"{operation.target_name}={operation.desired_value}"
                )

        raise GlobalCliSetupError(
            f"Unsupported global CLI setup target type: {operation.target_type}"
        )
