# EOLib

[![PyPI - Version](https://img.shields.io/pypi/v/eolib.svg)](https://pypi.org/project/eolib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/eolib.svg)](https://pypi.org/project/eolib)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Cirras_eolib-python&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Cirras_eolib-python)
[![Lint](https://github.com/Cirras/eolib-python/actions/workflows/lint.yml/badge.svg?event=push)](https://github.com/Cirras/eolib-python/actions/workflows/lint.yml)

A core Python library for writing applications related to Endless Online.

## Installation

```console
pip install eolib
```

## Features

Read and write the following EO data structures:

- Client packets
- Server packets
- Endless Map Files (EMF)
- Endless Item Files (EIF)
- Endless NPC Files (ENF)
- Endless Spell Files (ESF)
- Endless Class Files (ECF)

Utilities:

- Data reader
- Data writer
- Number encoding
- String encoding
- Data encryption
- Packet sequencer

## Development

### Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Available Commands

| Command                       | Description                                            |
| ----------------------------- | ------------------------------------------------------ |
| `uv build`                    | Build package                                          |
| `uv run task test`            | Run unit tests with coverage                           |
| `uv run task format`          | Format source files using `black`                      |
| `uv run task format:check`    | Check formatting using `black`                         |
| `uv run task typing`          | Check typing using `mypy`                              |
| `uv run task docs:build`      | Build documentation using `mkdocs`                     |
| `uv run task docs:serve`      | Build and serve documentation using `mkdocs`           |
| `uv run task docs:deploy`     | Build and deploy documentation using `mkdocs` & `mike` |
| `uv run task release:prepare` | Prepare and tag a new release                          |
