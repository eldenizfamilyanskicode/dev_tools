from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | JsonArray | JsonObject
type JsonArray = list[JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True)
class JsonMergeResult:
    content: str
    applied_paths: tuple[str, ...]
    preserved_paths: tuple[str, ...]
    conflict_paths: tuple[str, ...]


@dataclass
class JsonMergeAccumulator:
    applied_paths: list[str] = field(default_factory=list)
    preserved_paths: list[str] = field(default_factory=list)
    conflict_paths: list[str] = field(default_factory=list)


class JsonMergeService:
    def merge_json_content(
        self,
        current_content: str,
        managed_data: JsonObject,
        overwrite_existing_values: bool = False,
    ) -> str:
        merge_result: JsonMergeResult = self.build_merge_result(
            current_content=current_content,
            managed_data=managed_data,
            overwrite_existing_values=overwrite_existing_values,
        )
        return merge_result.content

    def build_merge_result(
        self,
        current_content: str,
        managed_data: JsonObject,
        overwrite_existing_values: bool = False,
    ) -> JsonMergeResult:
        current_data: JsonObject = {}

        if current_content.strip():
            loaded_data: object = json.loads(current_content)

            if not isinstance(loaded_data, dict):
                raise ValueError("Expected JSON object at document root.")

            current_data = cast(JsonObject, loaded_data)

        merge_accumulator: JsonMergeAccumulator = JsonMergeAccumulator()
        merged_data: JsonObject = self.merge_objects(
            current_data=current_data,
            managed_data=managed_data,
            overwrite_existing_values=overwrite_existing_values,
            path_parts=(),
            merge_accumulator=merge_accumulator,
        )

        return JsonMergeResult(
            content=self.dump_json(merged_data),
            applied_paths=tuple(merge_accumulator.applied_paths),
            preserved_paths=tuple(merge_accumulator.preserved_paths),
            conflict_paths=tuple(merge_accumulator.conflict_paths),
        )

    def merge_objects(
        self,
        current_data: JsonObject,
        managed_data: JsonObject,
        overwrite_existing_values: bool = False,
        path_parts: tuple[str, ...] = (),
        merge_accumulator: JsonMergeAccumulator | None = None,
    ) -> JsonObject:
        resolved_merge_accumulator: JsonMergeAccumulator = (
            merge_accumulator or JsonMergeAccumulator()
        )
        merged_data: JsonObject = {}

        for current_key, current_value in current_data.items():
            merged_data[current_key] = current_value

        for managed_key, managed_value in managed_data.items():
            managed_path_parts: tuple[str, ...] = path_parts + (managed_key,)
            managed_path: str = self.format_path(managed_path_parts)
            existing_value: JsonValue | None = merged_data.get(managed_key)

            if managed_key not in merged_data:
                merged_data[managed_key] = managed_value
                resolved_merge_accumulator.applied_paths.append(managed_path)
                continue

            if isinstance(existing_value, dict) and isinstance(managed_value, dict):
                merged_data[managed_key] = self.merge_objects(
                    current_data=existing_value,
                    managed_data=managed_value,
                    overwrite_existing_values=overwrite_existing_values,
                    path_parts=managed_path_parts,
                    merge_accumulator=resolved_merge_accumulator,
                )
                continue

            if isinstance(existing_value, list) and isinstance(managed_value, list):
                if overwrite_existing_values:
                    if existing_value != managed_value:
                        resolved_merge_accumulator.applied_paths.append(managed_path)

                    merged_data[managed_key] = managed_value
                    continue

                merged_values: JsonArray = self.merge_unique_lists(
                    current_values=existing_value,
                    managed_values=managed_value,
                )
                if merged_values != existing_value:
                    resolved_merge_accumulator.applied_paths.append(managed_path)

                merged_data[managed_key] = merged_values
                continue

            if isinstance(existing_value, dict) or isinstance(managed_value, dict):
                if overwrite_existing_values:
                    merged_data[managed_key] = managed_value
                    resolved_merge_accumulator.applied_paths.append(managed_path)
                    continue

                resolved_merge_accumulator.conflict_paths.append(managed_path)
                continue

            if isinstance(existing_value, list) or isinstance(managed_value, list):
                if overwrite_existing_values:
                    merged_data[managed_key] = managed_value
                    resolved_merge_accumulator.applied_paths.append(managed_path)
                    continue

                resolved_merge_accumulator.conflict_paths.append(managed_path)
                continue

            if existing_value == managed_value:
                continue

            if overwrite_existing_values:
                merged_data[managed_key] = managed_value
                resolved_merge_accumulator.applied_paths.append(managed_path)
                continue

            resolved_merge_accumulator.preserved_paths.append(managed_path)

        return merged_data

    def merge_unique_lists(
        self,
        current_values: JsonArray,
        managed_values: JsonArray,
    ) -> JsonArray:
        merged_values: JsonArray = []

        for current_value in current_values:
            merged_values.append(current_value)

        for managed_value in managed_values:
            already_exists: bool = False

            for existing_value in merged_values:
                if existing_value == managed_value:
                    already_exists = True
                    break

            if not already_exists:
                merged_values.append(managed_value)

        return merged_values

    def dump_json(self, data: JsonObject) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def format_path(self, path_parts: tuple[str, ...]) -> str:
        return ".".join(path_parts)

    def build_merge_reason(self, merge_result: JsonMergeResult) -> str:
        reason_parts: list[str] = []

        if merge_result.preserved_paths:
            reason_parts.append(
                "preserved existing values: "
                f"{self.format_paths(merge_result.preserved_paths)}"
            )

        if merge_result.conflict_paths:
            reason_parts.append(
                "conflicting existing value types: "
                f"{self.format_paths(merge_result.conflict_paths)}"
            )

        return "; ".join(reason_parts)

    def format_paths(self, paths: tuple[str, ...]) -> str:
        formatted_paths: list[str] = []

        for path in paths:
            formatted_paths.append(path)

        return ", ".join(formatted_paths)
