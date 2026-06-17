# Development Guide

## Setting Up a Development Environment

```bash
git clone https://github.com/rkriad585/localfs.git
cd localfs
pip install -e .
pip install ruff pytest build
```

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v --tb=short

# Specific test file
python -m pytest tests/test_main.py -v

# Specific test class
python -m pytest tests/test_main.py::TestIndexRoute -v

# With coverage
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Linting and Formatting

```bash
# Check code style
ruff check .

# Auto-format
ruff format .
```

## Project Structure

```
localfs/
├── src/
│   └── localfs/          # Python package
│       ├── __init__.py
│       ├── __main__.py    # `python -m localfs` entry point
│       ├── main.py        # Flask app, routes, helpers, CLI
│       ├── config.py      # Configuration constants
│       ├── theme.py       # Theme definitions and persistence
│       ├── templates/     # Jinja2 HTML templates
│       │   ├── base.html
│       │   ├── index.html
│       │   ├── player.html
│       │   ├── settings.html
│       │   ├── login.html
│       │   └── error.html
│       └── static/
│           ├── css/theme.css
│           ├── js/main.js
│           └── logo.svg
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Fixtures (test client, temp dirs)
│   ├── test_config.py
│   ├── test_main.py
│   └── test_theme.py
│

├── docs/                 # Documentation
├── pyproject.toml        # Project metadata
└── .version              # Version file
```

## Adding a New Route

1. Define the route function in `src/localfs/main.py`.
2. Create/update the Jinja2 template in `src/localfs/templates/`.
3. Add tests in `tests/test_main.py`.

## Adding a Configuration Option

1. Add the variable to `src/localfs/config.py`.
2. Reference it in `src/localfs/main.py` via `from . import config`.
3. Update `docs/configuration.md`.
4. Add a test in `tests/test_config.py`.

## Commit Conventions

We follow conventional commits:

```
feat: add new feature
fix: correct a bug
docs: update documentation
test: add or update tests
refactor: code restructuring
chore: build, CI, dependencies
```

## CI / Pre-merge Checklist

- [ ] Tests pass (`make test`)
- [ ] Linter passes (`make lint`)
- [ ] Code is formatted (`make format`)
- [ ] Documentation is updated (if applicable)
