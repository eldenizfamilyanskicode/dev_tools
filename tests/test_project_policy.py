from __future__ import annotations

import json
from pathlib import Path

from dev_tools.project_policy.application_service import ProjectPolicyService
from tests.project_policy_helpers import (
    bootstrap_and_record_project,
    build_project_policy_service,
)


def test_record_initialized_project_writes_manifest_and_index(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")
    index_content: str = (tmp_path / "index" / "project_index.toml").read_text(
        encoding="utf-8"
    )

    assert "gitignore.managed_block.common_local_artifacts" in manifest_content
    assert "pyproject.uv_python_tooling_defaults" in manifest_content
    assert f'project_root = "{project_root_path.as_posix()}"' in index_content
    assert 'status = "active"' in index_content


def test_manifest_records_preserved_policy_paths(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
                "devDependencies": {
                    "typescript": "5.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")

    assert 'status = "applied_with_skips"' in manifest_content
    assert 'preserved_paths = ["name", "version", "devDependencies.typescript"]' in (
        manifest_content
    )


def test_manifest_records_json_conflict_paths(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "scripts": "custom-script-shape",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")

    assert 'status = "conflict"' in manifest_content
    assert 'conflict_paths = ["scripts"]' in manifest_content

    package_document: dict[str, object] = json.loads(
        package_file_path.read_text(encoding="utf-8")
    )
    assert package_document == {"scripts": "custom-script-shape"}


def test_policy_plan_reports_json_conflict_without_partial_write(
    tmp_path: Path,
) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "scripts": "custom-script-shape",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.render_update_plan(
        requested_project_root=project_root_path,
        include_all_projects=False,
    )
    package_document: dict[str, object] = json.loads(
        package_file_path.read_text(encoding="utf-8")
    )

    assert "package_json.typescript_tooling_defaults@1 [conflict]" in result_text
    assert "action: conflict; status: conflict" in result_text
    assert "conflicts: scripts" in result_text
    assert package_document == {"scripts": "custom-script-shape"}


def test_policy_plan_shows_revision_action_and_merge_details(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.render_update_plan(
        requested_project_root=project_root_path,
        include_all_projects=False,
    )

    assert "package_json.typescript_tooling_defaults@1 [skipped]" in result_text
    assert "action: skip; status: skipped_existing" in result_text
    assert "target: package.json; merge: json_merge" in result_text
    assert "preserved: name, version" in result_text


def test_apply_policy_updates_preserves_user_values_and_records_satisfied_status(
    tmp_path: Path,
) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=project_root_path,
        include_all_projects=False,
    )
    package_document: dict[str, object] = json.loads(
        package_file_path.read_text(encoding="utf-8")
    )
    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")

    assert "Applied project policy updates" in result_text
    assert package_document["name"] == "custom-package"
    assert package_document["version"] == "9.9.9"
    assert 'status = "skipped_existing"' in manifest_content
    assert 'preserved_paths = ["name", "version"]' in manifest_content


def test_policy_plan_force_previews_overwrite_of_preserved_values(
    tmp_path: Path,
) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.render_update_plan(
        requested_project_root=project_root_path,
        include_all_projects=False,
        force=True,
    )

    assert "package_json.typescript_tooling_defaults@1 [drift]" in result_text
    assert "action: update; status: applied" in result_text
    assert "applied: name, version" in result_text


def test_apply_policy_updates_uses_global_index(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )
    pyproject_file_path: Path = project_root_path / "pyproject.toml"
    pyproject_file_path.write_text('[project]\nname = "custom"\n', encoding="utf-8")

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=None,
        include_all_projects=True,
    )

    pyproject_content: str = pyproject_file_path.read_text(encoding="utf-8")

    assert "Applied project policy updates" in result_text
    assert "[tool.uv]" in pyproject_content
    assert "[tool.ruff]" in pyproject_content
    assert pyproject_content.count("[project]") == 1


def test_apply_policy_updates_force_overwrites_conflicting_managed_values(
    tmp_path: Path,
) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "scripts": "custom-script-shape",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=project_root_path,
        include_all_projects=False,
        force=True,
    )
    package_document: dict[str, object] = json.loads(
        package_file_path.read_text(encoding="utf-8")
    )
    package_scripts: object = package_document["scripts"]

    assert "Applied project policy updates" in result_text
    assert isinstance(package_scripts, dict)
    assert package_scripts["typecheck"] == "tsc --noEmit"


def test_projects_doctor_marks_invalid_manifest(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )
    manifest_file_path: Path = project_root_path / ".dev_tools" / "policy_manifest.toml"
    manifest_file_path.write_text("manifest_version = ", encoding="utf-8")

    result_text: str = project_policy_service.render_registered_projects(refresh=True)

    assert "invalid_manifest" in result_text
    assert str(project_root_path) in result_text


def test_apply_all_skips_invalid_manifest_projects(tmp_path: Path) -> None:
    active_project_root_path: Path = tmp_path / "active_project"
    invalid_project_root_path: Path = tmp_path / "invalid_project"
    active_project_root_path.mkdir()
    invalid_project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=active_project_root_path,
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=invalid_project_root_path,
    )
    invalid_manifest_file_path: Path = (
        invalid_project_root_path / ".dev_tools" / "policy_manifest.toml"
    )
    invalid_manifest_file_path.write_text("manifest_version = ", encoding="utf-8")

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=None,
        include_all_projects=True,
    )

    assert str(active_project_root_path) in result_text
    assert "Skipped registered projects:" in result_text
    assert "invalid_manifest" in result_text
    assert str(invalid_project_root_path) in result_text
