from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import (
    JsonMergeResult,
    JsonMergeService,
    JsonObject,
)
from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
)


class JsonOperationBuilder:
    def __init__(
        self,
        json_merge_service: JsonMergeService,
        bootstrap_file_writer: BootstrapFileWriter,
    ) -> None:
        self.json_merge_service = json_merge_service
        self.bootstrap_file_writer = bootstrap_file_writer

    def build_operation(
        self,
        project_root_path: Path,
        relative_file_path: Path,
        managed_data: JsonObject,
        force: bool,
        create_only: bool,
        policy_id: str | None,
        policy_revision: int | None,
        merge_strategy: str,
    ) -> BootstrapFileOperation:
        target_file_path: Path = project_root_path / relative_file_path
        current_content: str = ""

        if target_file_path.exists():
            current_content = target_file_path.read_text(encoding="utf-8")

        try:
            merge_result: JsonMergeResult = self.json_merge_service.build_merge_result(
                current_content=current_content,
                managed_data=managed_data,
                overwrite_existing_values=force,
            )
        except ValueError:
            if target_file_path.exists() and not force:
                return BootstrapFileOperation(
                    relative_file_path=relative_file_path,
                    action=BootstrapFileAction.CONFLICT,
                    content=None,
                    reason="existing JSON is not safe to merge",
                    policy_id=policy_id,
                    policy_revision=policy_revision,
                    merge_strategy=merge_strategy,
                    conflict_paths=("$",),
                )

            merge_result = JsonMergeResult(
                content=self.json_merge_service.dump_json(managed_data),
                applied_paths=("$",),
                preserved_paths=(),
                conflict_paths=(),
            )

        return self.bootstrap_file_writer.build_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=merge_result.content,
            force=force,
            create_only=create_only,
            policy_id=policy_id,
            policy_revision=policy_revision,
            merge_strategy=merge_strategy,
            applied_paths=merge_result.applied_paths,
            preserved_paths=merge_result.preserved_paths,
            conflict_paths=merge_result.conflict_paths,
            reason=self.json_merge_service.build_merge_reason(merge_result),
        )
