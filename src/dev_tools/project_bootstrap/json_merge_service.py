from __future__ import annotations

import json

from typing import TypeAlias, cast

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | "JsonArray" | "JsonObject"
JsonArray: TypeAlias = list[JsonValue]
JsonObject: TypeAlias = dict[str, JsonValue]


class JsonMergeService:
    def merge_json_content(
        self,
        current_content: str,
        managed_data: JsonObject,
    ) -> str:
        current_data: JsonObject = {}

        if current_content.strip():
            loaded_data: object = json.loads(current_content)

            if not isinstance(loaded_data, dict):
                raise ValueError("Expected JSON object at document root.")

            current_data = cast(JsonObject, loaded_data)

        merged_data: JsonObject = self.merge_objects(
            current_data=current_data,
            managed_data=managed_data,
        )

        return self.dump_json(merged_data)

    def merge_objects(
        self,
        current_data: JsonObject,
        managed_data: JsonObject,
    ) -> JsonObject:
        merged_data: JsonObject = {}

        for current_key, current_value in current_data.items():
            merged_data[current_key] = current_value

        for managed_key, managed_value in managed_data.items():
            existing_value: JsonValue | None = merged_data.get(managed_key)

            if managed_key not in merged_data:
                merged_data[managed_key] = managed_value
                continue

            if isinstance(existing_value, dict) and isinstance(managed_value, dict):
                merged_data[managed_key] = self.merge_objects(
                    current_data=existing_value,
                    managed_data=managed_value,
                )
                continue

            if isinstance(existing_value, list) and isinstance(managed_value, list):
                merged_data[managed_key] = self.merge_unique_lists(
                    current_values=existing_value,
                    managed_values=managed_value,
                )
                continue

            merged_data[managed_key] = managed_value

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