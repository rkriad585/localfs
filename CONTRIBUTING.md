# Contributing to localfs

Thank you for considering contributing to localfs! We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code changes.

## How to Contribute

### Reporting Bugs

1. Check the [issues page](https://github.com/rkriad585/localfs/issues) to see if the bug has already been reported.
2. If not, open a new issue with:
   - A clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

Open an issue describing the feature, why it's useful, and how it might work. Feature requests are always welcome.

### Code Contributions

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes. Follow the existing code style — run `make lint` and `make format`.
4. Add or update tests. Run `make test` to verify everything passes.
5. Commit with a clear message:
   ```bash
   git commit -m "feat: add your feature description"
   ```
6. Push to your fork and open a pull request.

### Pull Request Guidelines

- Keep changes focused — one feature or fix per PR.
- Write a clear PR description explaining what and why.
- Ensure all tests pass.
- Update documentation if needed.

### Development Setup

```bash
git clone https://github.com/rkriad585/localfs.git
cd localfs
pip install -e .
pip install ruff pytest build
make test
```

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for both linting and formatting. Run before committing:

```bash
make lint
make format
```

## Questions?

Open a [discussion](https://github.com/rkriad585/localfs/discussions) or issue.
