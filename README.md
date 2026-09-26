# karafun-intercept

A [Textual](https://textual.textualize.io/) terminal user interface (TUI) application.

## Requirements

- Python >= 3.9
- [Textual](https://textual.textualize.io/) (installed automatically)

## Installation

```bash
pip install -e .
```

## Running

```bash
# from a terminal
karafun-intercept
```

Or with `uv`:

```bash
uv run karafun-intercept
```

## Development

- Lint: `ruff check --fix`
- Test: `pytest` (tests must pass with `-W error`)
