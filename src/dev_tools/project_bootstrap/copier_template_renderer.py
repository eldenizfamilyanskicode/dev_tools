from __future__ import annotations

from dev_tools.project_bootstrap.models import TemplateRenderRequest


class CopierTemplateRenderer:
    def render_template(self, request: TemplateRenderRequest) -> None:
        raise NotImplementedError(
            "Copier template rendering is available behind this port, but the "
            "current bootstrap implementation uses internal file writers."
        )
