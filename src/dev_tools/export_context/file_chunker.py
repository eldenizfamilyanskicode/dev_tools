from __future__ import annotations

from dev_tools.typings.integers import MaximumLinesPerChunk
from dev_tools.typings.strings import FileSeparator


class FileChunker:
    def split_text_into_chunks(
        self,
        content: str,
        maximum_lines_per_chunk: MaximumLinesPerChunk,
        separator_marker: FileSeparator,
    ) -> list[str]:
        if content == "":
            return []

        lines: list[str] = content.splitlines(keepends=True)
        blocks: list[list[str]] = self.split_lines_into_blocks(
            lines=lines,
            separator_marker=separator_marker,
        )
        chunks: list[list[str]] = self.assemble_chunks(
            blocks=blocks,
            maximum_lines_per_chunk=maximum_lines_per_chunk,
        )
        chunk_texts: list[str] = []

        for chunk_lines in chunks:
            chunk_text: str = "".join(chunk_lines)
            chunk_texts.append(chunk_text)

        return chunk_texts

    def split_lines_into_blocks(
        self,
        lines: list[str],
        separator_marker: FileSeparator,
    ) -> list[list[str]]:
        separator_marker_as_string: str = str(separator_marker)

        if separator_marker_as_string == "":
            raise ValueError("File separator cannot be empty.")

        blocks: list[list[str]] = []
        current_block: list[str] = []

        for line in lines:
            current_block.append(line)

            if separator_marker_as_string in line:
                blocks.append(current_block)
                current_block = []

        if current_block:
            blocks.append(current_block)

        return blocks

    def assemble_chunks(
        self,
        blocks: list[list[str]],
        maximum_lines_per_chunk: MaximumLinesPerChunk,
    ) -> list[list[str]]:
        chunks: list[list[str]] = []
        current_chunk: list[str] = []
        current_chunk_line_count: int = 0
        maximum_lines_per_chunk_as_int: int = int(maximum_lines_per_chunk)

        if maximum_lines_per_chunk_as_int <= 0:
            raise ValueError("maximum_lines_per_chunk must be greater than zero.")

        for block in blocks:
            block_line_count: int = len(block)
            would_exceed_limit: bool = (
                current_chunk_line_count + block_line_count
                > maximum_lines_per_chunk_as_int
            )

            if current_chunk and would_exceed_limit:
                chunks.append(current_chunk)
                current_chunk = []
                current_chunk_line_count = 0

            current_chunk.extend(block)
            current_chunk_line_count = current_chunk_line_count + block_line_count

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
