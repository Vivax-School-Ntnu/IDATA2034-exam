This project is a simulation of a smart home system, its built on a client server arithecture, for more details see the `./docs` directory.

# Running the program

This project uses [uv](https://docs.astral.sh/uv/getting-started/installation/), the following sections will assume you have it installed. 

The easiest way to run the server and devices is using [docker-compose](https://docs.docker.com/compose/):
```bash
docker compose up --build
```

Afterwards in a seperate terminal you then run
```bash
uv run controller
```

You can also run multiple instances of the controller and they should all sync between eachother via the server!

## Running without server
The controller also lets you test its TUI without a running server using `--mock`
```bash
uv run controller --mock
```
