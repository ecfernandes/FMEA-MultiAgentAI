# GitHub Security and Publish Guide

## What is already protected by `.gitignore`

The repository is configured to avoid committing common sensitive/local artifacts, including:
- API key files (`.env`, local secret files)
- Local vector store data (`data/vector_store/`)
- Virtual environment (`venv/`)
- IDE settings and caches (`.vscode/`, `__pycache__/`, `*.pyc`)

## Before pushing

### 1) Check for secrets in tracked files

```powershell
git grep -n "AIza"
git grep -n "api_key"
```

### 2) Review sample data

If `data/sample_documents/` contains sensitive project information, add it to `.gitignore` before pushing.

### 3) If a secret was committed

- Rotate/revoke the key immediately.
- Remove secret from repository history using an approved history-rewrite process.
- Force-push only if team/repository policy allows it.

## First push workflow

```powershell
# From repository root
git status
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

## Optional: GitHub Actions secret setup

1. Open repository `Settings` → `Secrets and variables` → `Actions`.
2. Add `UTCLLM_API_KEY` as a repository secret.

## Recommended repository defaults

- Enable branch protection on `main`
- Require pull requests for direct changes
- Enable secret scanning and Dependabot alerts
- Keep `.env` and local runtime data untracked
