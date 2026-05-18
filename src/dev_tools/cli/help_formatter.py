from __future__ import annotations

import argparse


class DevToolsHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def start_section(self, heading: str | None) -> None:
        section_heading: str | None = heading

        if heading == "positional arguments":
            section_heading = "command arguments"

        super().start_section(section_heading)
