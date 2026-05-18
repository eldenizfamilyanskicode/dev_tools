# dev-tools

Global CLI tools for exporting a project-aware context without copying `additional_tools`
into every repository.

## Core idea

`dev-tools` is installed once as a global/private Python package.

Each project keeps only local context in `.dev_tools/`:

- `.dev_tools/context.toml`
- `.dev_tools/include.toml`
- `.dev_tools/exclude.toml`
- `.dev_tools/about_current_project.md`
- `.dev_tools/output/`

`dev-tools init` automatically adds `.dev_tools/` to `.git/info/exclude`.
It also applies high-level project bootstrap defaults for editor settings,
Python/TypeScript tooling, and local ignore policy.

## CLI extension model

The root CLI does not know domain commands or menu items.

Each domain may expose its own contribution class:

- `project_init/cli.py`
- `tree_generation/cli.py`
- `include_generation/cli.py`
- `export_context/cli.py`

A contribution can:

1. register argparse subcommands;
2. return menu items for `dev-tools menu`;
3. call only its own domain application service.

The composition root is `dev_tools.cli.containers.cli_container.CliContainer`.

## Commands

```bash
dev-tools init
dev-tools init --dry-run
dev-tools init --application-type python --toolset ruff,pyright --strictness high
dev-tools init --application-type ts --toolset prettier --strictness medium
dev-tools init .dev_tools/about_current_project.md
dev-tools menu
dev-tools run y y
dev-tools run n n
dev-tools run --include-tree --include-about
dev-tools update-include-files
dev-tools tree --print
```

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
the VS Code interpreter path, and creates uv-oriented Python project defaults
when `pyproject.toml` is missing.

Merge policy is intentionally conservative:

- missing files are created;
- `.gitignore` uses a replaceable `dev-tools` managed block;
- `.vscode/settings.json`, `.vscode/extensions.json`, and `pyrightconfig.json`
  are JSON-merged while preserving unknown user keys;
- `pyproject.toml`, `package.json`, `tsconfig.json`, and
  `prettier.config.mjs` are created only when missing, unless `--force` is used.

Use `--dry-run` to print the plan without writing files:

```bash
dev-tools init --dry-run
```

Use `--force` when you intentionally want generated target files such as
`pyproject.toml` or `package.json` to be overwritten.

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
