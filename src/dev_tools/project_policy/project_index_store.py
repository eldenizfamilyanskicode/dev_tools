from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import ValidationError

from dev_tools.project_policy.constants import (
    GLOBAL_INDEX_FILE_NAME,
    GLOBAL_STATE_DIRECTORY_NAME,
    LINUX_STATE_ENVIRONMENT_VARIABLE_NAME,
    LOCAL_APPLICATION_DATA_ENVIRONMENT_VARIABLE_NAME,
    PROJECT_INDEX_VERSION,
)
from dev_tools.project_policy.manifest_store import ProjectPolicyManifestStore
from dev_tools.project_policy.models import (
    ProjectPolicyIndex,
    ProjectPolicyManifest,
    ProjectPolicyProjectId,
    RegisteredProject,
    RegisteredProjectStatus,
)
from dev_tools.shared.file_system import FileSystem


class ProjectIndexStore:
    def __init__(
        self,
        file_system: FileSystem,
        manifest_store: ProjectPolicyManifestStore,
        index_file_path: Path | None = None,
    ) -> None:
        self.file_system = file_system
        self.manifest_store = manifest_store
        self.index_file_path = index_file_path

    def resolve_index_file_path(self) -> Path:
        if self.index_file_path is not None:
            return self.index_file_path

        local_application_data_path: str | None = os.environ.get(
            LOCAL_APPLICATION_DATA_ENVIRONMENT_VARIABLE_NAME
        )
        if local_application_data_path is not None:
            return (
                Path(local_application_data_path)
                / GLOBAL_STATE_DIRECTORY_NAME
                / GLOBAL_INDEX_FILE_NAME
            )

        linux_state_path: str | None = os.environ.get(
            LINUX_STATE_ENVIRONMENT_VARIABLE_NAME
        )
        if linux_state_path is not None:
            return (
                Path(linux_state_path)
                / GLOBAL_STATE_DIRECTORY_NAME
                / GLOBAL_INDEX_FILE_NAME
            )

        return Path.home() / ".dev_tools" / GLOBAL_INDEX_FILE_NAME

    def load_index(self) -> ProjectPolicyIndex:
        index_file_path: Path = self.resolve_index_file_path()

        if not index_file_path.exists():
            return ProjectPolicyIndex(
                index_version=PROJECT_INDEX_VERSION,
                projects=(),
            )

        with index_file_path.open("rb") as index_file_handler:
            index_document: dict[str, object] = tomllib.load(index_file_handler)

        return self.build_index(index_document)

    def write_index(self, project_index: ProjectPolicyIndex) -> Path:
        index_file_path: Path = self.resolve_index_file_path()
        self.file_system.write_text(
            file_path=index_file_path,
            content=self.serialize_index(project_index),
        )
        return index_file_path

    def upsert_manifest(
        self,
        manifest: ProjectPolicyManifest,
        timestamp: str,
    ) -> ProjectPolicyIndex:
        project_index: ProjectPolicyIndex = self.load_index()
        manifest_file_path: Path = self.manifest_store.build_manifest_file_path(
            manifest.project_root_path
        )
        registered_project: RegisteredProject = RegisteredProject(
            project_id=manifest.project_id,
            project_root_path=manifest.project_root_path,
            manifest_file_path=manifest_file_path,
            last_seen_at=timestamp,
            status=RegisteredProjectStatus.ACTIVE,
        )
        updated_projects: list[RegisteredProject] = []
        replaced_existing_project: bool = False

        for existing_project in project_index.projects:
            if existing_project.project_id == registered_project.project_id:
                updated_projects.append(registered_project)
                replaced_existing_project = True
                continue

            if (
                existing_project.project_root_path.resolve()
                == registered_project.project_root_path.resolve()
            ):
                updated_projects.append(registered_project)
                replaced_existing_project = True
                continue

            updated_projects.append(existing_project)

        if not replaced_existing_project:
            updated_projects.append(registered_project)

        updated_index: ProjectPolicyIndex = ProjectPolicyIndex(
            index_version=project_index.index_version,
            projects=tuple(updated_projects),
        )
        self.write_index(updated_index)
        return updated_index

    def refresh_project_statuses(
        self,
        timestamp: str,
    ) -> ProjectPolicyIndex:
        project_index: ProjectPolicyIndex = self.load_index()
        refreshed_projects: list[RegisteredProject] = []

        for registered_project in project_index.projects:
            refreshed_projects.append(
                self.refresh_project_status(
                    registered_project=registered_project,
                    timestamp=timestamp,
                )
            )

        refreshed_index: ProjectPolicyIndex = ProjectPolicyIndex(
            index_version=project_index.index_version,
            projects=tuple(refreshed_projects),
        )
        self.write_index(refreshed_index)
        return refreshed_index

    def refresh_project_status(
        self,
        registered_project: RegisteredProject,
        timestamp: str,
    ) -> RegisteredProject:
        if not registered_project.project_root_path.exists():
            return registered_project.model_copy(
                update={
                    "last_seen_at": timestamp,
                    "status": RegisteredProjectStatus.MISSING,
                }
            )

        if not registered_project.manifest_file_path.exists():
            return registered_project.model_copy(
                update={
                    "last_seen_at": timestamp,
                    "status": RegisteredProjectStatus.INVALID_MANIFEST,
                }
            )

        try:
            manifest: ProjectPolicyManifest = self.manifest_store.load_manifest(
                registered_project.project_root_path
            )
        except (
            FileNotFoundError,
            NotADirectoryError,
            tomllib.TOMLDecodeError,
            TypeError,
            ValueError,
            ValidationError,
        ):
            return registered_project.model_copy(
                update={
                    "last_seen_at": timestamp,
                    "status": RegisteredProjectStatus.INVALID_MANIFEST,
                }
            )

        if manifest.project_root_path != registered_project.project_root_path.resolve():
            return registered_project.model_copy(
                update={
                    "last_seen_at": timestamp,
                    "status": RegisteredProjectStatus.INVALID_MANIFEST,
                }
            )

        return registered_project.model_copy(
            update={
                "last_seen_at": timestamp,
                "status": RegisteredProjectStatus.ACTIVE,
            }
        )

    def build_index(self, index_document: dict[str, object]) -> ProjectPolicyIndex:
        project_documents: tuple[dict[str, object], ...] = self.get_table_items(
            document=index_document,
            key="projects",
        )
        registered_projects: list[RegisteredProject] = []

        for project_document in project_documents:
            registered_projects.append(self.build_registered_project(project_document))

        return ProjectPolicyIndex(
            index_version=self.get_int(index_document, "index_version"),
            projects=tuple(registered_projects),
        )

    def build_registered_project(
        self,
        project_document: dict[str, object],
    ) -> RegisteredProject:
        return RegisteredProject(
            project_id=ProjectPolicyProjectId(
                self.get_string(project_document, "project_id")
            ),
            project_root_path=Path(
                self.get_string(project_document, "project_root")
            ).resolve(),
            manifest_file_path=Path(
                self.get_string(project_document, "manifest_path")
            ).resolve(),
            last_seen_at=self.get_string(project_document, "last_seen_at"),
            status=RegisteredProjectStatus(self.get_string(project_document, "status")),
        )

    def serialize_index(self, project_index: ProjectPolicyIndex) -> str:
        lines: list[str] = []
        lines.append(f"index_version = {project_index.index_version}")

        for registered_project in project_index.projects:
            escaped_project_id: str = self.escape_string(
                str(registered_project.project_id)
            )
            escaped_last_seen_at: str = self.escape_string(
                registered_project.last_seen_at
            )
            lines.append("")
            lines.append("[[projects]]")
            lines.append(f'project_id = "{escaped_project_id}"')
            lines.append(
                "project_root = "
                f'"{self.escape_string(registered_project.project_root_path.as_posix())}"'
            )
            lines.append(
                "manifest_path = "
                f'"{self.escape_string(registered_project.manifest_file_path.as_posix())}"'
            )
            lines.append(f'last_seen_at = "{escaped_last_seen_at}"')
            lines.append(f'status = "{registered_project.status.value}"')

        return "\n".join(lines).rstrip() + "\n"

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

    def get_int(self, document: dict[str, object], key: str) -> int:
        value: object | None = document.get(key)

        if not isinstance(value, int):
            raise TypeError(f"Expected `{key}` to be integer.")

        return value

    def escape_string(self, value: str) -> str:
        escaped_value: str = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return escaped_value
