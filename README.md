This project is a simulation of a smart home system, its built on a client server arithecture, for more details see the `./docs` directory.

# Running the program

This project uses [uv](https://docs.astral.sh/uv/getting-started/installation/), the following sections will assume you have it installed. 

<!-- TODO: Rember to update this when we implement the actual client-server parts. -->

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
