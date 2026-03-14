# GitHub Repository Setup Guide

This guide helps you publish your existing local Git repository to GitHub and enable the CI/CD baseline included in this project.

## 1) Create a new empty GitHub repository

1. Open GitHub and create a new repository.
2. Do **not** initialize it with README/.gitignore/license (your local project already has files).
3. Copy the repository URL (HTTPS or SSH).

## 2) Connect local repository to GitHub

Run from project root:

```powershell
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```

If `origin` already exists, update it:

```powershell
git remote set-url origin <YOUR_GITHUB_REPO_URL>
```

## 3) Verify GitHub Actions pipelines

After the first push, open **GitHub → Actions** and confirm these workflows are available:

- `CI` (`.github/workflows/ci.yml`)
- `Release` (`.github/workflows/release.yml`)

## 4) Enable branch protection for `main`

In **Settings → Branches → Add branch protection rule** for `main`:

- Require a pull request before merging
- Require approvals (recommended: at least 1)
- Require status checks to pass before merging:
  - `Lint (black + isort)`
  - `Type check (mypy)`
  - `Test (pytest)`
- Restrict direct pushes to `main`

## 5) Enable dependency and security automation

Already configured in repository files:

- Dependabot updates: `.github/dependabot.yml`
- Dependency vulnerability scan in CI: `pip-audit` job

Also enable in GitHub settings if available:

- **Code security and analysis → Dependabot alerts**
- **Code security and analysis → Dependabot security updates**

## 6) Open pull requests using the template

PR template file: `.github/pull_request_template.md`

This standardizes:

- Change summary
- Validation checklist
- Security checklist

## 7) Create a release (CD baseline)

Tagging a version triggers the release workflow:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Release workflow behavior:

1. Runs quality gates (black, isort, mypy, pytest)
2. Builds source archive artifact
3. Publishes a GitHub Release

## Notes

- Keep secrets out of the repository (`.env` is ignored).
- Use small feature branches and frequent pull requests.
- Keep CI green before merging to `main`.
