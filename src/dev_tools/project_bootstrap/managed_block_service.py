from __future__ import annotations


class ManagedBlockService:
    def build_managed_content(
        self,
        begin_marker: str,
        end_marker: str,
        block_body: tuple[str, ...],
    ) -> str:
        lines: list[str] = []
        lines.append(begin_marker)

        for body_line in block_body:
            lines.append(body_line)

        lines.append(end_marker)
        return "\n".join(lines) + "\n"

    def merge_managed_block(
        self,
        current_content: str,
        begin_marker: str,
        end_marker: str,
        block_body: tuple[str, ...],
    ) -> str:
        managed_content: str = self.build_managed_content(
            begin_marker=begin_marker,
            end_marker=end_marker,
            block_body=block_body,
        )
        current_lines: list[str] = current_content.splitlines()
        begin_index: int | None = None
        end_index: int | None = None

        for line_index, current_line in enumerate(current_lines):
            if current_line.strip() == begin_marker:
                begin_index = line_index

            if begin_index is not None and current_line.strip() == end_marker:
                end_index = line_index
                break

        if begin_index is not None and end_index is not None:
            replacement_lines: list[str] = managed_content.rstrip("\n").splitlines()
            updated_lines: list[str] = []

            for line_index, current_line in enumerate(current_lines):
                if line_index < begin_index or line_index > end_index:
                    updated_lines.append(current_line)

                if line_index == begin_index:
                    for replacement_line in replacement_lines:
                        updated_lines.append(replacement_line)

            return "\n".join(updated_lines).rstrip("\n") + "\n"

        updated_content: str = current_content
        if updated_content and not updated_content.endswith("\n"):
            updated_content = updated_content + "\n"

        if updated_content and not updated_content.endswith("\n\n"):
            updated_content = updated_content + "\n"

        return updated_content + managed_content

