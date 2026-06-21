# dev-tools

Global CLI tools for exporting a project-aware context without copying `additional_tools`
into every repository.

## Core idea

`dev-tools` is installed once as a global/private Python package.

Each project keeps only local context in `.dev_tools/`:

- `.dev_tools/context.toml`
- `.dev_tools/include.toml`
- `.dev_tools/exclude.toml`
- `.dev_tools/policy_manifest.toml`
- `.dev_tools/about_current_project.md`
- `.dev_tools/output/`

`dev-tools init` automatically adds `.dev_tools/` to `.git/info/exclude`.
It also applies high-level project bootstrap defaults for editor settings,
Python/TypeScript tooling, and local ignore policy.

`dev-tools init` records the concrete policies that were applied in the local
project policy manifest and registers the project path in a machine-local global
index. The index is intentionally local-only and exists so policy updates can be
planned or applied centrally without guessing which projects were initialized.

## Discover available tools

Use the generated CLI help as the source of truth for commands and arguments:

```bash
dev-tools --help
dev-tools init --help
dev-tools tree --help
dev-tools update-include-files --help
dev-tools run --help
dev-tools export-context --help
dev-tools projects --help
dev-tools policies --help
dev-tools global-cli --help
dev-tools global-cli setup --help
```

Use the interactive menu to see the workflow-oriented actions contributed by
each domain:

```bash
dev-tools menu
```

## Current domain contributions

The root CLI owns only global wiring and the `menu` command. Every project
operation is contributed by a domain through a `CliContribution`.

| Domain               | Contribution class                 | Commands                | Menu items                                                                                                         |
| -------------------- | ---------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `project_init`       | `ProjectInitCliContribution`       | `init`                  | Initialize project context                                                                                         |
| `project_policy`     | `ProjectPolicyCliContribution`     | `projects`, `policies`  |                                                                                                                    |
| `tree_generation`    | `TreeGenerationCliContribution`    | `tree`                  | Show project tree                                                                                                  |
| `include_generation` | `IncludeGenerationCliContribution` | `update-include-files`  | Update include files catalog                                                                                       |
| `export_context`     | `ExportContextCliContribution`     | `run`, `export-context` | Run export with about + tree; Run export without about/tree; Run export with tree only; Run export with about only |
| `global_cli`         | `GlobalCliCliContribution`         | `global-cli`            |                                                                                                                    |

## Common commands

```bash
dev-tools init
dev-tools init --dry-run
dev-tools init --skip-pyproject --skip-package-json
dev-tools init --application-type python --toolset ruff,pyright --strictness high
dev-tools init --application-type ts --toolset prettier --strictness medium
dev-tools init .dev_tools/about_current_project.md
dev-tools menu
dev-tools run y y
dev-tools run n n
dev-tools run --include-tree --include-about
dev-tools update-include-files
dev-tools tree --print
dev-tools projects list
dev-tools projects doctor
dev-tools policies status
dev-tools policies plan --all
dev-tools policies apply --project-root /absolute/project/path
dev-tools policies plan --project-root /absolute/project/path --force
dev-tools policies apply --project-root /absolute/project/path --force
dev-tools global-cli status
dev-tools global-cli setup --dry-run
dev-tools global-cli setup
```

## Global CLI layout

`dev-tools` owns one machine-local standard for globally installed CLI tools:

```text
C:\Users\User\repositories\global_cli\
  bin\
  uv_tools\
  README.md
```

`bin` is the only directory from this layout that should be in `PATH`.
`uv_tools` stores uv-managed tool environments. `dev-tools` does not move
existing virtual environments or executable files into this layout; `uv tool`
remains the canonical installation mechanism.

Prepare or inspect the layout explicitly:

```bash
dev-tools global-cli status
dev-tools global-cli setup --dry-run
dev-tools global-cli setup
```

The setup command:

- creates `global_cli\`, `global_cli\bin\`, `global_cli\uv_tools\`, and
  `global_cli\README.md` when missing;
- writes user-level `UV_TOOL_BIN_DIR` to `global_cli\bin`;
- writes user-level `UV_TOOL_DIR` to `global_cli\uv_tools`;
- ensures the user-level `Path` contains `global_cli\bin` and does not contain
  `global_cli\`, `global_cli\uv_tools`, or the default non-canonical uv tool
  bin `C:\Users\User\.local\bin`;
- updates global VS Code user `files.exclude` so common Python cache folders
  such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, and `.ruff_cache` stay
  hidden in the Explorer;
- preserves unrelated `Path` entries and existing `global_cli\README.md`
  content;
- does not move existing executable shims or uv tool environments.

When bootstrapping this project before `dev-tools` is already installed
globally, run the command from the repository and then install with uv:

```bash
uv run dev-tools global-cli setup
uv tool install --reinstall .
```

Open a new terminal after setup so Windows loads the updated user environment.

## CLI extension model

The root CLI does not know domain commands or menu items. It only collects
domain contributions and asks each contribution to register its own surface.

The shared contract is `dev_tools.cli.contracts.CliContribution`:

1. `register_commands(subparsers)` adds argparse subcommands.
2. `get_menu_items()` returns menu actions for `dev-tools menu`.
3. command and menu handlers call the domain application service.

The composition root is `dev_tools.cli.containers.cli_container.CliContainer`.
That container builds the ordered `cli_contributions` list consumed by:

- `CliArgumentParserFactory`, for command registration;
- `InteractiveMenuRunner`, for menu item collection.

To add a new domain:

1. Create the domain package, for example `src/dev_tools/new_domain/`.
2. Put domain behavior in an application service, for example
   `new_domain/application_service.py`.
3. Add `new_domain/cli.py` with a `NewDomainCliContribution` class.
4. Implement `register_commands()` and set each parser default to a command
   handler with `parser.set_defaults(command_handler=...)`.
5. Implement `get_menu_items()` and return `CliMenuItem` values if the domain
   should appear in `dev-tools menu`; return an empty tuple otherwise.
6. Add a dependency-injector container for the domain under
   `src/dev_tools/cli/containers/`.
7. Wire the domain container in `AppContainer`.
8. Wire the CLI contribution in `CliContainer.cli_contributions`.
9. Add or update tests for the command parser and domain service.
10. Update the "Current domain contributions" table above.

A contribution should stay thin: parse CLI arguments, call its own application
service, print user-facing results, and avoid reaching into another domain's
service directly.

## Project bootstrap

By default, `dev-tools init` is equivalent to:

```bash
dev-tools init \
  --application-type full \
  --toolset all \
  --strictness high
```

Supported application types are `python`, `ts`, and `full`. The `--toolset`
argument accepts `mypy`, `ruff`, `pyright`, `prettier`, and `all`; it can be
repeated or passed as a comma-separated list:

```bash
dev-tools init --toolset ruff,pyright
dev-tools init --toolset ruff --toolset pyright
```

Strictness can be `low`, `medium`, or `high`. For Python, strictness maps to
Pyright and VS Code type-checking mode. For TypeScript, `high` enables stricter
`tsconfig.json` options.

The bootstrap writes policy, not environments. It never creates or stores a
`.venv`; it adds `.venv/` and common cache/build folders to `.gitignore`, sets
the workspace VS Code interpreter path, and creates uv-oriented Python project
defaults when `pyproject.toml` is missing or can receive missing generated
sections safely. Machine-level user settings are configured by
`dev-tools global-cli setup`, not by per-project initialization.

Merge policy is intentionally conservative:

- missing files are created;
- `.gitignore` uses a replaceable `dev-tools` managed block;
- `.vscode/settings.json`, `.vscode/extensions.json`, and `pyrightconfig.json`
  are JSON-merged while preserving unknown user keys;
- `pyproject.toml` gets missing generated TOML sections and missing generated
  keys inside existing sections; existing values are preserved;
- `package.json` and `tsconfig.json` are JSON-merged while preserving unknown
  user keys;
- `prettier.config.mjs` is created only when missing, unless `--force` is used.

Use `--dry-run` to print the plan without writing files:

```bash
dev-tools init --dry-run
```

For mature projects where package metadata is already intentionally managed,
skip the generated project-file policies:

```bash
dev-tools init --skip-pyproject --skip-package-json
dev-tools init --application-type python --toolset ruff --skip-pyproject
```

These flags are recorded in `.dev_tools/policy_manifest.toml`, so later
`dev-tools policies plan` and `dev-tools policies apply` continue to skip those
files.

Use `--force` when you intentionally want generated target files such as
`pyproject.toml` or `package.json` to be overwritten.

## Project policy tracking

Initialization writes a local machine-only policy manifest:

```bash
.dev_tools/policy_manifest.toml
```

The manifest records the init settings, the `dev-tools` version at first init,
and each concrete policy id/revision with its latest status. This is the source
of truth for what was applied to the project.

The global project index lives under the user-local dev-tools state directory
and stores only project paths plus manifest locations. Use:

```bash
dev-tools projects list
dev-tools projects doctor
```

Policy updates are explicit. `plan` is read-only; `apply` mutates files and then
updates the manifest:

```bash
dev-tools policies status
dev-tools policies plan --all
dev-tools policies apply --all
```

When a managed JSON/TOML shape conflicts with an existing project value, the
default plan reports the conflict and skips that target file. Use `--force` on
`policies plan` to preview overwrite behavior, and `--force` on `policies apply`
only when overwriting conflicting managed values is intentional.

## Workflow

1. Run `dev-tools init` inside a git project.
2. Edit `.dev_tools/about_current_project.md`.
3. Run `dev-tools update-include-files`.
4. Open `.dev_tools/include.toml`.
5. Uncomment the file paths that should be exported.
6. Run `dev-tools run y y`.

Output order:

1. about current project
2. generated tree
3. content of selected files

Generated files are written to `.dev_tools/output/`.
