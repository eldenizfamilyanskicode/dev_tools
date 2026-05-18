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
dev-tools init .dev_tools/about_current_project.md
dev-tools menu
dev-tools run y y
dev-tools run n n
dev-tools run --include-tree --include-about
dev-tools update-include-files
dev-tools tree --print
```

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
