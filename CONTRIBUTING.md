# Contributing Guide

Thanks for contributing to **Investment Strategist**.

## Branching strategy

- `main` is the protected production-ready branch.
- Create feature/fix branches from `main`:
  - `feature/<short-name>`
  - `fix/<short-name>`
  - `chore/<short-name>`
- Keep pull requests focused and small.

## Commit conventions

Use clear, scoped commits. Suggested format:

```text
<type>(<scope>): <summary>
```

Examples:

- `feat(api): add simulation payload validation`
- `fix(etl): normalize MOEX close prices to float`
- `chore(ci): add dependency scan job`

## Pull request process

1. Sync with the latest `main`.
2. Run local quality checks:

```powershell
python -m black --check .
python -m isort --check-only .
python -m mypy .
python -m pytest
```

3. Open PR to `main` using the PR template.
4. Ensure CI is green before requesting review.
5. Address review feedback and keep history clean.

## Required quality gates

The CI workflow enforces:

- Black formatting check
- isort import order check
- mypy type checking
- pytest test suite

Dependency scanning (`pip-audit`) is also executed to surface vulnerabilities.

## Security and secrets

- Never commit `.env` or secrets.
- Use environment variables for sensitive configuration.
- Validate all external input in API and ETL paths.
- Keep dependencies updated (Dependabot is configured).

## Release process

- Create semantic tags like `v0.1.0`.
- Tag pushes trigger the Release workflow, which:
  - Re-runs quality gates
  - Builds a source archive
  - Publishes a GitHub Release
