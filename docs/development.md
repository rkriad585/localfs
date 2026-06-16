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
├── main.py              # Flask app, routes, helpers, CLI entry point
├── config.py            # Configuration constants
├── pyproject.toml       # Project metadata and scripts
│
├── templates/           # Jinja2 HTML templates
│   ├── index.html       # File grid
│   ├── player.html      # Media player
│   └── error.html       # Error pages
│
├── static/
│   ├── js/main.js       # Client-side search
│   └── logo.svg         # Project logo
│
├── tests/
│   ├── conftest.py      # Fixtures (test client, temp dirs)
│   ├── test_config.py   # Config tests
│   └── test_main.py     # Main app tests
│
└── docs/                # Documentation
```

## Adding a New Route

1. Define the route function in `main.py`.
2. Create/update the Jinja2 template in `templates/`.
3. Add tests in `tests/test_main.py`.

## Adding a Configuration Option

1. Add the variable to `config.py`.
2. Reference it in `main.py` via `import config`.
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
