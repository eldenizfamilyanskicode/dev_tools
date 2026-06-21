from __future__ import annotations

import tomllib
from pathlib import Path

from dev_tools.project_bootstrap.models import (
    ApplicationType,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_init.constants import DEFAULT_PROJECT_CONTEXT_DIRECTORY_NAME
from dev_tools.project_policy.constants import POLICY_MANIFEST_FILE_NAME
from dev_tools.project_policy.models import (
    PolicyApplicationStatus,
    ProjectPolicyInitSettings,
    ProjectPolicyManifest,
    ProjectPolicyProjectId,
    ProjectPolicyRecord,
)
from dev_tools.shared.file_system import FileSystem


class ProjectPolicyManifestStore:
    def __init__(self, file_system: FileSystem) -> None:
        self.file_system = file_system

    def build_manifest_file_path(self, project_root_path: Path) -> Path:
        return (
            project_root_path
            / DEFAULT_PROJECT_CONTEXT_DIRECTORY_NAME
            / POLICY_MANIFEST_FILE_NAME
        )

    def load_manifest(self, project_root_path: Path) -> ProjectPolicyManifest:
        manifest_file_path: Path = self.build_manifest_file_path(project_root_path)

        if not manifest_file_path.exists():
            raise FileNotFoundError(
                f"Project policy manifest not found: {manifest_file_path}. "
                "Run `dev-tools init` first."
            )

        with manifest_file_path.open("rb") as manifest_file_handler:
            manifest_document: dict[str, object] = tomllib.load(manifest_file_handler)

        return self.build_manifest(manifest_document)

    def write_manifest(self, manifest: ProjectPolicyManifest) -> Path:
        manifest_file_path: Path = self.build_manifest_file_path(
            manifest.project_root_path
        )
        self.file_system.write_text(
            file_path=manifest_file_path,
            content=self.serialize_manifest(manifest),
        )
        return manifest_file_path

    def build_manifest(
        self,
        manifest_document: dict[str, object],
    ) -> ProjectPolicyManifest:
        init_document: dict[str, object] = self.get_table(
            document=manifest_document,
            key="init",
        )
        policy_documents: tuple[dict[str, object], ...] = self.get_table_items(
            document=manifest_document,
            key="policies",
        )
        policy_records: list[ProjectPolicyRecord] = []

        for policy_document in policy_documents:
            policy_records.append(self.build_policy_record(policy_document))

        return ProjectPolicyManifest(
            manifest_version=self.get_int(manifest_document, "manifest_version"),
            project_id=ProjectPolicyProjectId(
                self.get_string(manifest_document, "project_id")
            ),
            project_root_path=Path(
                self.get_string(manifest_document, "project_root")
            ).resolve(),
            initialized_at=self.get_string(manifest_document, "initialized_at"),
            updated_at=self.get_string(manifest_document, "updated_at"),
            dev_tools_version_at_init=self.get_string(
                manifest_document,
                "dev_tools_version_at_init",
            ),
            init_settings=ProjectPolicyInitSettings(
                application_type=ApplicationType(
                    self.get_string(init_document, "application_type")
                ),
                tool_names=self.get_tool_names(init_document),
                strictness_level=StrictnessLevel(
                    self.get_string(init_document, "strictness")
                ),
                manage_pyproject=self.get_optional_bool(
                    init_document,
                    "manage_pyproject",
                    True,
                ),
                manage_package_json=self.get_optional_bool(
                    init_document,
                    "manage_package_json",
                    True,
                ),
            ),
            policies=tuple(policy_records),
        )

    def build_policy_record(
        self,
        policy_document: dict[str, object],
    ) -> ProjectPolicyRecord:
        raw_content_hash: str | None = self.get_optional_string(
            policy_document,
            "content_hash",
        )
        raw_applied_at: str | None = self.get_optional_string(
            policy_document,
            "applied_at",
        )

        return ProjectPolicyRecord(
            policy_id=self.get_string(policy_document, "policy_id"),
            policy_revision=self.get_int(policy_document, "policy_revision"),
            status=PolicyApplicationStatus(self.get_string(policy_document, "status")),
            merge_strategy=self.get_string(policy_document, "merge_strategy"),
            target_files=self.get_string_items(policy_document, "target_files"),
            reason=self.get_optional_string(policy_document, "reason") or "",
            applied_paths=self.get_optional_string_items(
                policy_document,
                "applied_paths",
            ),
            preserved_paths=self.get_optional_string_items(
                policy_document,
                "preserved_paths",
            ),
            conflict_paths=self.get_optional_string_items(
                policy_document,
                "conflict_paths",
            ),
            content_hash=raw_content_hash,
            applied_at=raw_applied_at,
        )

    def get_tool_names(
        self,
        init_document: dict[str, object],
    ) -> tuple[ToolName, ...]:
        raw_tool_names: tuple[str, ...] = self.get_string_items(
            init_document,
            "toolset",
        )
        tool_names: list[ToolName] = []

        for raw_tool_name in raw_tool_names:
            tool_names.append(ToolName(raw_tool_name))

        return tuple(tool_names)

    def serialize_manifest(self, manifest: ProjectPolicyManifest) -> str:
        lines: list[str] = []
        escaped_project_root: str = self.escape_string(
            manifest.project_root_path.as_posix()
        )
        serialized_tool_names: str = self.serialize_string_list(
            self.get_tool_name_values(manifest)
        )
        lines.append(f"manifest_version = {manifest.manifest_version}")
        lines.append(f'project_id = "{self.escape_string(str(manifest.project_id))}"')
        lines.append(f'project_root = "{escaped_project_root}"')
        lines.append(
            f'initialized_at = "{self.escape_string(manifest.initialized_at)}"'
        )
        lines.append(f'updated_at = "{self.escape_string(manifest.updated_at)}"')
        lines.append(
            "dev_tools_version_at_init = "
            f'"{self.escape_string(manifest.dev_tools_version_at_init)}"'
        )
        lines.append("")
        lines.append("[init]")
        lines.append(
            f'application_type = "{manifest.init_settings.application_type.value}"'
        )
        lines.append(f"toolset = {serialized_tool_names}")
        lines.append(f'strictness = "{manifest.init_settings.strictness_level.value}"')
        manage_pyproject: str = self.serialize_bool(
            manifest.init_settings.manage_pyproject
        )
        manage_package_json: str = self.serialize_bool(
            manifest.init_settings.manage_package_json
        )
        lines.append(f"manage_pyproject = {manage_pyproject}")
        lines.append(f"manage_package_json = {manage_package_json}")

        for policy_record in manifest.policies:
            lines.append("")
            lines.append("[[policies]]")
            lines.append(f'policy_id = "{self.escape_string(policy_record.policy_id)}"')
            lines.append(f"policy_revision = {policy_record.policy_revision}")
            lines.append(f'status = "{policy_record.status.value}"')
            lines.append(
                f'merge_strategy = "{self.escape_string(policy_record.merge_strategy)}"'
            )
            lines.append(
                "target_files = "
                f"{self.serialize_string_list(policy_record.target_files)}"
            )
            lines.append(f'reason = "{self.escape_string(policy_record.reason)}"')

            if policy_record.applied_paths:
                lines.append(
                    "applied_paths = "
                    f"{self.serialize_string_list(policy_record.applied_paths)}"
                )

            if policy_record.preserved_paths:
                lines.append(
                    "preserved_paths = "
                    f"{self.serialize_string_list(policy_record.preserved_paths)}"
                )

            if policy_record.conflict_paths:
                lines.append(
                    "conflict_paths = "
                    f"{self.serialize_string_list(policy_record.conflict_paths)}"
                )

            if policy_record.content_hash is not None:
                lines.append(
                    f'content_hash = "{self.escape_string(policy_record.content_hash)}"'
                )

            if policy_record.applied_at is not None:
                lines.append(
                    f'applied_at = "{self.escape_string(policy_record.applied_at)}"'
                )

        return "\n".join(lines).rstrip() + "\n"

    def get_tool_name_values(
        self,
        manifest: ProjectPolicyManifest,
    ) -> tuple[str, ...]:
        tool_name_values: list[str] = []

        for tool_name in manifest.init_settings.tool_names:
            tool_name_values.append(tool_name.value)

        return tuple(tool_name_values)

    def get_table(
        self,
        document: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        value: object | None = document.get(key)

        if not isinstance(value, dict):
            raise TypeError(f"Expected TOML table `{key}`.")

        table_document: dict[str, object] = {}
        for raw_key, raw_value in value.items():  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(raw_key, str):
                raise TypeError(f"Expected TOML table `{key}` keys to be strings.")

            table_document[raw_key] = raw_value

        return table_document

    def get_table_items(
        self,
        document: dict[str, object],
        key: str,
    ) -> tuple[dict[str, object], ...]:
        value: object | None = document.get(key)

        if value is None:
            return ()

        if not isinstance(value, list):
            raise TypeError(f"Expected TOML array table `{key}`.")

        table_items: list[dict[str, object]] = []

        for raw_item in value:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(raw_item, dict):
                raise TypeError(f"Expected `{key}` item to be a table.")

            table_item: dict[str, object] = {}
            for raw_key, raw_value in raw_item.items():  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(raw_key, str):
                    raise TypeError(f"Expected TOML table `{key}` keys to be strings.")

                table_item[raw_key] = raw_value

            table_items.append(table_item)

        return tuple(table_items)

    def get_string(self, document: dict[str, object], key: str) -> str:
        value: object | None = document.get(key)

        if not isinstance(value, str):
            raise TypeError(f"Expected `{key}` to be string.")

        return value

    def get_optional_string(self, document: dict[str, object], key: str) -> str | None:
        value: object | None = document.get(key)

        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(f"Expected `{key}` to be string.")

        return value

    def get_optional_bool(
        self,
        document: dict[str, object],
        key: str,
        default: bool,
    ) -> bool:
        value: object | None = document.get(key)

        if value is None:
            return default

        if not isinstance(value, bool):
            raise TypeError(f"Expected `{key}` to be boolean.")

        return value

    def get_int(self, document: dict[str, object], key: str) -> int:
        value: object | None = document.get(key)

        if not isinstance(value, int):
            raise TypeError(f"Expected `{key}` to be integer.")

        return value

    def get_string_items(
        self,
        document: dict[str, object],
        key: str,
    ) -> tuple[str, ...]:
        value: object | None = document.get(key)

        if not isinstance(value, list):
            raise TypeError(f"Expected `{key}` to be list of strings.")

        string_items: list[str] = []
        for raw_item in value:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(raw_item, str):
                raise TypeError(f"Expected `{key}` items to be strings.")

            string_items.append(raw_item)

        return tuple(string_items)

    def get_optional_string_items(
        self,
        document: dict[str, object],
        key: str,
    ) -> tuple[str, ...]:
        value: object | None = document.get(key)

        if value is None:
            return ()

        return self.get_string_items(document, key)

    def serialize_string_list(self, values: tuple[str, ...]) -> str:
        serialized_values: list[str] = []

        for value in values:
            serialized_values.append(f'"{self.escape_string(value)}"')

        return "[" + ", ".join(serialized_values) + "]"

    def serialize_bool(self, value: bool) -> str:
        if value:
            return "true"

        return "false"

    def escape_string(self, value: str) -> str:
        escaped_value: str = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return escaped_value
