from __future__ import annotations

from dev_tools.cli.application import DevToolsCliApplication
from dev_tools.cli.containers.app_container import AppContainer


def main() -> None:
    app_container: AppContainer = AppContainer()
    application: DevToolsCliApplication = app_container.cli.cli_application()
    exit_code: int = application.run()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
