Before starting work on a issue please assign yourself, or ask to be assigned, to the specific issue. 
Then create a dedicated branch for your changes (creating a fork if needed) and once done make a pull request targeting main.

# Running Tests/Lints

> [!NOTE]
> Tests and lints always runs in CI on pull requests, but it is also possible to run locally for faster iteration loops.

Tests are written using [pytest](https://docs.pytest.org/en/stable/) and can be ran using:
```bash
uv run pytest
```

Linting and formatting is done with [ruff](https://docs.astral.sh/ruff/) as follows:
```bash
uv run ruff check
```
Formatting can be applied with 
```bash
uv run ruff format
```
And some lints can be automatically fixed with
```bash
uv run ruff check --fix
```

Type checking is done with [basedpyright](https://docs.basedpyright.com/) in strict mode:
```bash
uv run basedpyright
```
